"use client";

import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { getComputeStatus } from "@/lib/api";
import type { ComputeStatus } from "@/lib/types";

export default function ComputePage() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<ComputeStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getComputeStatus()
      .then(setStatus)
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <PageHeader title={t("compute.title")} />
      <div className="content">
        {loading && <p className="loading-line">{t("compute.loading")}</p>}
        {!loading && status && (
          <>
            <div className="stat-grid">
              <div className="stat">
                <div className="stat-label">{t("compute.cpu_logical")}</div>
                <div className="stat-value">{status.cpu_logical_cores}</div>
              </div>
              <div className="stat">
                <div className="stat-label">{t("compute.ram_total")}</div>
                <div className="stat-value">{status.ram_total_gb} GB</div>
              </div>
              <div className="stat">
                <div className="stat-label">{t("compute.ram_available")}</div>
                <div className="stat-value">{status.ram_available_gb} GB</div>
              </div>
              <div className="stat">
                <div className="stat-label">{t("compute.disk_free")}</div>
                <div className="stat-value">{status.disk_free_gb} GB</div>
              </div>
              <div className="stat">
                <div className="stat-label">{t("compute.gpu")}</div>
                <div className="stat-value" style={{ fontSize: 16 }}>
                  {status.gpu_available ? t("compute.gpu_yes") : t("compute.gpu_no")}
                </div>
              </div>
              {status.gpu_available && status.gpu_vram_free_gb != null && (
                <div className="stat">
                  <div className="stat-label">{t("compute.vram")}</div>
                  <div className="stat-value" style={{ fontSize: 16 }}>
                    {status.gpu_vram_free_gb} / {status.gpu_vram_total_gb} GB
                  </div>
                </div>
              )}
            </div>

            {status.gpu_available && status.gpu_names.length > 0 && (
              <div className="panel" style={{ marginBottom: 20 }}>
                <div className="panel-header">
                  <h2>{t("compute.gpu_list")}</h2>
                </div>
                <div className="panel-body">
                  <ul style={{ margin: 0, paddingLeft: 18 }}>
                    {status.gpu_names.map((name) => (
                      <li key={name} className="mono">
                        {name}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            <div className="panel" style={{ marginBottom: 20 }}>
              <div className="panel-header">
                <h2>{t("compute.what_can_train")}</h2>
                <span className="pill pill-accent">
                  {t(
                    `compute.tiers.${status.recommendation_tier}`,
                    status.recommendation_tier
                  )}
                </span>
              </div>
              <div className="panel-body">
                <p style={{ margin: 0 }}>
                  {t(`compute.recommendation.${status.recommendation_tier}`, {
                    names: status.gpu_names.join(", ") || "—",
                  })}
                </p>
              </div>
            </div>

            {status.warnings.length > 0 && (
              <div className="panel">
                <div className="panel-header">
                  <h2>{t("compute.warnings")}</h2>
                </div>
                <div className="panel-body">
                  {status.warnings.map((w, idx) => (
                    <p key={idx} className="hint-text" style={{ marginBottom: 8 }}>
                      ⚠{" "}
                      {t(`compute.warnings_map.${w.code}`, {
                        disk_free_gb: w.disk_free_gb,
                        vram_free_gb: w.vram_free_gb,
                      })}
                    </p>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
