# Clawith → CoPaw 功能迁移方案（待审批）

> 状态：草案（仅文档，不实施）
> 
> 执行门禁：**必须在你明确审批通过后**才开始任何功能实现。

## 1. 目标与范围

### 1.1 目标
将开源项目 [Clawith](https://github.com/dataelement/Clawith) 中对 CoPaw 有明显增益的能力，按“最小可落地增量”迁移到 CoPaw，优先增强：
- 任务自治与触发能力
- 多 Agent 协作能力
- 可审计与可控能力

### 1.2 本轮范围（仅文档）
- 完成 Clawith 能力盘点与 CoPaw 差异分析
- 给出候选迁移项、优先级、影响面、风险与验收标准
- 不进行代码实现、不修改运行逻辑

### 1.3 非目标
- 不复制 Clawith 的完整多租户 Web 平台形态
- 不在本轮落地完整 RBAC/组织管理后台
- 不引入破坏 CoPaw 现有配置兼容性的改动

## 2. 调研基线（源码级）

### 2.1 Clawith 关键能力（已确认）
- 多类型触发器与统一触发守护进程
  - `backend/app/models/trigger.py`
  - `backend/app/services/trigger_daemon.py`
  - `backend/app/api/triggers.py`
- Agent 协作与委派
  - `backend/app/services/collaboration.py`
  - `backend/app/services/task_executor.py`
- 社交知识流（Plaza）
  - `backend/app/models/plaza.py`
  - `backend/app/api/plaza.py`
- 资源发现与 MCP 运行时导入
  - `backend/app/services/resource_discovery.py`
  - `backend/app/services/agent_tools.py`
- 配额与审计
  - `backend/app/services/quota_guard.py`
  - `backend/app/services/audit_logger.py`

### 2.2 CoPaw 当前能力（已确认）
- 已有多 Agent 工作区与热重载
  - `src/copaw/app/multi_agent_manager.py`
- 已有 cron（当前主要是 `cron` 表达式）与 heartbeat
  - `src/copaw/app/crons/models.py`
  - `src/copaw/app/crons/manager.py`
  - `src/copaw/app/crons/executor.py`
- 已有工具审批与 tool guard
  - `src/copaw/app/approvals/service.py`
  - `src/copaw/security/tool_guard/engine.py`
- 已有 MCP 客户端管理与技能 Hub
  - `src/copaw/app/mcp/manager.py`
  - `src/copaw/app/routers/mcp.py`
  - `src/copaw/agents/skills_hub.py`

## 3. 建议迁移项（按优先级）

## P0（建议首批）

### A. 统一触发器能力（在现有 cron 之上扩展）
**迁移目标**
- 在 CoPaw 现有 `cron` 之外，增加 `once / interval / on_message / webhook / poll` 触发类型（可分期逐步开放）。

**价值**
- 从“定时任务”升级为“事件驱动 + 定时驱动”混合自治。

**CoPaw 影响面（规划）**
- `src/copaw/app/crons/models.py`：调度模型扩展为 TriggerSpec
- `src/copaw/app/crons/manager.py`：统一调度入口
- `src/copaw/app/crons/api.py` 与 `src/copaw/cli/cron_cmd.py`：API/CLI 扩展
- 增加触发状态持久化字段（沿用现有 repo 模式，保持兼容）

**风险与约束**
- `poll`/`webhook` 存在 SSRF/滥用风险，需默认限流与私网拦截。
- 需要避免与现有 cron job ID 语义冲突。

---

### B. Agent 间协作（消息 + 委托最小闭环）
**迁移目标**
- 增加 Agent → Agent 直接消息与任务委托接口（先做最小可用，不做完整组织关系图）。

**价值**
- 让 CoPaw 的多 Agent 从“并列存在”变为“可编排协作”。

**CoPaw 影响面（规划）**
- 新增协作服务层（建议 `src/copaw/app/` 下新模块）
- 扩展 runner/agent 调用路径以支持跨 agent 会话
- 适配 console 展示最小协作记录（先文本日志级）

**风险与约束**
- 需要防止循环委派、消息风暴。
- 需明确跨 agent 权限边界（至少同 workspace / 同 owner）。

---

### C. 审计增强（操作链路可追踪）
**迁移目标**
- 将“触发执行、跨 Agent 协作、关键工具执行”统一写入可查询审计记录。

**价值**
- 提升可回溯性，便于排障与安全治理。

**CoPaw 影响面（规划）**
- 复用现有日志与 approval 机制，新增结构化审计仓储（轻量文件/JSON 起步）
- Console 增加审计视图入口（后续可迭代）

**风险与约束**
- 要控制日志体积与隐私字段脱敏。

## P1（审批后可选）

### D. MCP 资源发现/导入增强
**迁移目标**
- 在当前 MCP 管理基础上，增加“发现-导入-配置”向导，支持 registry 搜索与一键接入。

**价值**
- 降低工具生态接入门槛。

**风险**
- 第三方源可用性、认证流程复杂度。

---

### E. Plaza 式协作动态流（轻量版）
**迁移目标**
- 提供 Agent 进展广播流（先做系统事件 feed，不做完整社交产品）。

**价值**
- 提升团队感知和透明度。

**风险**
- 信息噪音与通知策略需要治理。

## 4. 分阶段落地建议（审批后执行）

### Phase 1（建议先做）
- A 统一触发器（先 `once + interval + on_message`，暂缓 `poll + webhook`）
- B Agent 协作最小闭环
- C 审计增强基础版

### Phase 2（按收益推进）
- A 补齐 `poll + webhook`（带安全护栏）
- D MCP 资源发现/导入增强
- E 轻量动态流

## 5. 兼容性与安全门槛

- 配置兼容：旧 cron 配置必须可无缝读取；新增字段需可选。
- 安全默认：
  - `poll/webhook` 默认关闭，需显式开启
  - 私网地址拦截、域名/IP 校验、频率限制
  - 审批机制继续对危险操作兜底
- 失败策略：触发器执行失败不阻塞主服务；采用可观测重试/降级。

## 6. 验收标准（文档级定义）

对每个迁移项统一以以下标准验收：
- 功能：达到“可用最小闭环”（能创建、能触发、能观察结果）
- 安全：通过现有 tool guard + 新增触发器防护
- 兼容：老配置不报错、行为不回归
- 可观测：有结构化日志/审计记录可追踪

## 7. 需要你审批的决策点

请你直接回复下面 4 项选择：

1. **首批范围**：是否按 `A+B+C` 作为第一批实现？
2. **触发器开放策略**：`Phase 1` 是否先不开放 `poll/webhook`？
3. **协作边界**：是否限定“同 owner/同 workspace 才允许跨 Agent 协作”？
4. **审计存储**：第一版是否采用“轻量文件/JSON 存储”，后续再升级？

## 8. 分支策略（已执行）

已创建实现分支：`codex/clawith-feature-migration-plan`

说明：当前分支仅用于提交迁移方案文档。**在你审批前不会进行任何功能实现。**
