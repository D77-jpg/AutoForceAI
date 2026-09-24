# 中秋假期双仓库开发执行计划

> 制定日期：2026-09-24
>
> 适用仓库：`D77-jpg/AutoForceAI`、`D77-jpg/Genesis_CRM`
>
> 目标：换电脑后从远程主干安全恢复开发环境，按可独立验收的小步完成阶段 4 剩余工作，最后完成阶段 5 的工程实现。
>
> 重要边界：阶段 5 的生产域名、正式 HTTPS、真实备份介质和 24 小时连续运行只能在最终部署环境验收；假期内可以完成代码、自动化测试、容器演练和操作文档，但不能用本地冒烟替代生产验收。

## 1. 当前权威状态

截至本文制定时，两个 GitHub 仓库的远程分支都只剩 `main`：

| 仓库 | 远程 main | 已完成 |
|---|---|---|
| AutoForceAI | `a55741a` | 阶段 0、1、2 核心、阶段 3、阶段 4.3 AI 报价单与 PDF、E2E 收口、登录端口修复 |
| Genesis_CRM | `e9b7c64` | Integration API v1、报价草稿扩展、权威 PDF、邮件中心、多项目、Agent V1.4 |

已存在正式标签：

- AutoForceAI：`autoforce-phase2-core-v1.0.0`
- Genesis_CRM：`genesis-integration-v1.0.0`

阶段状态：

| 阶段 | 状态 | 说明 |
|---|---|---|
| 阶段 0 地基修复 | ✅ 完成 | 已进入 main |
| 阶段 1 知识库、AI 客服、线索池 | ✅ 完成 | 已进入 main |
| 阶段 2 Genesis CRM 集成 | ✅ 工程核心完成 | 2.5 转为 Genesis 产品验收；2.8 SSO 保留 P3 |
| 阶段 3 获客引擎 | ✅ 完成 | 首页已接真实线索与 CRM 数据 |
| 阶段 4.3 AI 报价单 + PDF | ✅ 完成 | 双仓库、远程 CI、真实同步客户 E2E 均通过 |
| 阶段 4.1 / 4.4 | 🟡 待产品验收 | Genesis 已有大部分能力，只补真实缺口 |
| 阶段 4.2 / 4.5 | ⬜ 待开发 | 模板反哺、数字员工模板 |
| 阶段 5 | ⬜ 最后实施 | 生产工程、观测、安全、备份、部署 |

`a55741a` 和 `e9b7c64` 是换电脑时必须至少包含的基线。本文合并后 AutoForceAI 的 main 会产生更新的 SHA，因此最终判断应使用 `git log origin/main`，不能要求 HEAD 永远等于上述旧 SHA。

## 2. 回家换电脑后的正确操作

### 2.1 不是“fork main”，而是“从 main 创建短命分支”

当前账号已经可以向两个仓库推送协作分支，不需要再创建 GitHub Fork。这里口语中的“fork main”应理解为“从 `origin/main` 新建短命分支”。正确流程是：

```powershell
git clone https://github.com/D77-jpg/AutoForceAI.git D:\Trade\AutoForceAI
git clone https://github.com/D77-jpg/Genesis_CRM.git D:\Trade\Genesis_CRM

git -C D:\Trade\AutoForceAI fetch origin --prune
git -C D:\Trade\AutoForceAI switch --detach origin/main

git -C D:\Trade\Genesis_CRM fetch origin --prune
git -C D:\Trade\Genesis_CRM switch --detach origin/main
```

每个任务都从最新远程主干建立一条分支：

```powershell
git fetch origin --prune
git switch --detach origin/main
git switch -c codex/<任务名>

# 完成一个可独立验收的改动后
git add -A
git commit -m "<type>(<scope>): <清晰说明>"
git push -u origin HEAD
```

然后由人创建 PR、等待门禁、合入 main。合并后再开始下一任务：

```powershell
git fetch origin --prune
git switch --detach origin/main
git branch -D codex/<任务名>
git push origin --delete codex/<任务名>  # GitHub 未自动删除时才执行
```

禁止事项：

