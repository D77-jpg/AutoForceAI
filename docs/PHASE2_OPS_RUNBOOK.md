# 阶段 2 运维手册（Genesis CRM 集成）

> 适用范围：AutoForceAI 阶段 2 收口后的 CRM 集成运维（Genesis Integration API v1 冻结契约）。
> **铁律：本手册任何命令示例中严禁出现真实 token。** 所有 token 一律写作 `gci_<由-CLI-打印-的完整值>`。

---

## 0. 关键位置

| 项 | 位置 |
|---|---|
| 契约文件（唯一权威） | `Genesis_CRM/docs/integration/integration-v1.openapi.yaml` |
| 兼容性记录 | `AutoForceAI/docs/integration/COMPATIBILITY.md` |
| 凭证 CLI | `Genesis_CRM/server/` 下 `npm run integration:credential -- <命令>` |
| AutoForceAI 集成配置 | `/crm/settings`（管理员），API `PUT /api/v1/crm/integration/config` |
| 迁移 | `AutoForceAI/services/digital-brain/` 下 `alembic` |
| 加密密钥 | AutoForceAI 部署环境变量 `CRM_CREDENTIAL_ENCRYPTION_KEY`（只放 .env/密钥管理，永不入库入仓） |

`CRM_CREDENTIAL_ENCRYPTION_KEY` 必须使用 `cryptography.fernet.Fernet.generate_key()` 生成的
32-byte urlsafe-base64 Fernet key。普通短口令不会被自动派生为密钥，以避免数据库泄露后被离线穷举。

---

## 1. Genesis service credential 签发（最小 scope、单 project 绑定）

```bash
cd Genesis_CRM/server
npm run integration:credential -- create \
  --name "<用途标识，如 phase2-trial>" \
  --project <试运行 projectId> \
  --scopes "customers:upsert,outcomes:read,stats:read" \
  --note "<说明>"
```

- **最小 scope**：阶段 2 核心链路只需要 `customers:upsert, outcomes:read, stats:read`。
  `quotations:read` 仅在启用报价读取（阶段 4.3）时追加。
- **project 绑定**：试运行凭证只绑定一个试运行 project；`--project default` 解析为系统默认项目。
- CLI 只在创建/轮换时**打印一次**完整 token。立即通过安全渠道交给 AutoForceAI 配置人员；
  不要把终端输出截图/复制进工单或聊天。
- 管理命令：`list`（只显示前缀）、`rotate --id <id>`、`revoke --id <id>`。

## 2. AutoForceAI：保存 → 测试 → 启用（三段式）

1. **保存**：管理员在 `/crm/settings` 填 Genesis Base URL / Project ID / Token（可选 Web URL），保存。
   - 保存只负责配置；任何保存都会使之前的测试结论失效；
   - `base_url / project_id / token` 任一变化 → 自动停用投递（project 变化同时清空回流游标）。
2. **测试**：点「测试连接」。成功 → 记录健康指纹；失败 → 自动停用并显示 Genesis 端错误码。
3. **启用**：仅当「当前配置与最近一次成功测试的指纹一致且发生在 10 分钟内」才可启用
   （`POST /api/v1/crm/integration/enable`，不满足返回 409 并在按钮上禁用）。

等价 API：`PUT /config` → `POST /test` → `POST /enable`；停用 `POST /disable`。

## 3. token 轮换与撤销

```bash
# 轮换（Genesis 侧，旧凭证立即失效，打印一次新 token）
npm run integration:credential -- rotate --id <credentialId>
# 撤销
npm run integration:credential -- revoke --id <credentialId>
```

轮换/撤销后 AutoForceAI 侧必然出现 `auth_invalid`：投递暂停（retrying 1h）、回流暂停。
按 §2 重新「保存新 token → 测试 → 启用」即可恢复。**不需要** reset-binding。

## 4. credential_error 排障

`credential_error`（稳定 `CredentialError.code`）分两类：

| 现象 | 原因 | 处理 |
|---|---|---|
| `MISSING_ENCRYPTION_KEY` | 部署未配置 `CRM_CREDENTIAL_ENCRYPTION_KEY` | 配置密钥后重启 worker；已有密文需要与加密时**相同**的密钥 |
| `INVALID_ENCRYPTION_KEY` | 密钥不是合法 Fernet key | 使用 `Fernet.generate_key()` 生成并通过密钥管理器配置 |
| `DECRYPT_FAILED` | 密钥被更换 / 密文损坏 | 无法恢复旧 token：重新保存 token → 测试 → 启用 |
| `TOKEN_NOT_SET` | 配置未保存 token | 保存 token |
| `auth_invalid`（健康状态） | Genesis 端凭证被撤销/过期/scope 不足 | §3 轮换或重签 |

投递 job 表现为 `retrying`（next_retry 1 小时后），修复凭证后自动续投；门户会显示暂停原因。

## 5. 死信查看、修复与人工重投

