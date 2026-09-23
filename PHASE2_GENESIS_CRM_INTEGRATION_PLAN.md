# 阶段 2：Genesis_CRM 集成开发总纲

> 状态：**核心完成，发布收口中**（2.9 五项 P0 已完成；历史净化/凭证轮换/worker 并发保护/CI 门禁进行中）
> 初始规划日期：2026-09-22；状态更新：2026-09-23
> AutoForceAI 发布基线：`codex/phase2-release-ready`（净化后；原收口分支 `codex/phase2-closeout` 为本地恢复点，禁止推送）
> Genesis_CRM Integration API 基线：`codex/genesis-integration-release`（自 `e2e3486`）
> 兼容性记录：[docs/integration/COMPATIBILITY.md](./docs/integration/COMPATIBILITY.md)
> 运维手册：[docs/PHASE2_OPS_RUNBOOK.md](./docs/PHASE2_OPS_RUNBOOK.md)
> 下一步执行文档：[PHASE2_CLOSEOUT_AND_PHASE4_EXECUTION_PLAN.md](./PHASE2_CLOSEOUT_AND_PHASE4_EXECUTION_PLAN.md)

> 说明：本文第 2 节记录的是实施前基线，用于保留决策背景；当前完成状态和后续任务以“阶段 2.9 收口与阶段 4 启动执行计划”为准。

## 1. 结论

阶段 2 采用“两个系统、单一职责、API 集成”的方式，不合库、不复制 CRM 页面、不让 AutoForceAI 直接读写 MongoDB。

- AutoForceAI 是获客与询盘入口：知识库、AI 客服、营销获客、本地线索、来源归因。
- Genesis_CRM 是销售事实主库：客户档案、负责人、销售阶段、跟进、开发信、报价、成交/流失。
- AutoForceAI 只把合格线索可靠地交给 Genesis_CRM；交接后，销售状态以 Genesis_CRM 为准。
- `/crm` 做“集成门户与摘要”，不再重复建设客户、商机、合同 CRUD；明细工作跳转到 Genesis_CRM。
- 阶段 5 继续保留到最后。阶段 2 只预留监控、告警和 Agent Tool 所需的数据接口，不提前实施阶段 5。

## 2. 已确认的现状

### AutoForceAI

- 后端为 FastAPI + SQLAlchemy，当前开发环境可回退 SQLite，生产目标为 PostgreSQL。
- `Lead` 已承接 AI 客服询盘，按 `organization_id + email` 或 `session_uuid` 去重。
- `Lead` 注释为 Outbox，但尚无投递状态、幂等键、重试时间、CRM 外部 ID、死信记录。
- `/crm` 当前是占位页；`/crm/customers`、`/crm/opportunities`、`/crm/contracts` 仍标记“开发中”。
- 本地线索状态只有 `new / contacted / converted / dropped`，不能等同于 Genesis_CRM 的八段销售状态。

### Genesis_CRM

- 后端为 Express + MongoDB，前端为 Vite + React；本地服务为 `http://localhost:5173`，API 为 `http://localhost:5000/api`。
- 已有客户、跟进、开发信、模板、报价、Timeline、统计、项目工作空间和 Agent 诊断。
- 当前运行版已按 `projectId` 隔离数据，并通过 `X-Project-Id` 选择项目。
- 当前认证只有用户 JWT；没有适合后台集成的服务凭证、scope、轮换和撤销机制。
- `POST /api/customers` 支持建客户，但没有公开的外部来源 ID/幂等契约；仅依靠“项目内邮箱唯一”不足以保证可靠同步。
- 当前运行分支领先默认 `main`。开始联调前必须确定以哪个 Genesis_CRM commit/branch 作为契约基线。

## 3. 集成架构

```text
网站/AI 客服/营销渠道
          │
          ▼
AutoForceAI Lead（本地事实）
          │ 同一数据库事务
          ├──────────────► CRM Sync Job（Outbox）
          │                         │
          │                 后台投递器 + 租约抢占
          │                         │ HTTPS + Service Token
          ▼                         ▼
本地线索池               Genesis Integration API v1
                                    │
                                    ▼
                         Customer + External Reference
                                    │
                           Outcome Cursor / Polling
                                    │
                                    ▼
                         AutoForceAI 归因与 CRM 摘要
```

禁止的实现方式：

