"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { RiskPill, StatusPill } from "@/components/Pill";
import { createIncident, listIncidents } from "@/lib/api";
import type { Incident, RiskLevel } from "@/lib/types";

export default function IncidentsPage() {
  const router = useRouter();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [severity, setSeverity] = useState<RiskLevel>("low");
  const [category, setCategory] = useState("");
  const [summary, setSummary] = useState("");
  const [impact, setImpact] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    listIncidents()
      .then(setIncidents)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createIncident({ severity, category, summary, impact: impact || undefined });
      setCategory("");
      setSummary("");
      setImpact("");
      setSeverity("low");
      setShowForm(false);
      refresh();
    } catch {
      setError("Не удалось создать инцидент.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Incident Tracker"
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Отмена" : "Новый инцидент"}
          </button>
        }
      />
      <div className="content">
        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>Зарегистрировать инцидент</h2>
            </div>
            <div className="panel-body">
              <form onSubmit={handleCreate}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="severity">Серьёзность</label>
                    <select
                      id="severity"
                      value={severity}
                      onChange={(e) => setSeverity(e.target.value as RiskLevel)}
                    >
                      <option value="low">low</option>
                      <option value="medium">medium</option>
                      <option value="high">high</option>
                      <option value="critical">critical</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="category">Категория</label>
                    <input
                      id="category"
                      required
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      placeholder="Например: утечка данных, галлюцинация, сбой провайдера"
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="summary">Краткое описание</label>
                  <input
                    id="summary"
                    required
                    value={summary}
                    onChange={(e) => setSummary(e.target.value)}
                    placeholder="Что произошло"
                  />
                </div>
                <div className="field">
                  <label htmlFor="impact">Влияние</label>
                  <textarea
                    id="impact"
                    value={impact}
                    onChange={(e) => setImpact(e.target.value)}
                    placeholder="Кого и что затронуло"
                  />
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? "Создаём…" : "Зарегистрировать"}
                </button>
              </form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>Все инциденты</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Категория</th>
                <th>Описание</th>
                <th>Серьёзность</th>
                <th>Статус</th>
                <th>Создан</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={6}>Загрузка…</td>
                </tr>
              )}
              {!loading && incidents.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={6}>Инцидентов пока нет</td>
                </tr>
              )}
              {incidents.map((i) => (
                <tr
                  key={i.id}
                  className="clickable"
                  onClick={() => router.push(`/incidents/${i.id}`)}
                >
                  <td className="mono">#{i.id}</td>
                  <td>{i.category}</td>
                  <td>{i.summary}</td>
                  <td>
                    <RiskPill level={i.severity} />
                  </td>
                  <td>
                    <StatusPill status={i.status} />
                  </td>
                  <td className="mono">
                    {new Date(i.created_at).toLocaleString("ru-RU")}
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
