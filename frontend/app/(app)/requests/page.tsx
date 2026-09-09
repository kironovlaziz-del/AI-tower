"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { RiskPill, StatusPill } from "@/components/Pill";
import { createRequest, listProviders, listRequests, listUseCases } from "@/lib/api";
import type { AIRequest, Provider, UseCase } from "@/lib/types";

export default function RequestsPage() {
  const router = useRouter();
  const [requests, setRequests] = useState<AIRequest[]>([]);
  const [useCases, setUseCases] = useState<UseCase[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const [useCaseId, setUseCaseId] = useState<number | "">("");
  const [providerId, setProviderId] = useState<number | "">("");
  const [purpose, setPurpose] = useState("");
  const [inputText, setInputText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    Promise.all([listRequests(), listUseCases(), listProviders()])
      .then(([r, uc, p]) => {
        setRequests(r);
        setUseCases(uc);
        setProviders(p);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!useCaseId || !providerId) {
      setError("Выберите сценарий использования и поставщика.");
      return;
    }
    setSubmitting(true);
    try {
      await createRequest({
        use_case_id: Number(useCaseId),
        provider_id: Number(providerId),
        purpose,
        input_text: inputText,
      });
      setPurpose("");
      setInputText("");
      setShowForm(false);
      refresh();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(detail || "Не удалось создать запрос.");
    } finally {
      setSubmitting(false);
    }
  }

  const canCreate = useCases.length > 0 && providers.length > 0;

  return (
    <>
      <PageHeader
        title="Usage Registry"
        actions={
          <button
            className="btn btn-primary btn-sm"
            onClick={() => setShowForm((s) => !s)}
            disabled={!canCreate}
            title={canCreate ? undefined : "Сначала создайте сценарий и поставщика"}
          >
            {showForm ? "Отмена" : "Новый запрос"}
          </button>
        }
      />
      <div className="content">
        {!canCreate && (
          <p className="hint-text" style={{ marginBottom: 16 }}>
            Чтобы регистрировать запросы, сначала создайте хотя бы один{" "}
            <a href="/use-cases">сценарий использования</a> и одного{" "}
            <a href="/providers">поставщика</a>.
          </p>
        )}

        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>Новый запрос к AI</h2>
            </div>
            <div className="panel-body">
              <form onSubmit={handleCreate}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="use_case">Сценарий использования</label>
                    <select
                      id="use_case"
                      value={useCaseId}
                      onChange={(e) => setUseCaseId(Number(e.target.value))}
                      required
                    >
                      <option value="">Выберите…</option>
                      {useCases.map((uc) => (
                        <option key={uc.id} value={uc.id}>
                          {uc.name} ({uc.risk_level})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="provider">Поставщик</label>
                    <select
                      id="provider"
                      value={providerId}
                      onChange={(e) => setProviderId(Number(e.target.value))}
                      required
                    >
                      <option value="">Выберите…</option>
                      {providers.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name} ({p.type})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="purpose">Назначение</label>
                  <input
                    id="purpose"
                    required
                    value={purpose}
                    onChange={(e) => setPurpose(e.target.value)}
                    placeholder="Например: суммаризация обращения клиента"
                  />
                </div>
                <div className="field">
                  <label htmlFor="input_text">Текст запроса (промпт)</label>
                  <textarea
                    id="input_text"
                    required
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Промпт, который будет отправлен провайдеру"
                  />
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? "Отправляем…" : "Отправить запрос"}
                </button>
              </form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>Все запросы</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Назначение</th>
                <th>Риск</th>
                <th>Статус</th>
                <th>Создан</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={5}>Загрузка…</td>
                </tr>
              )}
              {!loading && requests.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={5}>Запросов пока нет</td>
                </tr>
              )}
              {requests.map((r) => (
                <tr
                  key={r.id}
                  className="clickable"
                  onClick={() => router.push(`/requests/${r.id}`)}
                >
                  <td className="mono">#{r.id}</td>
                  <td>{r.purpose}</td>
                  <td>
                    <RiskPill level={r.risk_level} />
                  </td>
                  <td>
                    <StatusPill status={r.status} />
                  </td>
                  <td className="mono">
                    {new Date(r.created_at).toLocaleString("ru-RU")}
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
