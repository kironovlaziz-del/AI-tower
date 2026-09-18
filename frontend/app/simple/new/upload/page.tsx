"use client";

import React, { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useWizard } from "@/lib/wizard";
import { parseWizardUpload } from "@/lib/api";
import { translateApiError } from "@/lib/errors";

export default function WizardUploadPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const { state, update } = useWizard();
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setError(null);
    setUploading(true);
    try {
      const result = await parseWizardUpload(file, state.taskType || "other");
      update({
        uploadedFile: file,
        uploadedFileName: file.name,
        qaPairs: result.qa_pairs,
        errorRowCount: result.error_row_count,
        hasUnstructuredText: result.has_unstructured_text,
        recommendedApproach: result.recommended_approach as typeof state.recommendedApproach,
        recommendedReason: result.recommended_reason,
      });
      router.push("/simple/new/parsed");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
        ?.detail;
      setError(translateApiError(detail, t, t("simple_mode.upload_failed")));
    } finally {
      setUploading(false);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <>
      <button
        className="btn btn-sm"
        onClick={() => router.push("/simple/new/source")}
        style={{ marginBottom: 20 }}
      >
        ← {t("common.back")}
      </button>
      <h1 style={{ fontSize: 20, marginBottom: 24 }}>{t("simple_mode.upload_title")}</h1>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className="panel"
        style={{
          padding: 48,
          textAlign: "center",
          cursor: "pointer",
          borderStyle: "dashed",
          borderWidth: 2,
          borderColor: dragging ? "var(--accent, #2451d9)" : "var(--border, #e5e7eb)",
          background: dragging ? "rgba(36,81,217,0.04)" : undefined,
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.tsv,.xlsx,.json,.jsonl,.txt,.pdf"
          style={{ display: "none" }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        <div style={{ fontSize: 40, marginBottom: 12 }}>📁</div>
        {uploading ? (
          <p>{t("simple_mode.upload_processing")}</p>
        ) : (
          <>
            <p style={{ fontWeight: 600, marginBottom: 4 }}>{t("simple_mode.upload_dropzone")}</p>
            <p className="hint-text">{t("simple_mode.upload_formats")}</p>
          </>
        )}
      </div>

      {error && (
        <p className="error-text" style={{ marginTop: 16 }}>
          {error}
        </p>
      )}

      <p className="hint-text" style={{ marginTop: 20 }}>
        💡 {t("simple_mode.upload_hint")}{" "}
        <a href="/example-qa.csv" download style={{ fontWeight: 600 }}>
          {t("simple_mode.upload_download_example")}
        </a>
      </p>
    </>
  );
}
