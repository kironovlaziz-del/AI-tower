"use client";

import React, { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useWizard } from "@/lib/wizard";

export default function WizardNoDataPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const { state, update } = useWizard();
  const [pastedText, setPastedText] = useState("");
  const [showPaste, setShowPaste] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function addFiles(fileList: FileList) {
    const files = Array.from(fileList);
    update({ noDataFiles: [...state.noDataFiles, ...files], hasUnstructuredText: true });
  }

  function removeFile(index: number) {
    update({ noDataFiles: state.noDataFiles.filter((_, i) => i !== index) });
  }

  function addPastedText() {
    if (!pastedText.trim()) return;
    const blob = new Blob([pastedText], { type: "text/plain" });
    const file = new File([blob], `${t("simple_mode.no_data_pasted_filename")}.txt`, {
      type: "text/plain",
    });
    update({ noDataFiles: [...state.noDataFiles, file], hasUnstructuredText: true });
    setPastedText("");
    setShowPaste(false);
  }

  function proceed() {
    // Documents-only, by definition - this branch never goes through the
    // parse-upload heuristic call, so the recommendation is set directly
    // rather than left implicit for screen 9 to guess at.
    update({
      recommendedApproach: "rag",
      recommendedReason: t("simple_mode.no_data_reason"),
    });
    router.push("/simple/new/personality");
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
      <h1 style={{ fontSize: 20, marginBottom: 8 }}>{t("simple_mode.no_data_title")}</h1>
      <p className="hint-text" style={{ marginBottom: 24 }}>{t("simple_mode.no_data_subtitle")}</p>

      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.txt"
        style={{ display: "none" }}
        onChange={(e) => e.target.files && addFiles(e.target.files)}
      />

      <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 20 }}>
        <button
          className="btn"
          onClick={() => inputRef.current?.click()}
          style={{ justifyContent: "flex-start", padding: "16px 20px" }}
        >
          📄 {t("simple_mode.no_data_upload_docs")}
        </button>
        <button
          className="btn"
          onClick={() => setShowPaste((s) => !s)}
          style={{ justifyContent: "flex-start", padding: "16px 20px" }}
        >
          📝 {t("simple_mode.no_data_paste_text")}
        </button>
      </div>

      {showPaste && (
        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-body">
            <textarea
              rows={6}
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              placeholder={t("simple_mode.no_data_paste_placeholder")}
              style={{ marginBottom: 10 }}
            />
            <button className="btn btn-sm btn-primary" onClick={addPastedText} disabled={!pastedText.trim()}>
              {t("simple_mode.no_data_paste_add")}
            </button>
          </div>
        </div>
      )}

      {state.noDataFiles.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <p className="hint-text" style={{ marginBottom: 8 }}>
            {t("simple_mode.no_data_files_added", { count: state.noDataFiles.length })}
          </p>
          {state.noDataFiles.map((f, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "8px 12px",
                background: "var(--bg-app, #f5f6f8)",
                borderRadius: 6,
                marginBottom: 6,
              }}
            >
              <span style={{ fontSize: 13 }}>📄 {f.name}</span>
              <button className="btn btn-sm" onClick={() => removeFile(i)}>✕</button>
            </div>
          ))}
        </div>
      )}

      <p className="hint-text" style={{ marginBottom: 20 }}>
        💡 {t("simple_mode.no_data_rag_hint")}
      </p>

      <button
        className="btn btn-primary"
        style={{ width: "100%", justifyContent: "center" }}
        disabled={state.noDataFiles.length === 0}
        onClick={proceed}
      >
        {t("simple_mode.continue")} →
      </button>
    </>
  );
}
