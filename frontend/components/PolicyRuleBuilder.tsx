"use client";

import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";

// A regular policy version's rules_json understands:
//   blocked_terms: string[]   -> a prompt containing any is rejected
//   effect: "require_approval" -> every request under this policy needs sign-off
// PII masking is automatic in the Prompt Firewall and is not configured here.

function toList(s: string): string[] {
  return s.split(/[,\n]/).map((x) => x.trim()).filter(Boolean);
}

export function PolicyRuleBuilder({
  value,
  onChange,
}: {
  value: Record<string, unknown>;
  onChange: (rules: Record<string, unknown>) => void;
}) {
  const { t } = useTranslation();

  const [blockedTerms, setBlockedTerms] = useState<string>(() => {
    const v = value?.blocked_terms;
    return Array.isArray(v) ? v.join(", ") : "";
  });
  const [requireApproval, setRequireApproval] = useState<boolean>(
    () => value?.effect === "require_approval"
  );

  useEffect(() => {
    const rules: Record<string, unknown> = {};
    const terms = toList(blockedTerms);
    if (terms.length) rules.blocked_terms = terms;
    if (requireApproval) rules.effect = "require_approval";
    onChange(rules);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [blockedTerms, requireApproval]);

  return (
    <div>
      <div style={{ border: "1px solid var(--border,#e5e7eb)", borderRadius: 8, padding: 12, marginBottom: 12 }}>
        <strong style={{ fontSize: 14 }}>🚫 {t("rulebuilder.pol_blocked_title")}</strong>
        <p className="hint-text" style={{ fontSize: 12, margin: "4px 0 8px" }}>{t("rulebuilder.pol_blocked_hint")}</p>
        <input
          value={blockedTerms}
          onChange={(e) => setBlockedTerms(e.target.value)}
          placeholder={t("rulebuilder.pol_blocked_ph")}
          style={{ width: "100%" }}
        />
      </div>

      <div style={{ border: "1px solid var(--border,#e5e7eb)", borderRadius: 8, padding: 12 }}>
        <label style={{ display: "flex", alignItems: "flex-start", gap: 10, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={requireApproval}
            onChange={(e) => setRequireApproval(e.target.checked)}
            style={{ marginTop: 3 }}
          />
          <span>
            <strong style={{ fontSize: 14 }}>⏸️ {t("rulebuilder.pol_approval_title")}</strong>
            <p className="hint-text" style={{ fontSize: 12, margin: "4px 0 0" }}>{t("rulebuilder.pol_approval_hint")}</p>
          </span>
        </label>
      </div>
    </div>
  );
}
