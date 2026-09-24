# 阶段 4.3：AI 报价单与 PDF 执行计划

> 状态：Wave A–C 已完成；Wave D 双仓库远程验收待执行（2026-09-24）
>
> 前置：阶段 2 工程核心完成；Integration API v1.0 基础契约保持冻结
>
> 执行顺序：Genesis_CRM → AutoForceAI → 双仓库 E2E
>
> 扩展契约：`docs/integration/quotation-draft-v1.1.openapi.yaml`
>
> 契约 SHA-256：`c2b7921dfe076dd1748ca220a2435de26eabc05161264f01514c4a5def397e33`
>
> Genesis_CRM：`main@e9b7c64`（实现提交 `4dd935b`、`fd64bbe`）
>
> AutoForceAI：实现基线 `2fc31d1`

## 1. 结论

阶段 4 不从开发信或跟进建议重新起步。Genesis_CRM 当前已经具备：

- 客户、邮件、跟进和报价的项目级权限隔离；
- 客户分析、英文邮件草稿、跟进建议与人工确认；
- 报价 CRUD、固定币种枚举、后端金额重算；
- 报价进入客户 Timeline，状态变更可显式推进客户到“报价中”；
- Integration API v1 的服务凭证、项目绑定、scope、审计和只读报价摘要。

阶段 4 首个新功能确定为 **4.3 AI 报价单 + PDF**。扩展契约和两端核心实现已经完成；
当前只剩双仓库远程 CI、真实已同步客户 E2E 与产品验收。阶段 2 的 v1.0 基础契约哈希保持不变。

## 2. 产品闭环

```text
已同步客户 / 线索需求 / 知识库依据
  → AutoForceAI 生成结构化报价建议
  → 显示缺失信息、风险和来源依据
  → 用户编辑并明确确认
  → Genesis 按外部客户引用幂等创建 draft
  → Genesis 权威重算行金额与总额
  → 报价进入客户 Timeline
  → Genesis 生成与当前报价版本一致的 PDF
```

明确禁止：

- AI 未经确认直接写入 Genesis 或发送报价；
- AI/前端提交 `amount`、`totalAmount` 并被服务端信任；
- 缺少单价、数量、币种时用猜测值补齐；
- 通过客户姓名或邮箱决定写入对象；
- AutoForceAI 自建第二套正式报价数据库或 PDF 权威版本。

## 3. 系统职责

### 3.1 AutoForceAI

- 选择一个已同步且属于当前 Genesis project 的客户；
- 从线索需求、知识库和允许的客户上下文生成建议；
- 保留来源引用，只传引用标识与标题，不复制知识库全文；
- 将不确定字段保持为空，并阻止未完成建议提交；
- 用户确认后生成稳定 `Idempotency-Key` 并调用 Genesis；
- 展示 Genesis 返回的权威金额、报价编号和 PDF 下载入口。

### 3.2 Genesis_CRM

- 按 `(projectId, sourceSystem, externalRef)` 定位客户；
- 校验服务凭证、`quotations:draft` / `quotations:read` scope 和项目绑定；
- 复用现有报价校验、编号、金额计算、权限和 Timeline 能力；
- 只允许集成端点创建 `draft`，不得创建 `sent/accepted` 等状态；
- 保存最小生成溯源元数据，不保存提示词、知识库正文或模型密钥；
- 服务端生成 PDF，权限和项目隔离与报价详情一致。

### 3.3 用户

- 确认产品、数量、单价、币种、条款、MOQ、交期和有效期；
- 明确点击“创建报价草稿”后才发生跨系统写入；
- 后续发送、谈判、接受、拒绝仍在 Genesis 内完成。

## 4. 冻结接口

基础路径仍为 `/api/integrations/v1`，新增能力标识为 `quotation-draft.v1`：

