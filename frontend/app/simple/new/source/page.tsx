"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useWizard, type WizardDataSource } from "@/lib/wizard";

const OPTIONS: { value: WizardDataSource; icon: string; titleKey: string; descKey?: string }[] = [
  { value: "file", icon: "📁", titleKey: "simple_mode.source_file", descKey: "simple_mode.source_file_desc" },
  { value: "connect", icon: "🔌", titleKey: "simple_mode.source_connect", descKey: "simple_mode.source_connect_desc" },
  { value: "manual", icon: "✏️", titleKey: "simple_mode.source_manual", descKey: "simple_mode.source_manual_desc" },
  { value: "no_data", icon: "📚", titleKey: "simple_mode.source_no_data", descKey: "simple_mode.source_no_data_desc" },
];

const ROUTES: Record<WizardDataSource, string> = {
  file: "/simple/new/upload",
  connect: "/simple/new/connect",
  manual: "/simple/new/manual",
  no_data: "/simple/new/no-data",
};

export default function WizardSourcePage() {
  const router = useRouter();
  const { t } = useTranslation();
  const { update } = useWizard();

  function choose(value: WizardDataSource) {
    update({ dataSource: value });
    router.push(ROUTES[value]);
  }

  return (
    <>
      <button
        className="btn btn-sm"
        onClick={() => router.push("/simple/new/task")}
        style={{ marginBottom: 20 }}
      >
        ← {t("common.back")}
      </button>
      <h1 style={{ fontSize: 20, marginBottom: 24 }}>{t("simple_mode.source_title")}</h1>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {OPTIONS.map((opt) => (
          <button
            key={opt.value}
            className="btn"
            onClick={() => choose(opt.value)}
            style={{
              flexDirection: "column",
              alignItems: "flex-start",
              padding: "16px 20px",
              gap: 4,
              textAlign: "left",
            }}
          >
            <span style={{ fontSize: 15, fontWeight: 600 }}>
              {opt.icon} {t(opt.titleKey)}
            </span>
            {opt.descKey && <span className="hint-text">{t(opt.descKey)}</span>}
          </button>
        ))}
      </div>
    </>
  );
}
