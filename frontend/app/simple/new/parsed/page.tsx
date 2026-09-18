"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useWizard } from "@/lib/wizard";

export default function WizardParsedPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const { state } = useWizard();

  // Guard against landing here directly (e.g. a refresh) without having
  // gone through the upload step - wizard state lives only in memory.
  useEffect(() => {
    if (!state.uploadedFileName) router.replace("/simple/new/source");
  }, [state.uploadedFileName, router]);

  if (!state.uploadedFileName) return null;

  return (
    <>
      <button
        className="btn btn-sm"
        onClick={() => router.push("/simple/new/upload")}
        style={{ marginBottom: 20 }}
      >
        ← {t("common.back")}
      </button>
      <h1 style={{ fontSize: 20, marginBottom: 8 }}>{t("simple_mode.parsed_title")}</h1>
      <p style={{ marginBottom: 20 }}>
        ✅ {t("simple_mode.parsed_file_loaded")}: <strong>{state.uploadedFileName}</strong>
      </p>

      <div className="panel" style={{ marginBottom: 20 }}>
        <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <p style={{ fontWeight: 600, marginBottom: 4 }}>{t("simple_mode.parsed_found")}:</p>

          {state.qaPairs.length > 0 && (
            <p>
              📝 {t("simple_mode.parsed_pairs_count", { count: state.qaPairs.length })}
            </p>
          )}
          {state.hasUnstructuredText && state.qaPairs.length === 0 && (
            <p>📄 {t("simple_mode.parsed_unstructured")}</p>
          )}
          {state.errorRowCount > 0 && (
            <p>
              ⚠️ {t("simple_mode.parsed_error_rows", { count: state.errorRowCount })}
            </p>
          )}
        </div>
      </div>

      <button
        className="btn btn-primary"
        style={{ width: "100%", justifyContent: "center" }}
        onClick={() =>
          router.push(state.qaPairs.length > 0 ? "/simple/new/review" : "/simple/new/personality")
        }
      >
        {t("simple_mode.continue")} →
      </button>
    </>
  );
}