| 方法 | 路径 | Scope | 用途 |
|---|---|---|---|
| `POST` | `/customers/{externalRef}/quotation-drafts` | `quotations:draft` | 幂等创建正式草稿 |
| `GET` | `/quotations/{quotationId}` | `quotations:read` | 读取权威详情 |
| `GET` | `/quotations/{quotationId}/pdf` | `quotations:read` | 下载服务端 PDF |

兼容策略：

- `docs/integration/integration-v1.openapi.yaml` 与其 SHA-256 保持不变；
- health 的 `contractVersion` 继续返回 `1.0`，避免破坏阶段 2 客户端；
- Genesis 可在 health 中向后兼容地增加可选 `capabilities`，其中包含
  `quotation-draft.v1`；AutoForceAI 首版仍以 scope + 端点响应为准；
- 新请求继续使用 `schemaVersion: "1.0"`，路径仍位于 Integration API v1；
- 删除字段、改变金额/幂等语义或更改路径必须发布新主版本。

## 5. 创建草稿规则

### 5.1 必需输入

- `schemaVersion = "1.0"`；
- `sourceSystem = "autoforce"`；
- `title`；
- `currency`；
- 至少一行 `items`；
- 每行必须有 `productName`、正数 `quantity`、非负 `unitPrice`；
- `Idempotency-Key` 请求头；
- `X-Project-Id` 请求头。

### 5.2 可选输入

- 型号、有效期、付款方式、交期、MOQ、备注；
- `markCustomerAsQuoting`，默认 `false`；
- `proposalTrace`：AutoForceAI proposal ID、模型标识和来源引用。

`proposalTrace` 只用于审计，不参与金额计算。来源引用仅允许：

- `lead`：本地线索或需求摘要；
- `knowledge`：知识库文档/片段 ID；
- `customer`：Genesis 客户引用；
- `quotation`：历史报价引用。

### 5.3 服务端权威字段

以下字段不得出现在创建请求中：

- `quotationId`、`quotationNo`；
- `items[].amount`；
- `totalAmount`；
- `status`（集成创建固定为 `draft`）；
- `createdBy`、`createdAt`、`updatedAt`、`version`。

Genesis 必须在写入前重新计算：

```text
line.amount = round(quantity × unitPrice, 2)
totalAmount = round(sum(line.amount), 2)
```

## 6. 幂等与并发

- 幂等范围：`projectId + credentialId + Idempotency-Key + operation`；
- 同键同载荷：返回首次成功结果，不再创建报价；
- 同键不同载荷：`409 CONFLICT`；
- AutoForceAI 网络重试必须复用原键；
- 幂等记录必须保存请求摘要哈希和响应资源 ID，不保存 service token；
- 用户主动修改建议并再次确认应生成新键，而不是复用旧键。

## 7. 权限、安全与隐私

- 服务凭证必须同时绑定当前 project 与相应 scope；
- 外部客户引用不存在、已归档或不属于当前项目时统一返回 `404 NOT_FOUND`；
- 报价详情和 PDF 查询必须按 `projectId + quotationId` 过滤；
- 审计日志记录 request ID、credential、project、externalRef、quotationId、结果与耗时；
- 日志禁止记录 token、完整提示词、知识库正文和 PDF 二进制；
- notes 和来源标题按普通用户输入进行转义，PDF 不执行 HTML；
- PDF 响应设置 `Content-Type: application/pdf`、安全文件名和 `nosniff`。

## 8. PDF MVP

PDF 至少包含：

- 公司名称与联系信息；
- 客户名称、公司；
- 报价编号、状态、币种、有效期；
- 产品名称、型号、数量、单价、行金额；
- 总金额、付款方式、MOQ、交期、备注；
- 生成时间与报价版本。

规则：

- PDF 只能从数据库中的权威报价生成；
- 同一 `quotationId + version` 生成内容稳定，并返回稳定 `ETag`；
- 报价变更后 `version` 增加，旧 ETag 失效；
- draft PDF 显示“草稿 / DRAFT”水印；
- 字体必须覆盖中文和英文，缺字不得静默替换为空白；
- 金额格式与币种一致，不做隐式汇率换算。

