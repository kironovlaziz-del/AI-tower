"use client";

import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { listAgentIncidents, getEscalationSummary } from "@/lib/agent_api";
import type { AgentIncidentT, EscalationSummaryRow } from "@/lib/agent_types";

export default function AgentIncidentsPage() {
  const { t } = useTranslation();
  const [incidents, setIncidents] = useState<AgentIncidentT[]>([]);
  const [summary, setSummary] = useState<EscalationSummaryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [unresolvedOnly, setUnresolvedOnly] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string>("capability_escalation");

  async function load() {
    setLoading(true);
    try {
      const [inc, sum] = await Promise.all([
        listAgentIncidents({
          incident_type: typeFilter,
          unresolved_only: unresolvedOnly,
          limit: 100,
        }),
        getEscalationSummary(),
      ]);
      setIncidents(inc.items || []);
      setSummary(sum.agents || []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [unresolvedOnly, typeFilter]);

  const caps = (inc: AgentIncidentT, key: string): string[] => {
    const d = (inc.details || {}) as Record<string, unknown>;
    const v = d[key];
    return Array.isArray(v) ? (v as string[]) : [];
  };

  return (
    <>
      <PageHeader title={t("agent_incidents.title")} />
      <div className="content">
        <p className="hint-text u-mb-16">{t("agent_incidents.hint")}</p>

        <div className="panel u-mb-16">
          <div className="panel-header"><h2>{t("agent_incidents.repeat_offenders")}</h2></div>
          <div style={{ padding: 12 }}>
            {loading && <div className="hint-text">{t("common.loading")}</div>}
            {!loading && summary.length === 0 && (
              <div className="hint-text">{t("agent_incidents.no_escalations")}</div>
            )}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
              {summary.map((row) => (
                <div key={row.agent_id} style={{
                  border: "1px solid var(--border)", borderRadius: 8, padding: "10px 14px", minWidth: 160,
                  background: row.attempts >= 3 ? "#fdecec" : "var(--bg-app)",
                }}>
                  <div style={{ fontWeight: 600 }}>{t("agent_incidents.agent")} #{row.agent_id}</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: row.attempts >= 3 ? "#c0392b" : "var(--text-primary)" }}>
                    {row.attempts} {t("agent_incidents.attempts")}
                  </div>
                  {row.last_attempt && (
                    <div className="hint-text" style={{ fontSize: 11 }}>
                      {t("agent_incidents.last")}: {new Date(row.last_attempt).toLocaleString()}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2>{t("agent_incidents.rejected_escalations")}</h2>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} style={{ fontSize: 13 }}>
                <option value="capability_escalation">{t("agent_incidents.type_capability")}</option>
                <option value="ttl_escalation">{t("agent_incidents.type_ttl")}</option>
                <option value="delegation_expired">{t("agent_incidents.type_expired")}</option>
                <option value="depth_exceeded">{t("agent_incidents.type_depth")}</option>
              </select>
              <label className="hint-text" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                <input type="checkbox" checked={unresolvedOnly} onChange={(e) => setUnresolvedOnly(e.target.checked)} />
                {t("agent_incidents.unresolved_only")}
              </label>
            </div>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>{t("agent_incidents.agent")}</th>
                  <th>{t("agent_incidents.over_requested")}</th>
                  <th>{t("agent_incidents.parent_had")}</th>
                  <th>{t("agent_incidents.chain")}</th>
                  <th>{t("agent_incidents.when")}</th>
                </tr>
              </thead>
              <tbody>
                {!loading && incidents.length === 0 && (
                  <tr><td colSpan={5} className="hint-text" style={{ textAlign: "center", padding: 20 }}>
                    {t("agent_incidents.no_escalations")}
                  </td></tr>
                )}
                {incidents.map((inc) => (
                  <tr key={inc.id}>
                    <td>#{inc.agent_id}</td>
                    <td>
                      {caps(inc, "escalated").map((c) => (
                        <span key={c} style={{
                          display: "inline-block", background: "#fdecec", color: "#c0392b",
                          borderRadius: 4, padding: "2px 8px", marginRight: 4, fontSize: 12, fontFamily: "monospace",
                        }}>{c}</span>
                      ))}
                    </td>
                    <td className="hint-text mono" style={{ fontSize: 12 }}>
                      {caps(inc, "parent_had").join(", ") || "—"}
                    </td>
                    <td className="hint-text">{inc.chain_id ? `#${inc.chain_id}` : "—"}</td>
                    <td className="hint-text" style={{ fontSize: 12 }}>{new Date(inc.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
