"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useWizard } from "@/lib/wizard";
import { listProviders, previewWizardChat } from "@/lib/api";
import type { Provider } from "@/lib/types";
import { translateApiError } from "@/lib/errors";

export default function WizardTestPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const { state, update, systemPrompt } = useWizard();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProviders().then((all) => {
      const withCreds = all.filter((p) => p.has_credentials);
      setProviders(withCreds);
      if (withCreds.length > 0 && !state.providerId) {
        update({ providerId: withCreds[0].id });
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function ask() {
    if (!question.trim() || !state.providerId) return;
    setAsking(true);
    setError(null);
    setAnswer(null);
    try {
      const result = await previewWizardChat({
        message: question,
        system_prompt: systemPrompt(),
        provider_id: state.providerId,
      });
      setAnswer(result.answer);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
        ?.detail;
      setError(translateApiError(detail, t, t("simple_mode.test_failed")));
    } finally {
      setAsking(false);
    }
  }

  return (
    <>
      <button
        className="btn btn-sm"
        onClick={() => router.push("/simple/new/personality")}
        style={{ marginBottom: 20 }}
      >
        ← {t("common.back")}
      </button>
      <h1 style={{ fontSize: 20, marginBottom: 8 }}>{t("simple_mode.test_title")}</h1>
      <p className="hint-text" style={{ marginBottom: 20 }}>{t("simple_mode.test_subtitle")}</p>

      {providers.length === 0 ? (
        <p className="hint-text" style={{ marginBottom: 20 }}>
          {t("simple_mode.test_no_provider")}
        </p>
      ) : (
        <div className="field" style={{ marginBottom: 16 }}>
          <label>{t("simple_mode.test_provider")}</label>
          <select
            value={state.providerId ?? ""}
            onChange={(e) => update({ providerId: Number(e.target.value) })}
          >
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="field" style={{ marginBottom: 12 }}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={t("simple_mode.test_question_placeholder")}
          onKeyDown={(e) => e.key === "Enter" && ask()}
        />
      </div>
      <button
        className="btn btn-primary"
        onClick={ask}
        disabled={asking || !question.trim() || !state.providerId}
        style={{ marginBottom: 20 }}
      >
        {asking ? t("common.loading") : t("simple_mode.test_ask")}
      </button>

      {answer && (
        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-body">
            <p style={{ marginBottom: 4 }}>👤 {question}</p>
            <p>🤖 {answer}</p>
          </div>
        </div>
      )}
      {error && <p className="error-text" style={{ marginBottom: 20 }}>{error}</p>}

      <button
        className="btn btn-primary"
        style={{ width: "100%", justifyContent: "center" }}
        onClick={() => router.push("/simple/new/training")}
      >
        {t("simple_mode.test_train_button")} →
      </button>
    </>
  );
}
