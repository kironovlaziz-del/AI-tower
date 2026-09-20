"use client";

import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { listAuditLogs } from "@/lib/api";
import type { AuditLog } from "@/lib/types";

const ENTITY_TYPES = [
  "organization",
  "user",
  "policy",
  "policy_version",
  "use_case",
  "provider",
  "request",
  "approval",
  "incident",
];

const ACTION_CLASS: Record<string, string> = {
  created: "pill-accent",
  registered: "pill-accent",
  updated: "pill-medium",
  approved: "pill-low",
  rejected: "pill-critical",
  blocked: "pill-critical",
};

function ActionPill({ action }: { action: string }) {
  return (
    <span className={`pill ${ACTION_CLASS[action] ?? "pill-neutral"}`}>{action}</span>
  );
}

export default function AuditLogsPage() {
  const { t, i18n } = useTranslation();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [entityType, setEntityType] = useState("");
  const [auditPage, setAuditPage] = useState(0);
  const AUDIT_PAGE_SIZE = 12;

  function refresh(filterType: string) {
    setLoading(true);
    listAuditLogs(filterType ? { entity_type: filterType } : undefined)
      .then((data) => { setLogs(data); setAuditPage(0); })
      .finally(() => setLoading(false));
  }

  useEffect(() => refresh(entityType), [entityType]);

  return (
    <>
      <PageHeader title={t("audit.title")} />
      <div className="content">
        <div className="panel">
          <div className="panel-header">
            <h2>{t("audit.table_title")}</h2>
            <select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              style={{
                border: "1px solid var(--border-strong)",
                borderRadius: 4,
                padding: "5px 8px",
              }}
            >
              <option value="">{t("audit.filter_all")}</option>
              {ENTITY_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>
          <table>
            <thead>
              <tr>
                <th>{t("audit.col_time")}</th>
                <th>{t("audit.col_entity")}</th>
                <th>{t("audit.col_id")}</th>
                <th>{t("audit.col_action")}</th>
                <th>{t("audit.col_user")}</th>
                <th>{t("audit.col_details")}</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={6}>{t("audit.loading")}</td>
                </tr>
              )}
              {!loading && logs.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={6}>{t("audit.empty")}</td>
                </tr>
              )}
              {logs.slice(auditPage * AUDIT_PAGE_SIZE, auditPage * AUDIT_PAGE_SIZE + AUDIT_PAGE_SIZE).map((log) => (
                <tr key={log.id}>
                  <td className="mono">
                    {new Date(log.created_at).toLocaleString(i18n.language)}
                  </td>
                  <td className="mono">{log.entity_type}</td>
                  <td className="mono">{log.entity_id ?? "—"}</td>
                  <td>
                    <ActionPill action={log.action} />
                  </td>
                  <td className="mono">
                    {log.actor_user_id != null
                      ? `#${log.actor_user_id}`
                      : t("audit.system_user")}
                  </td>
                  <td className="mono" style={{ maxWidth: 360, overflowWrap: "anywhere" }}>
                    {log.metadata_json ? JSON.stringify(log.metadata_json) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {logs.length > AUDIT_PAGE_SIZE && (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 4px", fontSize: 13 }}>
              <button type="button" className="btn btn-sm" disabled={auditPage === 0} onClick={() => setAuditPage((p) => Math.max(0, p - 1))}>{t("common.prev")}</button>
              <span className="hint-text">{auditPage * AUDIT_PAGE_SIZE + 1}-{Math.min((auditPage + 1) * AUDIT_PAGE_SIZE, logs.length)} / {logs.length}</span>
              <button type="button" className="btn btn-sm" disabled={(auditPage + 1) * AUDIT_PAGE_SIZE >= logs.length} onClick={() => setAuditPage((p) => p + 1)}>{t("common.next")}</button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}