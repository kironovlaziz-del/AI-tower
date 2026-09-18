"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useWizard } from "@/lib/wizard";
import {
  createTrainingJob,
  finalizeWizardRAG,
  getTrainingJob,
  uploadDataset,
} from "@/lib/api";

function pairsToCSV(pairs: { question: string; answer: string }[], columns: [string, string]): File {
  const escape = (s: string) => `"${s.replace(/"/g, '""')}"`;
  const lines = [columns.join(","), ...pairs.map((p) => `${escape(p.question)},${escape(p.answer)}`)];
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  return new File([blob], "wizard_data.csv", { type: "text/csv" });
}

export default function WizardTrainingPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const { state, update, systemPrompt } = useWizard();
  const [statusText, setStatusText] = useState(t("simple_mode.training_starting"));
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return; // React StrictMode/dev double-invoke guard
    startedRef.current = true;
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run() {
    const approach = state.recommendedApproach;
    const modelName = state.modelName || t("simple_mode.default_model_name");

    try {
      if (approach === "rag" || approach === "rag_few_shot" || !approach) {
        setStatusText(t("simple_mode.training_building_kb"));
        const files: File[] = [];
        if (state.uploadedFile && state.hasUnstructuredText) files.push(state.uploadedFile);
        files.push(...state.noDataFiles);

        const result = await finalizeWizardRAG({
          name: modelName,
          systemPrompt: systemPrompt(),
          qaPairs: state.qaPairs,
          files,
        });
        update({ resultCollectionId: result.collection_id });
        router.push("/simple/new/done");
        return;
      }

      if (approach === "fine_tuning") {
        if (state.qaPairs.length < 20) {
          setErrorMsg(t("simple_mode.training_not_enough_examples"));
          return;
        }
        setStatusText(t("simple_mode.training_uploading_data"));
        const csvFile = pairsToCSV(state.qaPairs, ["question", "text"]);
        const dataset = await uploadDataset({
          name: `${modelName} - data`,
          task_type: "transformer_text_generation",
          file: csvFile,
        });

        setStatusText(t("simple_mode.training_starting_job"));
        const job = await createTrainingJob({
          dataset_id: dataset.id,
          name: modelName,
          task_type: "transformer_text_generation",
          base_model: "distilgpt2",
          hyperparameters: { text_column: "text", system_prompt: systemPrompt() },
        });
        await pollJob(job.id);
        return;
      }

      if (approach === "fine_tuning_classification") {
        if (state.qaPairs.length < 20) {
          setErrorMsg(t("simple_mode.training_not_enough_examples"));
          return;
        }
        setStatusText(t("simple_mode.training_uploading_data"));
        const csvFile = pairsToCSV(state.qaPairs, ["text", "label"]);
        const dataset = await uploadDataset({
          name: `${modelName} - data`,
          task_type: "transformer_text_classification",
          file: csvFile,
        });

        setStatusText(t("simple_mode.training_starting_job"));
        const job = await createTrainingJob({
          dataset_id: dataset.id,
          name: modelName,
          task_type: "transformer_text_classification",
          target_column: "label",
          base_model: "google/bert_uncased_L-2_H-128_A-2",
          hyperparameters: { text_column: "text" },
        });
        await pollJob(job.id);
        return;
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
        ?.detail;
      setErrorMsg(typeof detail === "string" ? detail : t("simple_mode.training_failed"));
    }
  }

  async function pollJob(jobId: number) {
    setStatusText(t("simple_mode.training_in_progress"));
    const poll = async (): Promise<void> => {
      const job = await getTrainingJob(jobId);
      if (job.status === "completed") {
        update({ resultTrainingJobId: jobId });
        router.push("/simple/new/done");
        return;
      }
      if (job.status === "failed") {
        setErrorMsg(job.error_message || t("simple_mode.training_failed"));
        return;
      }
      setTimeout(poll, 4000);
    };
    await poll();
  }

  if (errorMsg) {
    return (
      <>
        <p className="error-text" style={{ marginBottom: 16 }}>{errorMsg}</p>
        <button className="btn btn-primary" onClick={() => router.push("/simple/new/test")}>
          ← {t("common.back")}
        </button>
      </>
    );
  }

  return (
    <div style={{ textAlign: "center", paddingTop: 60 }}>
      <div style={{ fontSize: 48, marginBottom: 20 }}>🧠</div>
      <h1 style={{ fontSize: 20, marginBottom: 16 }}>{t("simple_mode.training_title")}</h1>
      <p className="hint-text" style={{ marginBottom: 8 }}>{statusText}</p>
      <p className="hint-text">{t("simple_mode.training_can_close")}</p>
    </div>
  );
}
