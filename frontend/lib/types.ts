export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface User {
  id: number;
  org_id: number;
  email: string;
  name: string;
  role: "admin" | "approver" | "user";
  status: string;
  created_at: string;
}

export interface Policy {
  id: number;
  org_id: number;
  name: string;
  description?: string | null;
  status: string;
  created_at: string;
}

export interface PolicyVersion {
  id: number;
  policy_id: number;
  version: number;
  rules_json: Record<string, unknown>;
  created_by?: number | null;
  created_at: string;
  approved_by?: number | null;
  approved_at?: string | null;
}

export interface Provider {
  id: number;
  org_id: number;
  name: string;
  type: string;
  status: string;
  sla?: string | null;
  risk_score: number;
  base_url?: string | null;
  default_model?: string | null;
  has_credentials: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface UseCase {
  id: number;
  org_id: number;
  name: string;
  owner_user_id?: number | null;
  risk_level: RiskLevel;
  allowed_providers_json?: Record<string, unknown> | null;
  approved_policy_version_id?: number | null;
  status: string;
  created_at: string;
}

export interface AIRequest {
  id: number;
  org_id: number;
  use_case_id?: number | null;
  user_id?: number | null;
  provider_id?: number | null;
  input_text?: string | null;
  masked_input_text?: string | null;
  purpose?: string | null;
  risk_level: RiskLevel;
  status: string;
  firewall_flags?: string[] | null;
  created_at: string;
}

export interface AIResponse {
  id: number;
  request_id: number;
  provider_response_json?: Record<string, unknown> | null;
  response_text?: string | null;
  confidence_score?: number | null;
  created_at: string;
}

export interface Approval {
  id: number;
  request_id: number;
  approver_user_id?: number | null;
  decision?: string | null;
  reason?: string | null;
  created_at: string;
}

export interface Incident {
  id: number;
  org_id: number;
  request_id?: number | null;
  severity: RiskLevel;
  category: string;
  summary: string;
  impact?: string | null;
  root_cause?: string | null;
  status: string;
  created_at: string;
  resolved_at?: string | null;
}

export interface AuditLog {
  id: number;
  org_id: number;
  actor_user_id?: number | null;
  entity_type: string;
  entity_id?: number | null;
  action: string;
  metadata_json?: Record<string, unknown> | null;
  created_at: string;
}

export type OverrideType = "stop" | "edit" | "rollback";

export interface Override {
  id: number;
  request_id: number;
  override_type: OverrideType;
  override_payload_json?: Record<string, unknown> | null;
  operator_user_id?: number | null;
  created_at: string;
}

export type ShadowSightingStatus =
  | "new"
  | "reviewing"
  | "confirmed_shadow"
  | "dismissed"
  | "registered";

export interface ShadowSighting {
  id: number;
  org_id: number;
  tool_name: string;
  domain?: string | null;
  detected_via: string;
  user_hint?: string | null;
  notes?: string | null;
  status: ShadowSightingStatus;
  reported_by?: number | null;
  registered_provider_id?: number | null;
  created_at: string;
  resolved_at?: string | null;
}

export interface Dataset {
  id: number;
  org_id: number;
  name: string;
  description?: string | null;
  task_type: string;
  file_format?: string | null;
  size_bytes: number;
  uploaded_by?: number | null;
  created_at: string;
}

export interface ComputeStatus {
  cpu_logical_cores: number;
  cpu_physical_cores?: number | null;
  ram_total_gb: number;
  ram_available_gb: number;
  disk_total_gb: number;
  disk_free_gb: number;
  gpu_available: boolean;
  gpu_names: string[];
  gpu_detection_method: string;
  gpu_vram_total_gb?: number | null;
  gpu_vram_free_gb?: number | null;
  recommendation_tier: string;
  recommendation_detail: string;
  warnings: string[];
}

export type TrainingTaskType =
  | "tabular_classification"
  | "tabular_regression"
  | "transformer_text_classification"
  | "transformer_text_generation";
export type TrainingAlgorithm =
  | "logistic_regression"
  | "random_forest_classifier"
  | "linear_regression"
  | "random_forest_regressor";
export type TrainingJobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface TrainingJob {
  id: number;
  org_id: number;
  dataset_id: number;
  name: string;
  task_type: TrainingTaskType;
  target_column: string | null;
  algorithm?: TrainingAlgorithm | null;
  base_model?: string | null;
  hyperparameters_json?: Record<string, unknown> | null;
  feature_columns_json?: string[] | null;
  status: TrainingJobStatus;
  celery_task_id?: string | null;
  model_path?: string | null;
  metrics_json?: Record<string, number> | null;
  error_message?: string | null;
  created_by?: number | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface AllowedTransformerModel {
  id: string;
  label: string;
  note: string;
  estimated_vram_gb: number;
  fits_vram: boolean | null;
}

export interface AllowedModelsResponse {
  gpu_available: boolean;
  gpu_vram_total_gb?: number | null;
  gpu_vram_free_gb?: number | null;
  models: AllowedTransformerModel[];
  custom_model_allowed: boolean;
}

export type NotificationChannelType = "email" | "webhook";

export interface NotificationChannel {
  id: number;
  org_id: number;
  channel_type: NotificationChannelType;
  target: string;
  events_json: string[];
  enabled: boolean;
  created_by?: number | null;
  created_at: string;
}
