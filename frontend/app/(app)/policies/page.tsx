"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/Pill";
import { createPolicy, listPolicies } from "@/lib/api";
import type { Policy } from "@/lib/types";

export default function PoliciesPage() {
  const router = useRouter();
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
      setError("Не удалось создать политику.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Policy Center"
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Отмена" : "Новая политика"}
          </button>
        }
      />
      <div className="content">
        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>Новая политика</h2>
            </div>
            <div className="panel-body">
              <form onSubmit={handleCreate}>
                <div className="field">
                  <label htmlFor="name">Название</label>
                  <input
                    id="name"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Например: Использование внешних LLM"
                  />
                </div>
                <div className="field">
                  <label htmlFor="description">Описание</label>
                  <textarea
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Правила, зона применения, ограничения"
                  />
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? "Создаём…" : "Создать политику"}
                </button>
              </form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>Политики</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Описание</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={4}>Загрузка…</td>
                </tr>
              )}
              {!loading && policies.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={4}>Политик пока нет — создайте первую</td>
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