- 不直接提交或推送 main。
- 不使用 cherry-pick 搬运功能代码。
- 不从旧分支继续叠加新任务。
- 不把多个任务攒成一个大 PR。
- 不提交 `.env`、数据库、token、日志、`.next/`、`dist/`、`node_modules/`、虚拟环境或 `tsconfig.tsbuildinfo`。
- 不根据“某个磁盘目录里有代码”判断完成；只看 `origin/main` 的提交。

### 2.2 建议的软件版本

- Git for Windows
- Node.js 20.19 或更高版本
- Python 3.12
- MongoDB Community
- Docker Desktop（阶段 5 与 PostgreSQL 演练需要）
- PostgreSQL 16 + pgvector 可直接使用 Docker，不必安装到宿主机

### 2.3 AutoForceAI 初始化

```powershell
cd D:\Trade\AutoForceAI

py -3.12 -m venv services\digital-brain\venv
services\digital-brain\venv\Scripts\python.exe -m pip install --upgrade pip
services\digital-brain\venv\Scripts\python.exe -m pip install -r services\digital-brain\requirements.txt

cd apps\web-console
npm ci
Copy-Item .env.example .env.local
cd ..\..

Copy-Item services\digital-brain\.env.example services\digital-brain\.env
```

本地端口约定：

- AutoForceAI 后端：`8010`
- AutoForceAI 当前任务分支预览：`3051`
- AutoForceAI main 验收预览：`3050`

开发启动：

```powershell
cd D:\Trade\AutoForceAI\services\digital-brain
venv\Scripts\python.exe server.py

# 另一终端
cd D:\Trade\AutoForceAI\apps\web-console
npx next dev -p 3051
```

### 2.4 Genesis_CRM 初始化

```powershell
cd D:\Trade\Genesis_CRM
npm ci --prefix server
npm ci --prefix web
Copy-Item server\.env.example server\.env
```

编辑 `server/.env` 时至少设置：

- `PORT=5002`
- 长随机值 `JWT_SECRET`
- 本地管理员密码 `ADMIN_PASSWORD`
- `MONGODB_URI=mongodb://127.0.0.1:27017/cdlm`
- 开发期保持 `MAIL_TRANSPORT=mock`、`IMAP_ENABLED=false`

开发启动：

```powershell
cd D:\Trade\Genesis_CRM\server
$env:PORT='5002'
npm run dev

# 另一终端
cd D:\Trade\Genesis_CRM\web
$env:VITE_API_PROXY_TARGET='http://127.0.0.1:5002'
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

本地地址：

- Genesis 后端：`http://localhost:5002/api/health`
- Genesis 前端：`http://localhost:5173`

### 2.5 本地数据和密钥不会随 Git 到新电脑

不会被 Git 带走的内容包括：

- AutoForceAI 的 `.env`、SQLite 数据库和 CRM 加密密钥；
- Genesis 的 `server/.env`、MongoDB 数据、上传附件；
- Genesis Integration service token；
- node_modules、Python venv、Docker volume。

推荐在家里的电脑使用全新本地开发数据，重新创建测试账号、组织、项目和 service credential。不要为了“保持界面里原来的测试数据”复制整个旧 `.git` 目录。

如果确实复制 AutoForceAI SQLite 数据库，必须同时通过密码管理器安全复制同一份 `CRM_CREDENTIAL_ENCRYPTION_KEY`；缺少原密钥时，数据库里的 CRM token 无法解密。不要把密钥发到聊天、截图、Git、日志或 PR。

如果复制 Genesis 数据，应使用 `mongodump` / `mongorestore`，并单独备份 `server/uploads`。不要直接复制正在运行中的 MongoDB 数据目录。

重新签发 Integration credential 时使用单项目、最小 scope；4.3 已需要：

```text
customers:upsert
outcomes:read
stats:read
quotations:draft
quotations:read
```

原始 token 只在创建时显示一次。让模型处理该步骤时必须明确要求：不得把 token 打印到终端回显、聊天、日志或文件；更推荐由人手工复制到 AutoForceAI 设置页。

## 3. 每个任务都必须遵守的验收门槛

### 3.1 AutoForceAI

