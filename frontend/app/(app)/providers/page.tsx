"use client";

import React, { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/Pill";
import { createProvider, listProviders, updateProvider } from "@/lib/api";
import type { Provider } from "@/lib/types";

export default function ProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("openai");
  const [sla, setSla] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    listProviders()
      .then(setProviders)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createProvider({ name, type, sla: sla || undefined });
      setName("");
      setSla("");
      setShowForm(false);
      refresh();
    } catch {
      setError("Не удалось добавить поставщика.");
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleStatus(p: Provider) {
    const next = p.status === "active" ? "suspended" : "active";
    await updateProvider(p.id, { status: next });
    refresh();
  }

  return (
    <>
      <PageHeader
        title="Vendor Risk Desk"
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Отмена" : "Добавить поставщика"}
          </button>
        }
      />
      <div className="content">
        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>Новый поставщик AI</h2>
            </div>
            <div className="panel-body">
              <form onSubmit={handleCreate}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="name">Название</label>
                    <input
                      id="name"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="OpenAI, Anthropic, Azure OpenAI…"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="type">Тип</label>
                    <input
                      id="type"
                      required
                      value={type}
                      onChange={(e) => setType(e.target.value)}
                      placeholder="openai / anthropic / custom"
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="sla">SLA</label>
                  <input
                    id="sla"
                    value={sla}
                    onChange={(e) => setSla(e.target.value)}
                    placeholder="Например: 99.9% uptime, 24ч поддержка"
                  />
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? "Добавляем…" : "Добавить поставщика"}
                </button>
              </form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>Поставщики</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Тип</th>
                <th>SLA</th>
                <th>Риск-скор</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={7}>Загрузка…</td>
                </tr>
              )}
              {!loading && providers.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={7}>
                    Поставщиков пока нет — добавьте, чтобы можно было создавать запросы
                  </td>
                </tr>
              )}
              {providers.map((p) => (
                <tr key={p.id}>
                  <td className="mono">#{p.id}</td>
                  <td>{p.name}</td>
                  <td className="mono">{p.type}</td>
                  <td>{p.sla || "—"}</td>
                  <td className="mono">{p.risk_score.toFixed(1)}</td>
                  <td>
                    <StatusPill status={p.status} />
                  </td>
                  <td>
                    <button className="btn btn-sm" onClick={() => toggleStatus(p)}>
                      {p.status === "active" ? "Приостановить" : "Активировать"}
                    </button>
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
