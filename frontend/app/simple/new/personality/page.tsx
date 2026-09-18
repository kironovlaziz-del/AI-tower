"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useWizard, type WizardStyleKey } from "@/lib/wizard";

const STYLES: { key: WizardStyleKey; icon: string; titleKey: string; exampleKey: string }[] = [
  { key: "friendly", icon: "😊", titleKey: "simple_mode.style_friendly", exampleKey: "simple_mode.style_friendly_example" },
  { key: "formal", icon: "🎩", titleKey: "simple_mode.style_formal", exampleKey: "simple_mode.style_formal_example" },
  { key: "concise", icon: "⚡", titleKey: "simple_mode.style_concise", exampleKey: "simple_mode.style_concise_example" },
  { key: "custom", icon: "✏️", titleKey: "simple_mode.style_custom", exampleKey: "" },
];

export default function WizardPersonalityPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const { state, updatePersonality } = useWizard();
  const [newRule, setNewRule] = useState("");

  function addRule() {
    if (!newRule.trim()) return;
    updatePersonality({ extraRules: [...state.personality.extraRules, newRule.trim()] });
    setNewRule("");
  }

  function removeRule(index: number) {
    updatePersonality({
      extraRules: state.personality.extraRules.filter((_, i) => i !== index),
    });
  }

  return (
    <>
      <button
        className="btn btn-sm"
        onClick={() =>
          router.push(state.qaPairs.length > 0 ? "/simple/new/review" : "/simple/new/parsed")
        }
        style={{ marginBottom: 20 }}
      >
        ← {t("common.back")}
      </button>
      <h1 style={{ fontSize: 20, marginBottom: 8 }}>{t("simple_mode.personality_title")}</h1>
      <p className="hint-text" style={{ marginBottom: 20 }}>{t("simple_mode.personality_subtitle")}</p>

      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
        {STYLES.map((s) => (
          <button
            key={s.key}
            className="btn"
            onClick={() => updatePersonality({ styleKey: s.key })}
            style={{
              flexDirection: "column",
              alignItems: "flex-start",
              padding: "14px 18px",
              gap: 4,
              textAlign: "left",
              borderColor:
                state.personality.styleKey === s.key ? "var(--accent, #2451d9)" : undefined,
              borderWidth: state.personality.styleKey === s.key ? 2 : undefined,
            }}
          >
            <span style={{ fontWeight: 600 }}>
              {s.icon} {t(s.titleKey)}
            </span>
            {s.exampleKey && <span className="hint-text">«{t(s.exampleKey)}»</span>}
          </button>
        ))}
      </div>

      {state.personality.styleKey === "custom" && (
        <div className="field" style={{ marginBottom: 16 }}>
          <textarea
            placeholder={t("simple_mode.style_custom_placeholder")}
            value={state.personality.customStyleText}
            onChange={(e) => updatePersonality({ customStyleText: e.target.value })}
          />
        </div>
      )}

      <div className="field" style={{ marginBottom: 16 }}>
        <label>{t("simple_mode.personality_company_name")}</label>
        <input
          value={state.personality.companyName}
          onChange={(e) => updatePersonality({ companyName: e.target.value })}
          placeholder={t("simple_mode.personality_company_placeholder")}
        />
      </div>

      <div style={{ marginBottom: 24 }}>
        <label style={{ display: "block", marginBottom: 8, fontSize: 13, fontWeight: 600 }}>
          {t("simple_mode.personality_rules")}
        </label>
        {state.personality.extraRules.map((rule, i) => (
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
            <span style={{ fontSize: 13 }}>{rule}</span>
            <button className="btn btn-sm" onClick={() => removeRule(i)}>✕</button>
          </div>
        ))}
        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={newRule}
            onChange={(e) => setNewRule(e.target.value)}
            placeholder={t("simple_mode.personality_rule_placeholder")}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addRule())}
          />
          <button className="btn btn-sm" onClick={addRule}>
            + {t("simple_mode.personality_add_rule")}
          </button>
        </div>
      </div>

      <button
        className="btn btn-primary"
        style={{ width: "100%", justifyContent: "center" }}
        onClick={() => router.push("/simple/new/test")}
      >
        {t("simple_mode.continue")} →
      </button>
    </>
  );
}
