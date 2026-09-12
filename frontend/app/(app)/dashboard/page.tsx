"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslation } from "react-i18next";
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
  const { t, i18n } = useTranslation();
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
      <PageHeader title={t("dashboard.title")} />
      <div className="content">
        {loading ? (
          <p className="loading-line">{t("dashboard.loading")}</p>
        ) : (
          <>
            <div className="stat-grid">
              <div className="stat">
                <div className="stat-label">{t("dashboard.stat_use_cases")}</div>
                <div className="stat-value">{useCases.length}</div>
              </div>
              <div className="stat">
                <div className="stat-label">{t("dashboard.stat_requests")}</div>
                <div className="stat-value">{requests.length}</div>
              </div>
              <div className="stat">
                <div className="stat-label">{t("dashboard.stat_pending")}</div>
                <div className="stat-value">{pendingApprovals}</div>
              </div>
              <div className="stat">
                <div className="stat-label">{t("dashboard.stat_incidents")}</div>
                <div className="stat-value">{openIncidents}</div>
              </div>
              <div className="stat">
                <div className="stat-label">{t("dashboard.stat_policies")}</div>
                <div className="stat-value">{policies.length}</div>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <h2>{t("dashboard.recent_requests")}</h2>
                <Link href="/requests" className="btn btn-sm">
                  {t("dashboard.view_all")}
                </Link>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>{t("dashboard.col_id")}</th>
                    <th>{t("dashboard.col_purpose")}</th>
                    <th>{t("dashboard.col_risk")}</th>
                    <th>{t("dashboard.col_status")}</th>
                    <th>{t("dashboard.col_created")}</th>
                  </tr>
                </thead>
                <tbody>
                  {recentRequests.length === 0 && (
                    <tr className="empty-row">
                      <td colSpan={5}>{t("dashboard.empty_requests")}</td>
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
                        {new Date(r.created_at).toLocaleString(i18n.language)}
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