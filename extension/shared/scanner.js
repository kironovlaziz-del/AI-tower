// PII and Secret Tokens Detector
//
// SECURITY NOTE: findings intentionally carry NO fragment of the matched
// value. An earlier version included a "preview" (the first 4 chars of
// the match), which meant a DLP tool built to PREVENT secret leakage was
// itself shipping pieces of those secrets to the server. Findings now
// describe only WHAT kind of sensitive data was seen (type/label/
// severity), never any part of the value itself.

const PII_PATTERNS = [
  {
    type: "credit_card",
    label: "Credit Card Number",
    severity: "critical",
    regex: /\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b/
  },
  {
    type: "anthropic_key",
    label: "Anthropic API Key",
    severity: "critical",
    // Checked before the generic openai_key pattern so "sk-ant-..." is
    // labeled specifically rather than as a generic OpenAI key.
    regex: /\bsk-ant-[a-zA-Z0-9_-]{24,}\b/
  },
  {
    type: "openai_key",
    label: "OpenAI Secret Key",
    severity: "critical",
    regex: /\bsk-[a-zA-Z0-9_-]{24,}\b/
  },
  {
    type: "github_token",
    label: "GitHub Personal Access Token",
    severity: "critical",
    regex: /\b(?:ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{40,})\b/
  },
  {
    type: "aws_access_key",
    label: "AWS Access Key ID",
    severity: "critical",
    regex: /\bAKIA[0-9A-Z]{16}\b/
  },
  {
    type: "private_key",
    label: "Private Cryptographic Key",
    severity: "critical",
    regex: /-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----/
  },
  {
    type: "jwt_token",
    label: "JSON Web Token (JWT)",
    severity: "high",
    regex: /\beyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b/
  }
  // NOTE: a bare "email" pattern was removed on purpose. Almost any
  // pasted text contains an email address, so it fired constantly,
  // trained users to reflexively dismiss the warning, and buried the
  // genuinely critical hits (cards, keys). If email-in-prompt detection
  // is wanted later it should be a separately-configurable, lower-noise
  // rule, not an always-on medium-severity match.
];

// scanTextForPII returns one finding per pattern that matched. Each
// finding is metadata only - no slice of the matched value.
function scanTextForPII(text) {
  if (!text || typeof text !== "string") return [];
  const findings = [];
  for (const pattern of PII_PATTERNS) {
    if (pattern.regex.test(text)) {
      findings.push({
        type: pattern.type,
        label: pattern.label,
        severity: pattern.severity
      });
    }
  }
  return findings;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { PII_PATTERNS, scanTextForPII };
}