```powershell
cd D:\Trade\AutoForceAI\services\digital-brain
venv\Scripts\python.exe -m pytest tests -q

cd D:\Trade\AutoForceAI\apps\web-console
npm run typecheck
npm run build

cd D:\Trade\AutoForceAI
git diff --check
git status --short
```

只改后端时也要跑相关后端测试；跨端、路由、共享类型或依赖变化必须跑完整门禁。

### 3.2 Genesis_CRM

```powershell
cd D:\Trade\Genesis_CRM

npm run test:integration --prefix server
npm run test:mail --prefix server
npm run test:scratchpad --prefix server
npm run test:agent --prefix server
npm run typecheck --prefix server
npm run build --prefix server

npm run typecheck --prefix web
npm run build --prefix web

git diff --check
git status --short
```

测试必须是 `0 skipped`。不得通过删除、跳过、软失败或降低断言让门禁变绿。

### 3.3 跨仓库任务

先完成并合并 Genesis PR，再从 AutoForceAI 最新 main 开分支。不得在两个仓库里各自保留长期等待的半成品分支。

接口变化必须同时提供：

- OpenAPI 或等价契约；
- 稳定错误码；
- scope、project 隔离与鉴权规则；
- Genesis 契约测试；
- AutoForceAI 客户端解析测试；
- 双方兼容 commit 与哈希记录。

## 4. 剩余任务总表与执行顺序

严格按下表从上到下执行。一次只让模型做一个任务编号。

| 顺序 | 任务 | 仓库 | 优先级 | 结果 |
|---:|---|---|---|---|
| H-00 | 新电脑环境恢复与双端冒烟 | 两仓库 | P0 | 可开发基线，不产生 PR |
| H-01 | 清理虚假/重复前端入口 | AutoForceAI | P0 | 所有可点击入口都有真实页面或被移除 |
| H-02 | `/knowledge/solution` 真实方案生成页 | AutoForceAI | P1 | 替换占位页，接真实 solution API |
| H-03 | 2.5 + 4.1 未知邮件与开发信 Agent 验收 | Genesis | P0 | 只补真实缺口，不重写现有 Agent |
| H-04 | 4.4 跟进建议引擎验收与补缺 | Genesis | P0 | 建议、编辑、确认、落库闭环 |
| H-05 | 4.2 成交驱动的模板反哺 | Genesis | P1 | 模板效果归因与建议，不自动改模板 |
| H-06 | 4.5 外贸岗位数字员工模板 | AutoForceAI | P1 | 从模板创建可审计数字员工 |
| H-07 | 真实联网搜索工具 | AutoForceAI | P1 | 替换假 WebSearch 结果 |
| H-08 | 模型归因与监控趋势正确性 | AutoForceAI | P1 | 清理两个代码级 TODO |
| H-09 | 5.2 CRM 报价/订单状态 Agent Tool | AutoForceAI，必要时 Genesis | P2 | 报价真实可查，订单未有契约时明确不支持 |
| H-10 | 5.4 可观测性与告警记录 | AutoForceAI | P1 | 日志、费用、趋势、RPA 告警真实可查 |
| H-11 | 5.5 安全加固与依赖扫描 | 两仓库，分开 PR | P1 | 限流、密码、脱敏、扫描门禁 |
| H-12 | 5.6 PostgreSQL + MongoDB 备份恢复 | 两仓库/运维脚本 | P1 | 可备份、可校验、可恢复演练 |
| H-13 | 5.3 Docker Compose + Nginx + HTTPS | 两仓库，Genesis 先行 | P1 | 一键部署工程完成 |
| H-14 | 全量回归、文档收口与候选发布 | 两仓库 | P0 | 远程 CI 全绿，准备生产验收 |
| H-15 | 2.8 一次性 SSO | 两仓库 | P3 条件任务 | 仅在 HTTPS 和用户映射已稳定后启动 |

## 5. 各任务详细实施说明

### H-00：新电脑环境恢复与双端冒烟

不改代码，不创建 PR。

检查项：

