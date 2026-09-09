"use client";

import React, { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { getComputeStatus } from "@/lib/api";
import type { ComputeStatus } from "@/lib/types";

const TIER_LABEL: Record<string, string> = {
  gpu: "GPU доступен",
  minimal: "Минимум ресурсов",
  cpu_classic: "CPU: классический ML",
  cpu_light_nlp: "CPU: лёгкий NLP",
  cpu_generous: "CPU: достаточно ресурсов",
};

export default function ComputePage() {
  const [status, setStatus] = useState<ComputeStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getComputeStatus()
      .then(setStatus)
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <PageHeader title="Compute Detector" />
      <div className="content">
        {loading && <p className="loading-line">Определяем ресурсы сервера…</p>}
        {!loading && status && (
          <>
            <div className="stat-grid">
              <div className="stat">
                <div className="stat-label">CPU (логических ядер)</div>
                <div className="stat-value">{status.cpu_logical_cores}</div>
              </div>
              <div className="stat">
                <div className="stat-label">RAM всего</div>
                <div className="stat-value">{status.ram_total_gb} ГБ</div>
              </div>
              <div className="stat">
                <div className="stat-label">RAM свободно</div>
                <div className="stat-value">{status.ram_available_gb} ГБ</div>
              </div>
              <div className="stat">
                <div className="stat-label">Диск свободно</div>
                <div className="stat-value">{status.disk_free_gb} ГБ</div>
              </div>
              <div className="stat">
                <div className="stat-label">GPU</div>
                <div className="stat-value" style={{ fontSize: 16 }}>
                  {status.gpu_available ? "Да" : "Не обнаружен"}
                </div>
              </div>
              {status.gpu_available && status.gpu_vram_free_gb != null && (
                <div className="stat">
                  <div className="stat-label">VRAM свободно / всего</div>
                  <div className="stat-value" style={{ fontSize: 16 }}>
                    {status.gpu_vram_free_gb} / {status.gpu_vram_total_gb} ГБ
                  </div>
                </div>
              )}
            </div>

            {status.gpu_available && status.gpu_names.length > 0 && (
              <div className="panel" style={{ marginBottom: 20 }}>
                <div className="panel-header">
                  <h2>Обнаруженные GPU</h2>
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
                <h2>Что реально можно обучать на этом сервере</h2>
                <span className="pill pill-accent">
                  {TIER_LABEL[status.recommendation_tier] ?? status.recommendation_tier}
                </span>
              </div>
              <div className="panel-body">
                <p style={{ margin: 0 }}>{status.recommendation_detail}</p>
              </div>
            </div>

            {status.warnings.length > 0 && (
              <div className="panel">
                <div className="panel-header">
                  <h2>Предупреждения</h2>
                </div>
                <div className="panel-body">
                  {status.warnings.map((w) => (
                    <p key={w} className="hint-text" style={{ marginBottom: 8 }}>
                      ⚠ {w}
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
