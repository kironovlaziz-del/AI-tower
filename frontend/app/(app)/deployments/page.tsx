"use client";

import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { Form } from "@/components/Form";
import { StatusPill } from "@/components/Pill";
import {
  createDeployment,
  listDeployments,
  listTrainingJobs,
  predictViaDeployment,
  updateDeployment,
} from "@/lib/api";
import type { ModelDeployment, TrainingJob } from "@/lib/types";

export default function DeploymentsPage() {
  const { t, i18n } = useTranslation();
  const [deployments, setDeployments] = useState<ModelDeployment[]>([]);
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  const [name, setName] = useState("");
  const [jobId, setJobId] = useState<number | "">("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Test panel
  const [testOpenId, setTestOpenId] = useState<number | null>(null);
  const [testText, setTestText] = useState("");
  const [testResult, setTestResult] = useState<unknown>(undefined);
  const [testBusy, setTestBusy] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);

  function refresh() {
    setLoading(true);
    Promise.all([listDeployments(), listTrainingJobs()])
      .then(([d, j]) => {
        setDeployments(d);
        setJobs(j.filter((x) => x.status === "completed"));
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!jobId) {
      setError(t("deployments.training_job_placeholder"));
      return;
    }
    setSubmitting(true);
    try {
      await createDeployment({
        training_job_id: Number(jobId),
        name,
        description: description || undefined,
      });
      setName("");
      setJobId("");
      setDescription("");
      setShowForm(false);
      refresh();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(detail || t("deployments.failed"));
    } finally {
      setSubmitting(false);
    }
  }

  async function updateTrafficWeight(id: number, weight: number) {
    setBusyId(id);
    try {
      await updateDeployment(id, { traffic_weight: weight });
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  async function toggleStatus(dep: ModelDeployment) {
    setBusyId(dep.id);
    try {
      const next = dep.status === "active" ? "inactive" : "active";
      await updateDeployment(dep.id, { status: next });
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  async function handleTest(e: React.FormEvent) {
    e.preventDefault();
    if (testOpenId == null) return;
    setTestError(null);
    setTestBusy(true);
    try {
      const res = await predictViaDeployment(testOpenId, { text: testText });
      setTestResult(res.prediction);
    } catch {
      setTestError(t("deployments.test_failed"));
    } finally {
      setTestBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        title={t("deployments.title")}
        actions={
          <button
            className="btn btn-primary btn-sm"
            onClick={() => setShowForm((s) => !s)}
            disabled={jobs.length === 0}
            title={jobs.length === 0 ? t("deployments.no_completed_jobs") : undefined}
          >
            {showForm ? t("deployments.cancel") : t("deployments.new")}
          </button>
        }
      />
      <div className="content">
        {jobs.length === 0 && (
          <p className="hint-text u-mb-16">
            {t("deployments.no_completed_jobs")}
          </p>
        )}

        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>{t("deployments.form_title")}</h2>
            </div>
            <div className="panel-body">
              <Form onSubmit={handleCreate}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="name">{t("deployments.name")}</label>
                    <input
                      id="name"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder={t("deployments.name_placeholder")}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="job">{t("deployments.training_job")}</label>
                    <select
                      id="job"
                      required
                      value={jobId}
                      onChange={(e) => setJobId(Number(e.target.value))}
                    >
                      <option value="">{t("deployments.training_job_placeholder")}</option>
                      {jobs.map((j) => (
                        <option key={j.id} value={j.id}>
                          #{j.id} — {j.name} ({j.base_model || j.algorithm})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="description">{t("deployments.description")}</label>
                  <textarea
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder={t("deployments.description_placeholder")}
                  />
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? t("deployments.submitting") : t("deployments.submit")}
                </button>
              </Form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>{t("deployments.table_title")}</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>{t("deployments.col_id")}</th>
                <th>{t("deployments.col_name")}</th>
                <th>{t("deployments.col_version")}</th>
                <th>{t("deployments.col_job")}</th>
                <th>{t("deployments.col_status")}</th>
                <th>{t("deployments.col_weight")}</th>
                <th>{t("deployments.col_created")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={8}>{t("deployments.loading")}</td>
                </tr>
              )}
              {!loading && deployments.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={8}>{t("deployments.empty")}</td>
                </tr>
              )}
              {deployments.map((d) => (
                <React.Fragment key={d.id}>
                  <tr>
                    <td className="mono">#{d.id}</td>
                    <td>{d.name}</td>
                    <td className="mono">v{d.version}</td>
                    <td className="mono">#{d.training_job_id}</td>
                    <td>
                      <StatusPill status={d.status} />
                    </td>
                    <td className="mono">
                      {new Date(d.created_at).toLocaleString(i18n.language)}
                    </td>
                    <td className="u-nowrap">
                      <div className="u-btn-row">
                        <button
                          className="btn btn-sm"
                          disabled={busyId === d.id}
                          onClick={() => toggleStatus(d)}
                        >
                          {d.status === "active"
                            ? t("deployments.deactivate")
                            : t("deployments.activate")}
                        </button>
                        <button
                          className="btn btn-sm"
                          onClick={() => {
                            setTestOpenId(testOpenId === d.id ? null : d.id);
                            setTestText("");
                            setTestResult(undefined);
                            setTestError(null);
                          }}
                        >
                          {testOpenId === d.id ? "▾" : "▸"}{" "}
                          {t("deployments.test_submit")}
                        </button>
                      </div>
                    </td>
                  </tr>
                  {testOpenId === d.id && (
                    <tr>
                      <td colSpan={7} className="u-row-secondary">
                        <div className="u-panel-tight">
                          <strong>{t("deployments.test_title")}</strong>
                          <form onSubmit={handleTest} className="u-mt-8">
                            <div className="field">
                              <label htmlFor={`test-${d.id}`}>
                                {t("deployments.test_text")}
                              </label>
                              <input
                                id={`test-${d.id}`}
                                required
                                value={testText}
                                onChange={(e) => setTestText(e.target.value)}
                                placeholder={t("deployments.test_text_placeholder")}
                              />
                            </div>
                            {testError && <p className="error-text">{testError}</p>}
                            <button
                              className="btn btn-primary btn-sm"
                              type="submit"
                              disabled={testBusy}
                            >
                              {testBusy
                                ? t("deployments.test_predicting")
                                : t("deployments.test_submit")}
                            </button>
                            {testResult !== undefined && (
                              <span style={{ marginLeft: 12 }}>
                                <strong>{t("deployments.test_result")}:</strong>{" "}
                                <span className="mono">{String(testResult)}</span>
                              </span>
                            )}
                          </form>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
