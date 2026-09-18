"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/lib/auth";
import { StatusPill } from "@/components/Pill";
import { listDeployments } from "@/lib/api";
import type { ModelDeployment } from "@/lib/types";

const TILES = [
  { href: "/simple/new/task", icon: "🤖", labelKey: "simple_mode.tile_train" },
  { href: "/requests", icon: "📊", labelKey: "simple_mode.tile_monitor" },
  { href: "/policies", icon: "🛡️", labelKey: "simple_mode.tile_policies" },
  { href: "/datasets", icon: "📁", labelKey: "simple_mode.tile_datasets" },
];

export default function SimpleDashboardPage() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [deployments, setDeployments] = useState<ModelDeployment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listDeployments()
      .then((all) => setDeployments(all.filter((d) => d.status === "active")))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <h1 style={{ fontSize: 22, marginBottom: 4 }}>
        {t("simple_mode.welcome", { name: user?.name || "" })}
      </h1>
      <p className="hint-text" style={{ marginBottom: 28 }}>{t("simple_mode.what_today")}</p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
          marginBottom: 32,
        }}
      >
        {TILES.map((tile) => (
          <Link
            key={tile.href}
            href={tile.href}
            className="btn"
            style={{
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              padding: "28px 16px",
              height: "auto",
              gap: 10,
              textDecoration: "none",
              fontSize: 15,
              fontWeight: 600,
            }}
          >
            <span style={{ fontSize: 32 }}>{tile.icon}</span>
            {t(tile.labelKey)}
          </Link>
        ))}
      </div>

      <h2 style={{ fontSize: 15, marginBottom: 10 }}>{t("simple_mode.your_models")}</h2>
      <div className="panel">
        {loading && <div className="panel-body hint-text">{t("common.loading")}</div>}
        {!loading && deployments.length === 0 && (
          <div className="panel-body hint-text">{t("simple_mode.no_models_yet")}</div>
        )}
        {!loading &&
          deployments.map((d) => (
            <Link
              key={d.id}
              href="/playground"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "14px 18px",
                borderBottom: "1px solid var(--border, #e5e7eb)",
                textDecoration: "none",
                color: "inherit",
              }}
            >
              <span>🤖 {d.name}</span>
              <StatusPill status={d.status} />
            </Link>
          ))}
      </div>
    </>
  );
}
