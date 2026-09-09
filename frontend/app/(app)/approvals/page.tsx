"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/Pill";
import { decideApproval, listApprovals } from "@/lib/api";
import type { Approval } from "@/lib/types";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [reasonDraft, setReasonDraft] = useState<Record<number, string>>({});

  function refresh() {
    setLoading(true);
    listApprovals()
      .then(setApprovals)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function decide(id: number, decision: "approved" | "rejected") {
    setBusyId(id);
    try {
      await decideApproval(id, { decision, reason: reasonDraft[id] || undefined });
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  const pending = approvals.filter((a) => !a.decision);
  const decided = approvals.filter((a) => a.decision);

  return (
    <>
      <PageHeader title="Approval Workflow" />
      <div className="content">
        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-header">
            <h2>Ожидают решения</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Запрос</th>
                <th>Комментарий</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={4}>Загрузка…</td>
                </tr>
              )}
              {!loading && pending.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={4}>Нет запросов, ожидающих согласования</td>
                </tr>
              )}
              {pending.map((a) => (
                <tr key={a.id}>
                  <td className="mono">#{a.id}</td>
                  <td>
                    <Link href={`/requests/${a.request_id}`}>запрос #{a.request_id}</Link>
                  </td>
                  <td>
                    <input
                      placeholder="Причина (необязательно)"
                      value={reasonDraft[a.id] || ""}
                      onChange={(e) =>
                        setReasonDraft((d) => ({ ...d, [a.id]: e.target.value }))
                      }
                      style={{
                        border: "1px solid var(--border-strong)",
                        borderRadius: 4,
                        padding: "6px 8px",
                        width: "100%",
                      }}
                    />
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button
                      className="btn btn-sm btn-primary"
                      style={{ marginRight: 6 }}
                      disabled={busyId === a.id}
                      onClick={() => decide(a.id, "approved")}
                    >
                      Согласовать
                    </button>
                    <button
                      className="btn btn-sm btn-danger"
                      disabled={busyId === a.id}
                      onClick={() => decide(a.id, "rejected")}
                    >
                      Отклонить
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>История решений</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Запрос</th>
                <th>Решение</th>
                <th>Причина</th>
                <th>Дата</th>
              </tr>
            </thead>
            <tbody>
              {!loading && decided.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={5}>Решений пока нет</td>
                </tr>
              )}
              {decided.map((a) => (
                <tr key={a.id}>
                  <td className="mono">#{a.id}</td>
                  <td>
                    <Link href={`/requests/${a.request_id}`}>запрос #{a.request_id}</Link>
                  </td>
                  <td>
                    <StatusPill status={a.decision || ""} />
                  </td>
                  <td>{a.reason || "—"}</td>
                  <td className="mono">
                    {new Date(a.created_at).toLocaleString("ru-RU")}
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
