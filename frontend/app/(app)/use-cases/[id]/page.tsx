"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { RiskPill, StatusPill } from "@/components/Pill";
import {
  getUseCase,
  listPolicies,
  listPolicyVersions,
  updateUseCase,
} from "@/lib/api";
import type { Policy, PolicyVersion, RiskLevel, UseCase } from "@/lib/types";

export default function UseCaseDetailPage() {
  const params = useParams<{ id: string }>();
  const useCaseId = Number(params.id);

  const [useCase, setUseCase] = useState<UseCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [riskLevel, setRiskLevel] = useState<RiskLevel>("low");
  const [status, setStatus] = useState("active");
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const [policies, setPolicies] = useState<Policy[]>([]);
  const [selectedPolicyId, setSelectedPolicyId] = useState<number | "">("");
  const [versions, setVersions] = useState<PolicyVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<number | "">("");
  const [linking, setLinking] = useState(false);

  function refresh() {
    setLoading(true);
    getUseCase(useCaseId)
      .then((uc) => {
        setUseCase(uc);
        setRiskLevel(uc.risk_level);
        setStatus(uc.status);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!Number.isNaN(useCaseId)) refresh();
    listPolicies().then(setPolicies);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [useCaseId]);

  useEffect(() => {
    if (!selectedPolicyId) {
      setVersions([]);
      return;
    }
    listPolicyVersions(Number(selectedPolicyId)).then(setVersions);
  }, [selectedPolicyId]);

  async function handleSave() {
    setSaving(true);
    try {
      const updated = await updateUseCase(useCaseId, { risk_level: riskLevel, status });
      setUseCase(updated);
      setSavedAt(Date.now());
    } finally {
      setSaving(false);
    }
  }

  async function handleLinkPolicyVersion() {
    if (!selectedVersionId) return;
    setLinking(true);
    try {
      const updated = await updateUseCase(useCaseId, {
        approved_policy_version_id: Number(selectedVersionId),
      });
      setUseCase(updated);
    } finally {
      setLinking(false);
    }
  }

  if (loading || !useCase) {
    return (
      <>
        <PageHeader title="Сценарий использования" />
        <div className="content">
          <p className="loading-line">Загрузка…</p>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader title={useCase.name} />
      <div className="content">
        <div className="breadcrumb">
          <Link href="/use-cases">Сценарии использования</Link> / #{useCase.id}
        </div>

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-body">
            <dl className="kv-grid">
              <dt>Текущий риск</dt>
              <dd>
                <RiskPill level={useCase.risk_level} />
              </dd>
              <dt>Статус</dt>
              <dd>
                <StatusPill status={useCase.status} />
              </dd>
              <dt>Владелец (user id)</dt>
              <dd className="mono">{useCase.owner_user_id ?? "—"}</dd>
              <dt>Привязанная версия политики</dt>
              <dd className="mono">
                {useCase.approved_policy_version_id
                  ? `#${useCase.approved_policy_version_id}`
                  : "не привязана"}
              </dd>
              <dt>Создан</dt>
              <dd className="mono">
                {new Date(useCase.created_at).toLocaleString("ru-RU")}
              </dd>
            </dl>
          </div>
        </div>

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-header">
            <h2>Изменить</h2>
          </div>
          <div className="panel-body">
            <div className="form-row">
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
              <div className="field">
                <label htmlFor="status">Статус</label>
                <select id="status" value={status} onChange={(e) => setStatus(e.target.value)}>
                  <option value="active">active</option>
                  <option value="inactive">inactive</option>
                  <option value="suspended">suspended</option>
                </select>
              </div>
            </div>
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? "Сохраняем…" : "Сохранить изменения"}
            </button>
            {savedAt && (
              <span className="hint-text" style={{ marginLeft: 12 }}>
                Сохранено
              </span>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Привязать версию политики</h2>
          </div>
          <div className="panel-body">
            <p className="hint-text" style={{ marginBottom: 12 }}>
              Правила выбранной версии (например, <code>require_approval</code> или{" "}
              <code>blocked_terms</code>) будут применяться ко всем запросам в
              рамках этого сценария.
            </p>
            <div className="form-row">
              <div className="field">
                <label htmlFor="policy">Политика</label>
                <select
                  id="policy"
                  value={selectedPolicyId}
                  onChange={(e) => {
                    setSelectedPolicyId(e.target.value ? Number(e.target.value) : "");
                    setSelectedVersionId("");
                  }}
                >
                  <option value="">Выберите политику…</option>
                  {policies.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="version">Версия</label>
                <select
                  id="version"
                  value={selectedVersionId}
                  onChange={(e) =>
                    setSelectedVersionId(e.target.value ? Number(e.target.value) : "")
                  }
                  disabled={versions.length === 0}
                >
                  <option value="">Выберите версию…</option>
                  {versions.map((v) => (
                    <option key={v.id} value={v.id}>
                      v{v.version} (#{v.id}) {v.approved_at ? "— согласована" : "— не согласована"}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button
              className="btn btn-primary"
              onClick={handleLinkPolicyVersion}
              disabled={!selectedVersionId || linking}
            >
              {linking ? "Привязываем…" : "Привязать выбранную версию"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
