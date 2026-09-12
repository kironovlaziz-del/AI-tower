"use client";

import { Form } from "@/components/Form";
import React, { useState } from "react";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/lib/auth";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

export default function LoginPage() {
  const { login } = useAuth();
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(detail || t("auth.login_failed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">{t("auth.brand")}</div>
        <LanguageSwitcher variant="light" />
        <h1 className="auth-title">{t("auth.login_title")}</h1>
        <Form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="email">{t("auth.email")}</label>
            <input
              id="email"
              type="email"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </div>
          <div className="field">
            <label htmlFor="password">{t("auth.password")}</label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          {error && <p className="error-text">{error}</p>}
          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", justifyContent: "center", marginTop: 4 }}
            disabled={submitting}
          >
            {submitting ? t("auth.login_button_loading") : t("auth.login_button")}
          </button>
        </Form>
        <p className="auth-switch">
          {t("auth.no_account")} <Link href="/register">{t("auth.register_link")}</Link>
        </p>
      </div>
    </div>
  );
}