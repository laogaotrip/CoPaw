# Digital Employee Frontend Completion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete frontend integration for approved digital-employee features so users can validate all new capabilities in Console UI.

**Architecture:** Reuse existing Console route/layout and API request patterns, add three production pages (Digital Employee Settings, Collaboration, Cron Audit), wire to existing backend endpoints without breaking existing pages. Keep UI components in current style (`@agentscope-ai/design` + existing page patterns) and add full i18n keys for zh/en/ja/ru.

**Tech Stack:** React 18 + TypeScript + Vite + Ant Design/@agentscope-ai/design + react-i18next.

### Task 1: Add API contracts for new backend endpoints

**Files:**
- Create: `console/src/api/types/digitalEmployee.ts`
- Create: `console/src/api/modules/digitalEmployee.ts`
- Modify: `console/src/api/types/index.ts`
- Modify: `console/src/api/index.ts`

**Steps:**
1. Define typed interfaces for model slots, trigger policy, evolution config, collaboration requests/events/stats, and cron audit events/stats.
2. Add typed API module methods:
   - `/models/agent-slots` GET/PUT
   - `/config/triggers` GET/PUT
   - `/config/evolution` GET/PUT
   - `/collaboration/*` notify/consult/delegate/events/stats
   - `/cron/audit/events` and `/cron/audit/stats`
3. Export new types and mount module into shared `api` object.
4. Build once to validate no TypeScript contract issues.

### Task 2: Implement Digital Employee Settings page

**Files:**
- Create: `console/src/pages/Settings/DigitalEmployee/index.tsx`
- Create: `console/src/pages/Settings/DigitalEmployee/index.module.less`
- Modify: `console/src/layouts/MainLayout/index.tsx`
- Modify: `console/src/layouts/constants.ts`
- Modify: `console/src/layouts/Sidebar.tsx`

**Steps:**
1. Build page sections with existing card/form patterns:
   - model slots (primary/fallback/auto failover)
   - trigger security policy
   - self-evolution configuration
2. Load providers list to power provider/model selectors.
3. Handle save/reset flows with optimistic UX and robust error handling.
4. Add route and sidebar menu entry.
5. Verify build and route navigation.

### Task 3: Implement Collaboration page

**Files:**
- Create: `console/src/pages/Control/Collaboration/index.tsx`
- Create: `console/src/pages/Control/Collaboration/index.module.less`
- Modify: `console/src/layouts/MainLayout/index.tsx`
- Modify: `console/src/layouts/constants.ts`
- Modify: `console/src/layouts/Sidebar.tsx`

**Steps:**
1. Add action form for `notify` / `consult` / `delegate`.
2. Add event list table with filters (`mode`, `target_agent_id`, `limit`).
3. Add stats panel (`since_hours`, totals, by-mode, by-target).
4. Wire success/error messages and preserve agent-scoped behavior.
5. Verify build and API integration through dev server.

### Task 4: Implement Cron Audit page

**Files:**
- Create: `console/src/pages/Control/CronAudit/index.tsx`
- Create: `console/src/pages/Control/CronAudit/index.module.less`
- Modify: `console/src/layouts/MainLayout/index.tsx`
- Modify: `console/src/layouts/constants.ts`
- Modify: `console/src/layouts/Sidebar.tsx`

**Steps:**
1. Add audit filters (`job_id`, `status`, `trigger_type`, `limit`) and refresh actions.
2. Add events table and stats panel (`since_hours`).
3. Handle empty states and malformed payload defensively.
4. Verify build and visual consistency with existing Control pages.

### Task 5: Add i18n keys and run final verification

**Files:**
- Modify: `console/src/locales/zh.json`
- Modify: `console/src/locales/en.json`
- Modify: `console/src/locales/ja.json`
- Modify: `console/src/locales/ru.json`

**Steps:**
1. Add nav labels and page copy for all new UI strings.
2. Ensure no hardcoded user-visible strings remain in new pages.
3. Run `npm run build` in `console/` for type/build regression.
4. Smoke-check routes: `/digital-employee`, `/collaboration`, `/cron-audit`.
