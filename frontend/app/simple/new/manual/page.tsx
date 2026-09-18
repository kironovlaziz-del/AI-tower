"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useWizard } from "@/lib/wizard";
import { recommendApproach } from "@/lib/api";

export default function WizardManualPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const { state, update } = useWizard();
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  function addPair() {
    if (!question.trim() || !answer.trim()) return;
    update({
      qaPairs: [...state.qaPairs, { question: question.trim(), answer: answer.trim() }],
      hasUnstructuredText: false,
      uploadedFileName: state.uploadedFileName || t("simple_mode.manual_source_label"),
    });
    setQuestion("");
    setAnswer("");
  }

  function removePair(index: number) {
    update({ qaPairs: state.qaPairs.filter((_, i) => i !== index) });
  }

  async function proceed() {
    const result = await recommendApproach({
      task_type: state.taskType || "other",
      has_documents: false,
      qa_pair_count: state.qaPairs.length,
    });
    update({
      recommendedApproach: result.approach as typeof state.recommendedApproach,
      recommendedReason: result.reason,
    });
    router.push(state.qaPairs.length > 0 ? "/simple/new/review" : "/simple/new/personality");
  }

  return (
    <>
      <button
        className="btn btn-sm"
        onClick={() => router.push("/simple/new/source")}
        style={{ marginBottom: 20 }}
      >
        ← {t("common.back")}
      </button>
      <h1 style={{ fontSize: 20, marginBottom: 8 }}>{t("simple_mode.manual_title")}</h1>
      <p className="hint-text" style={{ marginBottom: 20 }}>{t("simple_mode.manual_subtitle")}</p>

      <div className="panel" style={{ marginBottom: 20 }}>
        <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div className="field">
            <label>{t("simple_mode.review_question")}</label>
            <input value={question} onChange={(e) => setQuestion(e.target.value)} />
          </div>
          <div className="field">
            <label>{t("simple_mode.review_answer")}</label>
            <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} />
          </div>
          <button className="btn btn-primary btn-sm" onClick={addPair} disabled={!question.trim() || !answer.trim()}>
            + {t("simple_mode.manual_add")}
          </button>
        </div>
      </div>

      {state.qaPairs.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <p className="hint-text" style={{ marginBottom: 8 }}>
            {t("simple_mode.manual_added_count", { count: state.qaPairs.length })}
          </p>
          {state.qaPairs.map((pair, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "8px 12px",
                background: "var(--bg-app, #f5f6f8)",
                borderRadius: 6,
                marginBottom: 6,
              }}
            >
              <span style={{ fontSize: 13 }}>
                <strong>{pair.question}</strong> — {pair.answer}
              </span>
              <button className="btn btn-sm" onClick={() => removePair(i)}>✕</button>
            </div>
          ))}
        </div>
      )}

      <button
        className="btn btn-primary"
        style={{ width: "100%", justifyContent: "center" }}
        disabled={state.qaPairs.length === 0}
        onClick={proceed}
      >
        {t("simple_mode.continue")} →
      </button>
    </>
  );
}
