"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
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

const OVERRIDE_LABEL: Record<string, string> = {
  stop: "остановлен оператором",
  edit: "промпт изменён оператором",
  rollback: "откачен оператором",
};

export default function RequestDetailPage() {
  const params = useParams<{ id: string }>();
  const requestId = Number(params.id);
  const { user } = useAuth();

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
        setEditText(r.masked_input_text || r.input_text || "");
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
      setOverrideError("Не удалось остановить запрос.");
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
      setOverrideError("Не удалось откатить запрос.");
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
      setOverrideError("Не удалось изменить текст промпта.");
    } finally {
      setOverrideBusy(false);
    }
  }

  if (loading || !request) {
    return (
      <>
        <PageHeader title="Action Trace" />
        <div className="content">
          <p className="loading-line">Загрузка…</p>
        </div>
      </>
    );
  }

  const canStopOrEdit = ["pending", "pending_approval"].includes(request.status);
  const canRollback = ["completed", "approved"].includes(request.status);

  return (
    <>
      <PageHeader title={`Запрос #${request.id}`} />
      <div className="content">
        <div className="breadcrumb">
          <Link href="/requests">Usage Registry</Link> / #{request.id}
        </div>

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-header">
            <h2>1. Запрос</h2>
          </div>
          <div className="panel-body">
            <dl className="kv-grid">
              <dt>Назначение</dt>
              <dd>{request.purpose}</dd>
              <dt>Уровень риска</dt>
              <dd>
                <RiskPill level={request.risk_level} />
              </dd>
              <dt>Статус</dt>
              <dd>
                <StatusPill status={request.status} />
              </dd>
              <dt>Сценарий</dt>
              <dd className="mono">#{request.use_case_id ?? "—"}</dd>
              <dt>Поставщик</dt>
              <dd className="mono">#{request.provider_id ?? "—"}</dd>
              <dt>Создан</dt>
              <dd className="mono">
                {new Date(request.created_at).toLocaleString("ru-RU")}
              </dd>
            </dl>
            <div className="section-title">Промпт (после маскирования Prompt Firewall)</div>
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
                    {overrideBusy ? "Сохраняем…" : "Сохранить"}
                  </button>
                  <button
                    className="btn btn-sm"
                    onClick={() => {
                      setEditMode(false);
                      setEditText(request.masked_input_text || request.input_text || "");
                    }}
                  >
                    Отмена
                  </button>
                </div>
              </>
            ) : (
              <div className="text-block">
                {request.masked_input_text || request.input_text || "—"}
              </div>
            )}
            {request.firewall_flags && request.firewall_flags.length > 0 && (
              <>
                <div className="section-title">Флаги Prompt Firewall</div>
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
              <h2>Заблокировано Prompt Firewall</h2>
            </div>
            <div className="panel-body">
              <p className="hint-text">
                Промпт содержит термин из блок-листа активной политики и не был
                отправлен поставщику. Исходный текст сохранён только для
                расследования и недоступен провайдеру.
              </p>
            </div>
          </div>
        )}

        {request.status === "failed" && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>Ошибка вызова подключения</h2>
            </div>
            <div className="panel-body">
              <p className="hint-text">
                Реальный вызов AI-провайдера завершился ошибкой (см. текст
                ответа ниже). Проверьте API-ключ и base URL на странице{" "}
                <a href="/connections">Connections</a>.
              </p>
            </div>
          </div>
        )}

        {request.status === "pending_approval" && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>2. Approval Workflow</h2>
            </div>
            <div className="panel-body">
              <p className="hint-text" style={{ marginBottom: 12 }}>
                Политика требует согласования перед выполнением этого запроса.
              </p>
              <button className="btn btn-primary" onClick={handleRouteToApproval} disabled={routing}>
                {routing ? "Отправляем…" : "Отправить на согласование"}
              </button>
            </div>
          </div>
        )}

        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-header">
            <h2>3. Ответ провайдера</h2>
          </div>
          <div className="panel-body">
            {response ? (
              <>
                <dl className="kv-grid">
                  <dt>Уверенность</dt>
                  <dd className="mono">
                    {response.confidence_score != null
                      ? response.confidence_score.toFixed(2)
                      : "—"}
                  </dd>
                  <dt>Получен</dt>
                  <dd className="mono">
                    {new Date(response.created_at).toLocaleString("ru-RU")}
                  </dd>
                </dl>
                <div className="section-title">Текст ответа</div>
                <div className="text-block">{response.response_text || "—"}</div>
              </>
            ) : (
              <p className="hint-text">
                Ответа пока нет — запрос ожидает согласования или обработки.
              </p>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Override Console</h2>
          </div>
          <div className="panel-body">
            {!canStopOrEdit && !canRollback && (
              <p className="hint-text" style={{ marginBottom: 12 }}>
                Для запроса в статусе «{request.status}» ручные действия недоступны.
              </p>
            )}
            <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
              {canStopOrEdit && (
                <button className="btn btn-danger btn-sm" onClick={handleStop} disabled={overrideBusy}>
                  Остановить
                </button>
              )}
              {canStopOrEdit && !editMode && (
                <button className="btn btn-sm" onClick={() => setEditMode(true)}>
                  Изменить текст промпта
                </button>
              )}
              {canRollback && (
                <button className="btn btn-danger btn-sm" onClick={handleRollback} disabled={overrideBusy}>
                  Откатить
                </button>
              )}
            </div>
            {overrideError && <p className="error-text">{overrideError}</p>}

            <div className="section-title">История ручных действий</div>
            {overrides.length === 0 ? (
              <p className="hint-text">Ручных вмешательств по этому запросу не было.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Время</th>
                    <th>Действие</th>
                    <th>Оператор</th>
                  </tr>
                </thead>
                <tbody>
                  {overrides.map((ov) => (
                    <tr key={ov.id}>
                      <td className="mono">
                        {new Date(ov.created_at).toLocaleString("ru-RU")}
                      </td>
                      <td>{OVERRIDE_LABEL[ov.override_type] ?? ov.override_type}</td>
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
