"use client";

import { Form } from "@/components/Form";
import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { RiskPill, StatusPill } from "@/components/Pill";
import { createIncident, listIncidents } from "@/lib/api";
import type { Incident, RiskLevel } from "@/lib/types";

export default function IncidentsPage() {
  const router = useRouter();
  const { t, i18n } = useTranslation();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [severity, setSeverity] = useState<RiskLevel>("low");
  const [category, setCategory] = useState("");
  const [summary, setSummary] = useState("");
  const [impact, setImpact] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    listIncidents()
      .then(setIncidents)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createIncident({ severity, category, summary, impact: impact || undefined });
      setCategory("");
      setSummary("");
      setImpact("");
      setSeverity("low");
      setShowForm(false);
      refresh();
    } catch {
      setError(t("incidents.failed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHeader
        title={t("incidents.title")}
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? t("incidents.cancel") : t("incidents.new")}
          </button>
        }
      />
      <div className="content">
        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>{t("incidents.form_title")}</h2>
            </div>
            <div className="panel-body">
              <Form onSubmit={handleCreate}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="severity">{t("incidents.severity")}</label>
                    <select
                      id="severity"
                      value={severity}
                      onChange={(e) => setSeverity(e.target.value as RiskLevel)}
                    >
                      <option value="low">{t("risk.low")}</option>
                      <option value="medium">{t("risk.medium")}</option>
                      <option value="high">{t("risk.high")}</option>
                      <option value="critical">{t("risk.critical")}</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="category">{t("incidents.category")}</label>
                    <input
                      id="category"
                      required
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      placeholder={t("incidents.category_placeholder")}
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="summary">{t("incidents.summary")}</label>
                  <input
                    id="summary"
                    required
                    value={summary}
                    onChange={(e) => setSummary(e.target.value)}
                    placeholder={t("incidents.summary_placeholder")}
                  />
                </div>
                <div className="field">
                  <label htmlFor="impact">{t("incidents.impact")}</label>
                  <textarea
                    id="impact"
                    value={impact}
                    onChange={(e) => setImpact(e.target.value)}
                    placeholder={t("incidents.impact_placeholder")}
                  />
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? t("incidents.submitting") : t("incidents.submit")}
                </button>
              </Form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>{t("incidents.table_title")}</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>{t("incidents.col_id")}</th>
                <th>{t("incidents.col_category")}</th>
                <th>{t("incidents.col_summary")}</th>
                <th>{t("incidents.col_severity")}</th>
                <th>{t("incidents.col_status")}</th>
                <th>{t("incidents.col_created")}</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={6}>{t("common.loading")}</td>
                </tr>
              )}
              {!loading && incidents.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={6}>{t("incidents.empty")}</td>
                </tr>
              )}
              {incidents.map((i) => (
                <tr
                  key={i.id}
                  className="clickable"
                  onClick={() => router.push(`/incidents/${i.id}`)}
                >
                  <td className="mono">#{i.id}</td>
                  <td>{i.category}</td>
                  <td>{i.summary}</td>
                  <td>
                    <RiskPill level={i.severity} />
                  </td>
                  <td>
                    <StatusPill status={i.status} />
                  </td>
                  <td className="mono">
                    {new Date(i.created_at).toLocaleString(i18n.language)}
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