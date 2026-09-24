# 阶段 2.9 收口与阶段 4 启动执行计划

> 文档状态：阶段 2 **工程核心已完成**；生产连续运行验收由产品负责人暂缓，阶段 4 已启动
> 日期：2026-09-23；状态更新：2026-09-24
> 适用仓库：AutoForceAI、Genesis_CRM
> 原则：阶段 5 继续保留到最后；本计划只完成阶段 2 的交付收口，并为阶段 4 建立清晰起点。
> 当前进度：§3 五项 P0、worker 并发保护、历史净化、凭证轮换、双仓库 CI、PG 演练与运维手册均已完成并合入 `main`；
> 正式标签 `autoforce-phase2-core-v1.0.0` / `genesis-integration-v1.0.0` 已建立；
> 24 小时连续运行不是当前开发前置条件，保留为阶段 5 生产发布前验收项，不据此阻塞阶段 4；
> 兼容性记录：docs/integration/COMPATIBILITY.md；运维手册：docs/PHASE2_OPS_RUNBOOK.md。

## 1. 执行结论

阶段 2 的业务核心与工程发布目标已经达成：双仓库代码已合并、标签与 CI 已建立，
线索交接、回流、凭证安全、项目隔离、迁移和 worker 租约均有测试与演练证据。
产品负责人选择以本地预览继续开发，24 小时连续运行验收移至阶段 5 正式生产上线前执行。

下一步按以下顺序推进：

1. 保持 Integration API v1.0 冻结契约与阶段 2 标签不变。
2. 阶段 4.0 已核对 Genesis 现有 Agent/报价能力，不重复开发邮件草稿、跟进建议和报价 CRUD。
3. 以 `PHASE4_AI_QUOTATION_EXECUTION_PLAN.md` 为当前执行入口。
4. 先冻结报价扩展契约，再按 Genesis → AutoForceAI → 双仓库 E2E 的顺序实现 4.3。

暂不启动：

- 阶段 5 的部署、HTTPS、全量可观测性、备份和正式生产加固。
- 2.8 一次性 SSO，继续保留为 P3。
- 重复建设客户、商机、报价和跟进页面。

## 2. 当前已验证状态

### 2.1 AutoForceAI

| 项目 | 状态 | 基线/结果 |
|---|---|---|
| Wave A/B：契约、客户端、连接配置 | 已完成 | `3e31290` |
| Wave C：Outbox、租约、退避、死信、重投 | 已完成 | `cf5fccf` |
| Wave D：成交回流、CRM 门户摘要 | 已完成 | `bd84e26` |
| CRM Python 测试 | 通过 | 31/31 |
| Web Console TypeScript | 通过 | `tsc --noEmit` |
| 本地 `main` 与远程 | 待处理 | `main` 比 `origin/main` 超前 19 个提交 |
| 工作区 | 非干净 | 存在未提交的 dashboard/UI 改动，不能混入 CRM 收口提交 |

### 2.2 Genesis_CRM

| 项目 | 状态 | 基线/结果 |
|---|---|---|
| Integration API v1 | 已完成 | `feat/integration-api-v1@e2e3486` |
| 服务凭证、scope、项目绑定、审计 | 已完成 | Integration API v1 |
| health/upsert/outcomes/stats | 已完成 | Integration API v1 |
| 客户状态与报价查询 | 已预留 | 阶段 5.2 可复用 |
| Integration API 测试 | 通过 | 13/13 |
| 前后端 TypeScript | 通过 | 双端 typecheck |
| 远程交付 | 待处理 | `feat/integration-api-v1` 暂无 upstream |

### 2.3 已跑通的业务闭环

```text
AutoForceAI 产生线索
  → 同事务创建 Outbox job
  → dispatcher 租约投递
  → Genesis 按 external ID + Idempotency-Key 幂等建档/关联
  → AutoForceAI 保存实体映射
  → Genesis 客户变更为 won/lost
  → outcome feed 游标回流
  → won 更新本地线索为 converted
  → /crm 展示真实连接、队列、漏斗与成交摘要
```

