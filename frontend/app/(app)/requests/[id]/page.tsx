"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { RiskPill, StatusPill } from "@/components/Pill";
import {
  createApproval,
  createOverride,
  getRequest,
  getRequestResponse,
  listOverrides,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AIRequest, AIResponse, Override } from "@/lib/types";

export default function RequestDetailPage() {
  const params = useParams<{ id: string }>();
  const requestId = Number(params.id);
  const { user } = useAuth();
  const { t, i18n } = useTranslation();

  const [request, setRequest] = useState<AIRequest | null>(null);
  const [response, setResponse] = useState<AIResponse | null>(null);
  const [overrides, setOverrides] = useState<Override[]>([]);
  const [loading, setLoading] = useState(true);
  const [routing, setRouting] = useState(false);
  const [overrideBusy, setOverrideBusy] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editText, setEditText] = useState("");
  const [overrideError, setOverrideError] = useState<string | null>(null);

  function refresh() {
    setLoading(true);
    Promise.all([
      getRequest(requestId),
      getRequestResponse(requestId).catch(() => null),
      listOverrides(requestId).catch(() => []),
    ])
      .then(([r, resp, ov]) => {
        setRequest(r);
        setResponse(resp);
        setOverrides(ov);
        setEditText(r.masked_input_text || "");
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!Number.isNaN(requestId)) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestId]);

  async function handleRouteToApproval() {
    if (!user) return;
    setRouting(true);
    try {
      await createApproval({ request_id: requestId, approver_user_id: user.id });
      refresh();
    } finally {
      setRouting(false);
    }
  }

  async function handleStop() {
    setOverrideError(null);
    setOverrideBusy(true);
    try {
      await createOverride({ request_id: requestId, override_type: "stop" });
      refresh();
    } catch {
      setOverrideError(t("requests.detail.stop_failed"));
    } finally {
      setOverrideBusy(false);
    }
  }

  async function handleRollback() {
    setOverrideError(null);
    setOverrideBusy(true);
    try {
      await createOverride({ request_id: requestId, override_type: "rollback" });
      refresh();
    } catch {
      setOverrideError(t("requests.detail.rollback_failed"));
    } finally {
      setOverrideBusy(false);
    }
  }

  async function handleSaveEdit() {
    setOverrideError(null);
    setOverrideBusy(true);
    try {
      await createOverride({
        request_id: requestId,
        override_type: "edit",
        override_payload_json: { masked_input_text: editText },
      });
      setEditMode(false);
      refresh();
    } catch {
      setOverrideError(t("requests.detail.edit_failed"));
    } finally {
      setOverrideBusy(false);
    }
  }

  if (loading || !request) {
    return (
      <>
        <PageHeader title={t("requests.title")} />
        <div className="content">
          <p className="loading-line">{t("requests.detail.loading")}</p>
        </div>
      </>
    );
  }

  const canStopOrEdit = ["pending", "pending_approval"].includes(request.status);
  const canRollback = ["completed", "approved"].includes(request.status);

  return (
    <>
      <PageHeader title={`#${request.id}`} />
      <div className="content">
        <div className="breadcrumb">
          <Link href="/requests">{t("requests.detail.breadcrumb")}</Link> / #{request.id}
        </div>

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-header">
            <h2>{t("requests.detail.request_section")}</h2>
          </div>
          <div className="panel-body">
            <dl className="kv-grid">
              <dt>{t("requests.detail.purpose")}</dt>
              <dd>{request.purpose}</dd>
              <dt>{t("requests.detail.risk")}</dt>
              <dd>
                <RiskPill level={request.risk_level} />
              </dd>
              <dt>{t("requests.detail.status")}</dt>
              <dd>
                <StatusPill status={request.status} />
              </dd>
              <dt>{t("requests.detail.use_case")}</dt>
              <dd className="mono">#{request.use_case_id ?? "—"}</dd>
              <dt>{t("requests.detail.provider")}</dt>
              <dd className="mono">#{request.provider_id ?? "—"}</dd>
              <dt>{t("requests.detail.created")}</dt>
              <dd className="mono">
                {new Date(request.created_at).toLocaleString(i18n.language)}
              </dd>
            </dl>
            <div className="section-title">{t("requests.detail.prompt_section")}</div>
            {editMode ? (
              <>
                <textarea
                  className="mono"
                  rows={4}
                  style={{ width: "100%" }}
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                />
                <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleSaveEdit}
                    disabled={overrideBusy}
                  >
                    {overrideBusy ? t("common.save") + "…" : t("common.save")}
                  </button>
                  <button
                    className="btn btn-sm"
                    onClick={() => {
                      setEditMode(false);
                      setEditText(request.masked_input_text || "");
                    }}
                  >
                    {t("common.cancel")}
                  </button>
                </div>
              </>
            ) : (
              <div className="text-block">
                {request.masked_input_text || "—"}
              </div>
            )}
            {request.firewall_flags && request.firewall_flags.length > 0 && (
              <>
                <div className="section-title">{t("requests.detail.flags_section")}</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {request.firewall_flags.map((flag) => (
                    <span
                      key={flag}
                      className={`pill ${
                        flag.startsWith("blocked_term:") ? "pill-critical" : "pill-accent"
                      }`}
                    >
                      {flag}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {request.status === "blocked" && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>{t("requests.detail.blocked_title")}</h2>
            </div>
            <div className="panel-body">
              <p className="hint-text">{t("requests.detail.blocked_hint")}</p>
            </div>
          </div>
        )}

        {request.status === "failed" && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>{t("requests.detail.failed_title")}</h2>
            </div>
            <div className="panel-body">
              <p className="hint-text">{t("requests.detail.failed_hint")}</p>
            </div>
          </div>
        )}

        {request.status === "pending_approval" && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>{t("requests.detail.approval_section")}</h2>
            </div>
            <div className="panel-body">
              <p className="hint-text" style={{ marginBottom: 12 }}>
                {t("requests.detail.approval_hint")}
              </p>
              <button
                className="btn btn-primary"
                onClick={handleRouteToApproval}
                disabled={routing}
              >
                {routing
                  ? t("requests.detail.sending")
                  : t("requests.detail.send_to_approval")}
              </button>
            </div>
          </div>
        )}

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-header">
            <h2>{t("requests.detail.response_section")}</h2>
          </div>
          <div className="panel-body">
            {response ? (
              <>
                <dl className="kv-grid">
                  <dt>{t("requests.detail.confidence")}</dt>
                  <dd className="mono">
                    {response.confidence_score != null
                      ? response.confidence_score.toFixed(2)
                      : "—"}
                  </dd>
                  <dt>{t("requests.detail.received")}</dt>
                  <dd className="mono">
                    {new Date(response.created_at).toLocaleString(i18n.language)}
                  </dd>
                </dl>
                <div className="section-title">{t("requests.detail.response_text")}</div>
                <div className="text-block">{response.response_text || "—"}</div>
              </>
            ) : (
              <p className="hint-text">{t("requests.detail.no_response")}</p>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>{t("requests.detail.override_title")}</h2>
          </div>
          <div className="panel-body">
            {!canStopOrEdit && !canRollback && (
              <p className="hint-text" style={{ marginBottom: 12 }}>
                {t("requests.detail.override_no_actions", { status: request.status })}
              </p>
            )}
            <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
              {canStopOrEdit && (
                <button className="btn btn-danger btn-sm" onClick={handleStop} disabled={overrideBusy}>
                  {t("requests.detail.stop")}
                </button>
              )}
              {canStopOrEdit && !editMode && (
                <button className="btn btn-sm" onClick={() => setEditMode(true)}>
                  {t("requests.detail.edit_prompt")}
                </button>
              )}
              {canRollback && (
                <button className="btn btn-danger btn-sm" onClick={handleRollback} disabled={overrideBusy}>
                  {t("requests.detail.rollback")}
                </button>
              )}
            </div>
            {overrideError && <p className="error-text">{overrideError}</p>}

            <div className="section-title">{t("requests.detail.override_history")}</div>
            {overrides.length === 0 ? (
              <p className="hint-text">{t("requests.detail.no_overrides")}</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>{t("requests.detail.col_time")}</th>
                    <th>{t("requests.detail.col_action")}</th>
                    <th>{t("requests.detail.col_operator")}</th>
                  </tr>
                </thead>
                <tbody>
                  {overrides.map((ov) => (
                    <tr key={ov.id}>
                      <td className="mono">
                        {new Date(ov.created_at).toLocaleString(i18n.language)}
                      </td>
                      <td>
                        {t(`requests.detail.override_labels.${ov.override_type}`, ov.override_type)}
                      </td>
                      <td className="mono">
                        {ov.operator_user_id != null ? `#${ov.operator_user_id}` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </>
  );
}