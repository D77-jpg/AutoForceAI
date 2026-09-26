# H-14 候选发布与生产 24 小时试运行清单（不可替代验收）

**状态：候选准备；生产验收未完成。** 本清单只记录两仓 H-13 已合并主线 `AutoForceAI@7b29a04` / `Genesis_CRM@2213b45` 的 H-14 起点；H-14 PR 合并后须重新锁定双仓 HEAD、远端 Actions、镜像 digest 和测试证据。合同基线另见 `docs/integration/COMPATIBILITY.md`，不可改动冻结哈希。H-14 不开发新功能；未经授权不删旧分支、不打候选 tag、不启动生产环境。

## 已在 H-14 工作分支本地验证（2026-09-26；PR 合并后要重跑）

- AutoForceAI 后端仓库 venv Python 3.14：`python -m pytest tests/ -q -ra`：247 passed，skip=0；另合同+迁移 32 passed，skip=0。Windows 全局 Python 3.14 缺少依赖曾导致 22 项收集错误，改用已安装仓库 venv 后全过；**远端 Python 3.11 CI 才是支持版本权威**。Web `npm test` 13/13、`npm run typecheck`、`npm run build` 通过。H-12 PostgreSQL 备份测试 Windows 10 项中 1 项因符号链接权限跳过；在 WSL/Linux 复测 10/10、skip=0。生产编排测试 2/2，`docker compose --env-file deploy/production.env.example -f deploy/compose.yaml config --quiet` 通过。
- Genesis server (`NODE_ENV=test`，未向外部邮件服务发信) `test:integration` 23、`test:mail` 79、`test:template-feedback` 3、`test:scratchpad` 3、`test:agent` 32、`test:security` 5，所有列出的套件 skip=0；server typecheck/build、web build 通过。备份+Docker 安全测试 7/7、skip=0；`docker compose --env-file production.env.example config --quiet` 通过。最初手动设置 `MONGODB_URI=127.0.0.1:27017` 但本机没有 Mongo 服务，mail 测试失败；随后移除该变量，使测试自己启动隔离的 `mongodb-memory-server` 并复测通过。**不要将这次初始失败误写成主线应用故障，也不能省略失败记录。**
- 两仓完整可达提交及历史树文件名已只按路径/规则检查（AutoForceAI 111 commits；Genesis 49 commits）：未发现实际 `.env`、数据库文件或私钥文件；形态扫描未发现新的非测试 token/私钥证据。AutoForceAI 已有六条精确 `.gitleaksignore` 指纹（历史撤销的 provider key、worker 旧默认值、测试标识），Genesis 四条合成 fixture 指纹；这些必须在保密环境确认撤销/例外后才可声称风险关闭。不能从有限规则扫描推断不存在任何隐藏密钥；以远端 pinned Gitleaks 全历史 redacted 扫描为候选门禁。

## 合并后必须执行（未完成不得标记候选发布）

1. 在两仓 **最新** `origin/main` 干净 checkout 获取确切 SHA（有先后依赖，先合 Genesis 收口 PR 再合 AutoForceAI 收口 PR），人工核对两个合同 SHA-256、接口能力、两仓构建镜像 digest。所有 CI 依照 main SHA/PR 结果收集可审计 URL；核对后端/前端、security、hygiene 和新增 H-12/H-13 operations gate **全绿且 skip=0**。PR 未合并时运行成功不能代替合并后 main Actions。
2. 检查远端 `git ls-remote --heads origin`：2026-09-26 AutoForceAI 尚有十余条已合并的 `codex/*` 旧分支，Genesis 尚有六条 `codex/*` 旧分支，另有本 H-14 工作分支；**“只保留 main 和必要 tag”目前不满足**。仅经仓库管理员确认这些分支不再承载未合并工作后，在人工作业中删除远端旧分支并核对 tag 仍指向已审定提交。Agent 不擅自删除；PR 合并后也应清理 H-14 分支。避免用 `git branch -r` 当作远端权威，以 `git ls-remote --heads origin` 核对。
3. 候选 tag 名称、双仓 SHA、Tag 签名/保护规则由发布负责人审定；在两仓 main 的**最终** Actions 全绿和上一步清理、历史安全审计关闭之前不创建 tag。既有阶段 2 正式 tag 不改指向。禁止在尚未部署的本地镜像或自签名 HTTPS 测试后标记生产就绪。
4. `deploy/README.md` 及 Genesis `docs/operations/docker-runtime.md` 的部署/ACME/恢复手册须在隔离主机实操：全新 Docker volume、两端健康/登录、线索交接与报价 E2E、PostgreSQL/Mongo 备份还原到**独立** rehearsal/test 库并核对表/项目和 RTO/RPO。H-13 本地 Docker Hub 拉取基础镜像曾遇 `unexpected EOF`，未完成全栈镜像和正式 ACME smoke；不能宣称阶段 5 “工程验收通过”或“生产上线完成”。

## 正式生产环境建成后才开始 24 小时试运行

由值班负责人记录起始/结束 UTC、域名/证书指纹、两仓 SHA/镜像 digest、演练备份 manifest ID、值班联系人、回滚方案及告警面板；以脱敏记录每小时观测服务可用性与健康、worker 心跳/队列峰值/死信、重复客户与跨项目污染、凭证轮换效果、成交回流时延、报价读取和告警通知。阈值和触发响应必须在试运行**前**由业务方签字；任一失败**立即停止变更并通知负责人**，不得自动 downgrade、删库或自动回滚。保留无凭证的报告及事件追溯。没有连续 24 小时实测数据不能写成已通过，也不得因本地 CI 全绿自动执行 H-15 SSO。