## 3. 阶段 2.9 工作包

### 3.1 P0-1：CRM service token 加密存储 ✅（2026-09-23 完成：Fernet 密文+旧明文迁移+稳定错误码）

#### 问题

AutoForceAI 当前不会把 token 返回前端，但 `crm_integration_configs.service_token` 仍是数据库明文。数据库备份、调试查询或误导出都可能暴露长期服务凭证。

#### 目标设计

- 新增环境变量 `CRM_CREDENTIAL_ENCRYPTION_KEY`。
- 数据库字段改为保存带版本前缀的密文，例如 `enc:v1:<ciphertext>`。
- 使用成熟的 authenticated encryption；项目已有 `cryptography` 时优先使用 Fernet，否则使用 AES-GCM。
- API、日志、异常、repr 均不得出现原始 token。
- `token_preview` 不能通过解密密文末尾生成，应单独保存 `token_last4`。
- 支持旧明文记录的一次性迁移；读取到旧格式时迁移，不长期保留双格式。
- 密钥缺失时：已有密文不得静默当作明文使用，服务应给出明确配置错误。

#### 建议文件

- 新增 `services/digital-brain/core/credentials.py`
- 修改 `services/digital-brain/database/shared_models.py`
- 修改 `services/digital-brain/routers/crm_integration_router.py`
- 新增 migration 与凭证测试

#### 验收标准

- [ ] 数据库中搜索不到原始 service token。
- [ ] 配置保存、连接测试、dispatcher、outcome poller 均能正常解密使用。
- [ ] 前端只收到 `has_token` 和 `token_preview`。
- [ ] 错密钥、缺密钥和损坏密文均返回稳定错误，不泄露密文或原文。
- [ ] token 更新后旧 token 不再被 AutoForceAI 使用。

### 3.2 P0-2：项目绑定变更保护 ✅（2026-09-23 完成：reset-binding+job/链接/cursor 按项目隔离）

#### 问题

当前管理员可以直接修改 `project_id`，但旧的 outcome cursor、实体映射、成功任务和门户统计不会自动隔离或重置，可能产生跨项目状态污染。

#### 首版规则

采用“绑定后不可直接切换”的保守方案：

- 没有成功同步记录时，允许修改 `project_id`。
- 已存在 `crm_entity_links` 或 succeeded job 时，普通保存接口拒绝修改 `project_id`。
- 如确需切换，使用独立的“重置 CRM 绑定”操作。
- 重置操作必须由企业管理员明确确认，并记录审计信息。
- 重置只解除当前配置与远端的绑定状态，不删除本地 Lead。
- 门户、任务和链接查询必须同时按 `organization_id + provider + project_id` 过滤。
- 新项目启用前必须重新测试 service token、scope 和项目绑定。

#### 重置动作建议

```text
POST /api/v1/crm/integration/reset-binding
{
  "expected_project_id": "old-project-id",
  "confirmation": "RESET"
}
```

重置至少完成：

- 停用投递。
- 清空 `outcome_cursor/outcome_polled_at`。
- 将旧项目 link 标记 archived，禁止与新项目混算；不要物理删除审计记录。
- 对未完成 job 做取消或归档，不能把旧 payload 投到新项目。

#### 验收标准

- [ ] 有历史同步记录时无法通过普通保存更换项目。
- [ ] 项目 A 的 cursor、link、job 不出现在项目 B 门户统计中。
- [ ] 重置后不会把旧 job 投递到新项目。
- [ ] 重置、重新连接、重新启用全流程有测试覆盖。

### 3.3 P0-3：限制 CRM base URL，防止 SSRF ✅（2026-09-23 完成：allowlist+重定向校验+IP 防护）

#### 问题

