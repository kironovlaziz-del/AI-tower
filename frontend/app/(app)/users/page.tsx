"use client";

import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/PageHeader";
import { Form } from "@/components/Form";
import { StatusPill } from "@/components/Pill";
import { useAuth } from "@/lib/auth";
import {
  inviteUser,
  listUsers,
  updateUserRole,
  updateUserStatus,
} from "@/lib/api";
import type { User, UserRole } from "@/lib/types";

const ROLES: UserRole[] = ["admin", "approver", "user"];

export default function UsersPage() {
  const { t, i18n } = useTranslation();
  const { user: me } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("user");
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    listUsers()
      .then(setUsers)
      .catch(() => setUsers([]))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await inviteUser({ name, email, password, role });
      setName("");
      setEmail("");
      setPassword("");
      setRole("user");
      setShowForm(false);
      refresh();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(detail || t("users.failed"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRoleChange(id: number, next: UserRole) {
    setBusyId(id);
    try {
      await updateUserRole(id, next);
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  async function handleStatusToggle(u: User) {
    setBusyId(u.id);
    try {
      await updateUserStatus(u.id, u.status === "active" ? "disabled" : "active");
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  if (me && me.role !== "admin") {
    return (
      <>
        <PageHeader title={t("users.title")} />
        <div className="content">
          <p className="hint-text">{t("users.admin_only")}</p>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title={t("users.title")}
        actions={
          <button
            className="btn btn-primary btn-sm"
            onClick={() => setShowForm((s) => !s)}
          >
            {showForm ? t("users.cancel") : t("users.invite")}
          </button>
        }
      />
      <div className="content">
        {showForm && (
          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-header">
              <h2>{t("users.form_title")}</h2>
            </div>
            <div className="panel-body">
              <Form onSubmit={handleInvite}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="name">{t("users.name")}</label>
                    <input
                      id="name"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder={t("users.name_placeholder")}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="email">{t("users.email")}</label>
                    <input
                      id="email"
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@company.com"
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="password">{t("users.password")}</label>
                    <input
                      id="password"
                      type="text"
                      required
                      minLength={8}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={t("users.password_hint")}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="role">{t("users.role")}</label>
                    <select
                      id="role"
                      value={role}
                      onChange={(e) => setRole(e.target.value as UserRole)}
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {t(`users.roles.${r}`)}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? t("users.submitting") : t("users.submit")}
                </button>
              </Form>
            </div>
          </div>
        )}

        <div className="panel">
          <div className="panel-header">
            <h2>{t("users.title")}</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>{t("users.col_id")}</th>
                <th>{t("users.col_name")}</th>
                <th>{t("users.col_email")}</th>
                <th>{t("users.col_role")}</th>
                <th>{t("users.col_status")}</th>
                <th>{t("users.col_created")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr className="empty-row">
                  <td colSpan={7}>{t("users.loading")}</td>
                </tr>
              )}
              {!loading && users.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={7}>{t("users.empty")}</td>
                </tr>
              )}
              {users.map((u) => {
                const isMe = me?.id === u.id;
                return (
                  <tr key={u.id}>
                    <td className="mono">#{u.id}</td>
                    <td>
                      {u.name}
                      {isMe && (
                        <span className="pill pill-accent" style={{ marginLeft: 8 }}>
                          {t("users.you")}
                        </span>
                      )}
                    </td>
                    <td className="mono">{u.email}</td>
                    <td>
                      <select
                        value={u.role}
                        disabled={busyId === u.id}
                        onChange={(e) => handleRoleChange(u.id, e.target.value as UserRole)}
                        style={{
                          border: "1px solid var(--border-strong)",
                          borderRadius: 4,
                          padding: "4px 8px",
                          background: "var(--bg-panel)",
                          fontSize: 12,
                        }}
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>
                            {t(`users.roles.${r}`)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <StatusPill status={u.status} />
                    </td>
                    <td className="mono">
                      {new Date(u.created_at).toLocaleString(i18n.language)}
                    </td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {!isMe && (
                        <button
                          className="btn btn-sm"
                          disabled={busyId === u.id}
                          onClick={() => handleStatusToggle(u)}
                        >
                          {u.status === "active"
                            ? t("users.deactivate")
                            : t("users.activate")}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
