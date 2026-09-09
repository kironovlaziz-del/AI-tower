"use client";

import React, { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { createProvider, listProviders, updateProvider } from "@/lib/api";
import type { Provider } from "@/lib/types";

const TYPE_DEFAULTS: Record<string, { base_url: string; default_model: string }> = {
  openai: { base_url: "https://api.openai.com/v1", default_model: "gpt-4o-mini" },
  anthropic: { base_url: "https://api.anthropic.com/v1", default_model: "claude-3-5-haiku-20241022" },
  azure_openai: { base_url: "", default_model: "gpt-4o-mini" },
  custom: { base_url: "", default_model: "" },
};

function ToggleSwitch({
  on,
  onClick,
  disabled,
}: {
  on: boolean;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button className="conn-toggle" onClick={onClick} disabled={disabled} type="button">
      <span className={`conn-toggle-track${on ? " on" : ""}`}>
        <span className="conn-toggle-thumb" />
      </span>
      {on ? "подключено" : "отключено"}
    </button>
  );
}

function ConnectionCard({
  provider,
  onToggle,
  onSaveCredentials,
  busy,
}: {
  provider: Provider;
  onToggle: () => void;
  onSaveCredentials: (fields: { api_key?: string; base_url?: string; default_model?: string }) => Promise<void>;
  busy: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState(provider.base_url || "");
  const [defaultModel, setDefaultModel] = useState(provider.default_model || "");
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    setSaving(true);
    try {
      await onSaveCredentials({
        api_key: apiKey || undefined,
        base_url: baseUrl,
        default_model: defaultModel,
      });
      setApiKey("");
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="conn-card">
      <div className="conn-card-header">
        <div>
          <div className="conn-card-name">{provider.name}</div>
          <div className="conn-card-type">{provider.type}</div>
        </div>
        <ToggleSwitch on={provider.status === "active"} onClick={onToggle} disabled={busy} />
      </div>
      <div className="hint-text">{provider.sla || "SLA не указан"}</div>
      <div>
        <span className={`pill ${provider.has_credentials ? "pill-low" : "pill-medium"}`}>
          {provider.has_credentials ? "ключ настроен" : "без ключа (mock-ответы)"}
        </span>
      </div>

      {!editing ? (
        <button className="btn btn-sm" onClick={() => setEditing(true)}>
          Настроить доступ
        </button>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="field" style={{ margin: 0 }}>
            <label>API-ключ {provider.has_credentials && "(оставьте пустым, чтобы не менять)"}</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
            />
          </div>
          <div className="field" style={{ margin: 0 }}>
            <label>Base URL</label>
            <input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder={TYPE_DEFAULTS[provider.type]?.base_url || "https://..."}
            />
          </div>
          <div className="field" style={{ margin: 0 }}>
            <label>Модель по умолчанию</label>
            <input
              value={defaultModel}
              onChange={(e) => setDefaultModel(e.target.value)}
              placeholder={TYPE_DEFAULTS[provider.type]?.default_model || "model-name"}
            />
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
              {saving ? "Сохраняем…" : "Сохранить"}
            </button>
            <button className="btn btn-sm" onClick={() => setEditing(false)} disabled={saving}>
              Отмена
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ConnectionsPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("openai");
  const [sla, setSla] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [defaultModel, setDefaultModel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    listProviders()
      .then(setProviders)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  function handleTypeChange(next: string) {
    setType(next);
    const defaults = TYPE_DEFAULTS[next];
    if (defaults) {
      setBaseUrl(defaults.base_url);
      setDefaultModel(defaults.default_model);
    }
  }

  async function handleToggle(p: Provider) {
    setBusyId(p.id);
    try {
      const next = p.status === "active" ? "suspended" : "active";
      await updateProvider(p.id, { status: next });
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  async function handleSaveCredentials(
    p: Provider,
    fields: { api_key?: string; base_url?: string; default_model?: string }
  ) {
    setBusyId(p.id);
    try {
      await updateProvider(p.id, fields);
      refresh();
    } finally {
      setBusyId(null);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createProvider({
        name,
        type,
        sla: sla || undefined,
        base_url: baseUrl || undefined,
        default_model: defaultModel || undefined,
        api_key: apiKey || undefined,
      });
      setName("");
      setSla("");
      setApiKey("");
      setBaseUrl("");
      setDefaultModel("");
      setType("openai");
      setShowForm(false);
      refresh();
    } catch {
      setError("Не удалось подключить.");
    } finally {
      setSubmitting(false);
    }
  }

  const activeCount = providers.filter((p) => p.status === "active").length;
  const withKeysCount = providers.filter((p) => p.has_credentials).length;

  return (
    <>
      <PageHeader
        title="Connections"
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Отмена" : "Подключить AI"}
          </button>
        }
      />
      <div className="content">
        <p className="hint-text" style={{ marginBottom: 16 }}>
          Здесь включаются/отключаются подключения и настраивается реальный
          доступ (API-ключ, base URL, модель по умолчанию). Ключ хранится в
          БД в зашифрованном виде и никогда не возвращается обратно в API —
          только показывается, настроен он или нет. Без ключа запросы через
          такое подключение получают явно помеченный mock-ответ, а не
          реальный вызов провайдера.
        </p>

        <div className="stat-grid" style={{ marginBottom: 4 }}>
          <div className="stat">
            <div className="stat-label">Подключено</div>
            <div className="stat-value">{activeCount}</div>
          </div>
          <div className="stat">
            <div className="stat-label">С реальным ключом</div>
            <div className="stat-value">{withKeysCount}</div>
          </div>
          <div className="stat">
            <div className="stat-label">Всего подключений</div>
            <div className="stat-value">{providers.length}</div>
          </div>
        </div>

        {showForm && (
          <div className="panel" style={{ margin: "20px 0" }}>
            <div className="panel-header">
              <h2>Новое подключение</h2>
            </div>
            <div className="panel-body">
              <form onSubmit={handleCreate}>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="name">Название</label>
                    <input
                      id="name"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="OpenAI, Anthropic, локальная модель…"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="type">Тип</label>
                    <select id="type" value={type} onChange={(e) => handleTypeChange(e.target.value)}>
                      <option value="openai">openai</option>
                      <option value="anthropic">anthropic</option>
                      <option value="azure_openai">azure_openai</option>
                      <option value="custom">custom</option>
                    </select>
                  </div>
                </div>
                <div className="form-row">
                  <div className="field">
                    <label htmlFor="base_url">Base URL</label>
                    <input
                      id="base_url"
                      value={baseUrl}
                      onChange={(e) => setBaseUrl(e.target.value)}
                      placeholder={TYPE_DEFAULTS[type]?.base_url || "https://..."}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="default_model">Модель по умолчанию</label>
                    <input
                      id="default_model"
                      value={defaultModel}
                      onChange={(e) => setDefaultModel(e.target.value)}
                      placeholder={TYPE_DEFAULTS[type]?.default_model || "model-name"}
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="api_key">API-ключ (необязательно — без него будут mock-ответы)</label>
                  <input
                    id="api_key"
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="sk-..."
                  />
                </div>
                <div className="field">
                  <label htmlFor="sla">SLA / примечание</label>
                  <input
                    id="sla"
                    value={sla}
                    onChange={(e) => setSla(e.target.value)}
                    placeholder="Необязательно"
                  />
                </div>
                {error && <p className="error-text">{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={submitting}>
                  {submitting ? "Подключаем…" : "Подключить"}
                </button>
              </form>
            </div>
          </div>
        )}

        {loading ? (
          <p className="loading-line">Загрузка…</p>
        ) : providers.length === 0 ? (
          <p className="hint-text">Подключений пока нет — добавьте первое.</p>
        ) : (
          <div className="conn-grid">
            {providers.map((p) => (
              <ConnectionCard
                key={p.id}
                provider={p}
                busy={busyId === p.id}
                onToggle={() => handleToggle(p)}
                onSaveCredentials={(fields) => handleSaveCredentials(p, fields)}
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}
