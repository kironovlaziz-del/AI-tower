"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { RiskPill, StatusPill } from "@/components/Pill";
import { getIncident, updateIncident } from "@/lib/api";
import type { Incident } from "@/lib/types";

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>();
  const incidentId = Number(params.id);

  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [rootCause, setRootCause] = useState("");
  const [status, setStatus] = useState("open");
  const [saving, setSaving] = useState(false);

  function refresh() {
    setLoading(true);
    getIncident(incidentId)
      .then((i) => {
        setIncident(i);
        setRootCause(i.root_cause || "");
        setStatus(i.status);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!Number.isNaN(incidentId)) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [incidentId]);

  async function handleSave() {
    setSaving(true);
    try {
      const updated = await updateIncident(incidentId, { root_cause: rootCause, status });
      setIncident(updated);
    } finally {
      setSaving(false);
    }
  }

  if (loading || !incident) {
    return (
      <>
        <PageHeader title="Инцидент" />
        <div className="content">
          <p className="loading-line">Загрузка…</p>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader title={`Инцидент #${incident.id}`} />
      <div className="content">
        <div className="breadcrumb">
          <Link href="/incidents">Incident Tracker</Link> / #{incident.id}
        </div>

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-body">
            <dl className="kv-grid">
              <dt>Категория</dt>
              <dd>{incident.category}</dd>
              <dt>Описание</dt>
              <dd>{incident.summary}</dd>
              <dt>Влияние</dt>
              <dd>{incident.impact || "—"}</dd>
              <dt>Серьёзность</dt>
              <dd>
                <RiskPill level={incident.severity} />
              </dd>
              <dt>Статус</dt>
              <dd>
                <StatusPill status={incident.status} />
              </dd>
              <dt>Связанный запрос</dt>
              <dd className="mono">
                {incident.request_id ? (
                  <Link href={`/requests/${incident.request_id}`}>
                    #{incident.request_id}
                  </Link>
                ) : (
                  "—"
                )}
              </dd>
              <dt>Создан</dt>
              <dd className="mono">
                {new Date(incident.created_at).toLocaleString("ru-RU")}
              </dd>
              <dt>Закрыт</dt>
              <dd className="mono">
                {incident.resolved_at
                  ? new Date(incident.resolved_at).toLocaleString("ru-RU")
                  : "—"}
              </dd>
            </dl>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Расследование</h2>
          </div>
          <div className="panel-body">
            <div className="field">
              <label htmlFor="root_cause">Первопричина</label>
              <textarea
                id="root_cause"
                value={rootCause}
                onChange={(e) => setRootCause(e.target.value)}
                placeholder="Что послужило причиной инцидента"
              />
            </div>
            <div className="field" style={{ maxWidth: 220 }}>
              <label htmlFor="status">Статус</label>
              <select id="status" value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="open">open</option>
                <option value="investigating">investigating</option>
                <option value="resolved">resolved</option>
              </select>
            </div>
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? "Сохраняем…" : "Сохранить"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
