"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useWizard, type WizardTaskType } from "@/lib/wizard";

const OPTIONS: { value: WizardTaskType; icon: string; labelKey: string }[] = [
  { value: "support_qa", icon: "💬", labelKey: "simple_mode.task_support" },
  { value: "style_writing", icon: "✍️", labelKey: "simple_mode.task_style" },
  { value: "classification", icon: "🏷️", labelKey: "simple_mode.task_classify" },
  { value: "other", icon: "🔧", labelKey: "simple_mode.task_other" },
];

export default function WizardTaskPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const { update } = useWizard();

  function choose(value: WizardTaskType) {
    update({ taskType: value });
    router.push("/simple/new/source");
  }

  return (
    <>
      <button className="btn btn-sm" onClick={() => router.push("/simple")} style={{ marginBottom: 20 }}>
        ← {t("common.back")}
      </button>
      <h1 style={{ fontSize: 20, marginBottom: 24 }}>{t("simple_mode.task_title")}</h1>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {OPTIONS.map((opt) => (
          <button
            key={opt.value}
            className="btn"
            onClick={() => choose(opt.value)}
            style={{
              justifyContent: "space-between",
              padding: "18px 20px",
              fontSize: 15,
              fontWeight: 500,
            }}
          >
            <span>
              {opt.icon} {t(opt.labelKey)}
            </span>
            <span>→</span>
          </button>
        ))}
      </div>
    </>
  );
}
