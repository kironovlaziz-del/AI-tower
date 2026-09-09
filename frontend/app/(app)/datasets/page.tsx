"use client";

import React, { useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { deleteDataset, listDatasets, uploadDataset } from "@/lib/api";
import type { Dataset } from "@/lib/types";

const TASK_TYPES = [
  { value: "text_classification", label: "Классификация текста" },
  { value: "regression", label: "Регрессия" },
  { value: "tabular", label: "Табличные данные" },
  { value: "other", label: "Другое" },
];

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [taskType, setTaskType] = useState("tabular");
  const fileRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  function refresh() {
    setLoading(true);
    listDatasets()
      .then(setDatasets)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Выберите файл датасета (.csv, .json, .jsonl, .txt, .tsv).");
      return;
    }
    setSubmitting(true);
    try {
      await uploadDataset({
        name,
        description: description || undefined,
        task_type: taskType,
        file,
      });
      setName("");
      setDescription("");
      setTaskType("tabular");
      if (fileRef.current) fileRef.current.value = "";
      setShowForm(false);
      refresh();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(detail || "Не удалось загрузить датасет.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number) {
    setBusyId(id);
    try {
      await deleteDataset(id);
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Dataset Manager"
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Отмена" : "Загрузить датасет"}
          </button>
        }
      />
      <div className="content">
        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>Загрузка датасета</h2>
            </div>
            <div className="panel-body">
              <form onSubmit={handleUpload}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="name">Название</label>
                    <input
                      id="name"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Отзывы клиентов за 2026"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="task_type">Тип задачи</label>
                    <select
                      id="task_type"
                      value={taskType}
                      onChange={(e) => setTaskType(e.target.value)}
                    >
                      {TASK_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="description">Описание</label>
                  <textarea
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Что внутри, откуда взяты данные"
                  />
                </div>
                <div className="field">
                  <label htmlFor="file">Файл (.csv, .json, .jsonl, .txt, .tsv, до 200 МБ)</label>
                  <input id="file" type="file" ref={fileRef} accept=".csv,.json,.jsonl,.txt,.tsv" />
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? "Загружаем…" : "Загрузить"}
                </button>
              </form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>Датасеты</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>Название</th>
                <th>Тип задачи</th>
                <th>Формат</th>
                <th>Размер</th>
                <th>Загружен</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={6}>Загрузка…</td>
                </tr>
              )}
              {!loading && datasets.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={6}>Датасетов пока нет</td>
                </tr>
              )}
              {datasets.map((d) => (
                <tr key={d.id}>
                  <td>
                    {d.name}
                    {d.description && (
                      <div className="hint-text">{d.description}</div>
                    )}
                  </td>
                  <td className="mono">{d.task_type}</td>
                  <td className="mono">{d.file_format || "—"}</td>
                  <td className="mono">{formatSize(d.size_bytes)}</td>
                  <td className="mono">
                    {new Date(d.created_at).toLocaleString("ru-RU")}
                  </td>
                  <td>
                    <button
                      className="btn btn-sm btn-danger"
                      disabled={busyId === d.id}
                      onClick={() => handleDelete(d.id)}
                    >
                      Удалить
                    </button>
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
