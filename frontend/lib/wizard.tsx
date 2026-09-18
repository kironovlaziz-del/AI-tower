"use client";

import React, { createContext, useContext, useState, useCallback } from "react";

export type WizardTaskType = "support_qa" | "style_writing" | "classification" | "other";
export type WizardDataSource = "file" | "connect" | "manual" | "no_data";
export type WizardApproach = "rag" | "rag_few_shot" | "fine_tuning" | "fine_tuning_classification";
export type WizardStyleKey = "friendly" | "formal" | "concise" | "custom";

export interface WizardQAPair {
  question: string;
  answer: string;
}

export interface WizardPersonality {
  styleKey: WizardStyleKey;
  customStyleText: string;
  companyName: string;
  extraRules: string[];
}

export interface WizardState {
  modelName: string;
  taskType: WizardTaskType | null;
  dataSource: WizardDataSource | null;

  // Populated by POST /simple-mode/parse-upload after screen 4.
  qaPairs: WizardQAPair[];
  errorRowCount: number;
  hasUnstructuredText: boolean;
  uploadedFileName: string | null;
  // The raw file is kept so it can be indexed into a RAG collection at
  // the end of the wizard without asking the person to upload it twice.
  uploadedFile: File | null;
  // For the "no data" branch: one or more documents to seed a RAG
  // knowledge base with directly (screens don't produce Q&A pairs here).
  noDataFiles: File[];

  recommendedApproach: WizardApproach | null;
  recommendedReason: string;

  personality: WizardPersonality;
  providerId: number | null;

  // Populated by screen 9 once creation actually happens, for screen 10
  // to link to the right place ("Открыть чат" needs to know whether that
  // means a RAG collection or a trained model deployment).
  resultCollectionId: number | null;
  resultTrainingJobId: number | null;
}

const DEFAULT_STATE: WizardState = {
  modelName: "",
  taskType: null,
  dataSource: null,
  qaPairs: [],
  errorRowCount: 0,
  hasUnstructuredText: false,
  uploadedFileName: null,
  uploadedFile: null,
  noDataFiles: [],
  recommendedApproach: null,
  recommendedReason: "",
  personality: {
    styleKey: "friendly",
    customStyleText: "",
    companyName: "",
    extraRules: [],
  },
  providerId: null,
  resultCollectionId: null,
  resultTrainingJobId: null,
};

interface WizardContextValue {
  state: WizardState;
  update: (patch: Partial<WizardState>) => void;
  updatePersonality: (patch: Partial<WizardPersonality>) => void;
  reset: () => void;
  systemPrompt: () => string;
}

const WizardContext = createContext<WizardContextValue | undefined>(undefined);

const STYLE_PROMPTS: Record<WizardStyleKey, string> = {
  friendly: "Отвечай дружелюбно и тепло, как заботливый помощник.",
  formal: "Отвечай формально и уважительно, в деловом стиле.",
  concise: "Отвечай кратко и по делу, без лишних слов.",
  custom: "",
};

export function WizardProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<WizardState>(DEFAULT_STATE);

  const update = useCallback((patch: Partial<WizardState>) => {
    setState((prev) => ({ ...prev, ...patch }));
  }, []);

  const updatePersonality = useCallback((patch: Partial<WizardPersonality>) => {
    setState((prev) => ({ ...prev, personality: { ...prev.personality, ...patch } }));
  }, []);

  const reset = useCallback(() => setState(DEFAULT_STATE), []);

  // Converts screen 7's human-language choices into the plain-text
  // system_prompt the backend actually uses (preview-chat, and the
  // fine-tuning generation trainer's system_prompt hyperparameter) -
  // kept in one place so screen 8's preview and the final "train/create"
  // call are guaranteed to use the exact same prompt.
  const systemPrompt = useCallback(() => {
    const { styleKey, customStyleText, companyName, extraRules } = state.personality;
    const parts: string[] = [];
    const base = styleKey === "custom" ? customStyleText : STYLE_PROMPTS[styleKey];
    if (base.trim()) parts.push(base.trim());
    if (companyName.trim()) {
      parts.push(`Ты — ассистент компании "${companyName.trim()}". Упоминай её при уместности.`);
    }
    for (const rule of extraRules) {
      if (rule.trim()) parts.push(rule.trim());
    }
    return parts.join(" ");
  }, [state.personality]);

  return (
    <WizardContext.Provider value={{ state, update, updatePersonality, reset, systemPrompt }}>
      {children}
    </WizardContext.Provider>
  );
}

export function useWizard() {
  const ctx = useContext(WizardContext);
  if (!ctx) throw new Error("useWizard must be used within WizardProvider");
  return ctx;
}
