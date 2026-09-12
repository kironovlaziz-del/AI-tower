"use client";

import { Form } from "@/components/Form";
import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/Pill";
import {
  createShadowSighting,
  listShadowSightings,
  registerShadowSighting,
  updateShadowSighting,
} from "@/lib/api";
import type { ShadowSighting } from "@/lib/types";

export default function ShadowAIPage() {
  const { t, i18n } = useTranslation();
  const [sightings, setSightings] = useState<ShadowSighting[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  const [toolName, setToolName] = useState("");
  const [domain, setDomain] = useState("");
  const [detectedVia, setDetectedVia] = useState("manual");
  const [userHint, setUserHint] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    listShadowSightings()
      .then(setSightings)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createShadowSighting({
        tool_name: toolName,
        domain: domain || undefined,
        detected_via: detectedVia,
        user_hint: userHint || undefined,
        notes: notes || undefined,
      });
      setToolName("");
      setDomain("");
      setUserHint("");
      setNotes("");
      setDetectedVia("manual");
      setShowForm(false);
      refresh();
    } catch {
      setError(t("shadow_ai.failed"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSetStatus(id: number, status: string) {
    setBusyId(id);
    try {
      await updateShadowSighting(id, { status });
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  async function handleRegister(id: number) {
    setBusyId(id);
    try {
      await registerShadowSighting(id, { provider_type: "custom" });
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  const open = sightings.filter((s) => !["dismissed", "registered"].includes(s.status));
  const resolved = sightings.filter((s) => ["dismissed", "registered"].includes(s.status));

  return (
    <>
      <PageHeader
        title={t("shadow_ai.title")}
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? t("shadow_ai.cancel") : t("shadow_ai.report")}
          </button>
        }
      />
      <div className="content">
        <p className="hint-text" style={{ marginBottom: 16 }}>
          {t("shadow_ai.hint")}
        </p>

        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>{t("shadow_ai.form_title")}</h2>
            </div>
            <div className="panel-body">
              <Form onSubmit={handleCreate}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="tool_name">{t("shadow_ai.tool_name")}</label>
                    <input
                      id="tool_name"
                      required
                      value={toolName}
                      onChange={(e) => setToolName(e.target.value)}
                      placeholder={t("shadow_ai.tool_name_placeholder")}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="domain">{t("shadow_ai.domain")}</label>
                    <input
                      id="domain"
                      value={domain}
                      onChange={(e) => setDomain(e.target.value)}
                      placeholder={t("shadow_ai.domain_placeholder")}
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="detected_via">{t("shadow_ai.detected_via")}</label>
                    <select
                      id="detected_via"
                      value={detectedVia}
                      onChange={(e) => setDetectedVia(e.target.value)}
                    >
                      <option value="manual">{t("shadow_ai.detected.manual")}</option>
                      <option value="expense_report">{t("shadow_ai.detected.expense_report")}</option>
                      <option value="network_proxy">{t("shadow_ai.detected.network_proxy")}</option>
                      <option value="browser_extension">{t("shadow_ai.detected.browser_extension")}</option>
                      <option value="other">{t("shadow_ai.detected.other")}</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="user_hint">{t("shadow_ai.user_hint")}</label>
                    <input
                      id="user_hint"
                      value={userHint}
                      onChange={(e) => setUserHint(e.target.value)}
                      placeholder={t("shadow_ai.user_hint_placeholder")}
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="notes">{t("shadow_ai.notes")}</label>
                  <textarea
                    id="notes"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder={t("shadow_ai.notes_placeholder")}
                  />
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? t("shadow_ai.submitting") : t("shadow_ai.submit")}
                </button>
              </Form>
            </div>
          </div>
        )}

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-header">
            <h2>{t("shadow_ai.open_title")}</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>{t("shadow_ai.col_tool")}</th>
                <th>{t("shadow_ai.col_domain")}</th>
                <th>{t("shadow_ai.col_source")}</th>
                <th>{t("shadow_ai.col_employee")}</th>
                <th>{t("shadow_ai.col_status")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={6}>{t("common.loading")}</td>
                </tr>
              )}
              {!loading && open.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={6}>{t("shadow_ai.empty_open")}</td>
                </tr>
              )}
              {open.map((s) => (
                <tr key={s.id}>
                  <td>{s.tool_name}</td>
                  <td className="mono">{s.domain || "—"}</td>
                  <td>{t(`shadow_ai.detected.${s.detected_via}`, s.detected_via)}</td>
                  <td>{s.user_hint || "—"}</td>
                  <td>
                    <StatusPill status={s.status} />
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      {s.status === "new" && (
                        <button
                          className="btn btn-sm"
                          disabled={busyId === s.id}
                          onClick={() => handleSetStatus(s.id, "reviewing")}
                        >
                          {t("shadow_ai.action_take")}
                        </button>
                      )}
                      <button
                        className="btn btn-sm btn-danger"
                        disabled={busyId === s.id}
                        onClick={() => handleSetStatus(s.id, "confirmed_shadow")}
                      >
                        {t("shadow_ai.action_confirm")}
                      </button>
                      <button
                        className="btn btn-sm btn-primary"
                        disabled={busyId === s.id}
                        onClick={() => handleRegister(s.id)}
                      >
                        {t("shadow_ai.action_register")}
                      </button>
                      <button
                        className="btn btn-sm"
                        disabled={busyId === s.id}
                        onClick={() => handleSetStatus(s.id, "dismissed")}
                      >
                        {t("shadow_ai.action_dismiss")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>{t("shadow_ai.resolved_title")}</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>{t("shadow_ai.col_tool")}</th>
                <th>{t("shadow_ai.col_status")}</th>
                <th>{t("shadow_ai.col_provider")}</th>
                <th>{t("shadow_ai.col_closed")}</th>
              </tr>
            </thead>
            <tbody>
              {!loading && resolved.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={4}>{t("shadow_ai.empty_resolved")}</td>
                </tr>
              )}
              {resolved.map((s) => (
                <tr key={s.id}>
                  <td>{s.tool_name}</td>
                  <td>
                    <StatusPill status={s.status} />
                  </td>
                  <td className="mono">
                    {s.registered_provider_id ? `#${s.registered_provider_id}` : "—"}
                  </td>
                  <td className="mono">
                    {s.resolved_at
                      ? new Date(s.resolved_at).toLocaleString(i18n.language)
                      : "—"}
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