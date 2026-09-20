"use client";

import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";

// The agent policy engine understands these rule keys (see
// agent_policy_engine.evaluate_custom_rule). Each builder row maps to one
// of them. The builder is the friendly face; the JSON it produces is
// exactly what the backend already consumes.
type RuleKind = "deny_tools" | "allow_only_tools" | "require_approval_tools" | "deny_action_types";

interface Row {
  kind: RuleKind;
  values: string; // comma-separated, edited as text
}

// what each rule does, in plain words (translated)
const RULE_META: { kind: RuleKind; icon: string }[] = [
  { kind: "deny_tools", icon: "🚫" },
  { kind: "require_approval_tools", icon: "⏸️" },
  { kind: "allow_only_tools", icon: "✅" },
  { kind: "deny_action_types", icon: "⛔" },
];

function toList(s: string): string[] {
  return s.split(/[,\n]/).map((x) => x.trim()).filter(Boolean);
}

/**
 * Emits a rules object like { deny_tools: [...], require_approval_tools: [...] }.
 * Value is controlled by the parent so it can also show/round-trip raw JSON.
 */
export function AgentRuleBuilder({
  value,
  onChange,
}: {
  value: Record<string, unknown>;
  onChange: (rules: Record<string, unknown>) => void;
}) {
  const { t } = useTranslation();

  // hydrate rows from the incoming value once
  const [rows, setRows] = useState<Row[]>(() => {
    const initial: Row[] = [];
    for (const { kind } of RULE_META) {
      const v = value?.[kind];
      if (Array.isArray(v) && v.length) initial.push({ kind, values: v.join(", ") });
    }
    return initial;
  });

  useEffect(() => {
    const rules: Record<string, unknown> = {};
    for (const r of rows) {
      const list = toList(r.values);
      if (list.length) rules[r.kind] = list;
    }
    onChange(rules);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows]);

  function addRow(kind: RuleKind) {
    setRows((rs) => [...rs, { kind, values: "" }]);
  }
  function updateRow(i: number, values: string) {
    setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, values } : r)));
  }
  function removeRow(i: number) {
    setRows((rs) => rs.filter((_, idx) => idx !== i));
  }

  const usedKinds = new Set(rows.map((r) => r.kind));

  return (
    <div>
      {rows.length === 0 && (
        <p className="hint-text" style={{ marginBottom: 12 }}>{t("rulebuilder.empty")}</p>
      )}

      {rows.map((row, i) => {
        const meta = RULE_META.find((m) => m.kind === row.kind)!;
        return (
          <div key={i} style={{ border: "1px solid var(--border,#e5e7eb)", borderRadius: 8, padding: 12, marginBottom: 10 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
              <strong style={{ fontSize: 14 }}>{meta.icon} {t(`rulebuilder.kind_${row.kind}`)}</strong>
              <button type="button" className="btn btn-sm" onClick={() => removeRow(i)} style={{ padding: "2px 8px" }}>✕</button>
            </div>
            <p className="hint-text" style={{ fontSize: 12, margin: "0 0 8px" }}>{t(`rulebuilder.hint_${row.kind}`)}</p>
            <input
              value={row.values}
              onChange={(e) => updateRow(i, e.target.value)}
              placeholder={t(`rulebuilder.ph_${row.kind}`)}
              style={{ width: "100%" }}
            />
          </div>
        );
      })}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 6 }}>
        {RULE_META.filter((m) => !usedKinds.has(m.kind)).map((m) => (
          <button key={m.kind} type="button" className="btn btn-sm" onClick={() => addRow(m.kind)}>
            + {m.icon} {t(`rulebuilder.kind_${m.kind}`)}
          </button>
        ))}
      </div>
    </div>
  );
}