- 两个仓库 `git status` 干净，当前提交来自 `origin/main`。
- 远端没有误用的旧功能分支。
- AutoForceAI 8010、3051 可访问。
- Genesis 5002、5173 可访问。
- AutoForceAI 能登录并读取 `/health`。
- Genesis 能登录，模板中心、用户管理、项目工作空间、Agent 诊断可打开。
- AutoForceAI CRM 设置能保存、测试、启用当前 Genesis 项目。
- 使用 Mock 邮件与测试数据，不发送真实邮件。

停止条件：任一基础测试失败时先修环境，不开始功能开发。

### H-01：清理虚假、重复和已取消的前端入口

建议分支：`codex/navigation-truthfulness`

当前事实：

- 电商整组仍显示“开发中”，但订单履约已经决定归 Genesis_CRM，AutoForceAI 不再建设第二套订单/客户模块。
- `/organization/agents` 与已有 `/workforce` 员工能力重复。
- `/digital-human/assets` 属于已暂缓的数字人模块。
- `/monitor/alerts` 还没有页面，将在 H-10 实现。
- `/knowledge/solution` 只有占位页面，将在 H-02 实现。

实现要求：

- 从侧边栏和首页快捷入口移除电商订单、客户会员等重复入口；不要创建空壳页面。
- 移除 `/organization/agents`，员工管理统一指向 `/workforce`。
- 暂时移除 `/digital-human/assets`；数字人首页明确标注远期，不伪装可用。
- `/monitor/alerts` 在 H-10 完成前不可作为可点击入口；可暂时隐藏。
- `/knowledge/solution` 保留但继续显示“开发中”，由紧随其后的 H-02 解除徽标。
- 清理 CRM 客户、商机、合同等重复 CRUD 入口；明细仍在 Genesis。
- 为导航配置增加静态测试或最小断言：菜单中不得出现没有路由的可点击地址。

验收：逐项点击导航，不出现 404、空白页或假数据页面。

### H-02：实现 `/knowledge/solution` 真实方案生成页

建议分支：`codex/knowledge-solution-ui`

后端已有：

- `POST /api/v1/solution/context`
- `POST /api/v1/solution/outline`
- `POST /api/v1/solution/page/content`
- PPT 生成/下载相关能力，以 `solution_router.py` 当前路由为准

实现要求：

- 选择组织内知识库，输入主题、目标受众和风格。
- 先展示检索到的文档来源、相关度和检索日志，再允许生成大纲。
- 大纲可编辑、增删、排序；缺少知识库结果时明确提示使用通用模型知识。
- 逐页生成内容，显示来源，不把模拟日志冒充模型真实思考过程。
- 生成 PPT 时有进度、失败重试和下载入口。
- 所有知识库 ID 必须由后端按 organization 再次过滤。
- 未配置模型时明确显示回退状态，不把模板结果标成 AI 实时生成。
- 删除侧边栏“开发中”徽标。

测试：组织隔离、空知识库、模型失败、非法 KB ID、PPT 下载、前端类型检查。

### H-03：2.5 + 4.1 未知邮件与开发信 Agent 验收

建议分支：`codex/mail-agent-acceptance`

只在 Genesis_CRM 开发。现有代码已经包含邮件线程分析、客户分析、回复草稿、客户预览、查重、人工确认和幂等能力。先写验收测试，只有失败项才改业务代码。

验收场景：

1. 未知发件人邮件只对管理员可见。
2. Agent 从邮件生成结构化客户预览，事实、推断和不确定字段分开。
3. 按邮箱、公司、域名等稳定字段查重，并展示可能重复客户。
4. 未经人工确认不得创建客户或发送邮件。
5. 同一确认幂等重放不会创建第二个客户。
6. 退订、退信、拒绝、垃圾邮件和提示词注入内容不得触发自动营销或客户创建。
7. 开发信仅保存 draft；真实发送仍需用户在发送界面再次确认。
8. project、角色、负责人权限隔离；越权统一返回 404。
9. Agent 输入中的网页或邮件指令只作为不可信内容，不得改变系统权限或调用未授权工具。

主要关注文件：