当前只检查 `http://` 或 `https://`，企业管理员可让 AutoForceAI 后端请求任意地址，包括本机服务、云元数据地址和内网管理端口。

#### 目标设计

- 增加 `CRM_ALLOWED_HOSTS`，生产环境必须配置明确域名/IP。
- development 环境可显式允许 `localhost:5000` 和 `127.0.0.1:5000`。
- 生产环境默认只允许 HTTPS。
- 禁止 URL 中包含用户名密码、fragment 和非预期端口。
- DNS 解析后再次检查目标 IP；禁止 loopback、link-local、云元数据和未授权私网地址。
- HTTP 重定向后的每一跳也必须重新校验。
- 客户端设置连接/读取超时和最大响应体。

#### 验收标准

- [ ] 合法 Genesis 地址通过。
- [ ] `169.254.169.254`、`file://`、带凭据 URL、未授权内网地址被拒绝。
- [ ] 重定向到非法地址被拒绝。
- [ ] 本地开发仍可连接 `localhost:5000`。

### 3.4 P0-4：建立正式数据库迁移 ✅（2026-09-23 完成：Alembic 0001-0003+启动对齐）

#### 问题

当前依赖 `create_all` 和 SQLite 专用 `ALTER TABLE`。它不能可靠升级已存在的 PostgreSQL 数据库。

#### 实施范围

- 引入 Alembic。
- 生成完整 baseline migration，不依赖运行时猜测表结构。
- 阶段 2 migration 至少包含：
  - `crm_integration_configs`
  - `crm_sync_jobs`
  - `crm_entity_links`
  - `crm_outcome_events`
  - `outcome_cursor`
  - `outcome_polled_at`
  - `web_base_url`
  - 阶段 2 所有唯一索引和普通索引
  - 凭证加密新增字段
- SQLite 用于开发测试，PostgreSQL migration 作为正式验收目标。
- `init_shared_db()` 不再承担生产 schema 升级职责。

#### 验收标准

- [ ] 空数据库可从零升级到 head。
- [ ] 阶段 1 数据库可升级到阶段 2 且数据不丢失。
- [ ] upgrade 后可 downgrade 一版或提供明确不可逆说明。
- [ ] PostgreSQL 上唯一约束、时间字段和 JSON 字段类型正确。
- [ ] 应用启动时发现 migration 落后会失败并提示，而不是带着旧 schema 继续运行。

### 3.5 P0-5：连接成功后才允许启用 ✅（2026-09-23 完成：保存/测试/启用拆分+变更自动停用）

#### 问题

当前配置保存可以同时写入 `enabled=true`，即使凭证、scope、契约版本或项目尚未验证。

#### 目标流程

```text
保存配置（默认 disabled）
  → POST /test
  → health 全项通过
  → POST /enable
  → dispatcher/outcome poller 开始工作
```

启用条件：

- 最近一次 health 为 `ok`。
- health 校验对应当前的 `base_url + project_id + token fingerprint`。
- contract version 为 `1.0`。
- 必需 scope 完整。
- health 结果未超过有效期，建议 10 分钟。

任何 base URL、project 或 token 变化都立即自动停用，并清除旧 health 结论。

#### 验收标准

- [ ] 未测试、测试失败或测试过期时不能启用。
- [ ] 修改 token/project/base URL 后自动停用。
- [ ] 401/403 会暂停投递与回流。
- [ ] 修复配置并重新测试后可恢复原有重试任务。

### 3.6 P1-1：后台任务进程模型

当前 dispatcher 在 FastAPI lifespan 内启动线程。Outbox 有租约保护，但多个 API worker 会启动多个 outcome poller。

阶段 2.9 的最低要求：

- 文档明确当前部署只能运行一个 API worker，或给 outcome poller 增加数据库租约。
- 加入 `CRM_BACKGROUND_WORKER_ENABLED`，避免 Web worker 全部自动启动后台线程。
- 输出 dispatcher/poller 存活状态和最近一次成功时间供健康检查使用。

