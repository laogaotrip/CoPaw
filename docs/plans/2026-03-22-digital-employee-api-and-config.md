# Digital Employee Migration - API & Config Notes (Batch 1-2)

This document records API/config additions for digital employee migration
batches, focused on backward compatibility.

## 1) Model Slots (A)

### New agent config fields
- `primary_model`
- `fallback_model`
- `auto_model_failover`

Legacy `active_model` is still supported and remains backward-compatible.

### New APIs
- `GET /models/agent-slots`
- `PUT /models/agent-slots`

### Compatibility
- `PUT /models/active` now syncs `primary_model` to keep old clients working.

## 2) Trigger Engine Phase-1 (B)

### Extended schedule types
- `cron` (existing)
- `once` (new)
- `interval` (new)
- `on_message` (new)

### New schedule fields (type-dependent)
- `at` (`once`)
- `every_seconds` (`interval`)
- `channel`, `user_id`, `session_id`, `contains`, `pattern` (`on_message`)

### Runtime behavior
- Inbound user messages can trigger `on_message` jobs.
- Requests dispatched by cron carry `source=cron` to prevent trigger loops.

## 3) Agent Collaboration v1 (C)

### Routing extension
- For cron `task_type=agent`, `dispatch.meta.target_agent_id` can route request
  execution to another agent runner in the same multi-agent manager.

### Compatibility
- If `target_agent_id` is not provided, behavior is unchanged.

## 4) Dual-layer Knowledge v1 (D)

### New agent knowledge config
- `knowledge.enable_personal`
- `knowledge.enable_team`
- `knowledge.team_knowledge_dir`
- `knowledge.team_file_globs`
- `knowledge.team_max_scan_files`

### Tool behavior extension
- `memory_search` supports `scope=auto|personal|team`.
- `personal`: existing memory search path.
- `team`: lightweight scan over configured shared files.

## 5) Autonomy Boundaries (E)

### New agent autonomy config
- `autonomy.level = L1|L2|L3`

### Tool-guard behavior
- `L1`: auto execute guarded tools (log only).
- `L2`: auto execute guarded tools + runtime notice.
- `L3`: approval required (existing behavior).

## 6) Self-evolution Full-auto (F)

### New agent evolution config
- `evolution.enabled`
- `evolution.mode = manual|semi_auto|full_auto`
- `evolution.every`
- `evolution.query_file`
- `evolution.timeout_seconds`
- `evolution.session_id`
- `evolution.user_id`

### New APIs
- `GET /config/evolution`
- `PUT /config/evolution`
- `GET /config/autonomy`
- `PUT /config/autonomy`

### Scheduler behavior
- Cron manager maintains an internal `_evolution` interval job when
  `enabled=true && mode=full_auto`.

## 7) Channel Hardening v1 (G)

### New channel config fields
- `send_retries` (default `0`)
- `send_retry_backoff_ms` (default `200`)

### Runtime behavior
- `send_event` and `send_text` use bounded retry wrapper.
- Default remains no retry to avoid behavior change.

### New API
- `GET /config/channels/health`
  - Returns enabled channel runtime status (`up` / `missing`).

## 8) MCP Discovery/Import v1 (H)

### New APIs
- `GET /mcp/discovery/presets`
- `POST /mcp/discovery/import`

### Preset scope
- Current built-ins: `filesystem`, `fetch`, `github`
- Import performs validation and creates standard MCP client config.

## 9) Test Summary

In Python 3.12 venv (`.venv312`) with project dependencies installed:

- Targeted migration tests: `30 passed`
- Full unit suite: `290 passed`

Commands used:
- `PYTHONPATH=src .venv312/bin/pytest -q tests/unit`

## 10) Trigger Engine Phase-2 (B)

### Extended schedule types
- `webhook` (new)
- `poll` (new)

### New schedule fields
- `webhook_event`, `webhook_source` (`webhook`)
- `poll_url`, `poll_method`, `poll_timeout_seconds`, `poll_expected_status`,
  `poll_headers`, `poll_body` (`poll`)
- Reuse response/event text filters: `contains`, `pattern`

### New API
- `POST /cron/webhook/trigger`
  - Body: `event`, `source`, `channel`, `user_id`, `session_id`, `text`, `payload`
  - Response: `{ "fired": <int> }`

### Runtime behavior
- `webhook` jobs are event-driven and do not create APScheduler jobs.
- `poll` jobs use interval scheduling (`every_seconds`) and only execute task
  when response filters match; unmatched probes set job state to `skipped`.

### Batch-2 test summary
- `tests/unit/crons`: `16 passed`
- `tests/unit`: `297 passed`

## 11) Agent Collaboration v2 (C)

### New APIs
- `POST /collaboration/notify`
- `POST /collaboration/consult`
- `POST /collaboration/delegate`

These endpoints are available in both global and agent-scoped routing.

### Runtime behavior
- `notify`: sends direct text notification through target agent channel manager.
- `consult`: asks target agent and returns aggregated response text.
- `delegate`: sends delegated task to target agent and returns aggregated response text.

