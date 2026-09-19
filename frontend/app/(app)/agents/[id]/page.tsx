"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { getAgent, listAgentActions } from "@/lib/agent_api";
import type { Agent, AgentActionT } from "@/lib/agent_types";

export default function AgentDetailPage() {
  const params = useParams<{ id: string }>();
  const agentId = Number(params.id);
  const { t, i18n } = useTranslation();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [actions, setActions] = useState<AgentActionT[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getAgent(agentId), listAgentActions({ agent_id: agentId })])
      .then(([a, acts]) => {
        setAgent(a);
        setActions(acts);
      })
      .finally(() => setLoading(false));
  }, [agentId]);

  if (loading) return <div className="content"><p className="hint-text">{t("common.loading")}</p></div>;
  if (!agent) return <div className="content"><p className="hint-text">{t("agents.not_found")}</p></div>;

  const chips = (label: string, values?: string[] | null) => (
    <div className="field">
      <label>{label}</label>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {(values && values.length > 0)
          ? values.map((v) => (
              <span key={v} className="pill pill-neutral mono" style={{ fontSize: 11 }}>{v}</span>
            ))
          : <span className="hint-text">—</span>}
      </div>
    </div>
  );

  return (
    <>
      <PageHeader title={`🤖 ${agent.name}`} />
      <div className="content">
        <Link href="/agents" className="btn btn-sm" style={{ marginBottom: 16 }}>← {t("agents.back")}</Link>

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-body">
            <div style={{ display: "flex", gap: 24, flexWrap: "wrap", marginBottom: 12 }}>
              <div><div className="hint-text">{t("agents.col_type")}</div><strong>{agent.agent_type || "—"}</strong></div>
              <div><div className="hint-text">{t("agents.col_status")}</div><strong>{t(`agents.status_${agent.status}`, agent.status)}</strong></div>
              <div><div className="hint-text">{t("agents.col_depth")}</div><strong>{agent.max_delegation_depth}</strong></div>
              <div><div className="hint-text">{t("agents.owner_team")}</div><strong>{agent.owner_team || "—"}</strong></div>
            </div>
            {chips(t("agents.capabilities"), agent.capabilities)}
            {chips(t("agents.tools"), agent.allowed_tools)}
            {chips(t("agents.models"), agent.allowed_models)}
            {agent.public_key && (
              <div className="field">
                <label>{t("agents.public_key")}</label>
                <code className="mono" style={{ fontSize: 11, wordBreak: "break-all" }}>{agent.public_key}</code>
              </div>
            )}
          </div>
        </div>

        <h2 style={{ fontSize: 15, marginBottom: 12 }}>{t("agents.recent_actions")}</h2>
        <div className="panel">
          <table>
            <thead>
              <tr>
                <th>{t("chains.tl_time")}</th>
                <th>{t("chains.tl_tool")}</th>
                <th>{t("chains.tl_result")}</th>
                <th>{t("chains.tl_reason")}</th>
              </tr>
            </thead>
            <tbody>
              {actions.length === 0 && <tr className="empty-row"><td colSpan={4}>{t("chains.no_actions")}</td></tr>}
              {actions.map((a) => (
                <tr key={a.id}>
                  <td className="mono" style={{ fontSize: 12 }}>{new Date(a.created_at).toLocaleString(i18n.language)}</td>
                  <td className="mono" style={{ fontSize: 12 }}>{a.tool_name}</td>
                  <td><span className={`pill ${a.policy_check_result === "denied" ? "pill-critical" : "pill-low"}`}>{a.policy_check_result}</span></td>
                  <td className="hint-text" style={{ fontSize: 12 }}>{a.reason || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
