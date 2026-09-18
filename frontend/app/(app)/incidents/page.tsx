"use client";

import React, { useEffect, useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import Link from "next/link";
import { listIncidents, updateIncidentStatus } from "@/lib/api";
import type { Incident } from "@/lib/types";

export default function IncidentsPage() {
  const { t, i18n } = useTranslation();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const data = await listIncidents();
      setIncidents(data || []);
    } catch (err: any) {
      setError(err?.message || "Failed to load incidents");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleStatusChange(id: number, newStatus: string) {
    setUpdatingId(id);
    try {
      await updateIncidentStatus(id, newStatus);
      await loadData();
    } catch (err: any) {
      alert(err?.message || "Failed to update incident status");
    } finally {
      setUpdatingId(null);
    }
  }

  const filteredIncidents = useMemo(() => {
    return incidents.filter((item) => {
      if (statusFilter !== "all" && item.status.toLowerCase() !== statusFilter.toLowerCase()) {
        return false;
      }
      if (severityFilter !== "all" && item.severity.toLowerCase() !== severityFilter.toLowerCase()) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesSummary = (item.summary || "").toLowerCase().includes(q);
        const matchesCat = (item.category || "").toLowerCase().includes(q);
        const matchesImpact = (item.impact || "").toLowerCase().includes(q);
        const matchesRoot = (item.root_cause || "").toLowerCase().includes(q);
        if (!matchesSummary && !matchesCat && !matchesImpact && !matchesRoot) {
          return false;
        }
      }
      return true;
    });
  }, [incidents, statusFilter, severityFilter, searchQuery]);

  const stats = useMemo(() => {
    const total = incidents.length;
    const open = incidents.filter((i) => i.status.toLowerCase() === "open").length;
    const investigating = incidents.filter((i) => i.status.toLowerCase() === "investigating").length;
    const criticalOrHigh = incidents.filter((i) => ["critical", "high"].includes(i.severity.toLowerCase())).length;
    return { total, open, investigating, criticalOrHigh };
  }, [incidents]);

  function formatDate(isoString?: string) {
    if (!isoString) return "-";
    try {
      return new Date(isoString).toLocaleString(i18n.language === "uz" ? "uz-UZ" : "en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  }

  function getSeverityBadge(sev: string) {
    const s = sev.toLowerCase();
    let bg = "#F3F4F6";
    let color = "#374151";
    if (s === "critical") {
      bg = "#FEE2E2";
      color = "#991B1B";
    } else if (s === "high") {
      bg = "#FFEDD5";
      color = "#9A3412";
    } else if (s === "medium") {
      bg = "#FEF3C7";
      color = "#92400E";
    } else if (s === "low") {
      bg = "#E0E7FF";
      color = "#3730A3";
    }

    const label = t(`incidents.filter_severity_${s}`) || s.toUpperCase();

    return (
      <span
        style={{
          display: "inline-block",
          padding: "3px 8px",
          borderRadius: "6px",
          fontSize: "11px",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.5px",
          backgroundColor: bg,
          color: color,
        }}
      >
        {label}
      </span>
    );
  }

  function getStatusBadge(status: string) {
    const st = status.toLowerCase();
    let bg = "#F3F4F6";
    let color = "#4B5563";
    if (st === "open") {
      bg = "#FEE2E2";
      color = "#DC2626";
    } else if (st === "investigating") {
      bg = "#FEF3C7";
      color = "#D97706";
    } else if (st === "resolved") {
      bg = "#D1FAE5";
      color = "#059669";
    }

    const label = t(`incidents.status_${st}`) || st;

    return (
      <span
        style={{
          display: "inline-block",
          padding: "3px 8px",
          borderRadius: "999px",
          fontSize: "12px",
          fontWeight: 600,
          backgroundColor: bg,
          color: color,
        }}
      >
        {label}
      </span>
    );
  }

  return (
    <div style={{ width: "100%", maxWidth: "100%", boxSizing: "border-box" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "24px", fontWeight: 700, margin: "0 0 6px 0", color: "#111827" }}>
          {t("incidents.title")}
        </h1>
        <p style={{ margin: 0, fontSize: "14px", color: "#6B7280" }}>
          {t("incidents.subtitle")}
        </p>
      </div>

      {/* Metric Cards Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "14px",
          marginBottom: "20px",
        }}
      >
        <div style={{ background: "#FFFFFF", padding: "16px 20px", borderRadius: "10px", border: "1px solid #E5E7EB", boxShadow: "0 1px 2px rgba(0,0,0,0.03)" }}>
          <div style={{ fontSize: "12px", fontWeight: 600, color: "#6B7280", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
            {t("incidents.stat_total")}
          </div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: "#111827" }}>{stats.total}</div>
        </div>

        <div style={{ background: "#FFFFFF", padding: "16px 20px", borderRadius: "10px", border: "1px solid #E5E7EB", boxShadow: "0 1px 2px rgba(0,0,0,0.03)" }}>
          <div style={{ fontSize: "12px", fontWeight: 600, color: "#DC2626", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
            {t("incidents.stat_open")}
          </div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: "#DC2626" }}>{stats.open}</div>
        </div>

        <div style={{ background: "#FFFFFF", padding: "16px 20px", borderRadius: "10px", border: "1px solid #E5E7EB", boxShadow: "0 1px 2px rgba(0,0,0,0.03)" }}>
          <div style={{ fontSize: "12px", fontWeight: 600, color: "#D97706", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
            {t("incidents.stat_investigating")}
          </div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: "#D97706" }}>{stats.investigating}</div>
        </div>

        <div style={{ background: "#FFFFFF", padding: "16px 20px", borderRadius: "10px", border: "1px solid #E5E7EB", boxShadow: "0 1px 2px rgba(0,0,0,0.03)" }}>
          <div style={{ fontSize: "12px", fontWeight: 600, color: "#991B1B", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
            {t("incidents.stat_critical")}
          </div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: "#991B1B" }}>{stats.criticalOrHigh}</div>
        </div>
      </div>

      {/* Main Table Card */}
      <div
        style={{
          background: "#FFFFFF",
          borderRadius: "12px",
          border: "1px solid #E5E7EB",
          boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
          overflow: "hidden",
        }}
      >
        {/* Controls Bar: Search & Select Filters */}
        <div
          style={{
            padding: "16px",
            borderBottom: "1px solid #F3F4F6",
            display: "flex",
            flexWrap: "wrap",
            gap: "12px",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ flex: "1 1 240px", minWidth: "220px" }}>
            <input
              type="text"
              placeholder={t("incidents.search_placeholder")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px",
                fontSize: "14px",
                border: "1px solid #D1D5DB",
                borderRadius: "6px",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                padding: "8px 12px",
                fontSize: "13px",
                fontWeight: 500,
                color: "#374151",
                border: "1px solid #D1D5DB",
                borderRadius: "6px",
                backgroundColor: "#FFF",
                cursor: "pointer",
              }}
            >
              <option value="all">{t("incidents.filter_status_all")}</option>
              <option value="open">{t("incidents.filter_status_open")}</option>
              <option value="investigating">{t("incidents.filter_status_investigating")}</option>
              <option value="resolved">{t("incidents.filter_status_resolved")}</option>
            </select>

            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              style={{
                padding: "8px 12px",
                fontSize: "13px",
                fontWeight: 500,
                color: "#374151",
                border: "1px solid #D1D5DB",
                borderRadius: "6px",
                backgroundColor: "#FFF",
                cursor: "pointer",
              }}
            >
              <option value="all">{t("incidents.filter_severity_all")}</option>
              <option value="critical">{t("incidents.filter_severity_critical")}</option>
              <option value="high">{t("incidents.filter_severity_high")}</option>
              <option value="medium">{t("incidents.filter_severity_medium")}</option>
              <option value="low">{t("incidents.filter_severity_low")}</option>
            </select>
          </div>
        </div>

        {error && (
          <div style={{ padding: "16px", background: "#FEE2E2", color: "#991B1B", fontSize: "14px" }}>
            {error}
          </div>
        )}

        {/* Responsive Table Container */}
        <div style={{ width: "100%", overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", minWidth: "900px", textAlign: "left" }}>
            <thead>
              <tr style={{ background: "#F9FAFB", borderBottom: "1px solid #E5E7EB" }}>
                <th style={{ padding: "12px 16px", fontSize: "12px", fontWeight: 600, color: "#6B7280", width: "110px" }}>
                  {t("incidents.col_severity")}
                </th>
                <th style={{ padding: "12px 16px", fontSize: "12px", fontWeight: 600, color: "#6B7280" }}>
                  {t("incidents.col_summary")}
                </th>
                <th style={{ padding: "12px 16px", fontSize: "12px", fontWeight: 600, color: "#6B7280", width: "160px" }}>
                  {t("incidents.col_category")}
                </th>
                <th style={{ padding: "12px 16px", fontSize: "12px", fontWeight: 600, color: "#6B7280", width: "120px" }}>
                  {t("incidents.col_status")}
                </th>
                <th style={{ padding: "12px 16px", fontSize: "12px", fontWeight: 600, color: "#6B7280", width: "150px" }}>
                  {t("incidents.col_detected_at")}
                </th>
                <th style={{ padding: "12px 16px", fontSize: "12px", fontWeight: 600, color: "#6B7280", width: "170px", textAlign: "right" }}>
                  {t("incidents.col_actions")}
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} style={{ padding: "32px", textAlign: "center", color: "#6B7280", fontSize: "14px" }}>
                    Loading incidents...
                  </td>
                </tr>
              ) : filteredIncidents.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: "40px 16px", textAlign: "center", color: "#6B7280", fontSize: "14px" }}>
                    {incidents.length === 0 ? t("incidents.no_incidents") : t("incidents.no_results")}
                  </td>
                </tr>
              ) : (
                filteredIncidents.map((item) => (
                  <tr
                    key={item.id}
                    style={{
                      borderBottom: "1px solid #F3F4F6",
                      transition: "background 0.15s ease",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#F9FAFB")}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                  >
                    <td style={{ padding: "12px 16px", verticalAlign: "top" }}>
                      {getSeverityBadge(item.severity)}
                    </td>
                    <td style={{ padding: "12px 16px", verticalAlign: "top" }}>
                      <Link
                        href={`/incidents/${item.id}`}
                        style={{
                          fontSize: "14px",
                          fontWeight: 600,
                          color: "#1E40AF",
                          textDecoration: "none",
                          display: "inline-block",
                          marginBottom: "4px",
                        }}
                      >
                        {item.summary}
                      </Link>
                      {item.impact && (
                        <div style={{ fontSize: "12px", color: "#4B5563", lineHeight: 1.4, marginBottom: "4px" }}>
                          {item.impact}
                        </div>
                      )}
                      {item.root_cause && (
                        <div style={{ fontSize: "11px", color: "#9CA3AF" }}>
                          <span style={{ fontWeight: 600 }}>{t("incidents.root_cause_label")}:</span> {item.root_cause}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: "12px 16px", verticalAlign: "top" }}>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "12px",
                          color: "#374151",
                          background: "#F3F4F6",
                          border: "1px solid #E5E7EB",
                          wordBreak: "break-all",
                        }}
                      >
                        {item.category}
                      </span>
                    </td>
                    <td style={{ padding: "12px 16px", verticalAlign: "top" }}>
                      {getStatusBadge(item.status)}
                    </td>
                    <td style={{ padding: "12px 16px", fontSize: "12px", color: "#6B7280", verticalAlign: "top" }}>
                      {formatDate(item.created_at)}
                    </td>
                    <td style={{ padding: "12px 16px", verticalAlign: "top", textAlign: "right" }}>
                      <div style={{ display: "inline-flex", gap: "6px", justifyContent: "flex-end" }}>
                        {item.status.toLowerCase() === "open" && (
                          <button
                            disabled={updatingId === item.id}
                            onClick={() => handleStatusChange(item.id, "investigating")}
                            style={{
                              padding: "4px 8px",
                              fontSize: "12px",
                              fontWeight: 500,
                              background: "#FEF3C7",
                              color: "#92400E",
                              border: "1px solid #FCD34D",
                              borderRadius: "5px",
                              cursor: "pointer",
                            }}
                          >
                            {t("incidents.btn_investigate")}
                          </button>
                        )}
                        {item.status.toLowerCase() !== "resolved" ? (
                          <button
                            disabled={updatingId === item.id}
                            onClick={() => handleStatusChange(item.id, "resolved")}
                            style={{
                              padding: "4px 8px",
                              fontSize: "12px",
                              fontWeight: 500,
                              background: "#D1FAE5",
                              color: "#065F46",
                              border: "1px solid #6EE7B7",
                              borderRadius: "5px",
                              cursor: "pointer",
                            }}
                          >
                            {t("incidents.btn_resolve")}
                          </button>
                        ) : (
                          <button
                            disabled={updatingId === item.id}
                            onClick={() => handleStatusChange(item.id, "open")}
                            style={{
                              padding: "4px 8px",
                              fontSize: "12px",
                              fontWeight: 500,
                              background: "#F3F4F6",
                              color: "#374151",
                              border: "1px solid #D1D5DB",
                              borderRadius: "5px",
                              cursor: "pointer",
                            }}
                          >
                            {t("incidents.btn_reopen")}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
