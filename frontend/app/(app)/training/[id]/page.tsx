"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/Pill";
import { getTrainingJob, predictWithTrainingJob, cancelTrainingJob, retryTrainingJob } from "@/lib/api";
import type { TrainingJob } from "@/lib/types";

export default function TrainingJobDetailPage() {
  const params = useParams<{ id: string }>();
  const jobId = Number(params.id);

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

  async function handleCancel() {
    setLifecycleError(null);
    setLifecycleBusy(true);
    try {
      const updated = await cancelTrainingJob(jobId);
      setJob(updated);
    } catch {
      setLifecycleError("Не удалось остановить обучение.");
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
      setLifecycleError("Не удалось перезапустить обучение.");
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
      setPredictError("Не удалось получить предсказание.");
    } finally {
      setPredicting(false);
    }
  }

  if (loading || !job) {
    return (
      <>
        <PageHeader title="Задание обучения" />
        <div className="content">
          <p className="loading-line">Загрузка…</p>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader title={job.name} />
      <div className="content">
        <div className="breadcrumb">
          <Link href="/training">Training Service</Link> / #{job.id}
        </div>

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-body">
            <dl className="kv-grid">
              <dt>Статус</dt>
              <dd>
                <StatusPill status={job.status} />
              </dd>
              <dt>{isTransformer ? "Базовая модель" : "Алгоритм"}</dt>
              <dd className="mono">{job.base_model || job.algorithm}</dd>
              <dt>Тип задачи</dt>
              <dd className="mono">{job.task_type}</dd>
              {!isGeneration && (
                <>
                  <dt>{isClassification ? "Колонка с меткой" : "Целевая колонка"}</dt>
                  <dd className="mono">{job.target_column}</dd>
                </>
              )}
              <dt>Признаки</dt>
              <dd className="mono">
                {job.feature_columns_json?.join(", ") || "определяются во время обучения"}
              </dd>
              <dt>Создано</dt>
              <dd className="mono">
                {new Date(job.created_at).toLocaleString("ru-RU")}
              </dd>
              <dt>Завершено</dt>
              <dd className="mono">
                {job.finished_at ? new Date(job.finished_at).toLocaleString("ru-RU") : "—"}
              </dd>
            </dl>
          </div>
        </div>

        {(job.status === "queued" || job.status === "running") && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-body">
              <p className="hint-text" style={{ marginBottom: 12 }}>
                Задание выполняется в фоне — страница обновится автоматически по
                готовности.{" "}
                {isTransformer &&
                  "Fine-tuning без GPU может занять от нескольких минут до нескольких часов."}
              </p>
              {lifecycleError && <p className="error-text">{lifecycleError}</p>}
              <button className="btn btn-danger btn-sm" onClick={handleCancel} disabled={lifecycleBusy}>
                {lifecycleBusy ? "Останавливаем…" : "Остановить обучение"}
              </button>
            </div>
          </div>
        )}

        {(job.status === "failed" || job.status === "cancelled") && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-body">
              {lifecycleError && <p className="error-text">{lifecycleError}</p>}
              <button className="btn btn-primary btn-sm" onClick={handleRetry} disabled={lifecycleBusy}>
                {lifecycleBusy ? "Запускаем…" : "Запустить заново"}
              </button>
              <span className="hint-text" style={{ marginLeft: 12 }}>
                Перезапустит с теми же параметрами.
              </span>
            </div>
          </div>
        )}

        {job.status === "failed" && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>Ошибка</h2>
            </div>
            <div className="panel-body">
              <div className="text-block">{job.error_message || "Неизвестная ошибка"}</div>
            </div>
          </div>
        )}

        {job.status === "completed" && job.metrics_json && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>Метрики качества</h2>
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
                  Perplexity — чем ниже, тем увереннее модель предсказывает
                  следующий токен на отложенных данных. Прямого «процента
                  точности» для генерации текста не существует.
                </p>
              )}
            </div>
          </div>
        )}

        {job.status === "completed" && (
          <div className="panel">
            <div className="panel-header">
              <h2>{isGeneration ? "Сгенерировать текст" : "Проверить предсказание"}</h2>
            </div>
            <div className="panel-body">
              <form onSubmit={handlePredict}>
                {isGeneration && (
                  <>
                    <div className="field">
                      <label htmlFor="predict-text">Начало текста (промпт)</label>
                      <textarea
                        id="predict-text"
                        required
                        value={predictText}
                        onChange={(e) => setPredictText(e.target.value)}
                        placeholder="Введите начало текста, модель продолжит"
                      />
                    </div>
                    <div className="field" style={{ maxWidth: 220 }}>
                      <label htmlFor="max_new_tokens">Сколько токенов сгенерировать</label>
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
                    <label htmlFor="predict-text">Текст</label>
                    <textarea
                      id="predict-text"
                      required
                      value={predictText}
                      onChange={(e) => setPredictText(e.target.value)}
                      placeholder="Введите текст для классификации"
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
                    ? "Считаем…"
                    : isGeneration
                    ? "Сгенерировать"
                    : "Получить предсказание"}
                </button>
                {prediction !== undefined && (
                  <div className="text-block" style={{ marginTop: 12 }}>
                    {isGeneration ? (
                      String(prediction)
                    ) : (
                      <>
                        Результат: <strong>{String(prediction)}</strong>
                      </>
                    )}
                  </div>
                )}
              </form>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