## 9. AutoForceAI AI 建议结构

本地建议在确认前不写入 Genesis，至少包含：

- 客户外部引用和币种；
- 产品名称、型号、数量、建议单价；
- MOQ、付款方式、交期、有效期；
- `missingFields`：尚不能提交的字段；
- `warnings`：价格、认证、交期或需求冲突；
- `sources`：支持建议的来源引用；
- 模型与生成时间等最小审计元数据。

提交门槛：

- `missingFields` 为空；
- 每一行数量、单价已由用户看到并确认；
- 至少一个有效来源；
- 用户拥有当前 AutoForceAI organization 的操作权限；
- CRM 配置 enabled、health 有效且具备新增 scope。

## 10. 错误与重试

| HTTP | code | AutoForceAI 行为 |
|---:|---|---|
| 400/422 | `VALIDATION_ERROR` | 显示字段错误，不自动重试 |
| 401 | `UNAUTHORIZED` | 标记凭证失效，停止写入 |
| 403 | `FORBIDDEN_SCOPE` | 提示重新签发最小权限凭证 |
| 404 | `NOT_FOUND` | 提示客户/报价未关联或已不存在 |
| 409 | `CONFLICT` | 停止重试，提示幂等键冲突 |
| 429 | `RATE_LIMITED` | 按 `Retry-After` 退避 |
| 5xx | `INTERNAL_ERROR` | 有限重试并保留原幂等键 |

PDF 失败不得回滚已成功创建的报价草稿；用户可稍后重试下载。

## 11. 实施波次

### Wave A：Genesis 集成写入（✅ 已完成）

- 新增 `quotations:draft` scope；
- 新增集成校验、handler、service 与幂等存储；
- 复用 `createQuotation`，固定 status=draft；
- 增加详情端点与完整契约测试。

### Wave B：Genesis PDF（✅ 已完成）

- 增加报价版本字段或等价的稳定内容版本；
- 实现 PDF renderer、字体资产和下载端点；
- 覆盖中英文、金额、权限、项目隔离和稳定 ETag 测试。

### Wave C：AutoForceAI 建议与审批（✅ 已完成）

- 新增结构化建议 schema 与生成服务；
- 接入知识库与已同步客户上下文；
- 新增可编辑确认页面；
- 新增 Genesis 客户端方法与错误映射；
- 创建成功后展示深链和 PDF 下载。

### Wave D：双仓库验收（🟡 进行中）

- [x] 镜像扩展契约并固定哈希；
- [x] Genesis 契约/业务测试与 AutoForceAI 解析测试；
- [ ] 一条真实已同步客户 E2E；
- [ ] AutoForceAI PR 远程 CI、敏感信息扫描和产品验收。

## 12. 完成定义

- [x] 未确认前 Genesis 中没有新报价；
- [x] 确认后只创建一份 draft，重复请求返回同一报价；
- [x] 请求无法传入或覆盖行金额、总额和状态；
- [x] Genesis 重算金额并返回权威详情；
- [x] 报价进入正确客户的 Timeline；
- [x] 跨项目、缺 scope、撤销凭证和越权读取均被拒绝；
- [x] PDF 与数据库字段一致，中文英文可读，draft 有水印；
- [x] 同一报价版本 PDF 内容和 ETag 稳定；
- [x] AutoForceAI 展示来源、缺失信息和风险，不编造关键字段；
- [ ] 两仓库测试、typecheck、build、远程 CI 与敏感信息检查全绿。

## 13. 非本阶段范围

- 自动发送报价邮件；
- 在线签署、付款和订单履约；
- 汇率换算、税费、折扣审批和复杂多版本谈判；
- 4.2 成交模板反哺；
- 4.5 外贸岗位数字员工模板；
- 阶段 5 的生产部署、HTTPS、备份和 24 小时连续运行验收。
