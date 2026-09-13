"use client";

import { Form } from "@/components/Form";
import React, { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { deleteDataset, listDatasets, uploadDataset } from "@/lib/api";
import type { Dataset } from "@/lib/types";

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DatasetsPage() {
  const { t, i18n } = useTranslation();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [taskType, setTaskType] = useState("tabular");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  const TASK_TYPES = [
    { value: "text_classification", labelKey: "datasets.task_types.text_classification" },
    { value: "regression", labelKey: "datasets.task_types.regression" },
    { value: "tabular", labelKey: "datasets.task_types.tabular" },
    { value: "other", labelKey: "datasets.task_types.other" },
  ];

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
    if (!selectedFile) {
      setError(t("datasets.error_no_file"));
      return;
    }
    setSubmitting(true);
    try {
      await uploadDataset({
        name,
        description: description || undefined,
        task_type: taskType,
        file: selectedFile,
      });
      setName("");
      setDescription("");
      setTaskType("tabular");
      setSelectedFile(null);
      if (fileRef.current) fileRef.current.value = "";
      setShowForm(false);
      refresh();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(detail || t("datasets.error_upload"));
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
        title={t("datasets.title")}
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? t("datasets.cancel") : t("datasets.upload")}
          </button>
        }
      />
      <div className="content">
        {showForm && (
          <div className="panel u-mb-20">
            <div className="panel-header">
              <h2>{t("datasets.form_title")}</h2>
            </div>
            <div className="panel-body">
              <Form onSubmit={handleUpload}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="name">{t("datasets.name")}</label>
                    <input
                      id="name"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder={t("datasets.name_placeholder")}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="task_type">{t("datasets.task_type")}</label>
                    <select
                      id="task_type"
                      value={taskType}
                      onChange={(e) => setTaskType(e.target.value)}
                    >
                      {TASK_TYPES.map((tt) => (
                        <option key={tt.value} value={tt.value}>
                          {t(tt.labelKey)}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="description">{t("datasets.description")}</label>
                  <textarea
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder={t("datasets.description_placeholder")}
                  />
                </div>
                <div className="field">
                  <label>{t("datasets.file")}</label>
                  <input
                    id="file"
                    type="file"
                    ref={fileRef}
                    accept=".csv,.json,.jsonl,.txt,.tsv"
                    style={{ display: "none" }}
                    onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                  />
                  <div className="file-input-row">
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => fileRef.current?.click()}
                    >
                      {t("datasets.choose_file")}
                    </button>
                    <span className={`file-name${selectedFile ? " has-file" : ""}`}>
                      {selectedFile
                        ? selectedFile.name
                        : t("datasets.no_file_selected")}
                    </span>
                  </div>
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? t("datasets.submitting") : t("datasets.submit")}
                </button>
              </Form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>{t("datasets.table_title")}</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>{t("datasets.col_name")}</th>
                <th>{t("datasets.col_task_type")}</th>
                <th>{t("datasets.col_format")}</th>
                <th>{t("datasets.col_size")}</th>
                <th>{t("datasets.col_uploaded")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={6}>{t("common.loading")}</td>
                </tr>
              )}
              {!loading && datasets.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={6}>{t("datasets.empty")}</td>
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
                  <td className="mono">
                    {t(`datasets.task_types.${d.task_type}`, d.task_type)}
                  </td>
                  <td className="mono">{d.file_format || "—"}</td>
                  <td className="mono">{formatSize(d.size_bytes)}</td>
                  <td className="mono">
                    {new Date(d.created_at).toLocaleString(i18n.language)}
                  </td>
                  <td>
                    <button
                      className="btn btn-sm btn-danger"
                      disabled={busyId === d.id}
                      onClick={() => handleDelete(d.id)}
                    >
                      {t("datasets.delete")}
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
