"use client";

import React, { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/Pill";
import { translateApiError } from "@/lib/errors";
import {
  chatWithDeployment,
  listDeployments,
  type DeploymentChatResponse,
} from "@/lib/api";
import type { ModelDeployment } from "@/lib/types";

interface ChatMessage {
  id: number;
  role: "user" | "model";
  text: string;
  meta?: {
    label?: string;
    latency_ms?: number;
    version?: number;
    model_type?: string;
  };
}

let nextId = 1;

export default function PlaygroundPage() {
  const { t } = useTranslation();
  const [deployments, setDeployments] = useState<ModelDeployment[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  function refresh() {
    setLoading(true);
    listDeployments()
      .then((d) => {
        setDeployments(d.filter((x) => x.status === "active"));
        if (d.length > 0 && selectedId == null) {
          setSelectedId(d[0].id);
        }
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  // Reset conversation when switching models.
  useEffect(() => {
    setMessages([]);
    setError(null);
  }, [selectedId]);

  // Auto-scroll on new message.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const selected = deployments.find((d) => d.id === selectedId) || null;

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!selected || !draft.trim() || sending) return;

    const userText = draft.trim();
    setDraft("");
    setError(null);
    setMessages((m) => [...m, { id: nextId++, role: "user", text: userText }]);
    setSending(true);

    try {
      const res: DeploymentChatResponse = await chatWithDeployment(
        selected.id,
        userText,
      );

      // For classification tasks, translate the raw label into a nicer
      // sentence. Generation models just echo the produced text.
      let displayText: string;
      if (res.model_type === "transformer_text_classification") {
        displayText = t("playground.classified_as", { label: res.response });
      } else {
        displayText = res.response;
      }

      setMessages((m) => [
        ...m,
        {
          id: nextId++,
          role: "model",
          text: displayText,
          meta: {
            latency_ms: res.latency_ms,
            version: res.version,
            model_type: res.model_type,
          },
        },
      ]);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })
        ?.response?.data?.detail;
      setError(translateApiError(detail, t, t("playground.failed")));
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends; Shift+Enter inserts a newline.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend(e as unknown as React.FormEvent);
    }
  }

  const activeCount = deployments.length;

  return (
    <>
      <PageHeader title={t("playground.title")} />
      <div className="content playground-content">
        <div className="playground-layout">
          {/* Model picker */}
          <aside className="playground-sidebar">
            <div className="panel">
              <div className="panel-header">
                <h2>{t("playground.models")}</h2>
                <span className="pill pill-neutral">{activeCount}</span>
              </div>
              <div className="panel-body" style={{ padding: 8 }}>
                {loading && (
                  <p className="hint-text" style={{ padding: 8 }}>
                    {t("playground.loading")}
                  </p>
                )}
                {!loading && activeCount === 0 && (
                  <p className="hint-text" style={{ padding: 8 }}>
                    {t("playground.no_models")}
                  </p>
                )}
                {deployments.map((d) => (
                  <button
                    key={d.id}
                    type="button"
                    className={`playground-model-row${
                      selectedId === d.id ? " active" : ""
                    }`}
                    onClick={() => setSelectedId(d.id)}
                  >
                    <div className="playground-model-name">{d.name}</div>
                    <div className="playground-model-meta">
                      <span className="mono">v{d.version}</span>
                      <StatusPill status={d.status} />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </aside>

          {/* Chat panel */}
          <section className="playground-chat-panel">
            <div className="panel playground-chat">
              <div className="panel-header">
                <h2>
                  {selected
                    ? `${selected.name} v${selected.version}`
                    : t("playground.pick_model")}
                </h2>
                {selected && (
                  <span className="pill pill-accent">
                    #{selected.training_job_id}
                  </span>
                )}
              </div>

              <div className="playground-messages">
                {messages.length === 0 && selected && (
                  <div className="playground-empty">
                    <p>{t("playground.empty_hint")}</p>
                    <p className="hint-text">
                      {t("playground.empty_examples")}
                    </p>
                  </div>
                )}
                {messages.length === 0 && !selected && (
                  <div className="playground-empty">
                    <p>{t("playground.pick_model_hint")}</p>
                  </div>
                )}

                {messages.map((m) => (
                  <div
                    key={m.id}
                    className={`playground-bubble playground-bubble-${m.role}`}
                  >
                    <div className="playground-bubble-text">{m.text}</div>
                    {m.meta && (
                      <div className="playground-bubble-meta mono">
                        v{m.meta.version} · {m.meta.latency_ms} ms
                      </div>
                    )}
                  </div>
                ))}

                {sending && (
                  <div className="playground-bubble playground-bubble-model">
                    <div className="playground-typing">
                      <span className="playground-dot" />
                      <span className="playground-dot" />
                      <span className="playground-dot" />
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              <form className="playground-input" onSubmit={handleSend}>
                <textarea
                  ref={inputRef}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    selected
                      ? t("playground.placeholder")
                      : t("playground.pick_model_placeholder")
                  }
                  disabled={!selected || sending}
                  rows={2}
                />
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={!selected || !draft.trim() || sending}
                >
                  {sending ? t("playground.sending") : t("playground.send")}
                </button>
              </form>

              {error && (
                <p className="error-text" style={{ padding: "0 16px 12px" }}>
                  {error}
                </p>
              )}
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
