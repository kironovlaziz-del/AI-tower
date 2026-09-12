import axios from "axios";
import type {
  User,
  Policy,
  PolicyVersion,
  Provider,
  UseCase,
  AIRequest,
  AIResponse,
  Approval,
  Incident,
  AuditLog,
  Override,
  OverrideType,
  ShadowSighting,
  Dataset,
  ComputeStatus,
  TrainingJob,
  TrainingTaskType,
  TrainingAlgorithm,
  AllowedModelsResponse,
  NotificationChannel,
  NotificationChannelType,
  RiskLevel,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

const TOKEN_KEY = "ai_ct_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      typeof window !== "undefined" &&
      error?.response?.status === 401 &&
      window.location.pathname !== "/login"
    ) {
      clearToken();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ---- Auth ----
export async function login(email: string, password: string) {
  const { data } = await api.post<{ access_token: string; token_type: string }>(
    "/auth/login",
    { email, password }
  );
  return data;
}

export async function register(payload: {
  email: string;
  password: string;
  name: string;
  org_name: string;
}) {
  const { data } = await api.post<User>("/users/register", payload);
  return data;
}

export async function getMe() {
  const { data } = await api.get<User>("/users/me");
  return data;
}


// ---- Users (admin-only management) ----
export async function listUsers() {
  const { data } = await api.get<User[]>("/users/");
  return data;
}

export async function inviteUser(payload: {
  email: string;
  name: string;
  role: "admin" | "approver" | "user";
  password: string;
}) {
  const { data } = await api.post<User>("/users/invite", payload);
  return data;
}

export async function updateUserRole(id: number, role: "admin" | "approver" | "user") {
  const { data } = await api.put<User>(`/users/${id}/role`, { role });
  return data;
}

export async function updateUserStatus(id: number, status: "active" | "disabled") {
  const { data } = await api.put<User>(`/users/${id}/status`, { status });
  return data;
}

// ---- Policies (Policy Center) ----
export async function listPolicies() {
  const { data } = await api.get<Policy[]>("/policies/");
  return data;
}

export async function getPolicy(id: number) {
  const { data } = await api.get<Policy>(`/policies/${id}`);
  return data;
}

export async function createPolicy(payload: { name: string; description?: string }) {
  const { data } = await api.post<Policy>("/policies/", payload);
  return data;
}

export async function listPolicyVersions(policyId: number) {
  const { data } = await api.get<PolicyVersion[]>(`/policies/${policyId}/versions`);
  return data;
}

export async function createPolicyVersion(
  policyId: number,
  rulesJson: Record<string, unknown>
) {
  const { data } = await api.post<PolicyVersion>(`/policies/${policyId}/versions`, {
    rules_json: rulesJson,
  });
  return data;
}

export async function approvePolicyVersion(policyId: number, versionId: number) {
  const { data } = await api.post<PolicyVersion>(
    `/policies/${policyId}/versions/${versionId}/approve`
  );
  return data;
}

// ---- Providers (Vendor Risk Desk) ----
export async function listProviders() {
  const { data } = await api.get<Provider[]>("/providers/");
  return data;
}

export async function createProvider(payload: {
  name: string;
  type: string;
  status?: string;
  sla?: string;
  risk_score?: number;
  base_url?: string;
  default_model?: string;
  api_key?: string;
}) {
  const { data } = await api.post<Provider>("/providers/", payload);
  return data;
}

export async function updateProvider(
  id: number,
  payload: Partial<{
    name: string;
    type: string;
    status: string;
    sla: string;
    risk_score: number;
    base_url: string;
    default_model: string;
    api_key: string;
  }>
) {
  const { data } = await api.put<Provider>(`/providers/${id}`, payload);
  return data;
}

// ---- Use cases ----
export async function listUseCases() {
  const { data } = await api.get<UseCase[]>("/use-cases/");
  return data;
}

export async function getUseCase(id: number) {
  const { data } = await api.get<UseCase>(`/use-cases/${id}`);
  return data;
}

export async function createUseCase(payload: {
  name: string;
  risk_level: RiskLevel;
  owner_user_id?: number;
  approved_policy_version_id?: number;
}) {
  const { data } = await api.post<UseCase>("/use-cases/", payload);
  return data;
}

export async function updateUseCase(
  id: number,
  payload: Partial<{
    name: string;
    risk_level: RiskLevel;
    status: string;
    approved_policy_version_id: number;
  }>
) {
  const { data } = await api.put<UseCase>(`/use-cases/${id}`, payload);
  return data;
}

// ---- Requests (Usage Registry / Action Trace) ----
export async function listRequests() {
  const { data } = await api.get<AIRequest[]>("/requests/");
  return data;
}

export async function getRequest(id: number) {
  const { data } = await api.get<AIRequest>(`/requests/${id}`);
  return data;
}

export async function getRequestResponse(id: number) {
  const { data } = await api.get<AIResponse | null>(`/requests/${id}/response`);
  return data;
}

export async function createRequest(payload: {
  use_case_id: number;
  provider_id: number;
  input_text: string;
  purpose: string;
}) {
  const { data } = await api.post<AIRequest>("/requests/", payload);
  return data;
}

// ---- Approvals ----
export async function listApprovals() {
  const { data } = await api.get<Approval[]>("/approvals/");
  return data;
}

export async function createApproval(payload: { request_id: number }) {
  const { data } = await api.post<Approval>("/approvals/", payload);
  return data;
}

export async function decideApproval(
  id: number,
  payload: { decision: "approved" | "rejected"; reason?: string }
) {
  const { data } = await api.post<Approval>(`/approvals/${id}/decision`, payload);
  return data;
}

// ---- Incidents ----
export async function listIncidents() {
  const { data } = await api.get<Incident[]>("/incidents/");
  return data;
}

export async function getIncident(id: number) {
  const { data } = await api.get<Incident>(`/incidents/${id}`);
  return data;
}

export async function createIncident(payload: {
  request_id?: number;
  severity: RiskLevel;
  category: string;
  summary: string;
  impact?: string;
}) {
  const { data } = await api.post<Incident>("/incidents/", payload);
  return data;
}

export async function updateIncident(
  id: number,
  payload: Partial<{
    severity: RiskLevel;
    category: string;
    summary: string;
    impact: string;
    root_cause: string;
    status: string;
  }>
) {
  const { data } = await api.put<Incident>(`/incidents/${id}`, payload);
  return data;
}

// ---- Audit & Reporting ----
export async function listAuditLogs(filters?: {
  entity_type?: string;
  entity_id?: number;
  actor_user_id?: number;
}) {
  const params = new URLSearchParams();
  if (filters?.entity_type) params.set("entity_type", filters.entity_type);
  if (filters?.entity_id != null) params.set("entity_id", String(filters.entity_id));
  if (filters?.actor_user_id != null)
    params.set("actor_user_id", String(filters.actor_user_id));
  const qs = params.toString();
  const { data } = await api.get<AuditLog[]>(`/audit-logs/${qs ? `?${qs}` : ""}`);
  return data;
}

// ---- Override Console ----
export async function listOverrides(requestId: number) {
  const { data } = await api.get<Override[]>("/overrides/", {
    params: { request_id: requestId },
  });
  return data;
}

export async function createOverride(payload: {
  request_id: number;
  override_type: OverrideType;
  override_payload_json?: Record<string, unknown>;
}) {
  const { data } = await api.post<Override>("/overrides/", payload);
  return data;
}

// ---- Shadow AI Monitor ----
export async function listShadowSightings(statusFilter?: string) {
  const { data } = await api.get<ShadowSighting[]>("/shadow-ai/", {
    params: statusFilter ? { status_filter: statusFilter } : undefined,
  });
  return data;
}

export async function createShadowSighting(payload: {
  tool_name: string;
  domain?: string;
  detected_via?: string;
  user_hint?: string;
  notes?: string;
}) {
  const { data } = await api.post<ShadowSighting>("/shadow-ai/", payload);
  return data;
}

export async function updateShadowSighting(
  id: number,
  payload: { status?: string; notes?: string }
) {
  const { data } = await api.put<ShadowSighting>(`/shadow-ai/${id}`, payload);
  return data;
}

export async function registerShadowSighting(
  id: number,
  payload?: { provider_type?: string; provider_sla?: string }
) {
  const { data } = await api.post<ShadowSighting>(`/shadow-ai/${id}/register`, payload || {});
  return data;
}

// ---- MLOps: Compute Detector ----
export async function getComputeStatus() {
  const { data } = await api.get<ComputeStatus>("/compute/status");
  return data;
}

// ---- MLOps: Dataset Manager ----
export async function listDatasets() {
  const { data } = await api.get<Dataset[]>("/datasets/");
  return data;
}

export async function uploadDataset(payload: {
  name: string;
  description?: string;
  task_type: string;
  file: File;
}) {
  const form = new FormData();
  form.append("name", payload.name);
  if (payload.description) form.append("description", payload.description);
  form.append("task_type", payload.task_type);
  form.append("file", payload.file);
  const { data } = await api.post<Dataset>("/datasets/", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function deleteDataset(id: number) {
  await api.delete(`/datasets/${id}`);
}

// ---- MLOps: Training Service ----
export async function listTrainingJobs() {
  const { data } = await api.get<TrainingJob[]>("/training-jobs/");
  return data;
}

export async function getTrainingJob(id: number) {
  const { data } = await api.get<TrainingJob>(`/training-jobs/${id}`);
  return data;
}

export async function createTrainingJob(payload: {
  dataset_id: number;
  name: string;
  task_type: TrainingTaskType;
  target_column?: string;
  algorithm?: TrainingAlgorithm;
  base_model?: string;
  hyperparameters?: Record<string, unknown>;
}) {
  const { data } = await api.post<TrainingJob>("/training-jobs/", payload);
  return data;
}

export async function getAllowedModels(taskType: string = "transformer_text_classification") {
  const { data } = await api.get<AllowedModelsResponse>("/compute/allowed-models", {
    params: { task_type: taskType },
  });
  return data;
}

export async function cancelTrainingJob(id: number) {
  const { data } = await api.post<TrainingJob>(`/training-jobs/${id}/cancel`);
  return data;
}

export async function retryTrainingJob(id: number) {
  const { data } = await api.post<TrainingJob>(`/training-jobs/${id}/retry`);
  return data;
}

/**
 * Trigger a streaming download of a training job's model artifact.
 *
 * The backend issues a short-lived, single-purpose token via POST
 * /training-jobs/{id}/download-token, then the browser navigates directly
 * to the streaming download URL. This keeps large model files out of
 * JavaScript memory - a 1 GB model would otherwise be buffered twice
 * (once in axios, once in the resulting Blob).
 */
export async function downloadTrainingJobModel(id: number, filenameHint: string) {
  const { data } = await api.post<{ token: string; expires_in: number }>(
    `/training-jobs/${id}/download-token`
  );
  const url = `${API_BASE_URL}/training-jobs/${id}/download?token=${encodeURIComponent(data.token)}`;

  // Native navigation so the browser streams the response to disk.
  const link = document.createElement("a");
  link.href = url;
  link.download = filenameHint;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

export async function predictWithTrainingJob(
  id: number,
  features: Record<string, unknown>
) {
  const { data } = await api.post<{ prediction: unknown }>(
    `/training-jobs/${id}/predict`,
    { features }
  );
  return data;
}

// ---- Notification Service ----
export async function listNotificationChannels() {
  const { data } = await api.get<NotificationChannel[]>("/notification-channels/");
  return data;
}

export async function getNotificationEventTypes() {
  const { data } = await api.get<{ event_types: string[] }>(
    "/notification-channels/event-types"
  );
  return data.event_types;
}

export async function createNotificationChannel(payload: {
  channel_type: NotificationChannelType;
  target: string;
  events: string[];
  enabled?: boolean;
}) {
  const { data } = await api.post<NotificationChannel>("/notification-channels/", payload);
  return data;
}

export async function updateNotificationChannel(
  id: number,
  payload: Partial<{ target: string; events: string[]; enabled: boolean }>
) {
  const { data } = await api.put<NotificationChannel>(`/notification-channels/${id}`, payload);
  return data;
}

export async function deleteNotificationChannel(id: number) {
  await api.delete(`/notification-channels/${id}`);
}

export async function testNotificationChannel(id: number) {
  await api.post(`/notification-channels/${id}/test`);
}
