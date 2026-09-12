"use client";

import { Form } from "@/components/Form";
import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/Pill";
import { createPolicy, listPolicies } from "@/lib/api";
import type { Policy } from "@/lib/types";

export default function PoliciesPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    listPolicies()
      .then(setPolicies)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createPolicy({ name, description: description || undefined });
      setName("");
      setDescription("");
      setShowForm(false);
      refresh();
    } catch {
      setError(t("policies.failed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHeader
        title={t("policies.title")}
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? t("policies.cancel") : t("policies.new")}
          </button>
        }
      />
      <div className="content">
        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>{t("policies.form_title")}</h2>
            </div>
            <div className="panel-body">
              <Form onSubmit={handleCreate}>
                <div className="field">
                  <label htmlFor="name">{t("policies.name")}</label>
                  <input
                    id="name"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder={t("policies.name_placeholder")}
                  />
                </div>
                <div className="field">
                  <label htmlFor="description">{t("policies.description")}</label>
                  <textarea
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder={t("policies.description_placeholder")}
                  />
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? t("policies.submitting") : t("policies.submit")}
                </button>
              </Form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>{t("policies.title")}</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>{t("policies.col_id")}</th>
                <th>{t("policies.col_name")}</th>
                <th>{t("policies.col_description")}</th>
                <th>{t("policies.col_status")}</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={4}>{t("common.loading")}</td>
                </tr>
              )}
              {!loading && policies.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={4}>{t("policies.empty")}</td>
                </tr>
              )}
              {policies.map((p) => (
                <tr
                  key={p.id}
                  className="clickable"
                  onClick={() => router.push(`/policies/${p.id}`)}
                >
                  <td className="mono">#{p.id}</td>
                  <td>{p.name}</td>
                  <td>{p.description || "—"}</td>
                  <td>
                    <StatusPill status={p.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}