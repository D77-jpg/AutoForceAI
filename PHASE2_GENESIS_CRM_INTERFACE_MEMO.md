# 2.0 Genesis_CRM 接口约定备忘

> 目标：在 CRM 继续演进时，保护 AutoForceAI 的对接点不被重构破坏。

1. **系统边界**：AutoForceAI 负责获客、询盘和来源；Genesis_CRM 负责客户主档、销售阶段、跟进、报价和成交。两端只通过 HTTP API 集成，禁止直接访问对方数据库。
2. **租户边界**：每个 AutoForceAI `organization_id` 显式绑定一个 Genesis `projectId`。后台请求不得依赖默认项目回退。
3. **认证边界**：后台同步使用专用 service token，不使用管理员账号密码或用户 JWT。token 必须可撤销、轮换、限定 scope，并与 project 绑定。
4. **版本边界**：新增 `/api/integrations/v1`，请求携带 `schemaVersion: "1.0"`。v1 内只允许向后兼容地新增可选字段；删除/改名/改变语义必须发布 v2。
5. **幂等边界**：客户交接以 `(projectId, sourceSystem, externalId)` 为业务唯一键，以 `Idempotency-Key` 为请求幂等键。邮箱不是幂等键，只用于发现可能重复客户。
6. **状态边界**：AutoForceAI 本地 `converted` 表示合格线索，映射 Genesis `interested`，不表示成交。只有 Genesis `won` 才进入成交归因。
7. **更新边界**：首次交接允许创建或关联客户；后续自动同步只补齐空字段，不覆盖 CRM 人工维护的负责人、销售阶段、跟进、报价和备注。
8. **可靠性边界**：AutoForceAI 使用持久化 outbox、指数退避、死信和人工重投。重试必须复用原幂等键；4xx 数据错误不无限重试。
9. **回流边界**：成交/流失通过带 opaque cursor 的增量事件接口回流；消费方按 event ID 幂等处理，不能通过全量客户列表轮询猜测变化。
10. **安全边界**：日志不得包含 token、密码、完整会话或邮件正文；只记录 request ID、项目、外部 ID、错误码、耗时和脱敏摘要。
11. **UI 边界**：AutoForceAI `/crm` 是集成门户和摘要，不复制 Genesis 的客户/商机/报价 CRUD。详情通过深链进入 Genesis；免登另走一次性 SSO code。
12. **当前冻结点**：联调前需明确 Genesis_CRM 采用 `main@72183fb` 还是当前运行分支 `codex/agent-v1-4-hardening@356a21d`。未确定基线前只开发 AutoForceAI 的适配器接口与 mock，不连接真实写接口。

首版必须冻结的端点：`health`、`customers/upsert`、`outcomes`、`stats/overview`；为阶段 5.2 预留客户状态与报价只读查询。
