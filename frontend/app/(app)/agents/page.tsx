"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { listAgents, killAgent } from "@/lib/agent_api";
import type { Agent } from "@/lib/agent_types";

function statusClass(s: string): string {
  switch (s) {
    case "active":
      return "pill-low";
    case "suspended":
      return "pill-critical";
    case "retired":
      return "pill-neutral";
    default:
      return "pill-neutral";
  }
}

export default function AgentsPage() {
  const { t, i18n } = useTranslation();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);

  function refresh() {
    setLoading(true);
    listAgents()
      .then(setAgents)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleKill(a: Agent) {
    const reason = window.prompt(t("agents.kill_prompt", { name: a.name }) as string);
    if (reason === null) return; // cancelled
    setBusyId(a.id);
    try {
      await killAgent(a.id, reason || "manual kill", true);
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <PageHeader
        title={t("agents.title")}
        actions={
          <Link href="/agents/new" className="btn btn-primary btn-sm">
            {t("agents.register")}
          </Link>
        }
      />
      <div className="content">
        <p className="hint-text u-mb-16">{t("agents.hint")}</p>

        <div style={{ display: "flex", gap: 10, marginBottom: 18, flexWrap: "wrap" }}>
          <Link href="/agent-chains" className="btn btn-sm">{t("agents.view_chains")}</Link>
        </div>

        <div className="panel">
          <div className="panel-header"><h2>{t("agents.table_title")}</h2></div>
          <table>
            <thead>
              <tr>
                <th>{t("agents.col_name")}</th>
                <th>{t("agents.col_type")}</th>
                <th>{t("agents.col_tools")}</th>
                <th>{t("agents.col_depth")}</th>
                <th>{t("agents.col_status")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr className="empty-row"><td colSpan={6}>{t("common.loading")}</td></tr>}
              {!loading && agents.length === 0 && (
                <tr className="empty-row"><td colSpan={6}>{t("agents.empty")}</td></tr>
              )}
              {agents.map((a) => (
                <tr key={a.id}>
                  <td>
                    <Link href={`/agents/${a.id}`} style={{ fontWeight: 600 }}>{a.name}</Link>
                    {a.owner_team && (
                      <div className="hint-text" style={{ fontSize: 11 }}>{a.owner_team}</div>
                    )}
                  </td>
                  <td>{a.agent_type || "—"}</td>
                  <td className="mono" style={{ fontSize: 11 }}>
                    {(a.allowed_tools || []).join(", ") || "—"}
                  </td>
                  <td>{a.max_delegation_depth}</td>
                  <td>
                    <span className={`pill ${statusClass(a.status)}`}>
                      {t(`agents.status_${a.status}`, a.status)}
                    </span>
                  </td>
                  <td className="u-nowrap">
                    {a.status !== "suspended" && (
                      <button
                        className="btn btn-sm btn-danger"
                        disabled={busyId === a.id}
                        onClick={() => handleKill(a)}
                      >
                        {t("agents.kill")}
                      </button>
                    )}
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
