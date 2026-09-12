"use client";

import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { Form } from "@/components/Form";
import {
  createNotificationChannel,
  deleteNotificationChannel,
  getNotificationEventTypes,
  listNotificationChannels,
  testNotificationChannel,
  updateNotificationChannel,
} from "@/lib/api";
import type { NotificationChannel, NotificationChannelType } from "@/lib/types";

export default function NotificationsPage() {
  const { t } = useTranslation();
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
      setError(t("notifications.need_event"));
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
      setError(t("notifications.failed"));
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
        title={t("notifications.title")}
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? t("notifications.cancel") : t("notifications.new")}
          </button>
        }
      />
      <div className="content">
        <p className="hint-text" style={{ marginBottom: 16 }}>
          {t("notifications.hint")}
        </p>

        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>{t("notifications.form_title")}</h2>
            </div>
            <div className="panel-body">
              <Form onSubmit={handleCreate}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="channel_type">{t("notifications.type")}</label>
                    <select
                      id="channel_type"
                      value={channelType}
                      onChange={(e) => setChannelType(e.target.value as NotificationChannelType)}
                    >
                      <option value="email">{t("notifications.type_email")}</option>
                      <option value="webhook">{t("notifications.type_webhook")}</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="target">
                      {channelType === "email"
                        ? t("notifications.target_email")
                        : t("notifications.target_webhook")}
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
                  <label>{t("notifications.events")}</label>
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
                        {t(`notifications.events_map.${ev}`, ev)}
                      </label>
                    ))}
                  </div>
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? t("notifications.submitting") : t("notifications.submit")}
                </button>
              </Form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>{t("notifications.table_title")}</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>{t("notifications.col_type")}</th>
                <th>{t("notifications.col_target")}</th>
                <th>{t("notifications.col_events")}</th>
                <th>{t("notifications.col_status")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={5}>{t("notifications.loading")}</td>
                </tr>
              )}
              {!loading && channels.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={5}>{t("notifications.empty")}</td>
                </tr>
              )}
              {channels.map((ch) => (
                <tr key={ch.id}>
                  <td className="mono">{ch.channel_type}</td>
                  <td className="mono">{ch.target}</td>
                  <td style={{ maxWidth: 280 }}>
                    {ch.events_json
                      .map((ev) => t(`notifications.events_map.${ev}`, ev))
                      .join(", ")}
                  </td>
                  <td>
                    <span className={`pill ${ch.enabled ? "pill-low" : "pill-neutral"}`}>
                      {ch.enabled ? t("notifications.enabled") : t("notifications.disabled")}
                    </span>
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button
                        className="btn btn-sm"
                        disabled={busyId === ch.id}
                        onClick={() => handleTest(ch.id)}
                      >
                        {t("notifications.test")}
                      </button>
                      <button
                        className="btn btn-sm"
                        disabled={busyId === ch.id}
                        onClick={() => handleToggleEnabled(ch)}
                      >
                        {ch.enabled ? t("notifications.disable") : t("notifications.enable")}
                      </button>
                      <button
                        className="btn btn-sm btn-danger"
                        disabled={busyId === ch.id}
                        onClick={() => handleDelete(ch.id)}
                      >
                        {t("notifications.delete")}
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