- `server/src/routes/agent.routes.ts`
- `server/src/services/agent/mail-thread-analysis.service.ts`
- `server/src/services/agent/customer-analysis.service.ts`
- `server/src/services/agent/scratchpad-customer.service.ts`
- `web/src/components/agent/*`
- `server/tests/agent.test.ts`、`server/tests/mail-center.test.ts`

如果所有场景已通过，只提交新增验收测试和验收报告，不进行无意义重构。

### H-04：4.4 跟进建议引擎验收与补缺

建议分支：`codex/followup-agent-acceptance`

同样只在 Genesis_CRM 开发。现有客户分析和邮件分析已经能生成、编辑和确认跟进建议。

验收场景：

- 建议依据必须来自客户档案、Timeline、邮件、跟进和报价，不得编造交期、价格或承诺。
- 返回跟进方式、目的、建议时间、理由和来源。
- 用户可以编辑；未经勾选确认不写数据库。
- 确认后更新 `nextFollowUpAt` 并产生 Timeline 记录。
- 重复确认幂等，不创建重复跟进。
- 退订、退信、明确拒绝客户不安排未来营销跟进。
- 已成交或已流失状态不能被低级建议降级。
- 跨项目与非负责人越权返回 404。

完成后更新阶段 4 文档，把 4.1、4.4 标记为“验收完成”；不要在 AutoForceAI 再做一套相同引擎。

### H-05：4.2 成交驱动的模板反哺

建议分支：`codex/template-performance-feedback`

只在 Genesis_CRM 开发，第一版是“可解释的统计与建议”，不是自动训练模型，也不能自动覆盖模板。

数据设计：

- DevelopmentLetter 保存不可变归因：`templateId`、发送时模板名称快照、模板内容版本或内容哈希。
- 历史无 templateId 的邮件归为“未归因”，不得猜测。
- 以项目为边界，按模板统计发送、回复、有意向、报价、成交、退订和退信。
- 成交归因只表示相关性，不宣称模板单独导致成交。
- 样本小于配置门槛时显示“样本不足”，不做排名。

接口与 UI：

- 模板中心增加效果摘要与时间窗口筛选。
- 展示分母、样本数和各阶段转化率。
- Agent 可以生成“建议修改副本”，用户确认后复制为新模板；不得直接改原模板。
- 保存建议来源、生成模型和时间；不得保存完整提示词或密钥。

测试：项目隔离、历史无归因、模板删除后的快照、重复事件、成交/流失变化、最小样本门槛。

### H-06：4.5 外贸岗位数字员工模板

建议分支：`codex/workforce-role-templates`

在 AutoForceAI 现有 `/workforce` 基础上实施，不另建第三套 Agent 平台。

首批模板：

- 线索研究员：搜索、去重、生成待审核线索，不自动联系。
- 销售开发助手：生成开发信草稿，不自动发送。
- 跟进协调员：生成跟进建议和排期，写入前人工确认。
- 报价助手：调用已完成的 4.3 建议与草稿报价流程。
- 客服助手：回答知识库问题，可查询报价状态，不修改订单。

每个模板必须定义：

- 角色目标与明确禁止事项；
- 允许的工具白名单；
- 数据范围与 organization/project 边界；
- 最大步骤、超时、费用预算；
- 所有外部写入和发送动作的人审门槛；
- prompt/version 与审计字段。

UI 提供“从模板创建”，创建后仍可编辑；模板升级不能静默覆盖已有员工配置。

### H-07：接入真实联网搜索

建议分支：`codex/real-web-search`

当前 `services/digital-brain/core/tools/web_search.py` 返回固定假结果，必须替换。

实现要求：

- 定义 provider 接口，首选复用现有 `SERPER_API_KEY`；如需 SerpApi/Bing，增加明确环境变量和文档。
- 设置连接、读取和总超时；限制查询长度、结果数和响应体大小。
- 只允许 HTTPS provider URL，禁止用户传入任意 base URL。
- 返回统一字段：title、snippet、url、provider、retrieved_at。
- provider 未配置时返回稳定 `SEARCH_NOT_CONFIGURED`，不得返回假新闻。
- 429/5xx 有限重试；4xx 不重试；日志不记录 key。
- 对结果 URL 做基本协议校验，网页内容始终视为不可信数据。

