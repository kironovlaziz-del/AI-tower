"use client";

import React from "react";
import Link from "next/link";
import { useTranslation } from "react-i18next";

export default function SimpleModeSettingsPage() {
  const { t } = useTranslation();
  return (
    <>
      <h1 style={{ fontSize: 20, marginBottom: 20 }}>{t("simple_mode.settings")}</h1>
      <div className="panel">
        <div className="panel-body">
          <p style={{ marginBottom: 14 }}>{t("simple_mode.switch_to_advanced_desc")}</p>
          <Link className="btn btn-primary" href="/dashboard">
            {t("simple_mode.switch_to_advanced")}
          </Link>
        </div>
      </div>
    </>
  );
}
