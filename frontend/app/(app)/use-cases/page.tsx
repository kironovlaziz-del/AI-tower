"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { RiskPill, StatusPill } from "@/components/Pill";
import { createUseCase, listUseCases } from "@/lib/api";
import type { RiskLevel, UseCase } from "@/lib/types";

export default function UseCasesPage() {
  const router = useRouter();
  const [useCases, setUseCases] = useState<UseCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [riskLevel, setRiskLevel] = useState<RiskLevel>("low");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    listUseCases()
      .then(setUseCases)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createUseCase({ name, risk_level: riskLevel });
      setName("");
      setRiskLevel("low");
      setShowForm(false);
      refresh();
    } catch {
      setError("Не удалось создать сценарий.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Сценарии использования"
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Отмена" : "Новый сценарий"}
          </button>
        }
      />
      <div className="content">
        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>Новый сценарий использования</h2>
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
                      placeholder="Например: Поддержка клиентов через GPT"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="risk">Уровень риска</label>
                    <select
                      id="risk"
                      value={riskLevel}
                      onChange={(e) => setRiskLevel(e.target.value as RiskLevel)}
                    >
                      <option value="low">low</option>
                      <option value="medium">medium</option>
                      <option value="high">high</option>
                      <option value="critical">critical</option>
                    </select>
                  </div>
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? "Создаём…" : "Создать сценарий"}
                </button>
              </form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>Все сценарии</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Риск</th>
                <th>Статус</th>
                <th>Политика</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={5}>Загрузка…</td>
                </tr>
              )}
              {!loading && useCases.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={5}>Сценариев пока нет</td>
                </tr>
              )}
              {useCases.map((uc) => (
                <tr
                  key={uc.id}
                  className="clickable"
                  onClick={() => router.push(`/use-cases/${uc.id}`)}
                >
                  <td className="mono">#{uc.id}</td>
                  <td>{uc.name}</td>
                  <td>
                    <RiskPill level={uc.risk_level} />
                  </td>
                  <td>
                    <StatusPill status={uc.status} />
                  </td>
                  <td className="mono">
                    {uc.approved_policy_version_id
                      ? `version #${uc.approved_policy_version_id}`
                      : "не привязана"}
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
