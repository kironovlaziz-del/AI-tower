"use client";

import React, { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { listProviders, chatWithRagCollection, getRagCollection } from "@/lib/api";
import type { Provider } from "@/lib/types";
import type { RagCollectionInfo } from "@/lib/api";
import { translateApiError } from "@/lib/errors";

interface ChatMessage {
  role: "user" | "model";
  text: string;
}

export default function SimpleModelChatPage() {
  const params = useParams<{ collectionId: string }>();
  const collectionId = Number(params.collectionId);
  const router = useRouter();
  const { t } = useTranslation();

  const [collection, setCollection] = useState<RagCollectionInfo | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [providerId, setProviderId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getRagCollection(collectionId).then(setCollection);
    listProviders().then((all) => {
      const withCreds = all.filter((p) => p.has_credentials);
      setProviders(withCreds);
      if (withCreds.length > 0) setProviderId(withCreds[0].id);
    });
  }, [collectionId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    if (!draft.trim() || !providerId) return;
    const question = draft.trim();
    setMessages((m) => [...m, { role: "user", text: question }]);
    setDraft("");
    setSending(true);
    setError(null);
    try {
      const result = await chatWithRagCollection(collectionId, question, providerId);
      setMessages((m) => [...m, { role: "model", text: result.answer }]);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
        ?.detail;
      setError(translateApiError(detail, t, t("simple_mode.chat_failed")));
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <button className="btn btn-sm" onClick={() => router.push("/simple")} style={{ marginBottom: 20 }}>
        ← {t("simple_mode.back_to_dashboard")}
      </button>
      <h1 style={{ fontSize: 20, marginBottom: 20 }}>🤖 {collection?.name || "..."}</h1>

      {providers.length > 1 && (
        <div className="field" style={{ marginBottom: 12 }}>
          <select value={providerId ?? ""} onChange={(e) => setProviderId(Number(e.target.value))}>
            {providers.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
      )}

      <div className="panel" style={{ minHeight: 300, marginBottom: 16 }}>
        <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {messages.length === 0 && (
            <p className="hint-text">{t("simple_mode.chat_empty")}</p>
          )}
          {messages.map((m, i) => (
            <div key={i}>
              <p style={{ fontWeight: m.role === "user" ? 600 : 400 }}>
                {m.role === "user" ? "👤" : "🤖"} {m.text}
              </p>
            </div>
          ))}
          <div ref={endRef} />
        </div>
      </div>

      {error && <p className="error-text" style={{ marginBottom: 12 }}>{error}</p>}

      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder={t("simple_mode.chat_placeholder")}
          disabled={!providerId}
          style={{ flex: 1 }}
        />
        <button className="btn btn-primary" onClick={send} disabled={sending || !providerId}>
          {sending ? t("common.loading") : t("simple_mode.test_ask")}
        </button>
      </div>
      {providers.length === 0 && (
        <p className="hint-text" style={{ marginTop: 12 }}>{t("simple_mode.test_no_provider")}</p>
      )}
    </>
  );
}
