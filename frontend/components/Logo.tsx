"use client";

import React from "react";

/**
 * Brand logo: a "verified node" mark — a delegation graph converging on a
 * central node with a trust checkmark inside it, expressing the product's
 * signature property (verifiable trust between agents). Beside it, a clean
 * lowercase wordmark. Pure SVG — crisp at any size.
 *
 *   <Logo />                  sidebar default
 *   <Logo size="lg" center /> large, centered — for login / register
 */
export function Logo({
  size = "sm",
  center = false,
  collapsed = false,
}: {
  size?: "sm" | "lg";
  center?: boolean;
  collapsed?: boolean;
}) {
  const mark = size === "lg" ? 46 : 34;
  const font = size === "lg" ? 22 : 15;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: center ? "center" : "flex-start",
        gap: size === "lg" ? 13 : 10,
      }}
    >
      {/* verified-node mark */}
      <svg width={mark} height={mark} viewBox="0 0 48 48" fill="none" aria-hidden="true" style={{ flexShrink: 0 }}>
        <g stroke="#22D3EE" strokeWidth="1.3" opacity="0.5">
          <line x1="10" y1="14" x2="24" y2="24" />
          <line x1="38" y1="14" x2="24" y2="24" />
          <line x1="10" y1="34" x2="24" y2="24" />
        </g>
        <circle cx="10" cy="14" r="2.6" fill="#3B82F6" />
        <circle cx="38" cy="14" r="2.6" fill="#3B82F6" />
        <circle cx="10" cy="34" r="2.6" fill="#3B82F6" />
        {/* central verified node */}
        <circle cx="24" cy="24" r="9" fill="none" stroke="#22D3EE" strokeWidth="2" />
        <path d="M19.5 24 L22.5 27 L29 20" stroke="#22D3EE" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>

      {!collapsed && (
        <div style={{ fontSize: font, fontWeight: 600, letterSpacing: "0.02em", whiteSpace: "nowrap" }}>
          <span style={{ color: "#22D3EE" }}>proven</span><span style={{ color: "#AFC4E4", fontWeight: 500 }}>za</span>
        </div>
      )}
    </div>
  );
}
