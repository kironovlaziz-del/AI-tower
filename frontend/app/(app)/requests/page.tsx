"use client";

import { Form } from "@/components/Form";
import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { RiskPill, StatusPill } from "@/components/Pill";
import { createRequest, listProviders, listRequests, listUseCases } from "@/lib/api";
import type { AIRequest, Provider, UseCase } from "@/lib/types";

export default function RequestsPage() {
  const router = useRouter();
  const { t, i18n } = useTranslation();
  const [requests, setRequests] = useState<AIRequest[]>([]);
  const [useCases, setUseCases] = useState<UseCase[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const [useCaseId, setUseCaseId] = useState<number | "">("");
  const [providerId, setProviderId] = useState<number | "">("");
  const [purpose, setPurpose] = useState("");
  const [inputText, setInputText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    Promise.all([listRequests(), listUseCases(), listProviders()])
      .then(([r, uc, p]) => {
        setRequests(r);
        setUseCases(uc);
        setProviders(p);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!useCaseId || !providerId) {
      setError(t("requests.must_select"));
      return;
    }
    setSubmitting(true);
    try {
      await createRequest({
        use_case_id: Number(useCaseId),
        provider_id: Number(providerId),
        purpose,
        input_text: inputText,
      });
      setPurpose("");
      setInputText("");
      setShowForm(false);
      refresh();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(detail || t("requests.failed"));
    } finally {
      setSubmitting(false);
    }
  }

  const canCreate = useCases.length > 0 && providers.length > 0;

  return (
    <>
      <PageHeader
        title={t("requests.title")}
        actions={
          <button
            className="btn btn-primary btn-sm"
            onClick={() => setShowForm((s) => !s)}
            disabled={!canCreate}
          >
            {showForm ? t("requests.cancel") : t("requests.new")}
          </button>
        }
      />
      <div className="content">
        {!canCreate && (
          <p className="hint-text" style={{ marginBottom: 16 }}>
            {t("requests.hint_no_prereqs")}
          </p>
        )}

        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>{t("requests.form_title")}</h2>
            </div>
            <div className="panel-body">
              <Form onSubmit={handleCreate}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="use_case">{t("requests.use_case")}</label>
                    <select
                      id="use_case"
                      value={useCaseId}
                      onChange={(e) => setUseCaseId(Number(e.target.value))}
                      required
                    >
                      <option value="">{t("requests.use_case_placeholder")}</option>
                      {useCases.map((uc) => (
                        <option key={uc.id} value={uc.id}>
                          {uc.name} ({t(`risk.${uc.risk_level}`, uc.risk_level)})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="provider">{t("requests.provider")}</label>
                    <select
                      id="provider"
                      value={providerId}
                      onChange={(e) => setProviderId(Number(e.target.value))}
                      required
                    >
                      <option value="">{t("requests.provider_placeholder")}</option>
                      {providers.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name} ({p.type})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="purpose">{t("requests.purpose")}</label>
                  <input
                    id="purpose"
                    required
                    value={purpose}
                    onChange={(e) => setPurpose(e.target.value)}
                    placeholder={t("requests.purpose_placeholder")}
                  />
                </div>
                <div className="field">
                  <label htmlFor="input_text">{t("requests.input_text")}</label>
                  <textarea
                    id="input_text"
                    required
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder={t("requests.input_text_placeholder")}
                  />
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? t("requests.submitting") : t("requests.submit")}
                </button>
              </Form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>{t("requests.title")}</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>{t("requests.col_id")}</th>
                <th>{t("requests.col_purpose")}</th>
                <th>{t("requests.col_risk")}</th>
                <th>{t("requests.col_status")}</th>
                <th>{t("requests.col_created")}</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={5}>{t("common.loading")}</td>
                </tr>
              )}
              {!loading && requests.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={5}>{t("requests.empty")}</td>
                </tr>
              )}
              {requests.map((r) => (
                <tr
                  key={r.id}
                  className="clickable"
                  onClick={() => router.push(`/requests/${r.id}`)}
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
      </div>
    </>
  );
}