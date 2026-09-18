"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useWizard } from "@/lib/wizard";

const PREVIEW_COUNT = 3;

export default function WizardReviewPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const { state, update } = useWizard();
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editQ, setEditQ] = useState("");
  const [editA, setEditA] = useState("");
  const [addingNew, setAddingNew] = useState(false);
  const [newQ, setNewQ] = useState("");
  const [newA, setNewA] = useState("");

  function startEdit(index: number) {
    setEditingIndex(index);
    setEditQ(state.qaPairs[index].question);
    setEditA(state.qaPairs[index].answer);
  }

  function saveEdit() {
    if (editingIndex === null) return;
    const next = [...state.qaPairs];
    next[editingIndex] = { question: editQ, answer: editA };
    update({ qaPairs: next });
    setEditingIndex(null);
  }

  function removePair(index: number) {
    update({ qaPairs: state.qaPairs.filter((_, i) => i !== index) });
  }

  function addPair() {
    if (!newQ.trim() || !newA.trim()) return;
    update({ qaPairs: [...state.qaPairs, { question: newQ.trim(), answer: newA.trim() }] });
    setNewQ("");
    setNewA("");
    setAddingNew(false);
  }

  const visible = state.qaPairs.slice(0, PREVIEW_COUNT);
  const remaining = state.qaPairs.length - visible.length;

  return (
    <>
      <button
        className="btn btn-sm"
        onClick={() => router.push("/simple/new/parsed")}
        style={{ marginBottom: 20 }}
      >
        ← {t("common.back")}
      </button>
      <h1 style={{ fontSize: 20, marginBottom: 24 }}>{t("simple_mode.review_title")}</h1>

      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 12 }}>
        {visible.map((pair, i) => (
          <div key={i} className="panel">
            <div className="panel-body">
              {editingIndex === i ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <input value={editQ} onChange={(e) => setEditQ(e.target.value)} />
                  <textarea value={editA} onChange={(e) => setEditA(e.target.value)} />
                  <div style={{ display: "flex", gap: 8 }}>
                    <button className="btn btn-sm btn-primary" onClick={saveEdit}>
                      {t("common.save")}
                    </button>
                    <button className="btn btn-sm" onClick={() => setEditingIndex(null)}>
                      {t("common.cancel")}
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                  <div>
                    <p style={{ fontWeight: 600 }}>{t("simple_mode.review_question")}: {pair.question}</p>
                    <p className="hint-text">{t("simple_mode.review_answer")}: {pair.answer}</p>
                  </div>
                  <div style={{ display: "flex", gap: 6, whiteSpace: "nowrap" }}>
                    <button className="btn btn-sm" onClick={() => startEdit(i)}>✏️</button>
                    <button className="btn btn-sm" onClick={() => removePair(i)}>🗑️</button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {remaining > 0 && (
        <p className="hint-text" style={{ marginBottom: 16 }}>
          {t("simple_mode.review_and_more", { count: remaining })}
        </p>
      )}

      {addingNew ? (
        <div className="panel" style={{ marginBottom: 16 }}>
          <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <input
              placeholder={t("simple_mode.review_question")}
              value={newQ}
              onChange={(e) => setNewQ(e.target.value)}
            />
            <textarea
              placeholder={t("simple_mode.review_answer")}
              value={newA}
              onChange={(e) => setNewA(e.target.value)}
            />
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-sm btn-primary" onClick={addPair}>
                {t("common.save")}
              </button>
              <button className="btn btn-sm" onClick={() => setAddingNew(false)}>
                {t("common.cancel")}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <button className="btn btn-sm" onClick={() => setAddingNew(true)} style={{ marginBottom: 20 }}>
          + {t("simple_mode.review_add_pair")}
        </button>
      )}

      <button
        className="btn btn-primary"
        style={{ width: "100%", justifyContent: "center" }}
        onClick={() => router.push("/simple/new/personality")}
      >
        {t("simple_mode.continue")} →
      </button>
    </>
  );
}
