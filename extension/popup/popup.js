// Popup: shows current-tab status and lets the user view/set the
// server URL and ingestion key (needed when the extension is installed
// manually rather than via the server's preconfigured download).

// ---- current tab status ---------------------------------------------
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  const statusEl = document.getElementById("current-tab-status");
  if (!tabs || !tabs[0] || !tabs[0].url) {
    statusEl.textContent = "No active page";
    return;
  }
  try {
    const host = new URL(tabs[0].url).hostname;
    const aiTool = lookupDomain(host);
    if (aiTool) {
      statusEl.textContent = "\u26A0\uFE0F " + aiTool.name + " (risk " + aiTool.risk + ")";
      statusEl.style.color = "#dc2626";
    } else {
      statusEl.textContent = "Standard website (" + host + ")";
      statusEl.style.color = "#64748b";
    }
  } catch (e) {
    statusEl.textContent = "Unknown";
  }
});

// ---- connection state + settings form -------------------------------
const apiUrlInput = document.getElementById("api-url");
const keyInput = document.getElementById("ingestion-key");
const saveBtn = document.getElementById("save-btn");
const saveStatus = document.getElementById("save-status");
const configState = document.getElementById("config-state");

function renderConfigState(hasKey) {
  if (hasKey) {
    configState.textContent = "\u2713 Configured and reporting";
    configState.className = "config-state config-ok";
  } else {
    configState.textContent = "\u2717 Not configured \u2014 enter your ingestion key below";
    configState.className = "config-state config-missing";
  }
}

chrome.storage.local.get(["apiUrl", "ingestionKey"], (stored) => {
  if (stored.apiUrl) apiUrlInput.value = stored.apiUrl;
  if (stored.ingestionKey) {
    // Don't echo the real key back into a readable field; show a masked
    // placeholder so the user knows one is set without exposing it.
    keyInput.placeholder = "\u2022\u2022\u2022\u2022 key saved \u2014 type to replace";
  }
  renderConfigState(Boolean(stored.ingestionKey));
});

saveBtn.addEventListener("click", () => {
  const apiUrl = apiUrlInput.value.trim();
  const key = keyInput.value.trim();

  const toSave = {};
  if (apiUrl) toSave.apiUrl = apiUrl;
  // Only overwrite the stored key if the user actually typed a new one,
  // so re-saving just the URL doesn't wipe an existing key.
  if (key) toSave.ingestionKey = key;

  chrome.storage.local.set(toSave, () => {
    saveStatus.textContent = "Saved";
    keyInput.value = "";
    chrome.storage.local.get(["ingestionKey"], (s) => renderConfigState(Boolean(s.ingestionKey)));
    setTimeout(() => (saveStatus.textContent = ""), 2000);
  });
});