测试完全 mock HTTP，不消耗真实 API 配额。

### H-08：模型归因与监控趋势正确性

拆成两个独立 PR，不要混在一起。

PR A：`codex/inspector-model-attribution`

- 移除 `core/quality/inspector.py` 中写死的 `glm-4-flash`。
- 从实际 LLM runtime/factory 返回 provider、model 和 request ID。
- 失败时保存明确的未知值，不猜测模型。
- 增加至少两种 provider 与回退模式测试。

PR B：`codex/monitor-daily-trend`

- 监控接口按请求时区或统一 UTC 生成连续日期桶。
- 无调用日期也返回 0，不能让折线图跳天。
- 补充 token、调用次数、成功/失败、费用字段。
- 数据库聚合兼容 SQLite 与 PostgreSQL；日期边界有测试。
- 删除已经过时的 TODO 注释。

### H-09：5.2 CRM 报价/订单状态 Agent Tool

建议分支：`codex/crm-status-tools`

当前 Genesis 已有客户与报价读取能力，但没有冻结的订单履约接口。

第一版：

- 实现 `get_crm_customer_status`。
- 实现 `get_crm_quotation_status`，使用 `quotations:read`。
- 只允许读取当前 organization 绑定的 project 和已有实体映射。
- 输出脱敏的状态、编号、金额、币种、更新时间和 Genesis 深链。
- Agent Tool 不接受任意 base URL、project ID 或 token。
- CRM 未启用、凭证失效、映射缺失、scope 不足均返回稳定业务错误。
- 查询行为记录审计，但不记录 token、完整客户隐私或 PDF 二进制。

订单状态：

- 在 Genesis 正式冻结订单契约前，工具返回 `ORDER_STATUS_NOT_SUPPORTED`。
- 不得通过抓页面、查询 Mongo 内部集合或伪造示例数据来冒充订单查询。
- 将来如新增订单 API，按 Genesis → 契约 → AutoForceAI 的顺序另开跨仓库任务。

### H-10：5.4 可观测性与告警记录

建议分支：`codex/observability-alerts`

实现范围：

- API 结构化日志：request ID、route、status、latency、organization；禁止记录 Authorization、Cookie、token、密码和正文。
- LLM 用量：实际 provider/model、输入/输出 token、费用、延迟、状态和错误类别。
- `/platform/monitor` 与 `/monitor` 使用真实统计，处理空数据和部分失败。
- RPA/CRM worker 失败生成持久化告警；相同错误按指纹去重并累计次数。
- 实现 `/monitor/alerts` 页面：时间、来源、严重度、状态、首次/最近发生、脱敏摘要、确认/解决。
- 告警通知支持可选 webhook/email，默认关闭；发送失败不能影响主业务。
- 增加 retention 配置和清理任务，避免日志表无限增长。

不引入“每次轮询都发通知”的噪声策略。告警必须有首次、新增、升级和恢复语义。

### H-11：5.5 安全加固

两个仓库分别建立 PR；不要用一个仓库的 JWT 或 cookie 登录另一个仓库。

AutoForceAI：

- 登录、注册、Agent、搜索、报价确认和管理接口按用户/IP 分层限流。
- 生产环境禁止 mock 微信登录和不安全默认 JWT secret。
- 密码长度、常见弱密码和登录失败策略有测试。
- CORS 使用 allowlist；生产禁止任意 localhost/private host。
- 配置、异常和日志统一脱敏。
- `pip-audit`、`npm audit`、secret scan 加入 CI；高危漏洞必须处理或记录有期限的例外。

Genesis：

- 保持现有限流、helmet、项目隔离，补齐 Agent/Integration/文件下载边界测试。
- 生产环境要求强 JWT secret、管理员密码与 MAIL_CREDENTIAL_ENCRYPTION_KEY。
- SMTP/IMAP/Integration token 不得进入响应、日志或审计 detail。
- 检查上传文件签名、大小、文件名和路径穿越。
- `npm audit` 和 secret scan 作为门禁。

安全修复不得通过关闭错误信息、跳过测试或放宽项目隔离来“解决”。

### H-12：5.6 PostgreSQL + MongoDB 备份恢复

