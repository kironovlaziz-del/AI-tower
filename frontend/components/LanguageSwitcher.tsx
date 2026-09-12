"use client";

import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGUAGES } from "@/lib/i18n";

export function LanguageSwitcher({ variant = "sidebar" }: { variant?: "sidebar" | "light" }) {
  const { i18n } = useTranslation();

  const select = (
    <select
      id="lang-switcher-select"
      className={`lang-switcher lang-switcher-${variant}`}
      value={i18n.language.split("-")[0]}
      onChange={(e) => i18n.changeLanguage(e.target.value)}
      aria-label="Language"
    >
      {SUPPORTED_LANGUAGES.map((lang) => (
        <option key={lang.code} value={lang.code}>
          {lang.label}
        </option>
      ))}
    </select>
  );

  // Sidebar variant keeps the compact look — no label.
  if (variant === "sidebar") return select;

  // Light variant (login/register) gets a label so it's obvious what the
  // dropdown does.
  return (
    <div style={{ marginBottom: 16 }}>
      <label className="lang-switcher-label" htmlFor="lang-switcher-select">
        🌐 {i18n.t("language.switch")}
      </label>
      {select}
    </div>
  );
}