阶段 5 再决定是否拆成独立 worker/任务队列；本阶段不引入 Redis/Celery。

#### 验收标准

- [ ] 两个进程同时启动时不会重复推进同一组织的 outcome cursor。
- [ ] worker 被关闭时 API 仍能正常提供只读门户。
- [ ] worker 重启后能继续消费租约过期任务。

### 3.7 P1-2：CI 与发布门禁

每次合并必须运行：

#### AutoForceAI

```text
pytest test_crm_contract.py test_crm_dispatcher.py test_crm_outcomes.py
web-console tsc --noEmit
web-console production build
```

#### Genesis_CRM

```text
npm run test:integration --prefix server
npm run typecheck
npm run build
```

CI 还应检查：

- OpenAPI 契约文件存在且版本匹配。
- AutoForceAI contract model 能解析 Genesis 示例响应。
- 禁止提交 `.env`、service token、数据库文件和调试日志。
- 两个仓库记录彼此兼容的 commit/tag。

## 4. 双仓库合并与发布顺序

### 4.1 Genesis_CRM

当前依赖关系：

```text
main@72183fb
  └─ codex/agent-v1-4-hardening@356a21d
       └─ feat/integration-api-v1@e2e3486
```

建议拆成两个可审查合并单元：

1. `codex/agent-v1-4-hardening` → `main`。
2. `feat/integration-api-v1` 更新到最新 `main` 后 → `main`。

合并前要求：

- [ ] 工作区干净。
- [ ] Agent 全量测试通过。
- [ ] Integration 13 项测试通过。
- [ ] 前后端 build/typecheck 通过。
- [ ] 创建正式 Integration API service token 的操作手册经过人工演练。
- [ ] 合并后打 `genesis-integration-v1.0.0` 标签。

### 4.2 AutoForceAI

- 阶段 2 当前已经提交在本地 `main`。
- 本地 `main` 比 `origin/main` 超前 19 个提交。
- dashboard/UI 文件存在未提交修改，必须独立处理；不要顺手加入 CRM 收口提交。

建议：

1. 从当前阶段 2 基线创建 `codex/phase2-closeout`。
2. 只在该分支完成 2.9 修复和测试。
3. dashboard/UI 改动单独提交或继续保留，不与 2.9 混合。
4. 通过门禁后把 2.9 合回 `main` 并推送。
5. 打 `autoforce-phase2-core-v1.0.0` 标签。

禁止使用会丢失工作区改动的 `reset --hard` 或覆盖式 checkout。

## 5. 24 小时试运行计划

### 5.1 范围

- 选择一个真实但低风险的 AutoForceAI organization。
- 显式绑定一个 Genesis project。
- 使用单独的试运行 service credential，不复用管理员 JWT。
- 首批只投入 10–20 条测试或低风险线索。

### 5.2 场景清单

| 场景 | 操作 | 期望结果 |
|---|---|---|
| 正常建档 | 投递全新邮箱线索 | Genesis 创建 1 个客户，AutoForceAI job succeeded |
| 邮箱关联 | CRM 已有同邮箱客户 | 返回 linked，不覆盖人工字段 |
| 并发重复 | 同一 external ID 并发投递 10 次 | 只产生 1 个客户 |
| 短时停机 | 停止 Genesis 5 分钟再恢复 | job 退避后自动成功 |
| 数据错误 | 构造不合法 payload | 进入 dead，不无限重试 |
| 人工重投 | 修复错误后点击重投 | 复用业务线索并最终成功 |
| 凭证撤销 | 撤销 service token | 投递与回流暂停，配置显示 auth_invalid |
| 凭证轮换 | 更新新 token 并测试/启用 | 原队列继续处理，不重新建线索 |
| 成交回流 | Genesis 状态改为 won | 一个轮询周期内本地变为 converted |
| 流失回流 | Genesis 状态改为 lost | 更新 CRM 摘要，不擅自覆盖本地状态 |
| 跨项目访问 | 用项目 A 凭证访问项目 B | 返回 PROJECT_MISMATCH |
| 服务重启 | 重启 AutoForceAI | 未完成任务和 cursor 正常续跑 |

