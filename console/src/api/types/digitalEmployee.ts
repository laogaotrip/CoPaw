import type { ModelSlotConfig } from "./provider";

export interface AgentModelSlotsResponse {
  active_model: ModelSlotConfig | null;
  primary_model: ModelSlotConfig | null;
  fallback_model: ModelSlotConfig | null;
  auto_model_failover: boolean;
}

export interface AgentModelSlotsRequest {
  primary_model: ModelSlotConfig | null;
  fallback_model: ModelSlotConfig | null;
  auto_model_failover: boolean;
}

export interface AgentTriggerPolicyConfig {
  enable_webhook: boolean;
  enable_poll: boolean;
  block_private_network: boolean;
  allowed_poll_domains: string[];
}

export interface EvolutionConfig {
  enabled: boolean;
  mode: string;
  every: string;
  query_file: string;
  timeout_seconds: number;
  session_id: string;
  user_id: string;
}

export interface CollaborationActionRequest {
  target_agent_id: string;
  prompt?: string;
  text?: string;
  user_id?: string;
  session_id?: string;
  channel?: string;
  hop_count?: number;
}

export interface CollaborationActionResponse {
  ok?: boolean;
  target_agent_id?: string;
  response_text?: string;
  events?: unknown[];
}

export interface CollaborationEvent {
  ts?: string;
  mode?: string;
  source_agent_id?: string;
  target_agent_id?: string;
  user_id?: string;
  session_id?: string;
  prompt?: string;
  response_text?: string;
  [key: string]: unknown;
}

export interface CollaborationEventsResponse {
  events: CollaborationEvent[];
}

export interface CollaborationStats {
  total: number;
  by_mode: Record<string, number>;
  by_target_agent: Record<string, number>;
  since_hours: number;
}

export interface CronAuditEvent {
  ts?: string;
  job_id?: string;
  status?: string;
  trigger_type?: string;
  detail?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface CronAuditEventsResponse {
  events: CronAuditEvent[];
}

export interface CronAuditStats {
  total: number;
  by_status: Record<string, number>;
  by_trigger_type: Record<string, number>;
  since_hours: number;
}