### Guardrails
- Reject self-target collaboration (`target_agent_id == source_agent_id`).
- Delegation hop limit (`<= 3`) to avoid delegation loops.
- Validate target runner/channel-manager availability.

### Lightweight audit
- Source workspace writes collaboration records to:
  - `collaboration_events.jsonl`

### Batch-3 test summary
- `tests/unit/collaboration/test_service.py`: `4 passed`
- `tests/unit`: `301 passed`

## 12) Trigger Security Guardrails (B hardening)

### New per-agent config (`agent.json`)
- `triggers.enable_webhook` (default `true`)
- `triggers.enable_poll` (default `true`)
- `triggers.block_private_network` (default `true`)
- `triggers.allowed_poll_domains` (default `[]`)

### New APIs
- `GET /config/triggers`
- `PUT /config/triggers`

### Runtime hardening behavior
- `poll_url` validation:
  - only `http/https` scheme allowed
  - host required
  - optional domain allowlist check (`allowed_poll_domains`)
  - private/local network blocking when `block_private_network=true`
- Trigger type policy enforcement:
  - `webhook` jobs rejected when `enable_webhook=false`
  - `poll` jobs rejected when `enable_poll=false`
  - inbound webhook dispatch is ignored when `enable_webhook=false`

### Batch-4 test summary
- `tests/unit/crons/test_trigger_security.py`: `4 passed`
- `tests/unit`: `306 passed`

## 13) Collaboration Hardening (C)

### New API
- `GET /collaboration/events`
  - Query params:
    - `limit` (1-500, default 50)
    - `mode` (optional: `notify|consult|delegate`)
    - `target_agent_id` (optional)

### Runtime behavior
- Collaboration boundary enforcement:
  - Source and target agent workspaces must share the same workspaces root.
  - Cross-root collaboration requests are rejected.
- Collaboration event query:
  - Reads from `collaboration_events.jsonl`
  - Returns latest-first order
  - Supports in-memory filtering by mode and target agent

### Batch-5 test summary
- `tests/unit/collaboration/test_service.py`: `6 passed`
- `tests/unit/collaboration/test_api.py`: `1 passed`
- `tests/unit`: `309 passed`

## 14) Cron Audit Enhancement (C)

### New API
- `GET /cron/audit/events`
  - Query params:
    - `limit` (1-1000, default 100)
    - `job_id` (optional)
    - `status` (optional)
    - `trigger_type` (optional)

### Runtime behavior
- Cron manager writes structured audit lines to:
  - `cron_audit_events.jsonl` (workspace-level alongside jobs store)
- Audit records include:
  - trigger fired (`on_message`, `webhook`)
  - execution result (`success`, `error`, `cancelled`, `skipped`)
- Query returns latest-first order with in-memory filters.

### Batch-6 test summary
- `tests/unit/crons/test_audit_events.py`: `2 passed`
- `tests/unit/crons`: `22 passed`
- `tests/unit`: `311 passed`

## 15) Collaboration Observability Stats (C)

### New API
- `GET /collaboration/stats`
  - Query params:
    - `since_hours` (0-720, default 24)

### Runtime behavior
- Service aggregates collaboration events from `collaboration_events.jsonl`.
- Returns:
  - `total`
  - `by_mode`
  - `by_target_agent`
  - `since_hours`
- Time-window filter uses event `time` field; `since_hours=0` means all records.

### Batch-7 test summary
- `tests/unit/collaboration/test_service.py`: `8 passed`
- `tests/unit/collaboration/test_api.py`: `2 passed`
- `tests/unit`: `313 passed`

## 16) Cron Audit Stats (C)

### New API
- `GET /cron/audit/stats`
  - Query params:
    - `since_hours` (0-720, default 24)

### Runtime behavior
- Cron manager aggregates audit events from `cron_audit_events.jsonl`.
- Returns:
  - `total`
  - `by_status`
  - `by_trigger_type`
  - `since_hours`
- Time-window filter uses audit `time` field; `since_hours=0` means all records.

### Batch-8 test summary
- `tests/unit/crons/test_audit_events.py`: `4 passed`
- `tests/unit/crons`: `24 passed`
- `tests/unit`: `315 passed`

## 17) API Contract Regression Suite

### Added coverage
- `GET /config/triggers`
- `PUT /config/triggers`
- `GET /cron/audit/events`
- `GET /cron/audit/stats`

### Test file
- `tests/unit/app/test_api_contract_new_features.py`

### Batch-9 test summary
- `tests/unit/app/test_api_contract_new_features.py`: `3 passed`
- `tests/unit`: `318 passed`

## 18) API Error Contract Regression Suite

### Added coverage
- collaboration error mapping:
  - `notify`: `CollaborationError -> 400`
  - `consult`: unexpected error `-> 500`
  - `delegate`: `CollaborationError -> 400`
- cron error mapping:
  - `POST /cron/jobs/{job_id}/run`: missing job (`KeyError`) `-> 404`
  - `POST /cron/jobs/{job_id}/run`: unexpected error `-> 500`

### Test file
- `tests/unit/app/test_api_error_contracts.py`

### Batch-10 test summary
- `tests/unit/app/test_api_error_contracts.py`: `5 passed`
- `tests/unit`: `323 passed`
