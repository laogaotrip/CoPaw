import { request } from "../request";
import type {
  AgentModelSlotsRequest,
  AgentModelSlotsResponse,
  AgentTriggerPolicyConfig,
  EvolutionConfig,
  CollaborationActionRequest,
  CollaborationActionResponse,
  CollaborationEventsResponse,
  CollaborationStats,
  CronAuditEventsResponse,
  CronAuditStats,
} from "../types/digitalEmployee";

export const digitalEmployeeApi = {
  getAgentModelSlots: () =>
    request<AgentModelSlotsResponse>("/models/agent-slots"),

  updateAgentModelSlots: (body: AgentModelSlotsRequest) =>
    request<AgentModelSlotsResponse>("/models/agent-slots", {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  getTriggerPolicy: () => request<AgentTriggerPolicyConfig>("/config/triggers"),

  updateTriggerPolicy: (body: AgentTriggerPolicyConfig) =>
    request<AgentTriggerPolicyConfig>("/config/triggers", {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  getEvolutionConfig: () => request<EvolutionConfig>("/config/evolution"),

  updateEvolutionConfig: (body: EvolutionConfig) =>
    request<EvolutionConfig>("/config/evolution", {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  notifyCollaboration: (body: CollaborationActionRequest) =>
    request<CollaborationActionResponse>("/collaboration/notify", {
      method: "POST",
      body: JSON.stringify({
        target_agent_id: body.target_agent_id,
        text: body.text ?? "",
        channel: body.channel ?? "console",
        user_id: body.user_id ?? "collaboration",
        session_id: body.session_id ?? "collaboration",
      }),
    }),

  consultCollaboration: (body: CollaborationActionRequest) =>
    request<CollaborationActionResponse>("/collaboration/consult", {
      method: "POST",
      body: JSON.stringify({
        target_agent_id: body.target_agent_id,
        prompt: body.prompt ?? "",
        user_id: body.user_id ?? "collaboration",
        session_id: body.session_id ?? "collaboration",
        hop_count: body.hop_count ?? 0,
      }),
    }),

  delegateCollaboration: (body: CollaborationActionRequest) =>
    request<CollaborationActionResponse>("/collaboration/delegate", {
      method: "POST",
      body: JSON.stringify({
        target_agent_id: body.target_agent_id,
        prompt: body.prompt ?? "",
        user_id: body.user_id ?? "collaboration",
        session_id: body.session_id ?? "collaboration",
        hop_count: body.hop_count ?? 0,
      }),
    }),

  listCollaborationEvents: (params?: {
    limit?: number;
    mode?: string;
    target_agent_id?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    if (params?.mode) query.set("mode", params.mode);
    if (params?.target_agent_id)
      query.set("target_agent_id", params.target_agent_id);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request<CollaborationEventsResponse>(
      `/collaboration/events${suffix}`,
    );
  },

  getCollaborationStats: (since_hours = 24) =>
    request<CollaborationStats>(
      `/collaboration/stats?since_hours=${encodeURIComponent(String(since_hours))}`,
    ),

  listCronAuditEvents: (params?: {
    limit?: number;
    job_id?: string;
    status?: string;
    trigger_type?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    if (params?.job_id) query.set("job_id", params.job_id);
    if (params?.status) query.set("status", params.status);
    if (params?.trigger_type) query.set("trigger_type", params.trigger_type);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request<CronAuditEventsResponse>(`/cron/audit/events${suffix}`);
  },

  getCronAuditStats: (since_hours = 24) =>
    request<CronAuditStats>(
      `/cron/audit/stats?since_hours=${encodeURIComponent(String(since_hours))}`,
    ),
};
