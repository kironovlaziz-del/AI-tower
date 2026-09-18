// Background Service Worker
//
// Responsibilities:
//   - detect navigation to known AI services (domain_visit events)
//   - receive PII-paste reports from the content script
//   - batch events and flush them to the AI Control Tower backend
//
// The API URL and ingestion key are NOT hardcoded here to real values:
// they are injected at download time by the server's
// /shadow-ai/extension/download endpoint (which bakes in a fresh,
// org-scoped key), or set by the user in the popup. The defaults below
// are inert placeholders so a raw checkout never carries a working key.

importScripts("../shared/domains.js");

const PLACEHOLDER_CONFIG = {
  apiUrl: "http://localhost:8000/api/v1/shadow-ai/ingest",
  ingestionKey: "" // intentionally empty - see note above
};

// ---- stable per-install agent id -------------------------------------
// Generated once and persisted, so the same browser install reports the
// same agent_id across service-worker restarts (the worker is torn down
// and respawned frequently in MV3). A random-per-load id would make one
// browser look like many different agents.
async function getAgentId() {
  const { agentId } = await chrome.storage.local.get("agentId");
  if (agentId) return agentId;
  const fresh = "browser-ext-" + crypto.randomUUID();
  await chrome.storage.local.set({ agentId: fresh });
  return fresh;
}

async function getConfig() {
  const stored = await chrome.storage.local.get(["apiUrl", "ingestionKey"]);
  return {
    apiUrl: stored.apiUrl || PLACEHOLDER_CONFIG.apiUrl,
    ingestionKey: stored.ingestionKey || PLACEHOLDER_CONFIG.ingestionKey
  };
}

// ---- batching --------------------------------------------------------
// Events are queued and flushed together, rather than one HTTP request
// per event (which, despite the old function being named sendBatch,
// is what the previous version actually did). Flush triggers on either a
// size threshold or a short timer, whichever comes first.
const BATCH_MAX = 25;
const BATCH_INTERVAL_MS = 5000;

let queue = [];
let flushTimer = null;

function enqueue(event) {
  queue.push(event);
  if (queue.length >= BATCH_MAX) {
    flush();
  } else if (!flushTimer) {
    flushTimer = setTimeout(flush, BATCH_INTERVAL_MS);
  }
}

async function flush() {
  if (flushTimer) {
    clearTimeout(flushTimer);
    flushTimer = null;
  }
  if (queue.length === 0) return;

  const batch = queue;
  queue = [];

  const config = await getConfig();
  if (!config.ingestionKey) {
    // No key configured yet - drop rather than spamming a doomed request.
    // The popup tells the user to configure the extension.
    console.warn("[AI-CT] No ingestion key configured; " + batch.length + " event(s) not sent.");
    return;
  }

  try {
    const response = await fetch(config.apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Ingestion-Key": config.ingestionKey
      },
      body: JSON.stringify({ events: batch })
    });
    console.log("[AI-CT] Batch sent (" + batch.length + " events), status: " + response.status);
  } catch (err) {
    console.warn("[AI-CT] Failed to report telemetry:", err);
  }
}

// ---- event construction ----------------------------------------------
async function buildEvent(partial) {
  const agentId = await getAgentId();
  return {
    event_id: crypto.randomUUID(),
    event_type: partial.event_type || "domain_visit",
    agent_id: agentId,
    domain: partial.domain || "",
    risk_score: typeof partial.risk_score === "number" ? partial.risk_score : 0.5,
    action_taken: partial.action_taken || "monitored",
    payload: partial.payload || {},
    timestamp: new Date().toISOString()
  };
}

// ---- content-script messages (PII paste reports) ---------------------
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message && message.action === "report_event") {
    buildEvent(message).then(enqueue);
    sendResponse({ status: "queued" });
  }
  return false;
});

// ---- navigation to known AI services ---------------------------------
// Dedup: chrome.tabs.onUpdated fires "complete" more than once per real
// navigation (subframes, history updates). We remember the last host
// reported per tab and skip repeats, so one visit is one event.
const lastReportedHostByTab = {};

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status !== "complete" || !tab || !tab.url) return;

  let host;
  try {
    host = new URL(tab.url).hostname;
  } catch (e) {
    return;
  }

  const aiTool = lookupDomain(host);
  if (!aiTool) {
    // Left an AI site (or navigated to a non-AI one) - clear the memo so
    // a later return to the same AI host reports again.
    if (lastReportedHostByTab[tabId]) delete lastReportedHostByTab[tabId];
    return;
  }

  if (lastReportedHostByTab[tabId] === host) return; // already reported
  lastReportedHostByTab[tabId] = host;

  buildEvent({
    event_type: "domain_visit",
    domain: host,
    risk_score: aiTool.risk,
    action_taken: "monitored",
    payload: { tool_name: aiTool.name, category: aiTool.category }
    // NOTE: the full tab.url is deliberately NOT sent - the path/query of
    // an AI-tool URL can itself contain sensitive content. The host is
    // enough to record "this AI service was used".
  }).then(enqueue);
});

// Clean up the per-tab memo when a tab closes, to avoid unbounded growth.
chrome.tabs.onRemoved.addListener((tabId) => {
  delete lastReportedHostByTab[tabId];
});
