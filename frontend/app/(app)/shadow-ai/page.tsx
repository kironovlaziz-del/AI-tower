"use client";

import React, { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/Pill";
import {
  createShadowSighting,
  listShadowSightings,
  registerShadowSighting,
  updateShadowSighting,
} from "@/lib/api";
import type { ShadowSighting } from "@/lib/types";

const DETECTED_VIA_LABEL: Record<string, string> = {
  manual: "вручную",
  expense_report: "отчёт о расходах",
  network_proxy: "сетевой прокси",
  browser_extension: "браузерное расширение",
  other: "другое",
};

export default function ShadowAIPage() {
  const [sightings, setSightings] = useState<ShadowSighting[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  const [toolName, setToolName] = useState("");
  const [domain, setDomain] = useState("");
  const [detectedVia, setDetectedVia] = useState("manual");
  const [userHint, setUserHint] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    listShadowSightings()
      .then(setSightings)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createShadowSighting({
        tool_name: toolName,
        domain: domain || undefined,
        detected_via: detectedVia,
        user_hint: userHint || undefined,
        notes: notes || undefined,
      });
      setToolName("");
      setDomain("");
      setUserHint("");
      setNotes("");
      setDetectedVia("manual");
      setShowForm(false);
      refresh();
    } catch {
      setError("Не удалось сохранить находку.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSetStatus(id: number, status: string) {
    setBusyId(id);
    try {
      await updateShadowSighting(id, { status });
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  async function handleRegister(id: number) {
    setBusyId(id);
    try {
      await registerShadowSighting(id, { provider_type: "custom" });
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  const open = sightings.filter((s) => !["dismissed", "registered"].includes(s.status));
  const resolved = sightings.filter((s) => ["dismissed", "registered"].includes(s.status));

  return (
    <>
      <PageHeader
        title="Shadow AI Monitor"
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Отмена" : "Сообщить о находке"}
          </button>
        }
      />
      <div className="content">
        <p className="hint-text" style={{ marginBottom: 16 }}>
          Реестр несанкционированного использования AI-инструментов: ручные
          сигналы, отчёты о расходах, данные сетевого прокси или браузерного
          расширения. Каждую находку нужно подтвердить, зарегистрировать как
          легитимного поставщика или отклонить.
        </p>

        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>Новая находка</h2>
            </div>
            <div className="panel-body">
              <form onSubmit={handleCreate}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="tool_name">Инструмент</label>
                    <input
                      id="tool_name"
                      required
                      value={toolName}
                      onChange={(e) => setToolName(e.target.value)}
                      placeholder="Например: ChatGPT (личный аккаунт), Midjourney"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="domain">Домен</label>
                    <input
                      id="domain"
                      value={domain}
                      onChange={(e) => setDomain(e.target.value)}
                      placeholder="chat.openai.com"
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="detected_via">Источник обнаружения</label>
                    <select
                      id="detected_via"
                      value={detectedVia}
                      onChange={(e) => setDetectedVia(e.target.value)}
                    >
                      <option value="manual">Вручную</option>
                      <option value="expense_report">Отчёт о расходах</option>
                      <option value="network_proxy">Сетевой прокси</option>
                      <option value="browser_extension">Браузерное расширение</option>
                      <option value="other">Другое</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="user_hint">Сотрудник (если известен)</label>
                    <input
                      id="user_hint"
                      value={userHint}
                      onChange={(e) => setUserHint(e.target.value)}
                      placeholder="email или имя"
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="notes">Заметки</label>
                  <textarea
                    id="notes"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Обстоятельства обнаружения, контекст"
                  />
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? "Сохраняем…" : "Сохранить находку"}
                </button>
              </form>
            </div>
          </div>
        )}

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-header">
            <h2>Требуют разбора</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>Инструмент</th>
                <th>Домен</th>
                <th>Источник</th>
                <th>Сотрудник</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={6}>Загрузка…</td>
                </tr>
              )}
              {!loading && open.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={6}>Открытых находок нет</td>
                </tr>
              )}
              {open.map((s) => (
                <tr key={s.id}>
                  <td>{s.tool_name}</td>
                  <td className="mono">{s.domain || "—"}</td>
                  <td>{DETECTED_VIA_LABEL[s.detected_via] ?? s.detected_via}</td>
                  <td>{s.user_hint || "—"}</td>
                  <td>
                    <StatusPill status={s.status} />
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      {s.status === "new" && (
                        <button
                          className="btn btn-sm"
                          disabled={busyId === s.id}
                          onClick={() => handleSetStatus(s.id, "reviewing")}
                        >
                          В работу
                        </button>
                      )}
                      <button
                        className="btn btn-sm btn-danger"
                        disabled={busyId === s.id}
                        onClick={() => handleSetStatus(s.id, "confirmed_shadow")}
                      >
                        Подтвердить риск
                      </button>
                      <button
                        className="btn btn-sm btn-primary"
                        disabled={busyId === s.id}
                        onClick={() => handleRegister(s.id)}
                      >
                        Зарегистрировать
                      </button>
                      <button
                        className="btn btn-sm"
                        disabled={busyId === s.id}
                        onClick={() => handleSetStatus(s.id, "dismissed")}
                      >
                        Отклонить
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Разобранные</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>Инструмент</th>
                <th>Статус</th>
                <th>Провайдер</th>
                <th>Закрыто</th>
              </tr>
            </thead>
            <tbody>
              {!loading && resolved.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={4}>Пока ничего не разобрано</td>
                </tr>
              )}
              {resolved.map((s) => (
                <tr key={s.id}>
                  <td>{s.tool_name}</td>
                  <td>
                    <StatusPill status={s.status} />
                  </td>
                  <td className="mono">
                    {s.registered_provider_id ? `#${s.registered_provider_id}` : "—"}
                  </td>
                  <td className="mono">
                    {s.resolved_at ? new Date(s.resolved_at).toLocaleString("ru-RU") : "—"}
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
