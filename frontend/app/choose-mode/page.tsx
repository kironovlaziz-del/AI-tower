"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/lib/auth";
import { updateMyUIMode } from "@/lib/api";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

export default function ChooseModePage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const { t } = useTranslation();
  const [submitting, setSubmitting] = useState<"simple" | "advanced" | null>(null);

  React.useEffect(() => {
    if (!loading && !user) router.replace("/login");
    // Already chosen (e.g. someone navigated back here manually) - don't
    // make them choose again, just send them where they'd normally land.
    if (!loading && user?.ui_mode === "simple") router.replace("/simple");
    if (!loading && user?.ui_mode === "advanced") router.replace("/dashboard");
  }, [loading, user, router]);

  async function choose(mode: "simple" | "advanced") {
    setSubmitting(mode);
    try {
      await updateMyUIMode(mode);
      router.push(mode === "simple" ? "/simple" : "/dashboard");
    } finally {
      setSubmitting(null);
    }
  }

  if (loading || !user) return null;

  return (
    <div className="auth-shell">
      <div className="auth-card" style={{ maxWidth: 640 }}>
        <div className="auth-brand">{t("auth.brand")}</div>
        <LanguageSwitcher variant="light" />
        <h1 className="auth-title">{t("choose_mode.title")}</h1>
        <p className="hint-text" style={{ marginBottom: 24 }}>{t("choose_mode.subtitle")}</p>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 16,
          }}
        >
          <button
            type="button"
            className="btn"
            disabled={submitting !== null}
            onClick={() => choose("simple")}
            style={{
              flexDirection: "column",
              alignItems: "flex-start",
              padding: 20,
              height: "auto",
              textAlign: "left",
              gap: 8,
            }}
          >
            <span style={{ fontSize: 28 }}>🚀</span>
            <strong style={{ fontSize: 16 }}>{t("choose_mode.simple_title")}</strong>
            <span className="hint-text">{t("choose_mode.simple_desc")}</span>
          </button>

          <button
            type="button"
            className="btn"
            disabled={submitting !== null}
            onClick={() => choose("advanced")}
            style={{
              flexDirection: "column",
              alignItems: "flex-start",
              padding: 20,
              height: "auto",
              textAlign: "left",
              gap: 8,
            }}
          >
            <span style={{ fontSize: 28 }}>⚙️</span>
            <strong style={{ fontSize: 16 }}>{t("choose_mode.advanced_title")}</strong>
            <span className="hint-text">{t("choose_mode.advanced_desc")}</span>
          </button>
        </div>

        <p className="hint-text" style={{ marginTop: 20 }}>{t("choose_mode.switch_later")}</p>
      </div>
    </div>
  );
}
