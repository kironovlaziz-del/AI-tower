"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/Pill";
import {
  createTrainingJob,
  getAllowedModels,
  listDatasets,
  listTrainingJobs,
} from "@/lib/api";
import type {
  AllowedModelsResponse,
  Dataset,
  TrainingAlgorithm,
  TrainingJob,
  TrainingTaskType,
} from "@/lib/types";

const SKLEARN_ALGORITHMS_BY_TASK: Record<
  "tabular_classification" | "tabular_regression",
  { value: TrainingAlgorithm; label: string }[]
> = {
  tabular_classification: [
    { value: "logistic_regression", label: "Логистическая регрессия" },
    { value: "random_forest_classifier", label: "Random Forest (классификация)" },
  ],
  tabular_regression: [
    { value: "linear_regression", label: "Линейная регрессия" },
    { value: "random_forest_regressor", label: "Random Forest (регрессия)" },
  ],
};

export default function TrainingPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [allowedModels, setAllowedModels] = useState<AllowedModelsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const [name, setName] = useState("");
  const [datasetId, setDatasetId] = useState<number | "">("");
  const [taskType, setTaskType] = useState<TrainingTaskType>("tabular_classification");
  const [algorithm, setAlgorithm] = useState<TrainingAlgorithm>("logistic_regression");
  const [targetColumn, setTargetColumn] = useState("");
  const [textColumn, setTextColumn] = useState("");
  const [baseModel, setBaseModel] = useState("");
  const [customModel, setCustomModel] = useState("");
  const [epochs, setEpochs] = useState(1);
  const [batchSize, setBatchSize] = useState(8);
  const [maxLength, setMaxLength] = useState(128);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isTransformerClassification = taskType === "transformer_text_classification";
  const isGeneration = taskType === "transformer_text_generation";
  const isTransformer = isTransformerClassification || isGeneration;

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

  useEffect(() => {
    if (!isTransformer) return;
    getAllowedModels(taskType).then((m) => {
      setAllowedModels(m);
      if (m.models.length > 0) setBaseModel(m.models[0].id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskType]);

  function handleTaskTypeChange(next: TrainingTaskType) {
    setTaskType(next);
    if (next === "tabular_classification" || next === "tabular_regression") {
      setAlgorithm(SKLEARN_ALGORITHMS_BY_TASK[next][0].value);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!datasetId) {
      setError("Выберите датасет.");
      return;
    }
    setSubmitting(true);
    try {
      const job = await createTrainingJob({
        dataset_id: Number(datasetId),
        name,
        task_type: taskType,
        target_column: isGeneration ? undefined : targetColumn,
        algorithm: isTransformer ? undefined : algorithm,
        base_model: isTransformer ? (customModel || baseModel) : undefined,
        hyperparameters: isTransformer
          ? { text_column: textColumn, epochs, batch_size: batchSize, max_length: maxLength }
          : undefined,
      });
      setShowForm(false);
      setName("");
      setTargetColumn("");
      setTextColumn("");
      setCustomModel("");
      router.push(`/training/${job.id}`);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(detail || "Не удалось запустить обучение.");
    } finally {
      setSubmitting(false);
    }
  }

  const tabularDatasets = datasets.filter(
    (d) => d.file_format === "csv" || d.file_format === "tsv"
  );

  return (
    <>
      <PageHeader
        title="Training Service"
        actions={
          <button
            className="btn btn-primary btn-sm"
            onClick={() => setShowForm((s) => !s)}
            disabled={tabularDatasets.length === 0}
            title={
              tabularDatasets.length === 0
                ? "Сначала загрузите датасет в формате CSV/TSV"
                : undefined
            }
          >
            {showForm ? "Отмена" : "Новое обучение"}
          </button>
        }
      />
      <div className="content">
        <p className="hint-text" style={{ marginBottom: 16 }}>
          Классический ML работает через scikit-learn на CPU. Fine-tuning
          трансформеров использует PyTorch + Transformers — один и тот же код
          для CPU и GPU: доступные модели ограничены реальным железом (см.{" "}
          <a href="/compute">Compute Detector</a>).
        </p>

        {tabularDatasets.length === 0 && (
          <p className="hint-text" style={{ marginBottom: 16 }}>
            Нет ни одного датасета в формате CSV/TSV — сначала загрузите его в{" "}
            <a href="/datasets">Dataset Manager</a>.
          </p>
        )}

        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>Новое задание обучения</h2>
            </div>
            <div className="panel-body">
              <form onSubmit={handleCreate}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="name">Название</label>
                    <input
                      id="name"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Прогноз оттока клиентов v1"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="dataset">Датасет</label>
                    <select
                      id="dataset"
                      required
                      value={datasetId}
                      onChange={(e) => setDatasetId(Number(e.target.value))}
                    >
                      <option value="">Выберите…</option>
                      {tabularDatasets.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name} ({d.file_format})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="field">
                  <label htmlFor="task_type">Тип задачи</label>
                  <select
                    id="task_type"
                    value={taskType}
                    onChange={(e) => handleTaskTypeChange(e.target.value as TrainingTaskType)}
                  >
                    <option value="tabular_classification">
                      Классический ML — классификация (табличные данные)
                    </option>
                    <option value="tabular_regression">
                      Классический ML — регрессия (табличные данные)
                    </option>
                    <option value="transformer_text_classification">
                      Fine-tuning трансформера — классификация текста
                    </option>
                    <option value="transformer_text_generation">
                      Fine-tuning трансформера — генерация текста (GPT-2)
                    </option>
                  </select>
                </div>

                {!isTransformer && (
                  <div className="field">
                    <label htmlFor="algorithm">Алгоритм</label>
                    <select
                      id="algorithm"
                      value={algorithm}
                      onChange={(e) => setAlgorithm(e.target.value as TrainingAlgorithm)}
                    >
                      {SKLEARN_ALGORITHMS_BY_TASK[
                        taskType as "tabular_classification" | "tabular_regression"
                      ].map((a) => (
                        <option key={a.value} value={a.value}>
                          {a.label}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {isTransformer && (
                  <>
                    <div className="field">
                      <label htmlFor="base_model">Базовая модель</label>
                      <select
                        id="base_model"
                        value={baseModel}
                        onChange={(e) => setBaseModel(e.target.value)}
                      >
                        {allowedModels?.models.map((m) => (
                          <option key={m.id} value={m.id} disabled={m.fits_vram === false}>
                            {m.label}
                            {m.fits_vram === true && " ✓ помещается в VRAM"}
                            {m.fits_vram === false && " ✗ не хватит VRAM"}
                          </option>
                        ))}
                      </select>
                      <span className="hint-text">
                        {allowedModels?.models.find((m) => m.id === baseModel)?.note}
                        {allowedModels?.gpu_vram_free_gb != null && (
                          <>
                            {" "}
                            Свободно VRAM: {allowedModels.gpu_vram_free_gb} ГБ, нужно
                            (с запасом) ~
                            {(
                              (allowedModels.models.find((m) => m.id === baseModel)
                                ?.estimated_vram_gb ?? 0) * 1.3
                            ).toFixed(1)}{" "}
                            ГБ.
                          </>
                        )}
                      </span>
                    </div>
                    {allowedModels?.custom_model_allowed && (
                      <div className="field">
                        <label htmlFor="custom_model">
                          Или свой ID модели с Hugging Face (необязательно, доступно т.к. обнаружен GPU)
                        </label>
                        <input
                          id="custom_model"
                          value={customModel}
                          onChange={(e) => setCustomModel(e.target.value)}
                          placeholder={isGeneration ? "например: gpt2-xl" : "например: distilroberta-base"}
                        />
                      </div>
                    )}
                    <div className="field">
                      <label htmlFor="text_column">Колонка с текстом</label>
                      <input
                        id="text_column"
                        required
                        value={textColumn}
                        onChange={(e) => setTextColumn(e.target.value)}
                        placeholder="Например: review_text"
                      />
                      {isGeneration && (
                        <span className="hint-text">
                          Отдельная колонка с меткой не нужна — модель учится
                          продолжать сам текст.
                        </span>
                      )}
                    </div>
                    <div className="form-row">
                      <div className="field">
                        <label htmlFor="epochs">Эпохи</label>
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
                        <label htmlFor="batch_size">Batch size</label>
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
                        <label htmlFor="max_length">Макс. длина текста (токенов)</label>
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
                    {!allowedModels?.gpu_available && (
                      <p className="hint-text" style={{ marginBottom: 12 }}>
                        ⚠ GPU не обнаружен — даже маленькая модель может
                        обучаться от нескольких минут до нескольких часов в
                        зависимости от размера датасета. Задание выполняется
                        в фоне, страницу можно закрыть.
                      </p>
                    )}
                  </>
                )}

                {!isGeneration && (
                  <div className="field">
                    <label htmlFor="target_column">
                      {isTransformerClassification ? "Колонка с меткой (label)" : "Целевая колонка"}
                    </label>
                    <input
                      id="target_column"
                      required
                      value={targetColumn}
                      onChange={(e) => setTargetColumn(e.target.value)}
                      placeholder="Точное имя колонки из датасета, например: label"
                    />
                    {!isTransformer && (
                      <span className="hint-text">
                        Признаками станут все остальные числовые колонки датасета.
                      </span>
                    )}
                  </div>
                )}

                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? "Запускаем…" : "Запустить обучение"}
                </button>
              </form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>Задания обучения</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>Название</th>
                <th>Модель/алгоритм</th>
                <th>Статус</th>
                <th>Создано</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={4}>Загрузка…</td>
                </tr>
              )}
              {!loading && jobs.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={4}>Заданий пока нет</td>
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
                    {new Date(j.created_at).toLocaleString("ru-RU")}
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