- AutoForceAI 直接连接或修改 Genesis_CRM 的 MongoDB。
- 后台任务保存并复用 `admin/password` 或长期用户 JWT。
- 把 Genesis_CRM 前端 iframe 到 AutoForceAI 作为正式集成。
- 用邮箱作为唯一幂等键；邮箱只可作为“可能重复”的辅助匹配条件。
- 两端互相覆盖销售状态，造成循环同步。

## 4. 数据所有权与同步方向

| 数据 | 权威系统 | 同步方向 | 规则 |
|---|---|---|---|
| 询盘原文、会话、来源、营销活动 | AutoForceAI | 不复制全文 | CRM 只接收摘要与来源引用 |
| 客户基础档案 | Genesis_CRM | AutoForceAI → Genesis | 首次交接创建/关联；之后默认不自动覆盖人工编辑 |
| 销售阶段、负责人、跟进 | Genesis_CRM | Genesis → AutoForceAI 摘要 | AutoForceAI 只展示，不反向修改 |
| 报价 | Genesis_CRM | Genesis → AutoForceAI 摘要/Agent 查询 | 阶段 4/5 复用，不在 AutoForceAI 重建 |
| 成交/流失 | Genesis_CRM | Genesis → AutoForceAI | 用于获客归因和漏斗闭环 |
| 同步任务、重试、死信 | AutoForceAI | 本地 | 不进入 Genesis 业务表 |
| 外部实体映射 | 两端均留引用 | 双方只读引用 | 由稳定 external ID 关联，不能靠姓名/邮箱猜测 |

## 5. 组织与项目映射

AutoForceAI 的一个 `organization_id` 必须显式绑定一个 Genesis_CRM `projectId`。不要依赖 Genesis 的默认项目回退，否则多项目场景会把线索写错工作区。

建议配置结构：

| 字段 | 说明 |
|---|---|
| `organization_id` | AutoForceAI 企业 ID，唯一 |
| `provider` | 固定 `genesis_crm` |
| `base_url` | 例如 `http://localhost:5000/api` |
| `project_id` | Genesis ObjectId，必填 |
| `project_name` | 最近一次连接测试返回的显示名 |
| `credential_ref` | 服务端凭证引用，不返回前端明文 |
| `enabled` | 是否允许新任务投递 |
| `contract_version` | 固定为 `1.0` |
| `last_health_status/checked_at` | 最近连接测试结果 |

配置页仅允许企业管理员操作。页面保存后必须调用 Integration API 的 health/me 接口校验凭证与项目绑定，不能只校验 URL 格式。

## 6. Genesis Integration API v1

现有用户 API 保持不变，新增专用前缀：`/api/integrations/v1`。

### 6.1 服务凭证

新增集成凭证实体，原始 token 仅创建时显示一次，数据库只存哈希。

- 凭证绑定一个或多个 `projectId`，首版建议“一项目一 token”。
- scope 最少包含：`customers:upsert`、`outcomes:read`、`stats:read`、`quotations:read`。
- 支持状态、过期时间、最近使用时间、轮换和撤销。
- 每次请求记录 `requestId`、credential、project、scope、结果和耗时，但不记录 token 与完整询盘内容。

### 6.2 必需端点

| 方法与路径 | 用途 |
|---|---|
| `GET /integrations/v1/health` | 校验版本、凭证、项目和 scope |
| `POST /integrations/v1/customers/upsert` | 按外部 ID 幂等创建或关联客户 |
| `GET /integrations/v1/outcomes?cursor=...` | 增量读取成交/流失事件 |
| `GET /integrations/v1/stats/overview` | `/crm` 门户摘要 |
| `GET /integrations/v1/customers/{externalRef}` | 5.2 Agent Tool 查询客户状态预留 |
| `GET /integrations/v1/customers/{externalRef}/quotations` | 5.2 报价状态查询预留 |

### 6.3 Upsert 请求语义

- Header 必须带 `Authorization: Bearer <service-token>` 和 `Idempotency-Key`。
- Body 必须带 `schemaVersion: "1.0"`、`sourceSystem: "autoforce"`、`externalId: "lead:<id>"`。
- Genesis 必须为 `(projectId, sourceSystem, externalId)` 建唯一约束。
- 同一个幂等键重复请求必须返回相同结果，不重复创建客户。
- 若外部 ID 未关联，但同项目邮箱已存在：返回 `linked`，建立外部引用；不得报错后让 AutoForceAI 无限重试。
- 若外部 ID 已关联：默认只补齐空字段，不覆盖销售人工维护字段。显式 `replace` 不纳入首版。
- 响应返回 `action: created | linked | unchanged`、`customerId`、`projectId`、`remoteUpdatedAt`。

