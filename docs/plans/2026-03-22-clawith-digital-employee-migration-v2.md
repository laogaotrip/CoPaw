# Clawith → CoPaw 数字员工化迁移方案 V2（待审批）

> 状态：草案（仅文档，不实施）
>
> 执行门禁：**你明确审批通过前，不进行任何功能实现**。

## 1. 目标重定义（按你的要求）

本次迁移目标不再是“补若干功能点”，而是把 CoPaw 的 Agent 升级为“完整数字员工单元”。

每个 Agent 需要具备 5 个核心能力域：
1. **自我进化能力**（可持续提升技能/工具能力）
2. **渠道集成能力**（可独立对接并服务多渠道）
3. **主备模型能力**（每个 Agent 独立主备模型策略）
4. **知识库能力**（可持续沉淀、检索、引用组织知识）
5. **自治执行能力**（任务触发、协作、审批、审计）

## 2. 现状差异（源码对照）

### 2.1 CoPaw 已具备（可复用）

- 多 Agent 工作区与热重载
  - `src/copaw/app/multi_agent_manager.py`
- 每 Agent 独立渠道配置（已经是 per-agent）
  - `src/copaw/app/routers/config.py`
  - `src/copaw/config/config.py` (`AgentProfileConfig.channels`)
- 每 Agent 独立 active model（但非主备）
  - `src/copaw/config/config.py` (`AgentProfileConfig.active_model`)
  - `src/copaw/app/routers/providers.py` (`/models/active`)
- 记忆检索与向量检索基础（memory_search + embedding）
  - `src/copaw/agents/memory/memory_manager.py`
  - `src/copaw/agents/tools/memory_search.py`
- 工具审批与安全护栏
  - `src/copaw/app/approvals/service.py`
  - `src/copaw/security/tool_guard/engine.py`
- cron + heartbeat 调度基础
  - `src/copaw/app/crons/models.py`
  - `src/copaw/app/crons/manager.py`

### 2.2 Clawith 可借鉴的增量能力

- 统一 Trigger 引擎（cron/once/interval/poll/on_message/webhook）
  - `backend/app/models/trigger.py`
  - `backend/app/services/trigger_daemon.py`
- 自治边界（L1/L2/L3）与审批闭环
  - `backend/app/services/autonomy_service.py`
- Agent 协作（委托/咨询/通知）
  - `backend/app/services/collaboration.py`
- 运行时资源发现与 MCP 导入
  - `backend/app/services/resource_discovery.py`
- Skill Creator 体系（能力自扩展）
  - `backend/app/services/skill_creator_content.py`
- 触发与执行审计
  - `backend/app/services/audit_logger.py`

### 2.3 关键差距（针对“数字员工”目标）

1. **自我进化**：CoPaw 有技能导入与技能管理，但缺“能力改进闭环”（评估→优化→再部署）。
2. **渠道数字员工化**：CoPaw有 per-agent channel config，但缺“渠道身份策略 + 渠道质量SLO + 渠道告警”。
3. **主备模型**：CoPaw 当前是 `active_model + global fallback`，不等于“每 Agent 显式主备模型策略”。
4. **知识库**：CoPaw 有 memory_search，但缺“组织级/Agent级知识域、知识摄取流水线、版本化治理”。
5. **自治执行**：CoPaw 有 cron/heartbeat，但缺 Clawith 风格多触发统一调度与跨 Agent 协作编排。

## 3. 数字员工能力模型（目标态）

每个 Agent 的目标配置建议升级为：
- `Identity`: 角色、职责边界、协作白名单
- `Channels`: 独立渠道接入、渠道 SLA、渠道优先级
- `Models`: `primary_model`, `fallback_model`, `routing_policy`
- `Knowledge`: `personal_memory`, `team_kb`, `external_kb_connectors`
- `Autonomy`: `trigger_policies`, `approval_level(L1/L2/L3)`, `audit_level`
- `Evolution`: `skill_feedback_loop`, `tool_discovery_policy`, `self-improvement cadence`

## 4. 迁移项清单（按优先级）

## P0（第一批，建议先做）

### A. 每 Agent 主备模型（显式化）
**目标**
- 从 `active_model` 升级为每 Agent 独立 `primary_model + fallback_model + failover_policy`。

**实现边界（规划，不执行）**
- 扩展 `AgentProfileConfig` 模型槽位结构。
- 保持对现有 `active_model` 的向后兼容映射。
- 在模型调用层实现主备切换触发条件（超时/错误码/熔断）。

**验收**
- 单 Agent 可独立配置主备模型并可观测切换行为。

---

