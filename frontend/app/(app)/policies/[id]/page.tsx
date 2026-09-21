"use client";

import { Form } from "@/components/Form";
import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { PolicyRuleBuilder } from "@/components/PolicyRuleBuilder";
import { StatusPill } from "@/components/Pill";
import {
  archivePolicy,
  activatePolicy,
  approvePolicyVersion,
  createPolicyVersion,
  getPolicy,
  listPolicyVersions,
} from "@/lib/api";
import type { Policy, PolicyVersion } from "@/lib/types";

export default function PolicyDetailPage() {
  const params = useParams<{ id: string }>();
  const policyId = Number(params.id);
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const [statusBusy, setStatusBusy] = useState(false);

  async function reloadPolicy() {
    try { const p = await getPolicy(policyId); setPolicy(p); } catch {}
  }
  async function handleArchive() {
    setStatusBusy(true);
    try { await archivePolicy(policyId); await reloadPolicy(); } finally { setStatusBusy(false); }
  }
  async function handleActivate() {
    setStatusBusy(true);
    try { await activatePolicy(policyId); await reloadPolicy(); } finally { setStatusBusy(false); }
  }

  const [policy, setPolicy] = useState<Policy | null>(null);
  const [versions, setVersions] = useState<PolicyVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [rulesText, setRulesText] = useState(
    '{\n  "effect": "require_approval"\n}'
  );
  const [ruleMode, setRuleMode] = useState<"visual"|"json">("visual");
  const [ruleObj, setRuleObj] = useState<Record<string,unknown>>({});
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
    if (ruleMode === "visual") {
      parsed = ruleObj;
    } else {
      try {
        parsed = JSON.parse(rulesText);
      } catch {
        setError(t("policies.detail.invalid_json"));
        return;
      }
    }
    setSubmitting(true);
    try {
      await createPolicyVersion(policyId, parsed);
      refresh();
    } catch {
      setError(t("policies.detail.create_failed"));
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
        <PageHeader title={t("policies.title")} />
        <div className="content">
          <p className="loading-line">{t("policies.detail.loading")}</p>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title={policy.name}
        actions={
          <div style={{ display: "inline-flex", gap: 8 }}>
            {policy.status === "active" ? (
              <button className="btn btn-sm" onClick={handleArchive} disabled={statusBusy}>{t("policies.detail.archive")}</button>
            ) : (
              <button className="btn btn-sm btn-primary" onClick={handleActivate} disabled={statusBusy}>{t("policies.detail.activate")}</button>
            )}
          </div>
        }
      />
      <div className="content">
        <div className="breadcrumb">
          <Link href="/policies">{t("policies.detail.breadcrumb")}</Link> / #{policy.id}
        </div>

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-body">
            <dl className="kv-grid">
              <dt>{t("policies.detail.status")}</dt>
              <dd>
                <StatusPill status={policy.status} />
              </dd>
              <dt>{t("policies.detail.description")}</dt>
              <dd>{policy.description || "—"}</dd>
              <dt>{t("policies.detail.created")}</dt>
              <dd className="mono">
                {new Date(policy.created_at).toLocaleString(i18n.language)}
              </dd>
            </dl>
          </div>
        </div>

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-header">
            <h2>{t("policies.detail.new_version_title")}</h2>
          </div>
          <div className="panel-body">
            <Form onSubmit={handleCreateVersion}>
              <div className="field">
                <label htmlFor="rules">{t("policies.detail.rules")}</label>
                {(() => null)()}
                <div style={{ display: "inline-flex", gap: 4, marginBottom: 10, border: "1px solid var(--border)", borderRadius: 8, padding: 3 }}>
                  <button type="button" className="btn btn-sm" style={{ background: ruleMode === "visual" ? "var(--bg-app)" : "transparent" }}
                    onClick={() => { setRuleMode("visual"); }}>{t("rulebuilder.mode_visual")}</button>
                  <button type="button" className="btn btn-sm" style={{ background: ruleMode === "json" ? "var(--bg-app)" : "transparent" }}
                    onClick={() => { setRulesText(JSON.stringify(ruleObj, null, 2)); setRuleMode("json"); }}>{t("rulebuilder.mode_json")}</button>
                </div>
                {ruleMode === "visual"
                  ? <PolicyRuleBuilder value={ruleObj} onChange={setRuleObj} />
                  : <textarea value={rulesText} onChange={(e) => setRulesText(e.target.value)} rows={7} style={{ width: "100%", fontFamily: "monospace", fontSize: 13 }} />}
                <span className="hint-text">{t("policies.detail.rules_hint")}</span>
              </div>
              {error && <p className="error-text">{error}</p>}
              <button className="btn btn-primary" type="submit" disabled={submitting}>
                {submitting
                  ? t("policies.detail.creating_version")
                  : t("policies.detail.create_version")}
              </button>
            </Form>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>{t("policies.detail.history_title")}</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>{t("policies.detail.col_version")}</th>
                <th>{t("policies.detail.col_rules")}</th>
                <th>{t("policies.detail.col_created")}</th>
                <th>{t("policies.detail.col_approval")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {versions.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={5}>{t("policies.detail.empty_versions")}</td>
                </tr>
              )}
              {versions.map((v) => (
                <tr key={v.id}>
                  <td className="mono">v{v.version}</td>
                  <td className="mono">{JSON.stringify(v.rules_json)}</td>
                  <td className="mono">
                    {new Date(v.created_at).toLocaleString(i18n.language)}
                  </td>
                  <td>
                    {v.approved_at ? (
                      <span className="pill pill-low">
                        {t("policies.detail.approved")}
                      </span>
                    ) : (
                      <span className="pill pill-neutral">
                        {t("policies.detail.pending")}
                      </span>
                    )}
                  </td>
                  <td>
                    {!v.approved_at && (
                      <button
                        className="btn btn-sm"
                        onClick={() => handleApprove(v.id)}
                      >
                        {t("policies.detail.approve")}
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