## 7. 字段映射

| AutoForceAI Lead | Genesis_CRM Customer | 说明 |
|---|---|---|
| `id` | `externalId = lead:<id>` | 稳定主键，不能复用邮箱 |
| `name` | `name` | Genesis 必填；缺失时用公司名，再缺失用“未命名询盘 + ID” |
| `company` | `company` | 直接映射 |
| `email` | `email` | 规范化小写；仅作重复辅助判断 |
| `phone` | `phone` | 直接映射 |
| `country` | `country` | 直接映射 |
| `products` | `interestedProducts` | 直接映射 |
| `source` | `leadSource` | 建议格式 `AutoForceAI / <channel>` |
| `intent_json.product_model` | `productModel` | 有值才写入 |
| `intent_json.category` | `productCategory` | 有值才写入 |
| `intent_json.quantity` | `expectedQuantity` | 保留单位 |
| `intent_json.target_price` | `targetPrice` | 保留币种 |
| `intent_json.moq` | `moq` | 有值才写入 |
| AI 需求摘要 | `requirementNotes` | 最长 5000 字，不复制完整会话 |
| 来源标识 | `tags` | `autoforce`、`channel:<slug>` |

初始状态映射：

| AutoForceAI | Genesis_CRM | 备注 |
|---|---|---|
| `new` | `pending` | 待开发 |
| `contacted` | `contacted` | 已联系 |
| `converted` | `interested` | 本地“转化”为合格线索，不等于成交 |
| `dropped` | 不自动推送 | 除非管理员显式重投 |

Genesis 的 `won` 才是成交归因；`quotation.accepted` 可作为辅助信号，不能替代成交定义。

## 8. AutoForceAI 可靠投递

不要继续把同步字段全部塞进 `leads`。新增两张表可以避免影响现有线索接口，并可通过 `create_all` 在 SQLite/PostgreSQL 中平滑新增。

### `crm_sync_jobs`

- `id`, `organization_id`, `lead_id`
- `event_type`（首版 `lead.upsert`）
- `idempotency_key`，唯一
- `payload_version`, `payload_json`, `payload_hash`
- `status`: `pending / leased / retrying / succeeded / dead`
- `attempt_count`, `next_attempt_at`
- `lease_owner`, `lease_expires_at`
- `last_error_code`, `last_error_summary`, `last_http_status`
- `created_at`, `updated_at`, `succeeded_at`, `dead_at`

### `crm_entity_links`

- `organization_id`, `lead_id`
- `provider`, `project_id`, `remote_customer_id`
- `remote_status`, `remote_updated_at`
- `last_outcome_cursor`, `synced_at`
- 唯一约束：`(provider, organization_id, lead_id)` 与 `(provider, project_id, remote_customer_id)`

线索写入与 job 创建必须在同一数据库事务完成。投递器使用租约抢占，避免多进程重复消费。

重试建议：30 秒、2 分钟、10 分钟、1 小时、6 小时，之后每天一次，最多 8 次。网络错误、408、429、5xx 可重试；请求字段 4xx 直接进死信；401/403 标记“配置失效”并暂停该组织的新投递。重试必须带原 idempotency key。

死信页首版可并入连接配置页：展示脱敏错误、尝试次数、最后时间，并提供“修复配置后重投”。重投只改变 job 状态，不生成新的业务线索。

## 9. 成交归因轮询

不使用“按 updatedAt 排序扫全量客户”的脆弱方案。Genesis 新增游标式 outcome feed，事件来自客户状态 Timeline：

- 返回 `eventId/cursor`、`externalId`、`customerId`、`fromStatus`、`toStatus`、`occurredAt`。
- AutoForceAI 按 organization/project 保存 opaque cursor。
- 每批处理与 cursor 提交放在同一事务；重复事件按 `eventId` 幂等。
- `won` 更新归因结果并把本地线索标记为 `converted`；`lost` 只更新 CRM 摘要，是否改为 `dropped` 由业务规则决定。
- 营销报表按线索最初的 source/campaign 归因，不采用 CRM 最近来源覆盖。

## 10. 2.5 未知邮件建档的归属调整

