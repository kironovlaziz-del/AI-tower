"use client";

import { Form } from "@/components/Form";
import React, { useState } from "react";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import { register } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

export default function RegisterPage() {
  const { login } = useAuth();
  const { t } = useTranslation();
  const [form, setForm] = useState({
    org_name: "",
    name: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function update(field: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register({ ...form, role: "admin" } as never);
      await login(form.email, form.password);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(detail || t("register.failed"));
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">{t("auth.brand")}</div>
        <LanguageSwitcher variant="light" />
        <h1 className="auth-title">{t("register.title")}</h1>
        <Form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="org_name">{t("register.org_name")}</label>
            <input
              id="org_name"
              required
              value={form.org_name}
              onChange={(e) => update("org_name", e.target.value)}
              placeholder={t("register.org_name_placeholder")}
            />
          </div>
          <div className="field">
            <label htmlFor="name">{t("register.your_name")}</label>
            <input
              id="name"
              required
              value={form.name}
              onChange={(e) => update("name", e.target.value)}
              placeholder={t("register.your_name_placeholder")}
            />
          </div>
          <div className="field">
            <label htmlFor="email">{t("register.email")}</label>
            <input
              id="email"
              type="email"
              required
              value={form.email}
              onChange={(e) => update("email", e.target.value)}
              placeholder="you@company.com"
            />
          </div>
          <div className="field">
            <label htmlFor="password">{t("register.password")}</label>
            <input
              id="password"
              type="password"
              required
              minLength={6}
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
              placeholder={t("register.password_hint")}
            />
          </div>
          {error && <p className="error-text">{error}</p>}
          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", justifyContent: "center", marginTop: 4 }}
            disabled={submitting}
          >
            {submitting ? t("register.submitting") : t("register.submit")}
          </button>
        </Form>
        <p className="auth-switch">
          {t("register.already_have")}{" "}
          <Link href="/login">{t("register.login_link")}</Link>
        </p>
      </div>
    </div>
  );
}