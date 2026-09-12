"use client";

import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import en from "@/locales/en.json";
import uz from "@/locales/uz.json";

export const SUPPORTED_LANGUAGES = [
  { code: "en", label: "English" },
  { code: "uz", label: "O'zbekcha" },
] as const;

export type LanguageCode = (typeof SUPPORTED_LANGUAGES)[number]["code"];

if (!i18n.isInitialized) {
  i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      resources: {
        en: { translation: en },
        uz: { translation: uz },
      },
      fallbackLng: "en",
      supportedLngs: ["en", "uz"],
      load: "languageOnly",
      nonExplicitSupportedLngs: true,
      interpolation: { escapeValue: false },
      // Не откладывать init через setTimeout — ресурсы уже переданы inline.
      // В i18next v23+ опция называется initAsync (initImmediate — deprecated).
      initAsync: false,
      react: {
        useSuspense: false,
      },
      detection: {
        order: ["localStorage", "navigator"],
        lookupLocalStorage: "ai_ct_lang",
        caches: ["localStorage"],
      },
    });
}

export default i18n;