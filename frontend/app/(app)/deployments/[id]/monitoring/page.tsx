"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { PageHeader } from "@/components/PageHeader";
import { fetchDeploymentMonitoring, type DeploymentMonitoring } from "@/lib/api";

const PALETTE = [
  "#2451d9", "#2f9e63", "#a9760a", "#c1541a", "#c1352f", "#676b76",
];

export default function DeploymentMonitoringPage() {
  const params = useParams<{ id: string }>();
  const deploymentId = Number(params.id);
  const router = useRouter();
  const { t, i18n } = useTranslation();

  const [data, setData] = useState<DeploymentMonitoring | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);

  useEffect(() => {
    setLoading(true);
    fetchDeploymentMonitoring(deploymentId, days)
      .then(setData)
      .finally(() => setLoading(false));
  }, [deploymentId, days]);

  if (loading || !data) {
    return (
      <>
        <PageHeader title={t("monitoring.title")} />
        <div className="content">
          <p className="loading-line">{t("common.loading")}</p>
        </div>
      </>
    );
  }

  const classData = Object.entries(data.predictions_by_class).map(
    ([name, value]) => ({ name, value }),
  );

  return (
    <>
      <PageHeader
        title={`${t("monitoring.title")}: ${data.deployment_name} v${data.deployment_version}`}
        actions={
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            style={{
              border: "1px solid var(--border-strong)",
              borderRadius: 4,
              padding: "5px 8px",
              background: "var(--bg-panel)",
              fontSize: 12,
            }}
          >
            <option value={1}>1d</option>
            <option value={7}>7d</option>
            <option value={30}>30d</option>
            <option value={90}>90d</option>
          </select>
        }
      />
      <div className="content">
        <div className="breadcrumb">
          <Link href="/deployments">{t("deployments.title")}</Link> / #{data.deployment_id} / {t("monitoring.title")}
        </div>

        <div className="stat-grid">
          <div className="stat">
            <div className="stat-label">{t("monitoring.total_predictions")}</div>
            <div className="stat-value">{data.total_predictions}</div>
          </div>
          <div className="stat">
            <div className="stat-label">{t("monitoring.avg_latency")}</div>
            <div className="stat-value">
              {data.latency_ms.avg != null ? `${data.latency_ms.avg.toFixed(1)} ms` : "—"}
            </div>
          </div>
          <div className="stat">
            <div className="stat-label">{t("monitoring.min_latency")}</div>
            <div className="stat-value">
              {data.latency_ms.min != null ? `${data.latency_ms.min.toFixed(1)} ms` : "—"}
            </div>
          </div>
          <div className="stat">
            <div className="stat-label">{t("monitoring.max_latency")}</div>
            <div className="stat-value">
              {data.latency_ms.max != null ? `${data.latency_ms.max.toFixed(1)} ms` : "—"}
            </div>
          </div>
        </div>

        {data.total_predictions === 0 ? (
          <div className="panel">
            <div className="panel-body">
              <p className="hint-text">{t("monitoring.no_data")}</p>
            </div>
          </div>
        ) : (
          <>
            <div className="panel u-mb-20">
              <div className="panel-header">
                <h2>{t("monitoring.predictions_trend")}</h2>
                <span className="hint-text">
                  {t("monitoring.window", { days })}
                </span>
              </div>
              <div className="panel-body">
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={data.predictions_by_day}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e4e9" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="count"
                      stroke="#2451d9"
                      strokeWidth={2}
                      name="Predictions"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="dashboard-grid-3">
              <div className="panel">
                <div className="panel-header">
                  <h2>{t("monitoring.predictions_by_class")}</h2>
                </div>
                <div className="panel-body">
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie
                        data={classData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={40}
                        outerRadius={80}
                        paddingAngle={2}
                      >
                        {classData.map((_, i) => (
                          <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="panel">
                <div className="panel-header">
                  <h2>{t("monitoring.feedback")}</h2>
                </div>
                <div className="panel-body">
                  {Object.keys(data.feedback).length === 0 ? (
                    <p className="hint-text">{t("monitoring.no_data")}</p>
                  ) : (
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart
                        data={Object.entries(data.feedback).map(([name, value]) => ({
                          name,
                          value,
                        }))}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e4e9" />
                        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                        <Tooltip />
                        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                          {Object.entries(data.feedback).map((_, i) => (
                            <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>

              <div className="panel">
                <div className="panel-header">
                  <h2>{t("monitoring.recent_predictions")}</h2>
                </div>
                <div className="panel-body" style={{ padding: 0, maxHeight: 240, overflowY: "auto" }}>
                  <table>
                    <thead>
                      <tr>
                        <th>{t("monitoring.col_time")}</th>
                        <th>{t("monitoring.col_prediction")}</th>
                        <th>{t("monitoring.col_latency")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.recent_predictions.map((r) => (
                        <tr key={r.id}>
                          <td className="mono" style={{ fontSize: 11 }}>
                            {new Date(r.created_at).toLocaleTimeString(i18n.language)}
                          </td>
                          <td className="mono">{r.prediction}</td>
                          <td className="mono">
                            {r.latency_ms != null ? r.latency_ms.toFixed(0) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