建议把通用编排放在 AutoForceAI `deploy/backup`，Genesis 仓库提供 Mongo 专用脚本与文档；各自独立 PR。

要求：

- PostgreSQL 使用 `pg_dump` 自定义格式，MongoDB 使用 `mongodump --archive --gzip`。
- 备份文件带 UTC 时间、数据库标识、SHA-256 和 manifest。
- 支持保留天数和最大份数，删除前校验目标目录，禁止对根目录或未解析路径递归删除。
- 临时文件写入完成并校验后再原子重命名。
- 可选加密，密钥不入库。
- 恢复默认只能恢复到名字包含 `rehearsal` / `restore_test` 的临时数据库。
- 恢复演练验证关键表/集合、行数、Alembic 版本、CRM 映射和 Genesis project 数量。
- 生成机器可读报告，明确 RTO/RPO 和失败原因。

严禁直接在生产数据库上执行破坏性 downgrade 或清库演练。

### H-13：5.3 Docker Compose + Nginx + HTTPS

这是阶段 5 的最后一个大工程任务。先在 Genesis 合并容器化，再在 AutoForceAI 编排。

Genesis PR：`codex/docker-runtime`

- server/web 多阶段 Dockerfile；非 root 运行。
- Mongo、uploads、备份目录使用 volume。
- healthcheck 使用真实 `/api/health`。
- 前端构建和 API 地址可配置。

AutoForceAI PR：`codex/production-compose`

- 新增 `deploy/`，包含 AutoForceAI backend/web、RPA worker、PostgreSQL+pgvector、Genesis、MongoDB、Nginx。
- 正式环境使用两个域名，例如 `app.example.com` 与 `crm.example.com`，不要依靠脆弱的子路径改写。
- 只暴露 80/443；数据库、内部 API 与 worker 不直接暴露公网。
- healthcheck、restart policy、资源限制、日志轮换和启动依赖齐全。
- `.env.production.example` 只有占位符；Compose 不包含真实密钥。
- Nginx 配置安全头、上传限制、超时、WebSocket/HMR 生产禁用。
- HTTPS 使用 ACME/证书挂载流程；本地自签名只用于演练，不能标记生产验收通过。
- 提供安装、升级、回滚、迁移、备份和故障排查手册。

验收：全新 Docker volume 从零启动、健康检查、双前端登录、线索交接、报价 E2E、备份恢复演练全部通过。

### H-14：全量回归与候选发布

不开发新功能，只做收口。

- 两仓库从最新 main 开干净 checkout。
- 跑完整门禁，skip=0。
- 检查两个远程只保留 main 和必要 tag。
- 扫描完整可达历史中的真实 token、密码、私钥和数据库文件。
- 更新兼容性记录、运行手册和阶段总表。
- 创建候选 tag 前必须确认远程 Actions 全绿。
- 生产环境完成后再执行 24 小时试运行；失败立即停止变更，不自动回滚。

24 小时试运行关注：服务可用性、worker 心跳、队列峰值、死信、重复客户、跨项目污染、凭证轮换、成交回流时延、报价读取和告警通知。

### H-15：2.8 一次性 SSO（条件任务）

只有以下条件全部成立才开始：

- AutoForceAI 与 Genesis 已使用正式 HTTPS 域名；
- 用户映射规则已冻结；
- 两端 session/cookie 安全策略已明确。

设计：

- AutoForceAI 后端用服务身份申请 30 秒有效、单次消费 code。
- code 绑定 externalUserId、Genesis user、project、return path、nonce。
- Genesis `/sso/exchange` 消费后签发自己的会话并立即作废 code。
- code 只允许同源 HTTPS 跳转，不进入日志；过期、重放、错项目全部失败。
- 不共享 JWT_SECRET，不把长期 JWT 放 URL。

如果条件不满足，保持 P3，不得为“全部做完”而实现不安全的本地版 SSO。

## 6. 明确不做或暂缓的内容

以下项目不是假期开发目标：

