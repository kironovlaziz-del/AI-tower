"use client";

import React, { useEffect } from "react";
import { useTranslation } from "react-i18next";

type FormFieldElement = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;

function hasMinLength(el: FormFieldElement): el is HTMLInputElement | HTMLTextAreaElement {
  return "minLength" in el;
}

function isEmailInput(el: FormFieldElement): el is HTMLInputElement {
  return "type" in el && (el as HTMLInputElement).type === "email";
}

export function Form({
  children,
  onSubmit,
  ...rest
}: React.FormHTMLAttributes<HTMLFormElement>) {
  const { t } = useTranslation();

  useEffect(() => {
    // "invalid" fires when the browser tries to submit an invalid form.
    // We replace the native message (localized by the OS, not by us) with
    // our own translation so the tooltip matches the current UI language.
    const handleInvalid = (e: Event) => {
      const target = e.target as FormFieldElement;
      if (!target || !("setCustomValidity" in target)) return;

      if (target.validity.valueMissing) {
        target.setCustomValidity(t("validation.required"));
      } else if (target.validity.typeMismatch && isEmailInput(target)) {
        target.setCustomValidity(t("validation.email_invalid"));
      } else if (target.validity.tooShort && hasMinLength(target)) {
        target.setCustomValidity(
          t("validation.min_length", { min: target.minLength })
        );
      }
    };

    // Clear the custom message as soon as the user fixes the field, so a
    // subsequent submit re-runs native validation instead of being stuck.
    const handleInput = (e: Event) => {
      const target = e.target as FormFieldElement;
      if (target && "setCustomValidity" in target) {
        target.setCustomValidity("");
      }
    };

    document.addEventListener("invalid", handleInvalid, true);
    document.addEventListener("input", handleInput, true);
    document.addEventListener("change", handleInput, true);
    return () => {
      document.removeEventListener("invalid", handleInvalid, true);
      document.removeEventListener("input", handleInput, true);
      document.removeEventListener("change", handleInput, true);
    };
  }, [t]);

  // NOTE: noValidate is intentionally NOT set — we want native HTML5
  // validation to run, but with messages replaced by the handler above.
  return (
    <form onSubmit={onSubmit} {...rest}>
      {children}
    </form>
  );
}
