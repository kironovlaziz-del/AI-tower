"use client";

import React, { useState } from "react";
import { useTranslation } from "react-i18next";

export function ExtensionBanner() {
  const { t } = useTranslation();
  const [showGuide, setShowGuide] = useState(false);

  return (
    <div className="mb-6 p-4 rounded-xl border border-blue-500/30 bg-blue-500/5 backdrop-blur-sm text-left">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="text-2xl select-none">🛡️</span>
          <div>
            <h4 className="text-sm font-semibold text-foreground">
              {t("extension_banner.title")}
            </h4>
            <p className="text-xs text-muted-foreground mt-0.5">
              {t("extension_banner.desc")}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setShowGuide((s) => !s)}
          className="shrink-0 text-xs font-medium px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors shadow-sm"
        >
          {showGuide ? t("extension_banner.hide_btn") : t("extension_banner.guide_btn")}
        </button>
      </div>

      {showGuide && (
        <div className="mt-3 pt-3 border-t border-border/50 text-xs text-muted-foreground space-y-1">
          <div className="font-semibold text-foreground">
            {t("extension_banner.install_guide")}
          </div>
          <div>{t("extension_banner.step1")}</div>
          <div>{t("extension_banner.step2")}</div>
          <div>{t("extension_banner.step3")}</div>
          <div>{t("extension_banner.step4")}</div>
        </div>
      )}
    </div>
  );
}
