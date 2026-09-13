"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { Form } from "@/components/Form";
import { StatusPill } from "@/components/Pill";
import {
  createTrainingJob,
  fetchAlgorithms,
  getAllowedModels,
  listDatasets,
  listTrainingJobs,
  type AlgorithmHyperparam,
  type AlgorithmInfo,
} from "@/lib/api";
import type {
  AllowedModelsResponse,
  Dataset,
  TrainingJob,
  TrainingTaskType,
} from "@/lib/types";

export default function TrainingPage() {
  const router = useRouter();
  const { t, i18n } = useTranslation();
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [allowedModels, setAllowedModels] = useState<AllowedModelsResponse | null>(null);
  const [algorithms, setAlgorithms] = useState<AlgorithmInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const [name, setName] = useState("");
  const [datasetId, setDatasetId] = useState<number | "">("");
  const [taskType, setTaskType] = useState<TrainingTaskType>("tabular_classification");
  const [algorithm, setAlgorithm] = useState<string>("");
  const [targetColumn, setTargetColumn] = useState("");
  const [textColumn, setTextColumn] = useState("");
  const [baseModel, setBaseModel] = useState("");
  const [customModel, setCustomModel] = useState("");
  const [epochs, setEpochs] = useState(1);
  const [batchSize, setBatchSize] = useState(8);
  const [maxLength, setMaxLength] = useState(128);

  // Dynamic hyperparameter values, keyed by param.name (string | number | "")
  const [hypervalues, setHypervalues] = useState<Record<string, string>>({});
  const [sklearnAdvanced, setSklearnAdvanced] = useState(false);

  // LoRA
  const [useLora, setUseLora] = useState(false);
  const [loraAdvanced, setLoraAdvanced] = useState(false);
  const [loraR, setLoraR] = useState(8);
  const [loraAlpha, setLoraAlpha] = useState(16);
  const [loraDropout, setLoraDropout] = useState(0.05);
  const [loraTargets, setLoraTargets] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isTransformerClassification = taskType === "transformer_text_classification";
  const isGeneration = taskType === "transformer_text_generation";
  const isTransformer = isTransformerClassification || isGeneration;

  const selectedAlgorithm = algorithms.find((a) => a.id === algorithm);
  const hasHyperparams =
    !!selectedAlgorithm && selectedAlgorithm.hyperparameters.length > 0;

  function refreshLists() {
    setLoading(true);
    Promise.all([listTrainingJobs(), listDatasets()])
      .then(([j, d]) => {
        setJobs(j);
        setDatasets(d);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refreshLists, []);

  // Load allowed transformer models when the task type is transformer-based.
  useEffect(() => {
    if (!isTransformer) return;
    getAllowedModels(taskType).then((m) => {
      setAllowedModels(m);
      if (m.models.length > 0) setBaseModel(m.models[0].id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskType]);

  // Load sklearn algorithms from the backend registry whenever the task
  // type is a tabular one. The frontend no longer hardcodes the list, so
  // adding an algorithm on the backend requires no rebuild here.
  useEffect(() => {
    if (isTransformer) return;
    fetchAlgorithms(taskType).then((list) => {
      setAlgorithms(list);
      // Reset selection + hyperparameter values to the first available
      // algorithm for this task type.
      if (list.length > 0) {
        setAlgorithm(list[0].id);
        setHypervalues({});
      } else {
        setAlgorithm("");
        setHypervalues({});
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskType]);

  function handleAlgorithmChange(next: string) {
    setAlgorithm(next);
    // Clear values so nothing stale from the previous algorithm is sent.
    setHypervalues({});
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!datasetId) {
      setError(t("datasets.name"));
      return;
    }
    setSubmitting(true);
    try {
      let hp: Record<string, unknown> = {};

      if (isTransformer) {
        hp = {
          text_column: textColumn,
          epochs,
          batch_size: batchSize,
          max_length: maxLength,
        };
        if (useLora) {
          hp.use_lora = true;
          hp.lora_r = loraR;
          hp.lora_alpha = loraAlpha;
          hp.lora_dropout = loraDropout;
          const targets = loraTargets
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean);
          if (targets.length > 0) hp.lora_target_modules = targets;
        }
      } else {
        // Copy any hyperparameter values the user set, coercing by type.
        // Empty strings are omitted so the backend falls back to defaults.
        if (selectedAlgorithm) {
          for (const p of selectedAlgorithm.hyperparameters) {
            const raw = hypervalues[p.name];
            if (raw === undefined || raw === "") continue;
            if (p.type === "int") hp[p.name] = parseInt(raw, 10);
            else if (p.type === "float") hp[p.name] = parseFloat(raw);
            else hp[p.name] = raw; // select
          }
        }
      }

      const job = await createTrainingJob({
        dataset_id: Number(datasetId),
        name,
        task_type: taskType,
        target_column: isGeneration ? undefined : targetColumn,
        algorithm: isTransformer ? undefined : algorithm,
        base_model: isTransformer ? customModel || baseModel : undefined,
        hyperparameters: Object.keys(hp).length > 0 ? hp : undefined,
      });
      setShowForm(false);
      setName("");
      setTargetColumn("");
      setTextColumn("");
      setCustomModel("");
      setHypervalues({});
      setSklearnAdvanced(false);
      setUseLora(false);
      setLoraAdvanced(false);
      router.push(`/training/${job.id}`);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(detail || t("training.submit"));
    } finally {
      setSubmitting(false);
    }
  }

  const tabularDatasets = datasets.filter(
    (d) => d.file_format === "csv" || d.file_format === "tsv"
  );

  function renderHyperparamField(p: AlgorithmHyperparam) {
    const value = hypervalues[p.name] ?? "";

    if (p.type === "select" && p.options) {
      return (
        <div className="field" key={p.name} style={{ minWidth: 200 }}>
          <label htmlFor={`hp-${p.name}`}>{t(p.label_key)}</label>
          <select
            id={`hp-${p.name}`}
            value={value}
            onChange={(e) =>
              setHypervalues((v) => ({ ...v, [p.name]: e.target.value }))
            }
          >
            <option value="">—</option>
            {p.options.map((o) => (
              <option key={o.value} value={o.value}>
                {t(o.label_key)}
              </option>
            ))}
          </select>
        </div>
      );
    }

    return (
      <div className="field" key={p.name} style={{ minWidth: 160 }}>
        <label htmlFor={`hp-${p.name}`}>{t(p.label_key)}</label>
        <input
          id={`hp-${p.name}`}
          type="number"
          step={p.type === "float" ? "any" : 1}
          min={p.min}
          max={p.max}
          value={value}
          onChange={(e) =>
            setHypervalues((v) => ({ ...v, [p.name]: e.target.value }))
          }
          placeholder={p.default != null ? String(p.default) : ""}
        />
      </div>
    );
  }

  return (
    <>
      <PageHeader
        title={t("training.title")}
        actions={
          <button
            className="btn btn-primary btn-sm"
            onClick={() => setShowForm((s) => !s)}
            disabled={tabularDatasets.length === 0}
          >
            {showForm ? t("training.cancel") : t("training.new")}
          </button>
        }
      />
      <div className="content">
        {tabularDatasets.length === 0 && (
          <p className="hint-text" style={{ marginBottom: 16 }}>
            {t("training.hint_no_datasets")}
          </p>
        )}

        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>{t("training.form_title")}</h2>
            </div>
            <div className="panel-body">
              <Form onSubmit={handleCreate}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="name">{t("training.name")}</label>
                    <input
                      id="name"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder={t("training.name_placeholder")}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="dataset">{t("training.dataset")}</label>
                    <select
                      id="dataset"
                      required
                      value={datasetId}
                      onChange={(e) => setDatasetId(Number(e.target.value))}
                    >
                      <option value="">{t("training.dataset_placeholder")}</option>
                      {tabularDatasets.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name} ({d.file_format})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="field">
                  <label htmlFor="task_type">{t("training.task_type")}</label>
                  <select
                    id="task_type"
                    value={taskType}
                    onChange={(e) => setTaskType(e.target.value as TrainingTaskType)}
                  >
                    <option value="tabular_classification">
                      {t("training.task_types.tabular_classification")}
                    </option>
                    <option value="tabular_regression">
                      {t("training.task_types.tabular_regression")}
                    </option>
                    <option value="transformer_text_classification">
                      {t("training.task_types.transformer_text_classification")}
                    </option>
                    <option value="transformer_text_generation">
                      {t("training.task_types.transformer_text_generation")}
                    </option>
                  </select>
                </div>

                {!isTransformer && (
                  <>
                    <div className="field">
                      <label htmlFor="algorithm">{t("training.algorithm")}</label>
                      <select
                        id="algorithm"
                        value={algorithm}
                        onChange={(e) => handleAlgorithmChange(e.target.value)}
                      >
                        {algorithms.length === 0 && (
                          <option value="">—</option>
                        )}
                        {algorithms.map((a) => (
                          <option key={a.id} value={a.id}>
                            {t(a.label_key)}
                          </option>
                        ))}
                      </select>
                    </div>

                    {hasHyperparams && (
                      <div className="panel" style={{ marginTop: 8, marginBottom: 8 }}>
                        <div className="panel-body" style={{ padding: 12 }}>
                          <button
                            type="button"
                            className="btn btn-sm"
                            onClick={() => setSklearnAdvanced((v) => !v)}
                          >
                            {sklearnAdvanced ? "▾" : "▸"}{" "}
                            {t("training.hyperparams_title")}
                          </button>

                          {sklearnAdvanced && selectedAlgorithm && (
                            <div style={{ marginTop: 12 }}>
                              <p className="hint-text" style={{ marginBottom: 12 }}>
                                {t("training.hyperparams_hint")}
                              </p>
                              <div className="form-row" style={{ flexWrap: "wrap" }}>
                                {selectedAlgorithm.hyperparameters.map(renderHyperparamField)}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </>
                )}

                {isTransformer && (
                  <>
                    <div className="field">
                      <label htmlFor="base_model">{t("training.base_model")}</label>
                      <select
                        id="base_model"
                        value={baseModel}
                        onChange={(e) => setBaseModel(e.target.value)}
                      >
                        {allowedModels?.models.map((m) => (
                          <option key={m.id} value={m.id} disabled={m.fits_vram === false}>
                            {m.label}
                            {m.fits_vram === true && ` ✓ ${t("training.hint_fits_vram")}`}
                            {m.fits_vram === false && ` ✗ ${t("training.hint_no_vram")}`}
                          </option>
                        ))}
                      </select>
                    </div>
                    {allowedModels?.custom_model_allowed && (
                      <div className="field">
                        <label htmlFor="custom_model">{t("training.custom_model")}</label>
                        <input
                          id="custom_model"
                          value={customModel}
                          onChange={(e) => setCustomModel(e.target.value)}
                          placeholder={isGeneration ? "gpt2-xl" : "distilroberta-base"}
                        />
                      </div>
                    )}
                    <div className="field">
                      <label htmlFor="text_column">{t("training.text_column")}</label>
                      <input
                        id="text_column"
                        required
                        value={textColumn}
                        onChange={(e) => setTextColumn(e.target.value)}
                        placeholder="review_text"
                      />
                    </div>
                    <div className="form-row">
                      <div className="field">
                        <label htmlFor="epochs">{t("training.epochs")}</label>
                        <input
                          id="epochs"
                          type="number"
                          min={1}
                          max={10}
                          value={epochs}
                          onChange={(e) => setEpochs(Number(e.target.value))}
                        />
                      </div>
                      <div className="field">
                        <label htmlFor="batch_size">{t("training.batch_size")}</label>
                        <input
                          id="batch_size"
                          type="number"
                          min={1}
                          max={64}
                          value={batchSize}
                          onChange={(e) => setBatchSize(Number(e.target.value))}
                        />
                      </div>
                      <div className="field">
                        <label htmlFor="max_length">{t("training.max_length")}</label>
                        <input
                          id="max_length"
                          type="number"
                          min={16}
                          max={512}
                          value={maxLength}
                          onChange={(e) => setMaxLength(Number(e.target.value))}
                        />
                      </div>
                    </div>

                    <div className="panel" style={{ marginTop: 8, marginBottom: 8 }}>
                      <div className="panel-body" style={{ padding: 12 }}>
                        <label
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                            fontSize: 13,
                            cursor: "pointer",
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={useLora}
                            onChange={(e) => setUseLora(e.target.checked)}
                          />
                          <strong>{t("training.use_lora")}</strong>
                        </label>
                        <p className="hint-text" style={{ marginTop: 6, marginLeft: 24 }}>
                          {t("training.use_lora_hint")}
                        </p>

                        {useLora && (
                          <div style={{ marginTop: 12, marginLeft: 24 }}>
                            <button
                              type="button"
                              className="btn btn-sm"
                              onClick={() => setLoraAdvanced((v) => !v)}
                            >
                              {loraAdvanced ? "▾" : "▸"} {t("training.lora_advanced")}
                            </button>
                            {loraAdvanced && (
                              <div style={{ marginTop: 12 }}>
                                <div className="form-row">
                                  <div className="field">
                                    <label htmlFor="lora_r">{t("training.lora_r")}</label>
                                    <input
                                      id="lora_r"
                                      type="number"
                                      min={1}
                                      max={256}
                                      value={loraR}
                                      onChange={(e) => setLoraR(Number(e.target.value))}
                                    />
                                  </div>
                                  <div className="field">
                                    <label htmlFor="lora_alpha">{t("training.lora_alpha")}</label>
                                    <input
                                      id="lora_alpha"
                                      type="number"
                                      min={1}
                                      max={512}
                                      value={loraAlpha}
                                      onChange={(e) => setLoraAlpha(Number(e.target.value))}
                                    />
                                  </div>
                                  <div className="field">
                                    <label htmlFor="lora_dropout">{t("training.lora_dropout")}</label>
                                    <input
                                      id="lora_dropout"
                                      type="number"
                                      min={0}
                                      max={0.9}
                                      step={0.01}
                                      value={loraDropout}
                                      onChange={(e) => setLoraDropout(Number(e.target.value))}
                                    />
                                  </div>
                                </div>
                                <div className="field">
                                  <label htmlFor="lora_targets">
                                    {t("training.lora_target_modules")}
                                  </label>
                                  <input
                                    id="lora_targets"
                                    value={loraTargets}
                                    onChange={(e) => setLoraTargets(e.target.value)}
                                    placeholder={t("training.lora_target_modules_placeholder")}
                                  />
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                )}

                {!isGeneration && (
                  <div className="field">
                    <label htmlFor="target_column">
                      {isTransformerClassification
                        ? t("training.target_column_label")
                        : t("training.target_column")}
                    </label>
                    <input
                      id="target_column"
                      required
                      value={targetColumn}
                      onChange={(e) => setTargetColumn(e.target.value)}
                      placeholder="label"
                    />
                  </div>
                )}

                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? t("training.submitting") : t("training.submit")}
                </button>
              </Form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>{t("training.table_title")}</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>{t("training.col_name")}</th>
                <th>{t("training.col_model")}</th>
                <th>{t("training.col_status")}</th>
                <th>{t("training.col_created")}</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={4}>{t("common.loading")}</td>
                </tr>
              )}
              {!loading && jobs.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={4}>{t("training.empty")}</td>
                </tr>
              )}
              {jobs.map((j) => (
                <tr
                  key={j.id}
                  className="clickable"
                  onClick={() => router.push(`/training/${j.id}`)}
                >
                  <td>{j.name}</td>
                  <td className="mono">{j.base_model || j.algorithm}</td>
                  <td>
                    <StatusPill status={j.status} />
                  </td>
                  <td className="mono">
                    {new Date(j.created_at).toLocaleString(i18n.language)}
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
