"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { Form } from "@/components/Form";
import { registerAgent } from "@/lib/agent_api";
import type { AgentCreated } from "@/lib/agent_types";

// small helper: comma/space separated string -> string[]
function toList(s: string): string[] {
  return s.split(/[,\n]/).map((x) => x.trim()).filter(Boolean);
}

export default function NewAgentPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [agentType, setAgentType] = useState("custom");
  const [ownerTeam, setOwnerTeam] = useState("");
  const [capabilities, setCapabilities] = useState("");
  const [tools, setTools] = useState("");
  const [models, setModels] = useState("");
  const [depth, setDepth] = useState(3);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<AgentCreated | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);
  const [copiedPriv, setCopiedPriv] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const agent = await registerAgent({
        name,
        agent_type: agentType,
        owner_team: ownerTeam || undefined,
        capabilities: toList(capabilities),
        allowed_tools: toList(tools),
        allowed_models: toList(models),
        max_delegation_depth: depth,
      });
      setCreated(agent);
    } catch {
      setError(t("agents.register_failed"));
    } finally {
      setSubmitting(false);
    }
  }

  async function copy(text: string, which: "key" | "priv") {
    try {
      await navigator.clipboard.writeText(text);
      if (which === "key") setCopiedKey(true);
      else setCopiedPriv(true);
    } catch {
      /* clipboard may be unavailable; value is still visible */
    }
  }

  if (created) {
    return (
      <>
        <PageHeader title={t("agents.registered_title")} />
        <div className="content">
          <div className="panel" style={{ borderColor: "var(--danger, #c0392b)" }}>
            <div className="panel-header"><h2>{t("agents.secrets_title")}</h2></div>
            <div className="panel-body">
              <p className="error-text" style={{ marginBottom: 14 }}>
                {t("agents.secrets_warning")}
              </p>

              <div className="field">
                <label>{t("agents.api_key")}</label>
                <div className="form-row" style={{ alignItems: "center" }}>
                  <code className="mono" style={{ wordBreak: "break-all", flex: 1 }}>{created.api_key}</code>
                  <button type="button" className="btn btn-sm" onClick={() => copy(created.api_key, "key")}>
                    {copiedKey ? t("agents.copied") : t("agents.copy")}
                  </button>
                </div>
              </div>

              <div className="field" style={{ marginTop: 12 }}>
                <label>{t("agents.private_key")}</label>
                <div className="form-row" style={{ alignItems: "center" }}>
                  <code className="mono" style={{ wordBreak: "break-all", flex: 1 }}>{created.private_key}</code>
                  <button type="button" className="btn btn-sm" onClick={() => copy(created.private_key, "priv")}>
                    {copiedPriv ? t("agents.copied") : t("agents.copy")}
                  </button>
                </div>
                <p className="hint-text" style={{ marginTop: 6 }}>{t("agents.private_key_note")}</p>
              </div>

              <button className="btn btn-primary" style={{ marginTop: 18 }} onClick={() => router.push("/agents")}>
                {t("agents.done")}
              </button>
            </div>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader title={t("agents.register")} />
      <div className="content">
        <div className="panel">
          <div className="panel-body">
            <Form onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="field">
                  <label>{t("agents.name")}</label>
                  <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="marketing-assistant" />
                </div>
                <div className="field">
                  <label>{t("agents.type")}</label>
                  <select value={agentType} onChange={(e) => setAgentType(e.target.value)}>
                    <option value="crewai">CrewAI</option>
                    <option value="langgraph">LangGraph</option>
                    <option value="autogen">AutoGen</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
              </div>
              <div className="field">
                <label>{t("agents.owner_team")}</label>
                <input value={ownerTeam} onChange={(e) => setOwnerTeam(e.target.value)} placeholder="marketing" />
              </div>
              <div className="field">
                <label>{t("agents.capabilities")}</label>
                <input value={capabilities} onChange={(e) => setCapabilities(e.target.value)} placeholder="read_analytics, generate_text" />
                <p className="hint-text">{t("agents.comma_hint")}</p>
              </div>
              <div className="field">
                <label>{t("agents.tools")}</label>
                <input value={tools} onChange={(e) => setTools(e.target.value)} placeholder="openai.chat, google.analytics.read" />
              </div>
              <div className="field">
                <label>{t("agents.models")}</label>
                <input value={models} onChange={(e) => setModels(e.target.value)} placeholder="gpt-4o-mini" />
              </div>
              <div className="field">
                <label>{t("agents.max_depth")}</label>
                <input type="number" min={0} max={10} value={depth} onChange={(e) => setDepth(Number(e.target.value))} />
              </div>
              {error && <p className="error-text">{error}</p>}
              <button className="btn btn-primary" type="submit" disabled={submitting}>
                {submitting ? t("agents.registering") : t("agents.register")}
              </button>
            </Form>
          </div>
        </div>
      </div>
    </>
  );
}
