"use client";

import React, { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import {
  createNotificationChannel,
  deleteNotificationChannel,
  getNotificationEventTypes,
  listNotificationChannels,
  testNotificationChannel,
  updateNotificationChannel,
} from "@/lib/api";
import type { NotificationChannel, NotificationChannelType } from "@/lib/types";

const EVENT_LABELS: Record<string, string> = {
  incident_created: "Создан инцидент",
  approval_pending: "Требуется согласование",
  shadow_ai_reported: "Замечено несанкционированное использование AI",
  request_blocked: "Запрос заблокирован Prompt Firewall",
  training_completed: "Обучение модели завершено",
  training_failed: "Обучение модели не удалось",
};

export default function NotificationsPage() {
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [eventTypes, setEventTypes] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  const [channelType, setChannelType] = useState<NotificationChannelType>("email");
  const [target, setTarget] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    Promise.all([listNotificationChannels(), getNotificationEventTypes()])
      .then(([c, e]) => {
        setChannels(c);
        setEventTypes(e);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  function toggleEvent(event: string) {
    setSelectedEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (selectedEvents.length === 0) {
      setError("Выберите хотя бы одно событие.");
      return;
    }
    setSubmitting(true);
    try {
      await createNotificationChannel({
        channel_type: channelType,
        target,
        events: selectedEvents,
      });
      setTarget("");
      setSelectedEvents([]);
      setShowForm(false);
      refresh();
    } catch {
      setError("Не удалось создать канал.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleEnabled(ch: NotificationChannel) {
    setBusyId(ch.id);
    try {
      await updateNotificationChannel(ch.id, { enabled: !ch.enabled });
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id: number) {
    setBusyId(id);
    try {
      await deleteNotificationChannel(id);
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  async function handleTest(id: number) {
    setBusyId(id);
    try {
      await testNotificationChannel(id);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Notification Service"
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Отмена" : "Новый канал"}
          </button>
        }
      />
      <div className="content">
        <p className="hint-text" style={{ marginBottom: 16 }}>
          Email отправляется только если на сервере настроен SMTP (см. `.env`
          — `SMTP_HOST` и другие переменные). Webhook работает всегда — на
          указанный URL уходит POST с JSON {"{ subject, message, metadata }"}.
        </p>

        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>Новый канал уведомлений</h2>
            </div>
            <div className="panel-body">
              <form onSubmit={handleCreate}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="channel_type">Тип</label>
                    <select
                      id="channel_type"
                      value={channelType}
                      onChange={(e) => setChannelType(e.target.value as NotificationChannelType)}
                    >
                      <option value="email">Email</option>
                      <option value="webhook">Webhook</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="target">
                      {channelType === "email" ? "Email-адрес" : "Webhook URL"}
                    </label>
                    <input
                      id="target"
                      required
                      value={target}
                      onChange={(e) => setTarget(e.target.value)}
                      placeholder={
                        channelType === "email"
                          ? "ops@example.com"
                          : "https://hooks.slack.com/services/..."
                      }
                    />
                  </div>
                </div>
                <div className="field">
                  <label>События</label>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {eventTypes.map((ev) => (
                      <label
                        key={ev}
                        style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}
                      >
                        <input
                          type="checkbox"
                          checked={selectedEvents.includes(ev)}
                          onChange={() => toggleEvent(ev)}
                        />
                        {EVENT_LABELS[ev] ?? ev}
                      </label>
                    ))}
                  </div>
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? "Создаём…" : "Создать канал"}
                </button>
              </form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>Каналы уведомлений</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>Тип</th>
                <th>Куда</th>
                <th>События</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={5}>Загрузка…</td>
                </tr>
              )}
              {!loading && channels.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={5}>Каналов пока нет</td>
                </tr>
              )}
              {channels.map((ch) => (
                <tr key={ch.id}>
                  <td className="mono">{ch.channel_type}</td>
                  <td className="mono">{ch.target}</td>
                  <td style={{ maxWidth: 280 }}>
                    {ch.events_json.map((ev) => EVENT_LABELS[ev] ?? ev).join(", ")}
                  </td>
                  <td>
                    <span className={`pill ${ch.enabled ? "pill-low" : "pill-neutral"}`}>
                      {ch.enabled ? "включён" : "выключен"}
                    </span>
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button
                        className="btn btn-sm"
                        disabled={busyId === ch.id}
                        onClick={() => handleTest(ch.id)}
                      >
                        Тест
                      </button>
                      <button
                        className="btn btn-sm"
                        disabled={busyId === ch.id}
                        onClick={() => handleToggleEnabled(ch)}
                      >
                        {ch.enabled ? "Выключить" : "Включить"}
                      </button>
                      <button
                        className="btn btn-sm btn-danger"
                        disabled={busyId === ch.id}
                        onClick={() => handleDelete(ch.id)}
                      >
                        Удалить
                      </button>
                    </div>
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