### B. 统一 Trigger 引擎（数字员工自治基础）
**目标**
- 在现有 cron 基础上，新增 `once/interval/on_message`（第一阶段），为自治执行打底。

**实现边界（规划，不执行）**
- `poll/webhook` 暂列二期，优先把“会话事件触发”和“单次触发”落地。
- 调度状态持久化与审计联动。

**验收**
- Agent 能自建触发条件，触发后自动执行，并在审计中可追踪。

---

### C. Agent 协作最小闭环
**目标**
- 支持 Agent→Agent 的“通知/咨询/委托”三种协作语义。

**实现边界（规划，不执行）**
- 第一版限制为同 owner（或同 workspace）协作。
- 防循环委托、防消息风暴。

**验收**
- 可稳定完成跨 Agent 委托并回传结果。

---

### D. 数字员工知识库 V1
**目标**
- 从 memory_search 升级为“个人记忆 + 团队知识域”的双层检索。

**实现边界（规划，不执行）**
- 个人层：沿用当前 `memory/*.md + embedding`。
- 团队层：先引入 workspace 级 `knowledge/` 目录与索引规则。
- 输出中明确引用来源（文件/片段）。

**验收**
- Agent 回答可引用个人与团队知识，且来源可追溯。

---

### E. 自治边界与审批级别（L1/L2/L3）
**目标**
- 把“可做什么、做之前是否要审批”从隐式规则升级为 Agent 显式自治策略。

**实现边界（规划，不执行）**
- L1：自动执行并记录
- L2：自动执行+通知
- L3：审批后执行

**验收**
- 高风险动作可按 Agent 策略分级控制。

## P1（第二批，可并行评估）

### F. 自我进化能力（Skill Evolution Loop）
**目标**
- 建立 Agent 技能进化闭环：发现能力缺口 → 生成/导入技能 → 验证 → 启用。

**实现边界（规划，不执行）**
- 先做“人工审批驱动”的半自动闭环（不直接放开全自动自改）。
- 引入评估指标：触发准确率、任务成功率、人工回退率。

**验收**
- 一个 Agent 能在审批下完成技能增强并产生可量化收益。

---

### G. 渠道数字员工化增强
**目标**
- 在 per-agent channel config 基础上，增加“渠道身份与服务质量”治理。

**实现边界（规划，不执行）**
- 渠道健康检查、失败重试策略、渠道级告警。
- 渠道角色标识（某 Agent 在某渠道的身份、职责标签）。

**验收**
- 单 Agent 跨渠道可稳定工作且可观测。

---

### H. MCP 资源发现/导入增强
**目标**
- 增加发现-导入-授权-启用流程，降低数字员工扩展工具门槛。

**验收**
- Agent 可在可控审批下完成工具生态扩展。

## 5. 分阶段实施建议（审批后）

### Phase 1（数字员工基础能力）
- A 主备模型
- B 统一 Trigger（先不含 poll/webhook）
- C Agent 协作闭环
- D 知识库 V1
- E 自治边界 L1/L2/L3

### Phase 2（数字员工进化能力）
- F 自我进化闭环
- G 渠道数字员工化增强
- H MCP 发现导入增强
- B 补齐 poll/webhook（含严格安全护栏）

## 6. 安全与治理基线

- `poll/webhook` 默认关闭，白名单开启。
- 私网/本地地址拦截、请求频控、超时熔断。
- 主备模型切换需审计（记录触发原因与回切）。
- 自我进化流程默认“审批后启用”，禁止无审批自动覆盖关键技能。
- 知识库引文强制带来源路径，避免“无依据回答”。

## 7. 对 CoPaw 架构的最小侵入原则

- 优先复用：`multi_agent_manager`、`approvals`、`tool_guard`、`memory_manager`。
- 配置兼容：旧 `active_model` 与旧 cron 规则都可继续运行。
- 渐进演进：先文件/JSON 级存储，后续再评估数据库化。

## 8. 需要你审批的决策点（V2）

请直接回复 1-6 的选择：

1. 首批是否按 `A+B+C+D+E` 执行？
2. 主备模型策略是否采用“每 Agent 显式主备 + 自动故障切换”？
3. Trigger 一期是否先不上 `poll/webhook`？
4. 协作边界是否先限制“同 owner/同 workspace”？
5. 自我进化是否先采用“半自动（审批后启用）”？
6. 知识库一期是否采用“个人记忆 + 团队 knowledge/ 目录双层检索”？

## 9. 分支与执行约束

- 当前分支：`codex/clawith-feature-migration-plan`
- 当前提交内容：仅迁移文档，不包含实现代码
- 承诺：你审批前，不进入实现阶段
