// Agent-to-Agent Governance API calls. Reuses the shared axios instance
// and Page<T>/unwrap conventions from api.ts.
import { api, Page } from "./api";
import type {
  Agent,
  AgentCreated,
  DelegationChainT,
  DelegationChainDetail,
  AgentActionT,
  AgentPolicyT,
  AgentIncidentT,
} from "./agent_types";

function items<T>(p: Page<T>): T[] {
  return p.items;
}

// ---- Agents ----
export async function listAgents() {
  const { data } = await api.get<Page<Agent>>("/agents/");
  return items(data);
}

export async function getAgent(id: number) {
  const { data } = await api.get<Agent>(`/agents/${id}`);
  return data;
}

export async function registerAgent(payload: {
  name: string;
  description?: string;
  agent_type?: string;
  owner_team?: string;
  capabilities?: string[];
  allowed_tools?: string[];
  allowed_models?: string[];
  max_delegation_depth?: number;
}) {
  const { data } = await api.post<AgentCreated>("/agents/register", payload);
  return data;
}

export async function updateAgent(
  id: number,
  payload: Partial<{
    name: string;
    description: string;
    owner_team: string;
    capabilities: string[];
    allowed_tools: string[];
    allowed_models: string[];
    max_delegation_depth: number;
    status: string;
  }>
) {
  const { data } = await api.put<Agent>(`/agents/${id}`, payload);
  return data;
}

export async function killAgent(id: number, reason: string, cascade = true) {
  const { data } = await api.post<{ agents_stopped: number[]; chains_terminated: number }>(
    `/agents/${id}/kill`,
    { reason, cascade }
  );
  return data;
}

// ---- Delegation chains ----
export async function listChains() {
  const { data } = await api.get<Page<DelegationChainT>>("/agents/delegation-chains/");
  return items(data);
}

export async function getChain(id: number) {
  const { data } = await api.get<DelegationChainDetail>(`/agents/delegation-chains/${id}`);
  return data;
}

// ---- Actions ----
export async function listAgentActions(params?: { chain_id?: number; agent_id?: number; result?: string }) {
  const { data } = await api.get<Page<AgentActionT>>("/agents/actions/", { params });
  return items(data);
}

export async function approveAgentAction(actionId: number) {
  const { data } = await api.post<AgentActionT>(`/agents/actions/${actionId}/approve`);
  return data;
}

export async function denyAgentAction(actionId: number, reason?: string) {
  const { data } = await api.post<AgentActionT>(`/agents/actions/${actionId}/deny`, { reason });
  return data;
}

// ---- Policies ----
export async function listAgentPolicies() {
  const { data } = await api.get<Page<AgentPolicyT>>("/agents/policies/");
  return items(data);
}

export async function createAgentPolicy(payload: {
  name: string;
  agent_id?: number | null;
  rules: Record<string, unknown>;
  priority?: number;
  enabled?: boolean;
}) {
  const { data } = await api.post<AgentPolicyT>("/agents/policies/", payload);
  return data;
}

// ---- Incidents ----
export async function listAgentIncidents() {
  const { data } = await api.get<Page<AgentIncidentT>>("/agents/incidents/");
  return items(data);
}

// ---- Governance graph ----
import type { GovernanceGraphT } from "./agent_types";

export async function getGovernanceGraph() {
  const { data } = await api.get<GovernanceGraphT>("/agents/graph");
  return data;
}