### 5.3 观察指标

- pending/retrying/dead 数量。
- 最老 pending job 年龄。
- 投递成功率与平均尝试次数。
- health 状态与最近成功时间。
- outcome 最近轮询时间和 cursor 是否持续推进。
- Genesis 客户数量是否与实体映射数量匹配。
- 日志中是否出现 token、完整会话或邮件正文。

### 5.4 通过条件

- [ ] 连续 24 小时没有无法解释的死信。
- [ ] 没有重复客户和跨项目数据。
- [ ] 所有故障场景恢复后无需修改数据库。
- [ ] token 撤销/轮换链路正常。
- [ ] `won` 回流时间不超过配置的两个轮询周期。
- [ ] 产品负责人确认 `/crm` 门户、线索同步状态与 Genesis 深链可用。

## 6. Wave E 处理决定

### 6.1 2.5 未知邮件确认建档

Genesis 当前 Agent 分支已有：

- 邮件线程分析。
- 询价/报价/谈判/退订/退信/拒绝识别。
- 回复草稿。
- 客户状态建议。
- 跟进建议与保存。
- 带审批和幂等保护的客户创建能力。

因此 2.5 不再作为 AutoForceAI 新模块开发。下一步只做产品验收：

1. 未知发件人邮件进入分析。
2. 生成结构化客户预览。
3. 查重并提示可能的已有客户。
4. 用户确认后建档或关联。
5. 退订、退信、拒绝、提示词注入场景禁止自动营销。

验收未通过时在 Genesis 内补缺，不在 AutoForceAI 再建一套邮箱 Agent。

### 6.2 2.8 一次性 SSO

保持 P3，暂不开发。满足以下任一条件后再启动：

- CRM 深链的重复登录已经明显影响业务员使用。
- 两端已有稳定用户映射规则。
- Genesis 已部署到正式域名并完成 HTTPS。

SSO 不得通过共享 JWT_SECRET 实现，仍采用 30 秒有效、单次消费的一次性 code。

## 7. 阶段 4 重新排期

### 7.1 能力重叠结论

| 原任务 | Genesis 当前能力 | 决策 |
|---|---|---|
| 4.1 开发信 AI 生成器 | 已有客户分析、邮件草稿保存 | 先验收补缺，不从零重做 |
| 4.2 模板反哺 | 尚未形成成交驱动闭环 | 等真实数据积累后做 |
| 4.3 AI 报价单 + PDF | 已有报价 CRUD，无 AI 生成和 PDF | 作为阶段 4 首个新开发 |
| 4.4 跟进建议引擎 | 已有建议、排期和保存能力 | 先验收补缺 |
| 4.5 外贸岗位数字员工模板 | 尚未形成正式模板体系 | 最后实施 |

### 7.2 推荐顺序

```text
4.0 现有 Agent 能力验收
  → 4.3 AI 报价单 + PDF MVP
  → 4.1/4.4 缺口补齐
  → 4.2 模板反哺
  → 4.5 数字员工模板
```

### 7.3 4.3 MVP 边界

#### 系统职责

- AutoForceAI：基于知识库、客户需求和历史上下文生成结构化报价建议。
- Genesis_CRM：保存正式报价草稿、重算金额、控制状态、生成 PDF、记录 Timeline。
- 用户：确认后才能创建或修改正式报价，不允许 Agent 无审批直接发送。

#### 建议接口扩展

Genesis Integration API v1 增加向后兼容的 `quotation-draft.v1` 能力扩展；
基础 v1.0 文件与哈希不变，扩展契约见
`docs/integration/quotation-draft-v1.1.openapi.yaml`：

