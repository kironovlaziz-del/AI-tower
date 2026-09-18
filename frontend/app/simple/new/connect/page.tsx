"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";

export default function WizardConnectPage() {
  const router = useRouter();
  const { t } = useTranslation();

  return (
    <>
      <button
        className="btn btn-sm"
        onClick={() => router.push("/simple/new/source")}
        style={{ marginBottom: 20 }}
      >
        ← {t("common.back")}
      </button>
      <div className="panel">
        <div className="panel-body" style={{ textAlign: "center", padding: 40 }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🔌</div>
          <h2 style={{ marginBottom: 8 }}>{t("simple_mode.connect_soon_title")}</h2>
          <p className="hint-text" style={{ marginBottom: 20 }}>
            {t("simple_mode.connect_soon_desc")}
          </p>
          <button className="btn btn-primary" onClick={() => router.push("/simple/new/source")}>
            {t("simple_mode.connect_choose_other")}
          </button>
        </div>
      </div>
    </>
  );
}
