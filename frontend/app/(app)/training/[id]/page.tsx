"use client";

import { Form } from "@/components/Form";
import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/Pill";
import {
  getTrainingJob,
  predictWithTrainingJob,
  cancelTrainingJob,
  retryTrainingJob,
  downloadTrainingJobModel,
} from "@/lib/api";
import type { TrainingJob } from "@/lib/types";

export default function TrainingJobDetailPage() {
  const params = useParams<{ id: string }>();
  const jobId = Number(params.id);
  const { t, i18n } = useTranslation();

  const [job, setJob] = useState<TrainingJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [featureValues, setFeatureValues] = useState<Record<string, string>>({});
  const [predictText, setPredictText] = useState("");
  const [maxNewTokens, setMaxNewTokens] = useState(50);
  const [prediction, setPrediction] = useState<unknown>(undefined);
  const [predicting, setPredicting] = useState(false);
  const [predictError, setPredictError] = useState<string | null>(null);
  const [lifecycleBusy, setLifecycleBusy] = useState(false);
  const [lifecycleError, setLifecycleError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  async function handleDownload() {
    if (!job) return;
    setDownloadError(null);
    setDownloading(true);
    try {
      const ext =
        job.task_type === "transformer_text_classification" ||
        job.task_type === "transformer_text_generation"
          ? "zip"
          : "joblib";
      await downloadTrainingJobModel(jobId, `${job.name}.${ext}`);
    } catch {
      setDownloadError(t("training.detail.download_failed"));
    } finally {
      setDownloading(false);
    }
  }

  async function handleCancel() {
    setLifecycleError(null);
    setLifecycleBusy(true);
    try {
      const updated = await cancelTrainingJob(jobId);
      setJob(updated);
    } catch {
      setLifecycleError(t("training.detail.cancel_failed"));
    } finally {
      setLifecycleBusy(false);
    }
  }

  async function handleRetry() {
    setLifecycleError(null);
    setLifecycleBusy(true);
    try {
      const updated = await retryTrainingJob(jobId);
      setJob(updated);
    } catch {
      setLifecycleError(t("training.detail.retry_failed"));
    } finally {
      setLifecycleBusy(false);
    }
  }

  function refresh() {
    getTrainingJob(jobId).then((j) => {
      setJob(j);
      setLoading(false);
    });
  }

  useEffect(() => {
    if (Number.isNaN(jobId)) return;
    refresh();
    const interval = setInterval(() => {
      getTrainingJob(jobId).then((j) => {
        setJob(j);
        if (j.status === "completed" || j.status === "failed" || j.status === "cancelled") {
          clearInterval(interval);
        }
      });
    }, 3000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const isClassification = job?.task_type === "transformer_text_classification";
  const isGeneration = job?.task_type === "transformer_text_generation";
  const isTransformer = isClassification || isGeneration;

  async function handlePredict(e: React.FormEvent) {
    e.preventDefault();
    setPredictError(null);
    setPredicting(true);
    try {
      let features: Record<string, unknown>;
      if (isGeneration) {
        features = { prompt: predictText, max_new_tokens: maxNewTokens };
      } else if (isClassification) {
        features = { text: predictText };
      } else {
        const numeric: Record<string, number> = {};
        for (const [key, value] of Object.entries(featureValues)) {
          numeric[key] = Number(value) || 0;
        }
        features = numeric;
      }
      const result = await predictWithTrainingJob(jobId, features);
      setPrediction(result.prediction);
    } catch {
      setPredictError(t("training.detail.predict_failed"));
    } finally {
      setPredicting(false);
    }
  }

  if (loading || !job) {
    return (
      <>
        <PageHeader title={t("training.title")} />
        <div className="content">
          <p className="loading-line">{t("training.detail.loading")}</p>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader title={job.name} />
      <div className="content">
        <div className="breadcrumb">
          <Link href="/training">{t("training.detail.breadcrumb")}</Link> / #{job.id}
        </div>

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-body">
            <dl className="kv-grid">
              <dt>{t("training.detail.status")}</dt>
              <dd>
                <StatusPill status={job.status} />
              </dd>
              <dt>{isTransformer ? t("training.detail.base_model") : t("training.detail.algorithm")}</dt>
              <dd className="mono">{job.base_model || job.algorithm}</dd>
              <dt>{t("training.detail.task_type")}</dt>
              <dd className="mono">{job.task_type}</dd>
              {!isGeneration && (
                <>
                  <dt>
                    {isClassification
                      ? t("training.detail.label_column")
                      : t("training.detail.target_column")}
                  </dt>
                  <dd className="mono">{job.target_column}</dd>
                </>
              )}
              <dt>{t("training.detail.features")}</dt>
              <dd className="mono">
                {job.feature_columns_json?.join(", ") ||
                  t("training.detail.determined_during_training")}
              </dd>
              <dt>{t("training.detail.created")}</dt>
              <dd className="mono">
                {new Date(job.created_at).toLocaleString(i18n.language)}
              </dd>
              <dt>{t("training.detail.finished")}</dt>
              <dd className="mono">
                {job.finished_at
                  ? new Date(job.finished_at).toLocaleString(i18n.language)
                  : "—"}
              </dd>
            </dl>
          </div>
        </div>

        {(job.status === "queued" || job.status === "running") && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-body">
              <p className="hint-text" style={{ marginBottom: 12 }}>
                {t("training.detail.running_hint")}
              </p>
              {lifecycleError && <p className="error-text">{lifecycleError}</p>}
              <button
                className="btn btn-danger btn-sm"
                onClick={handleCancel}
                disabled={lifecycleBusy}
              >
                {lifecycleBusy ? t("training.detail.cancelling") : t("training.detail.cancel")}
              </button>
            </div>
          </div>
        )}

        {(job.status === "failed" || job.status === "cancelled") && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-body">
              {lifecycleError && <p className="error-text">{lifecycleError}</p>}
              <button
                className="btn btn-primary btn-sm"
                onClick={handleRetry}
                disabled={lifecycleBusy}
              >
                {lifecycleBusy ? t("training.detail.retrying") : t("training.detail.retry")}
              </button>
              <span className="hint-text" style={{ marginLeft: 12 }}>
                {t("training.detail.retry_hint")}
              </span>
            </div>
          </div>
        )}

        {job.status === "failed" && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>{t("training.detail.error_title")}</h2>
            </div>
            <div className="panel-body">
              <div className="text-block">
                {job.error_message || t("training.detail.unknown_error")}
              </div>
            </div>
          </div>
        )}

        {job.status === "completed" && job.metrics_json && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>{t("training.detail.metrics_title")}</h2>
            </div>
            <div className="panel-body">
              <dl className="kv-grid">
                {Object.entries(job.metrics_json).map(([key, value]) => (
                  <React.Fragment key={key}>
                    <dt className="mono">{key}</dt>
                    <dd className="mono">
                      {typeof value === "number" ? value.toFixed(4) : String(value)}
                    </dd>
                  </React.Fragment>
                ))}
              </dl>
              {isGeneration && (
                <p className="hint-text" style={{ marginTop: 8 }}>
                  {t("training.detail.metrics_generation_hint")}
                </p>
              )}
            </div>
          </div>
        )}

        {job.status === "completed" && job.model_path && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>{t("training.detail.artifact_title")}</h2>
            </div>
            <div className="panel-body">
              <p className="hint-text" style={{ marginBottom: 12 }}>
                {isTransformer
                  ? t("training.detail.artifact_hint_transformer")
                  : t("training.detail.artifact_hint_sklearn")}
              </p>
              {downloadError && <p className="error-text">{downloadError}</p>}
              <button className="btn btn-sm" onClick={handleDownload} disabled={downloading}>
                {downloading
                  ? t("training.detail.downloading")
                  : t("training.detail.download")}
              </button>
            </div>
          </div>
        )}

        {job.status === "completed" && (
          <div className="panel">
            <div className="panel-header">
              <h2>
                {isGeneration
                  ? t("training.detail.predict_title_generation")
                  : t("training.detail.predict_title_classification")}
              </h2>
            </div>
            <div className="panel-body">
              <Form onSubmit={handlePredict}>
                {isGeneration && (
                  <>
                    <div className="field">
                      <label htmlFor="predict-text">{t("training.detail.predict_prompt")}</label>
                      <textarea
                        id="predict-text"
                        required
                        value={predictText}
                        onChange={(e) => setPredictText(e.target.value)}
                        placeholder={t("training.detail.predict_prompt_placeholder")}
                      />
                    </div>
                    <div className="field" style={{ maxWidth: 220 }}>
                      <label htmlFor="max_new_tokens">
                        {t("training.detail.predict_max_tokens")}
                      </label>
                      <input
                        id="max_new_tokens"
                        type="number"
                        min={5}
                        max={300}
                        value={maxNewTokens}
                        onChange={(e) => setMaxNewTokens(Number(e.target.value))}
                      />
                    </div>
                  </>
                )}
                {isClassification && (
                  <div className="field">
                    <label htmlFor="predict-text">{t("training.detail.predict_text")}</label>
                    <textarea
                      id="predict-text"
                      required
                      value={predictText}
                      onChange={(e) => setPredictText(e.target.value)}
                      placeholder={t("training.detail.predict_text_placeholder")}
                    />
                  </div>
                )}
                {!isTransformer && (
                  <div className="form-row" style={{ flexWrap: "wrap" }}>
                    {job.feature_columns_json?.map((col) => (
                      <div className="field" key={col} style={{ minWidth: 140 }}>
                        <label htmlFor={`feat-${col}`}>{col}</label>
                        <input
                          id={`feat-${col}`}
                          type="number"
                          step="any"
                          value={featureValues[col] || ""}
                          onChange={(e) =>
                            setFeatureValues((f) => ({ ...f, [col]: e.target.value }))
                          }
                        />
                      </div>
                    ))}
                  </div>
                )}
                {predictError && <p className="error-text">{predictError}</p>}
                <button className="btn btn-primary" type="submit" disabled={predicting}>
                  {predicting
                    ? t("training.detail.predicting")
                    : isGeneration
                    ? t("training.detail.predict_submit_generation")
                    : t("training.detail.predict_submit_classification")}
                </button>
                {prediction !== undefined && (
                  <div className="text-block" style={{ marginTop: 12 }}>
                    {isGeneration ? (
                      String(prediction)
                    ) : (
                      <>
                        {t("training.detail.result")} <strong>{String(prediction)}</strong>
                      </>
                    )}
                  </div>
                )}
              </Form>
            </div>
          </div>
        )}
      </div>
    </>
  );
}