- 查看：`GET /api/v1/crm/integration/jobs?status_filter=dead`（仅本组织、当前项目绑定）。
- 修复：按 `last_error_summary` 处理（客户数据问题→修线索；422 契约不符→查 Genesis 侧拒绝原因；凭证→见 §4）。
- 重投：`POST /api/v1/crm/integration/jobs/{job_id}/retry`（dead/cancelled 可重投；**旧项目绑定的 job 不允许重投**，防止串项目）。
- 全量重同步：`POST /api/v1/crm/integration/resync`（`confirm=RESYNC`，可选 `force=true` 覆盖 Genesis 端；需已绑定项目）。

## 6. project binding reset（危险操作）

**适用条件**：需要把集成换绑到另一个 Genesis project 且历史数据不迁移。
**确认步骤**：`POST /api/v1/crm/integration/reset-binding`，body：

```json
{ "expected_project_id": "<当前绑定的 projectId>", "confirmation": "RESET" }
```

执行效果（事务内）：停用投递 → 解绑 project → 清空回流游标 → 当前项目映射归档（保留可查）→ 取消旧项目未完成 job。
**审计记录**：`last_reset_at / last_reset_by` 写入配置，服务端写操作日志。前端要求输入 `RESET` 确认。

同一个 Genesis `project_id` 只能绑定一个 AutoForceAI organization；应用层会返回 409，数据库唯一索引
`uq_crm_config_provider_project` 负责并发兜底。升级到 0004 前如已有重复绑定，需先由管理员确认唯一归属并解绑其余配置。

## 7. worker 启停与健康

- 开关：`CRM_BACKGROUND_WORKER_ENABLED=0`（或 `false/off/no`）→ 该实例不跑后台投递/回流线程；
  API 与 `/crm` 只读门户照常。多实例部署时**至少保留一个** worker 开启的实例。
- 健康：`GET /api/v1/crm/integration/worker-health` 返回 worker 开关、dispatcher/poller 最近成功时间、
  租约归属与有效期、最近错误（脱敏）。
- 并发语义：dispatcher 使用 job 级租约；outcome poller 使用配置行级租约（60s，心跳续租），
  实例崩溃后租约过期由其它实例接管；重启后过期 job 租约自动回收续投。

## 8. PostgreSQL upgrade / downgrade

```bash
cd AutoForceAI/services/digital-brain
# 空库初始化 / 升级
DATABASE_URL="postgresql+psycopg://user:pass@host:5432/dbname" \
  venv/Scripts/python -m alembic upgrade head
# 阶段 1 老库（已有业务表、无 alembic 版本记录）：先打基线戳再升级
... -m alembic stamp 0001_phase1_baseline && ... -m alembic upgrade head
# 回滚到阶段 1 基线（删除全部 CRM 表，不动阶段 0/1 业务表）
... -m alembic downgrade 0001_phase1_baseline
```

- 启动时 `ensure_schema_current()` 自动对齐：SQLite 开发库无版本可 stamp；PostgreSQL 无版本会在任何
  `create_all`/stamp 前**拒绝启动**并提示执行上述显式迁移；落后→upgrade；库领先代码→拒绝启动。
- PG 迁移会 `CREATE EXTENSION IF NOT EXISTS vector`（需要数据库权限；无权限请先由 DBA 安装）。
- 枚举类型用幂等 `CREATE TYPE`（重复执行安全）。

## 9. 24 小时试运行步骤

1. 确认双仓库处于兼容性记录中的 commit（§0）。
2. Genesis 签发试运行凭证（§1，最小 scope、单试运行 project）。
3. AutoForceAI 配置密钥环境变量后完成「保存 → 测试 → 启用」（§2）。
4. 写入 ≥20 条试运行线索，确认 outbox 投递 `succeeded`、Genesis 端可见客户。
5. 在 Genesis 中将若干客户置为「成交/流失」，观察 ≤60s 内回流：线索状态与「最近成交事件」卡更新。
6. 期间观察 `/crm` 门户摘要、`worker-health` 心跳、日志无 credential_error/SSRF 告警。
7. 故意构造一次失败（临时撤销凭证）：确认暂停-告警-恢复链路符合 §3/§4，然后恢复。

## 10. 回滚条件与回滚步骤

**回滚条件**（任一）：连续凭证错误无法恢复；契约 422 大面积出现（说明两端版本漂移）；
PG 迁移后启动校验失败；试运行期发现跨项目数据串扰。

**回滚步骤**：
1. `POST /disable` 停用投递与回流（幂等，随时可执行）。
2. 保留数据排查：job/映射/事件表均不删除；reset-binding 仅在新项目绑定失败时按 §6 执行。
3. 代码回滚到上一个兼容 commit（见兼容性记录），数据库按需 `alembic downgrade 0001_phase1_baseline`
   （仅删 CRM 表；**先备份**）。
4. 禁止用"绕过校验/禁用门禁"方式带病运行。

## 11. 安全红线

- token/密钥永不写入：代码、文档、提交、测试快照、日志（打印仅限 `token_preview` 后 4 位掩码）。
- `.env`、`*.db`、日志目录严禁提交；CI 有敏感信息门禁。
- Genesis base_url 受 allowlist 约束（`CRM_ALLOWED_HOSTS`）；生产仅 HTTPS 且禁 localhost。
