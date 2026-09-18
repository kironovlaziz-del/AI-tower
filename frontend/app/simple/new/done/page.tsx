"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useWizard } from "@/lib/wizard";
import { createDeployment } from "@/lib/api";

export default function WizardDonePage() {
  const router = useRouter();
  const { t } = useTranslation();
  const { state, reset } = useWizard();
  const [deploymentId, setDeploymentId] = useState<number | null>(null);
  const [showApi, setShowApi] = useState(false);

  useEffect(() => {
    // A fine-tuned model isn't chattable until it has a deployment - the
    // wizard creates one automatically here so "Открыть чат" just works,
    // matching the plan's "no extra configuration screens" principle.
    if (state.resultTrainingJobId && !deploymentId) {
      createDeployment({
        training_job_id: state.resultTrainingJobId,
        name: state.modelName || t("simple_mode.default_model_name"),
      }).then((d) => setDeploymentId(d.id));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.resultTrainingJobId]);

  function openChat() {
    if (state.resultCollectionId) {
      router.push(`/simple/models/${state.resultCollectionId}`);
    } else {
      router.push("/playground");
    }
  }

  function finishAndReturnHome() {
    reset();
    router.push("/simple");
  }

  return (
    <div style={{ textAlign: "center", paddingTop: 40 }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
      <h1 style={{ fontSize: 20, marginBottom: 24 }}>{t("simple_mode.done_title")}</h1>

      <div className="panel" style={{ marginBottom: 28, textAlign: "left" }}>
        <div className="panel-body">
          <p style={{ fontWeight: 600 }}>
            🤖 {state.modelName || t("simple_mode.default_model_name")}
          </p>
          {state.qaPairs.length > 0 && (
            <p className="hint-text">
              {t("simple_mode.done_examples_count", { count: state.qaPairs.length })}
            </p>
          )}
        </div>
      </div>

      <p style={{ marginBottom: 14, fontWeight: 600, textAlign: "left" }}>
        {t("simple_mode.done_next_steps")}
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <button className="btn" onClick={openChat} style={{ justifyContent: "flex-start" }}>
          💬 {t("simple_mode.done_open_chat")}
        </button>
        <button
          className="btn"
          onClick={() => setShowApi((s) => !s)}
          style={{ justifyContent: "flex-start" }}
        >
          🔌 {t("simple_mode.done_connect_api")}
        </button>
        {showApi && (
          <div className="panel">
            <div className="panel-body">
              <pre className="mono" style={{ fontSize: 12, whiteSpace: "pre-wrap" }}>
                {state.resultCollectionId
                  ? `POST /api/v1/rag/collections/${state.resultCollectionId}/chat\n{"message": "...", "provider_id": <id>}`
                  : deploymentId
                  ? `POST /api/v1/deployments/${deploymentId}/chat\n{"message": "..."}`
                  : t("simple_mode.done_api_pending")}
              </pre>
            </div>
          </div>
        )}
        <button
          className="btn"
          onClick={() => router.push("/policies")}
          style={{ justifyContent: "flex-start" }}
        >
          🛡️ {t("simple_mode.done_configure_policies")}
        </button>
      </div>

      <button
        className="btn btn-sm"
        onClick={finishAndReturnHome}
        style={{ marginTop: 28 }}
      >
        {t("simple_mode.done_back_home")}
      </button>
    </div>
  );
}
