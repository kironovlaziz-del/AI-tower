"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { updateMyUIMode } from "@/lib/api";

export default function SimpleModeSettingsPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const [switching, setSwitching] = useState(false);

  async function switchToAdvanced() {
    setSwitching(true);
    try {
      await updateMyUIMode("advanced");
      router.push("/dashboard");
    } finally {
      setSwitching(false);
    }
  }

  return (
    <>
      <h1 style={{ fontSize: 20, marginBottom: 20 }}>{t("simple_mode.settings")}</h1>
      <div className="panel">
        <div className="panel-body">
          <p style={{ marginBottom: 14 }}>{t("simple_mode.switch_to_advanced_desc")}</p>
          <button className="btn btn-primary" onClick={switchToAdvanced} disabled={switching}>
            {switching ? t("common.loading") : t("simple_mode.switch_to_advanced")}
          </button>
        </div>
      </div>
    </>
  );
}
