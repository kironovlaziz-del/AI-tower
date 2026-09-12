"use client";

import { Form } from "@/components/Form";
import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useTranslation } from "react-i18next";
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
  const { t, i18n } = useTranslation();

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
      setError(t("policies.detail.invalid_json"));
      return;
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
      <PageHeader title={policy.name} />
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
                <textarea
                  id="rules"
                  className="mono"
                  rows={6}
                  value={rulesText}
                  onChange={(e) => setRulesText(e.target.value)}
                />
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