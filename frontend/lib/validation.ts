"use client";

import type { TFunction } from "i18next";

export interface FieldSpec {
  value: unknown;
  rules?: {
    required?: boolean;
    email?: boolean;
    minLength?: number;
  };
}

export type FieldErrors = Record<string, string>;

export function validateFields(
  fields: Record<string, FieldSpec>,
  t: TFunction
): FieldErrors {
  const errors: FieldErrors = {};

  for (const [name, spec] of Object.entries(fields)) {
    const { value, rules = {} } = spec;
    const isEmpty =
      value === undefined ||
      value === null ||
      value === "" ||
      (typeof value === "string" && value.trim() === "");

    if (rules.required && isEmpty) {
      errors[name] = t("validation.required");
      continue;
    }

    if (isEmpty) continue;

    if (rules.email && typeof value === "string") {
      const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRe.test(value)) {
        errors[name] = t("validation.email_invalid");
        continue;
      }
    }

    if (rules.minLength && typeof value === "string" && value.length < rules.minLength) {
      errors[name] = t("validation.min_length", { min: rules.minLength });
      continue;
    }
  }

  return errors;
}
