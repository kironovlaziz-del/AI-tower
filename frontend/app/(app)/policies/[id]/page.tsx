"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/Pill";
import {
  approvePolicyVersion,
  createPolicyVersion,
  getPolicy,
  listPolicyVersions,
} from "@/lib/api";
import type { Policy, PolicyVersion } from "@/lib/types";

export default function PolicyDetailPage() {
  const params = useParams<{ id: string }>();
  const policyId = Number(params.id);

  const [policy, setPolicy] = useState<Policy | null>(null);
  const [versions, setVersions] = useState<PolicyVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [rulesText, setRulesText] = useState(
    '{\n  "effect": "require_approval"\n}'
  );
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    Promise.all([getPolicy(policyId), listPolicyVersions(policyId)])
      .then(([p, v]) => {
        setPolicy(p);
        setVersions(v.sort((a, b) => b.version - a.version));
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!Number.isNaN(policyId)) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [policyId]);

  async function handleCreateVersion(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(rulesText);
    } catch {
      setError("Правила должны быть корректным JSON.");
      return;
    }
    setSubmitting(true);
    try {
      await createPolicyVersion(policyId, parsed);
      refresh();
    } catch {
      setError("Не удалось создать версию.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleApprove(versionId: number) {
    await approvePolicyVersion(policyId, versionId);
    refresh();
  }

  if (loading || !policy) {
    return (
      <>
        <PageHeader title="Политика" />
        <div className="content">
          <p className="loading-line">Загрузка…</p>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader title={policy.name} />
      <div className="content">
        <div className="breadcrumb">
          <Link href="/policies">Policy Center</Link> / #{policy.id}
        </div>

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-body">
            <dl className="kv-grid">
              <dt>Статус</dt>
              <dd>
                <StatusPill status={policy.status} />
              </dd>
              <dt>Описание</dt>
              <dd>{policy.description || "—"}</dd>
              <dt>Создана</dt>
              <dd className="mono">
                {new Date(policy.created_at).toLocaleString("ru-RU")}
              </dd>
            </dl>
          </div>
        </div>

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-header">
            <h2>Новая версия правил</h2>
          </div>
          <div className="panel-body">
            <form onSubmit={handleCreateVersion}>
              <div className="field">
                <label htmlFor="rules">Правила (JSON)</label>
                <textarea
                  id="rules"
                  className="mono"
                  rows={6}
                  value={rulesText}
                  onChange={(e) => setRulesText(e.target.value)}
                />
                <span className="hint-text">
                  Например: {"{ \"effect\": \"require_approval\" }"} — заставит
                  привязанные сценарии проходить согласование.
                </span>
              </div>
              {error && <p className="error-text">{error}</p>}
              <button className="btn btn-primary" type="submit" disabled={submitting}>
                {submitting ? "Сохраняем…" : "Создать версию"}
              </button>
            </form>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>История версий</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>Версия</th>
                <th>Правила</th>
                <th>Создана</th>
                <th>Согласование</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {versions.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={5}>Версий пока нет</td>
                </tr>
              )}
              {versions.map((v) => (
                <tr key={v.id}>
                  <td className="mono">v{v.version}</td>
                  <td className="mono">{JSON.stringify(v.rules_json)}</td>
                  <td className="mono">
                    {new Date(v.created_at).toLocaleString("ru-RU")}
                  </td>
                  <td>
                    {v.approved_at ? (
                      <span className="pill pill-low">approved</span>
                    ) : (
                      <span className="pill pill-neutral">pending</span>
                    )}
                  </td>
                  <td>
                    {!v.approved_at && (
                      <button
                        className="btn btn-sm"
                        onClick={() => handleApprove(v.id)}
                      >
                        Согласовать
                      </button>
                    )}
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