- AutoForceAI 自建订单履约、客户会员、合同和商机 CRUD；权威业务在 Genesis。
- 未冻结契约前伪造 CRM 订单状态。
- AI 自动发送开发信、报价或跟进消息。
- 自动修改高转化模板或自动训练模型。
- 数字人视频/直播与形象资产；整体继续暂缓。
- 正式支付、在线签署、复杂税费/折扣审批。
- 没有生产域名和证书时宣布 HTTPS/SSO/生产上线完成。
- 用本地短时冒烟代替阶段 5 的 24 小时试运行。

## 7. 建议的假期执行节奏

不要按“写了多少代码”推进，按“合入了多少个可独立验收的 PR”推进。

### 第一批：恢复与清债

1. H-00 环境恢复。
2. H-01 入口清理。
3. H-02 方案生成页。

### 第二批：完成阶段 4

1. H-03 邮件/开发信验收。
2. H-04 跟进建议验收。
3. H-05 模板反哺。
4. H-06 数字员工模板。

### 第三批：真实工具与状态查询

1. H-07 真实搜索。
2. H-08 两个正确性 PR。
3. H-09 CRM 查询工具。

### 第四批：阶段 5 工程实现

1. H-10 可观测性。
2. H-11 安全。
3. H-12 备份恢复。
4. H-13 部署。
5. H-14 收口。

H-15 只按条件启动。

## 8. 给能力较弱模型的固定任务提示词

每次新会话只给一个任务编号，使用下面模板：

```text
你现在只执行 MID_AUTUMN_HOLIDAY_DEVELOPMENT_PLAN.md 中的任务 H-XX，不做其他任务。

开工前：
1. 完整阅读仓库根目录 AGENTS.md。
2. git fetch origin --prune，确认工作区干净。
3. 从 origin/main 创建 codex/<任务名>，不得从旧功能分支继续。
4. 先阅读 H-XX 的范围、验收标准、禁止事项及相关现有代码和测试。

执行原则：
- 先复现/写失败测试，再做最小实现。
- 不重写已有能力，不顺手重构无关文件。
- 不降低测试，不添加 skip，不用 mock 冒充真实功能。
- 不提交 .env、token、数据库、日志、构建产物、node_modules 或 venv。
- 不修改另一个任务的范围；发现额外问题只记录到报告。
- 涉及外部写入、发送、删除、凭证、生产数据时停下说明，不自行扩大权限。

完成时：
1. 跑 H-XX 要求的测试及仓库门禁。
2. git diff --check，确认只改任务范围内文件。
3. 更新相关文档和验收记录。
4. commit 并 push 当前短命分支。
5. 输出：根因/设计、文件清单、测试实测结果、风险、PR 链接建议。
6. 不合并 main、不打 tag；等待人创建并合并 PR。
```

如果模型试图一次执行多个 H 编号，应立即停止并改为单任务。上下文不足时优先读代码和测试，不根据旧聊天猜测当前状态。

## 9. 每晚收工检查

- 当前改动是否已经 commit + push；未提交改动等于不存在。
- 当前 PR 是否已创建，Actions 是否真实运行并全绿。
- 已合并分支是否删除。
- 两个仓库是否都回到最新 `origin/main`。
- 是否意外提交 `.env`、token、数据库、日志或构建产物。
- 是否更新了任务状态和实测数字，而不是写“应该通过”。
- 是否有需要回到办公室才能完成的生产验收；明确列出，不伪造完成。

## 10. 假期结束时的完成定义

阶段 4 可以标记全部完成的条件：

- 4.1、4.4 真实验收完成并有测试证据；
- 4.2 有模板归因、可解释统计和人工确认改版流程；
- 4.3 保持现有 E2E 全绿；
- 4.5 数字员工模板可用且所有写入/发送默认需要人工确认。

阶段 5 可以标记“工程实现完成”的条件：

- 5.2、5.3、5.4、5.5、5.6 均已合入 main；
- 双仓库远程 CI 全绿；
- 全新环境 Compose 演练和临时库恢复演练通过；
- 运维、安全、备份与回滚文档齐全；
- 没有假数据入口、明文凭证或跨项目污染路径。

阶段 5 只有在正式环境 HTTPS、真实备份恢复和 24 小时试运行也通过后，才能标记“生产上线完成”。
