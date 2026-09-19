"use client";

import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { listAgentActions, approveAgentAction, denyAgentAction, listAgents } from "@/lib/agent_api";
import type { AgentActionT, Agent } from "@/lib/agent_types";

export default function AgentApprovalsPage() {
  const { t, i18n } = useTranslation();
  const [pending, setPending] = useState<AgentActionT[]>([]);
  const [agentNames, setAgentNames] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);

  function refresh() {
    setLoading(true);
    Promise.all([listAgentActions({ result: "pending_approval" }), listAgents()])
      .then(([acts, agents]) => {
        setPending(acts);
        const names: Record<number, string> = {};
        (agents as Agent[]).forEach((a) => (names[a.id] = a.name));
        setAgentNames(names);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  const nameOf = (id: number) => agentNames[id] || `agent#${id}`;

  async function handleApprove(id: number) {
    setBusyId(id);
    try {
      await approveAgentAction(id);
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  async function handleDeny(id: number) {
    const reason = window.prompt(t("agent_approvals.deny_prompt") as string);
    if (reason === null) return;
    setBusyId(id);
    try {
      await denyAgentAction(id, reason || undefined);
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <PageHeader title={t("agent_approvals.title")} />
      <div className="content">
        <p className="hint-text u-mb-16">{t("agent_approvals.hint")}</p>
        <div className="panel">
          <div className="panel-header"><h2>{t("agent_approvals.pending")}</h2></div>
          <table>
            <thead>
              <tr>
                <th>{t("agent_approvals.col_time")}</th>
                <th>{t("agent_approvals.col_agent")}</th>
                <th>{t("agent_approvals.col_tool")}</th>
                <th>{t("agent_approvals.col_reason")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr className="empty-row"><td colSpan={5}>{t("common.loading")}</td></tr>}
              {!loading && pending.length === 0 && (
                <tr className="empty-row"><td colSpan={5}>{t("agent_approvals.empty")}</td></tr>
              )}
              {pending.map((a) => (
                <tr key={a.id}>
                  <td className="mono" style={{ fontSize: 12 }}>{new Date(a.created_at).toLocaleString(i18n.language)}</td>
                  <td>{nameOf(a.agent_id)}</td>
                  <td className="mono" style={{ fontSize: 12 }}>{a.tool_name}</td>
                  <td className="hint-text" style={{ fontSize: 12, maxWidth: 320 }}>{a.reason || "—"}</td>
                  <td className="u-nowrap">
                    <div style={{ display: "inline-flex", gap: 6 }}>
                      <button className="btn btn-sm btn-primary" disabled={busyId === a.id} onClick={() => handleApprove(a.id)}>
                        {t("agent_approvals.approve")}
                      </button>
                      <button className="btn btn-sm btn-danger" disabled={busyId === a.id} onClick={() => handleDeny(a.id)}>
                        {t("agent_approvals.deny")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