当前 Genesis_CRM 运行分支已经具备邮件中心、邮件线程分析、Agent 审批记录和“确认后创建客户”的幂等能力。该任务应移到 Genesis_CRM 内完成，避免 AutoForceAI 再造一套邮箱同步、邮件安全与客户创建逻辑。

首版流程改为：未知发件人邮件 → Genesis Agent 提取客户预览 → 查重 → 人工确认 → 建档/关联。不要直接“无人值守自动建档”，避免垃圾邮件、退订邮件和提示词注入污染客户库。AutoForceAI 只消费最终客户/成交结果。

## 11. `/crm` 门户

`/crm` 只做集成状态与跨系统摘要：

- 连接状态、项目名称、契约版本、最近同步时间。
- 待投递、重试中、死信、已同步数量。
- Genesis 客户总数、销售漏斗、成交数、报价状态摘要。
- 最近同步线索及“在 Genesis 中打开”链接。
- 管理员可进入连接设置和死信重投。

移除或重定向 `/crm/customers`、`/crm/opportunities`、`/crm/contracts` 的“开发中”入口。正式明细操作仍在 Genesis_CRM；2.8 完成前使用普通深链并要求独立登录，完成后换成一次性 SSO 跳转。

## 12. 2.8 免登设计（P3）

不要共享两套 JWT_SECRET。采用一次性授权码：

1. AutoForceAI 后端以服务凭证向 Genesis 请求 30 秒有效、单次使用的 login code。
2. code 绑定 AutoForceAI user、Genesis user、projectId、return path 和 nonce。
3. 浏览器跳转到 Genesis `/sso/exchange?code=...`。
4. Genesis 消费 code 后签发自己的用户会话并立即作废 code。

需要先确定用户映射规则；建议使用不可变 `externalUserId`，邮箱只用于首次匹配提示。

## 13. 实施波次与验收门槛

### Wave A：冻结契约（2.0、2.1）

1. 确认 Genesis_CRM 集成基线分支/commit，并合并或固定当前 Agent 分支。
2. 在 Genesis 仓库维护 `integration-v1.openapi.yaml` 与示例 payload。
3. AutoForceAI 固定消费 v1 contract，加入请求/响应 schema 测试。

验收：字段、状态、错误码、鉴权、项目隔离、幂等、版本策略都有机器可校验的契约。

### Wave B：服务接入（2.2、2.3）

1. Genesis 服务凭证、scope、项目绑定、审计日志。
2. AutoForceAI `GenesisCRMClient`、配置模型和 admin-only 配置页。
3. 连接测试必须验证 health、project、scope 和 contract version。

验收：不使用人工账号即可完成只读 health；错 token、错项目、缺 scope 均返回稳定错误码且前端可解释。

### Wave C：可靠线索交接（2.4）

1. Outbox job、entity link、dispatcher、重试/死信。
2. Genesis customer upsert 与 external reference。
3. 本地线索页显示同步状态，支持单条重投。

验收：同一线索并发/重复投递 10 次只产生 1 个客户；服务停机后恢复可自动补投；无效 payload 进入死信；组织 A 不能写入项目 B。

### Wave D：销售闭环（2.7、2.6）

1. outcome cursor feed 与 AutoForceAI poller。
2. `/crm` 门户使用真实摘要，清理重复 CRM 入口。
3. 阶段 3 漏斗补上 CRM 成交归因。

验收：Genesis 把客户改为 `won` 后，AutoForceAI 在一个轮询周期内显示成交，并保持原始获客来源不变。

### Wave E：CRM 内 AI 与免登（2.5、2.8）

1. Genesis 未知邮件预览/查重/确认建档。
2. 一次性 SSO code 和用户映射。

验收：未知邮件未经确认不会建档；同一确认重复提交不重复创建；SSO code 过期或重放均失败。

## 14. 阶段 2 完成定义

- 线索交接、重试、死信和重投全链路可审计。
- 组织与 Genesis project 强绑定，跨项目隔离测试通过。
- 用户凭证与服务凭证完全分离，可撤销、可轮换、最小权限。
- Genesis 销售状态能回流 AutoForceAI 完成成交归因。
- `/crm` 不再出现伪功能或重复 CRUD，所有数据来自真实接口。
- 两端契约测试、集成测试和断网恢复测试通过。
- 2.5、2.8 若保留 P3，可单独延期，但 2.0–2.4、2.6、2.7 必须完成后才能宣布阶段 2 完成。