```text
POST /customers/{externalRef}/quotation-drafts
GET  /quotations/{quotationId}
GET  /quotations/{quotationId}/pdf
```

新增最小 scope：

- `quotations:draft`
- `quotations:read`

写请求必须支持 `Idempotency-Key`。价格、行金额和总额仍由 Genesis 后端权威计算。

#### AI 输出结构

- 客户与币种。
- 产品名称、型号、数量、建议单价。
- MOQ、付款方式、交期、有效期。
- 风险提示与缺失信息。
- 依据来源，至少关联知识库文档或客户需求记录。
- 不确定字段保持空值并提示用户，不得编造价格、认证或交期。

#### PDF MVP

- Genesis 服务端生成，保证数据与正式报价一致。
- 包含公司信息、客户信息、报价编号、产品明细、总额、币种、条款、有效期。
- 支持中文和英文字符。
- 下载接口执行项目和客户权限校验。
- 同一报价同一版本生成结果稳定。

#### 4.3 完成定义

- [ ] AI 能从一个已同步客户生成可编辑的结构化报价建议。
- [ ] 未确认前不写入 Genesis。
- [ ] 确认后创建一份 draft 报价且重复提交不重复创建。
- [ ] Genesis 重新计算所有金额，不信任 AI 或前端传入总额。
- [ ] PDF 与数据库报价字段一致。
- [ ] 报价创建进入客户 Timeline。
- [ ] 权限、项目隔离、幂等和错误场景测试通过。

## 8. 建议排期

| 批次 | 内容 | 预估 |
|---|---|---:|
| A | 阶段 2 工程核心与发布收口 | ✅ 已完成 |
| B | 阶段 4.0 能力验收与 4.3 契约冻结 | 当前批次 |
| C | Genesis 报价草稿集成端点、PDF 与测试 | 后续开发批次 |
| D | AutoForceAI AI 报价建议、人工确认与写入 | 后续开发批次 |
| E | 双仓库 E2E、远程 CI 与产品验收 | 后续验收批次 |
| F | 24 小时连续运行 | 阶段 5 生产发布前 |

以上是工作量估算，不包含阶段 5 的正式部署与运维设施。

## 9. 阶段 2 最终关闭条件

工程核心状态（截至 2026-09-24）：

- [x] 3.1–3.5 五项 P0 全部完成。
- [x] 双端测试、类型检查和 production build 全部通过。
- [x] 双仓库代码已经合入远程 `main`。
- [x] OpenAPI 契约和双方 commit/tag 已互相记录。
- [x] 没有明文 service token；旧开发凭证已撤销并轮换。
- [x] 跨项目统计、投递和回流隔离有测试覆盖。
- [x] PostgreSQL migration 经过真实容器演练。
- [x] 阶段 2 运维手册覆盖凭证、死信、绑定重置和 worker 运维。
- [ ] 24 小时连续运行验收（产品负责人主动暂缓，移至阶段 5，不阻塞阶段 4）。

因此阶段 2 标记为：`✅ 工程核心完成 / ⏸ 生产连续运行验收延后`。
Wave E 与 24 小时运行验收均为独立 backlog，不影响阶段 4 开发。

## 10. 下一轮直接执行清单

下一轮开发按以下顺序执行：

1. [x] 核对 Genesis 报价 CRUD、金额计算、项目权限、Agent 与 Timeline 能力。
2. [x] 冻结 `quotation-draft.v1` 扩展契约与验收清单。
3. [ ] Genesis 实现 `quotations:draft` scope、幂等创建草稿和报价详情端点。
4. [ ] Genesis 实现服务端 PDF 与稳定版本/缓存语义。
5. [ ] AutoForceAI 实现结构化报价建议、来源依据、缺失信息与人工确认。
6. [ ] 双仓库契约测试、E2E、远程 CI 与产品验收。
