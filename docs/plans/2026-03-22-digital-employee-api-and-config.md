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
