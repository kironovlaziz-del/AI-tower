"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { RiskPill, StatusPill } from "@/components/Pill";
import {
  listApprovals,
  listIncidents,
  listPolicies,
  listRequests,
  listUseCases,
} from "@/lib/api";
import type { AIRequest, Approval, Incident, Policy, UseCase } from "@/lib/types";

export default function DashboardPage() {
  const [useCases, setUseCases] = useState<UseCase[]>([]);
  const [requests, setRequests] = useState<AIRequest[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      listUseCases(),
      listRequests(),
      listApprovals(),
      listIncidents(),
      listPolicies(),
    ])
      .then(([uc, req, appr, inc, pol]) => {
        setUseCases(uc);
        setRequests(req);
        setApprovals(appr);
        setIncidents(inc);
        setPolicies(pol);
      })
      .finally(() => setLoading(false));
  }, []);

  const pendingApprovals = approvals.filter((a) => !a.decision).length;
  const openIncidents = incidents.filter((i) => i.status !== "resolved").length;
  const recentRequests = requests.slice(0, 6);

  return (
    <>
      <PageHeader title="Панель управления" />
      <div className="content">
        {loading ? (
          <p className="loading-line">Загрузка данных…</p>
        ) : (
          <>
            <div className="stat-grid">
              <div className="stat">
                <div className="stat-label">Сценарии использования</div>
                <div className="stat-value">{useCases.length}</div>
              </div>
              <div className="stat">
                <div className="stat-label">Запросов в реестре</div>
                <div className="stat-value">{requests.length}</div>
              </div>
              <div className="stat">
                <div className="stat-label">Ожидают согласования</div>
                <div className="stat-value">{pendingApprovals}</div>
              </div>
              <div className="stat">
                <div className="stat-label">Открытые инциденты</div>
                <div className="stat-value">{openIncidents}</div>
              </div>
              <div className="stat">
                <div className="stat-label">Политики</div>
                <div className="stat-value">{policies.length}</div>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <h2>Последние запросы (Action Trace)</h2>
                <Link href="/requests" className="btn btn-sm">
                  Весь реестр
                </Link>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Назначение</th>
                    <th>Риск</th>
                    <th>Статус</th>
                    <th>Создан</th>
                  </tr>
                </thead>
                <tbody>
                  {recentRequests.length === 0 && (
                    <tr className="empty-row">
                      <td colSpan={5}>Пока нет запросов в реестре использования</td>
                    </tr>
                  )}
                  {recentRequests.map((r) => (
                    <tr
                      key={r.id}
                      className="clickable"
                      onClick={() => (window.location.href = `/requests/${r.id}`)}
                    >
                      <td className="mono">#{r.id}</td>
                      <td>{r.purpose}</td>
                      <td>
                        <RiskPill level={r.risk_level} />
                      </td>
                      <td>
                        <StatusPill status={r.status} />
                      </td>
                      <td className="mono">
                        {new Date(r.created_at).toLocaleString("ru-RU")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </>
  );
}
