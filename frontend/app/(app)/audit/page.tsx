"use client";

import React, { useEffect, useState } from "react";
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
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [entityType, setEntityType] = useState("");

  function refresh(filterType: string) {
    setLoading(true);
    listAuditLogs(filterType ? { entity_type: filterType } : undefined)
      .then(setLogs)
      .finally(() => setLoading(false));
  }

  useEffect(() => refresh(entityType), [entityType]);

  return (
    <>
      <PageHeader title="Audit & Reporting" />
      <div className="content">
        <div className="panel">
          <div className="panel-header">
            <h2>Журнал действий</h2>
            <select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              style={{
                border: "1px solid var(--border-strong)",
                borderRadius: 4,
                padding: "5px 8px",
              }}
            >
              <option value="">Все типы объектов</option>
              {ENTITY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <table>
            <thead>
              <tr>
                <th>Время</th>
                <th>Объект</th>
                <th>ID</th>
                <th>Действие</th>
                <th>Пользователь</th>
                <th>Детали</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={6}>Загрузка…</td>
                </tr>
              )}
              {!loading && logs.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={6}>Записей пока нет</td>
                </tr>
              )}
              {logs.map((log) => (
                <tr key={log.id}>
                  <td className="mono">
                    {new Date(log.created_at).toLocaleString("ru-RU")}
                  </td>
                  <td className="mono">{log.entity_type}</td>
                  <td className="mono">{log.entity_id ?? "—"}</td>
                  <td>
                    <ActionPill action={log.action} />
                  </td>
                  <td className="mono">
                    {log.actor_user_id != null ? `#${log.actor_user_id}` : "system"}
                  </td>
                  <td className="mono" style={{ maxWidth: 360, overflowWrap: "anywhere" }}>
                    {log.metadata_json ? JSON.stringify(log.metadata_json) : "—"}
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
