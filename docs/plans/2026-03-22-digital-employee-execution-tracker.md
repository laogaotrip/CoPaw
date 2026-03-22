# Digital Employee Migration Execution Tracker

## Scope (Approved)
- A: Per-agent primary/fallback models (auto failover)
- B: Unified trigger engine (phase-1: once/interval/on_message)
- C: Agent collaboration loop
- D: Dual-layer knowledge base (personal + team knowledge)
- E: Autonomy boundaries (L1/L2/L3)
- F: Self-evolution loop (FULL AUTO)
- G: Channel digital-employee hardening
- H: MCP discovery/import enhancement

## Progress Matrix
- [~] A. Primary/Fallback Models (in progress: config + runtime wrapper + API done; full regression pending)
- [x] B. Unified Trigger Engine (phase-1/2 backend done: once/interval/on_message/webhook/poll)
- [~] C. Agent Collaboration (v1 backend routing via cron dispatch meta)
- [~] D. Knowledge Base V1 (dual-layer search API/tool done; regression pending)
- [~] E. Autonomy Boundaries (L1/L2/L3 policy wired to tool-guard flow)
- [~] F. Self-Evolution (full-auto scheduler + config APIs)
- [~] G. Channel Hardening (channel health + bounded send retries)
- [~] H. MCP Enhancement (preset discovery/import APIs)

## Non-Regression Requirements
- [ ] Existing config compatibility preserved (`active_model` and current cron behavior)
- [ ] Existing API compatibility preserved (no breaking schema changes)
- [ ] Existing frontend routes and component versions preserved
- [ ] i18n keys added for all new user-visible strings
- [ ] No new lint/test failures in existing suites

## Test Gates
- Unit tests for each new behavior
- Backward-compat tests for old configs
- Targeted regression tests for touched modules
- Full unit test pass before completion

## Change Log
- 2026-03-22: tracker created, implementation started with slice A.
- 2026-03-22: Slice A implemented:
  - Added `primary_model` / `fallback_model` / `auto_model_failover` to agent config.
  - Added runtime failover wrapper (`FallbackChatModel`) in model creation path.
  - Added API endpoints: `GET/PUT /models/agent-slots`.
  - Kept backward compatibility with `active_model`.
- 2026-03-22: Slice B phase-1 implemented:
  - Extended schedule type to support `once` / `interval` / `on_message`.
  - Added `on_message` dispatch hook in runner and cron manager.
  - Added loop prevention for cron-dispatched requests (`source=cron`).
  - Added unit tests for schedule validation and on_message matching.
- 2026-03-22: Slice C v1 implemented:
  - Added cron-level cross-agent routing via `dispatch.meta.target_agent_id`.
  - Default behavior unchanged when `target_agent_id` is not provided.
  - Added unit tests for same-agent and target-agent execution paths.
- 2026-03-22: Slice D v1 implemented:
  - Added `knowledge` config in `agent.json` (`enable_personal`, `enable_team`, `team_knowledge_dir`, file patterns).
  - Extended memory tool with scope-aware query (`auto|personal|team`).
  - Added lightweight shared-knowledge file scan fallback for team layer.
  - Added unit tests for config persistence and scoped tool forwarding.
- 2026-03-22: Slice E implemented:
  - Added per-agent autonomy policy config (`L1/L2/L3`).
  - Integrated policy into tool-guard flow:
    - `L1`: auto execute and log.
    - `L2`: auto execute with runtime notice.
    - `L3`: approval-first (existing behavior).
  - Added unit tests for autonomy-level gating.
- 2026-03-22: Slice F implemented:
  - Added per-agent evolution config (`enabled/mode/every/query_file/timeout`).
  - Added full-auto scheduler job in CronManager for evolution loop.
  - Added `/config/evolution` API for read/write and runtime reschedule.
- 2026-03-22: Slice G implemented:
  - Added channel health snapshot API (`GET /config/channels/health`).
  - Added bounded retry wrapper for channel outbound sends (`send_event`, `send_text`).
  - Added unit tests for retry behavior.
- 2026-03-22: Slice H implemented:
  - Added MCP preset discovery API (`GET /mcp/discovery/presets`).
  - Added MCP preset import API (`POST /mcp/discovery/import`).
  - Added unit tests for preset catalog.
- 2026-03-22: Slice B phase-2 implemented:
  - Extended schedule type to support `webhook` and `poll`.
  - Added webhook trigger API (`POST /cron/webhook/trigger`).
  - Added cron manager webhook dispatch matching (`webhook_event`, `webhook_source`, optional identity/text filters).
  - Added poll scheduler execution flow (interval-based poll + response filter + `skipped` status when unmatched).
  - Added unit tests for schedule validation, webhook/poll matching, and webhook API forwarding.
  - Regression: `tests/unit/crons` passed and full `tests/unit` passed.
