"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { WizardProvider } from "@/lib/wizard";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

export default function SimpleModeLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const { t } = useTranslation();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading) {
    return <div className="loading-line" style={{ padding: 40 }}>{t("common.loading")}</div>;
  }
  if (!user) return null;

  return (
    <WizardProvider>
      <div style={{ minHeight: "100vh", background: "var(--bg-app, #f5f6f8)" }}>
        <header
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "14px 24px",
            background: "var(--bg-panel, #fff)",
            borderBottom: "1px solid var(--border, #e5e7eb)",
          }}
        >
          <Link
            href="/simple"
            style={{ fontWeight: 700, fontSize: 16, textDecoration: "none", color: "inherit" }}
          >
            {t("auth.brand")}
          </Link>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <LanguageSwitcher />
            <span className="hint-text">👤 {user.name}</span>
            <Link href="/simple/settings" title={t("simple_mode.settings")} style={{ fontSize: 18 }}>
              ⚙️
            </Link>
            <button className="btn btn-sm" onClick={logout}>
              {t("sidebar.logout")}
            </button>
          </div>
        </header>
        <main style={{ maxWidth: 720, margin: "0 auto", padding: "32px 20px" }}>{children}</main>
      </div>
    </WizardProvider>
  );
}
