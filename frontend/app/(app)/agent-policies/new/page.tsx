"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { Form } from "@/components/Form";
import { AgentRuleBuilder } from "@/components/AgentRuleBuilder";
import { createAgentPolicy, listAgents } from "@/lib/agent_api";
import type { Agent } from "@/lib/agent_types";

export default function NewAgentPolicyPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [scope, setScope] = useState<"all" | number>("all");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [priority, setPriority] = useState(100);
  const [rules, setRules] = useState<Record<string, unknown>>({});
  const [mode, setMode] = useState<"visual" | "json">("visual");
  const [jsonText, setJsonText] = useState("{}");
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  React.useEffect(() => {
    listAgents().then(setAgents).catch(() => {});
  }, []);

  // when switching to JSON, seed it from the visual rules; when leaving
  // JSON, parse it back so both stay in sync.
  function switchMode(next: "visual" | "json") {
    if (next === "json") {
      setJsonText(JSON.stringify(rules, null, 2));
      setJsonError(null);
    } else {
      try {
        setRules(JSON.parse(jsonText || "{}"));
        setJsonError(null);
      } catch {
        setJsonError(t("rulebuilder.json_invalid"));
        return; // stay in JSON until it's valid
      }
    }
    setMode(next);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    let finalRules = rules;
    if (mode === "json") {
      try {
        finalRules = JSON.parse(jsonText || "{}");
      } catch {
        setJsonError(t("rulebuilder.json_invalid"));
        return;
      }
    }

    setSubmitting(true);
    try {
      await createAgentPolicy({
        name,
        agent_id: scope === "all" ? null : scope,
        rules: finalRules,
        priority,
        enabled: true,
      });
      router.push("/agent-policies");
    } catch {
      setError(t("agent_policies.create_failed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHeader title={t("agent_policies.new")} />
      <div className="content">
        <div className="panel">
          <div className="panel-body">
            <Form onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="field">
                  <label>{t("agent_policies.name")}</label>
                  <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="no-finance-tools" />
                </div>
                <div className="field">
                  <label>{t("agent_policies.scope")}</label>
                  <select value={String(scope)} onChange={(e) => setScope(e.target.value === "all" ? "all" : Number(e.target.value))}>
                    <option value="all">{t("agent_policies.all_agents")}</option>
                    {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </select>
                </div>
              </div>
              <div className="field">
                <label>{t("agent_policies.priority")}</label>
                <input type="number" value={priority} onChange={(e) => setPriority(Number(e.target.value))} style={{ maxWidth: 140 }} />
                <p className="hint-text">{t("agent_policies.priority_hint")}</p>
              </div>

              {/* mode toggle */}
              <div className="field">
                <label>{t("agent_policies.rules")}</label>
                <div style={{ display: "inline-flex", gap: 4, marginBottom: 12, border: "1px solid var(--border)", borderRadius: 8, padding: 3 }}>
                  <button type="button" onClick={() => switchMode("visual")}
                    className="btn btn-sm" style={{ background: mode === "visual" ? "var(--bg-app)" : "transparent" }}>
                    {t("rulebuilder.mode_visual")}
                  </button>
                  <button type="button" onClick={() => switchMode("json")}
                    className="btn btn-sm" style={{ background: mode === "json" ? "var(--bg-app)" : "transparent" }}>
                    {t("rulebuilder.mode_json")}
                  </button>
                </div>

                {mode === "visual" ? (
                  <AgentRuleBuilder value={rules} onChange={setRules} />
                ) : (
                  <>
                    <textarea
                      value={jsonText}
                      onChange={(e) => setJsonText(e.target.value)}
                      rows={8}
                      style={{ width: "100%", fontFamily: "monospace", fontSize: 13 }}
                    />
                    {jsonError && <p className="error-text">{jsonError}</p>}
                  </>
                )}
              </div>

              {error && <p className="error-text">{error}</p>}
              <button className="btn btn-primary" type="submit" disabled={submitting}>
                {submitting ? t("common.loading") : t("agent_policies.create")}
              </button>
            </Form>
          </div>
        </div>
      </div>
    </>
  );
}
