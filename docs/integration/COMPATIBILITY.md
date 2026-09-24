# 阶段 2 双仓库兼容性记录（Integration API v1）

> 本文件是 CI 门禁检查项：文件必须存在，且两仓库 commit 与契约哈希必须与当前发布一致。
> 任何一侧契约变更前，必须先更新本文件并走完两端回归。

## 冻结契约

- 契约文件：`Genesis_CRM/docs/integration/integration-v1.openapi.yaml`
  （本仓库内置冻结副本：`docs/integration/integration-v1.openapi.yaml`，CI 校验哈希）
- 契约版本：**1.0**
- 契约 SHA-256：`7798eb621795e8dc405ff56c0fdfb806622ec5a6144d85d6e839ee85d9061679`

## 双方实现基线（不可变 commit，CI 门禁校验）

| 仓库 | 实现基线 commit | 内容 |
|---|---|---|
| Genesis_CRM | `e2e3486` | Integration API v1 冻结实现（13/13 契约测试） |
| AutoForceAI | `491b1d3` | 阶段 2 核心：Wave A–D + 2.9 五项 P0 + §3.6 worker 租约（发布分支 `codex/phase2-release-ready` 上） |

> CI/文档提交不属于 API 实现基线；基线只记录契约实现 commit，不随门禁提交变化。

## 正式标签（合并完成、远程门禁全绿后由人工创建）

实现基线用于契约追踪；正式标签用于复现「最终通过远程门禁的完整发布状态」，两者不同：

- Genesis_CRM：`genesis-integration-v1.0.0` → 指向合并后 `main` 上包含 Integration API、测试修复、CI 门禁与兼容性记录的最终 release commit（**不**固定到 `e2e3486`）
- AutoForceAI：`autoforce-phase2-core-v1.0.0` → 指向合并后 `main` 上包含阶段 2 核心、worker 保护、migration、运维手册与 CI 门禁的最终 release commit（**不**固定到 `491b1d3`）

## 链路验收状态

- health / upsert / outcomes / stats 四端点契约测试：Genesis 13/13，AutoForceAI 75/75（含 39 项 2.9 新增）。
- 本地端到端（真实 Genesis 开发库）：保存→测试→启用、线索交付、成交回流均已验证；
  试运行凭证（最小 scope、单 project）已签发并完成冒烟投递。
- 稳定错误码表见 `PHASE2_GENESIS_CRM_INTEGRATION_PLAN.md` §契约一致性清单。

## 阶段 4.3 报价草稿扩展

- 扩展契约：`docs/integration/quotation-draft-v1.1.openapi.yaml`
- 扩展版本：**1.1.0**；基础 `contractVersion` 仍为 **1.0**
- 能力标识：`quotation-draft.v1`
- 扩展契约 SHA-256：`c2b7921dfe076dd1748ca220a2435de26eabc05161264f01514c4a5def397e33`
- Genesis_CRM：`main@e9b7c64`；写入实现 `4dd935b`，PDF 实现 `fd64bbe`
- AutoForceAI 实现基线：`2fc31d1`（AI 建议、来源校验、人工确认、客户端、PDF 代理与 UI）

本地验收：AutoForceAI 后端 `100 passed`，扩展契约测试 `skip=0`，前端 typecheck 与
production build 通过。远程 CI、真实已同步客户 E2E 与产品验收在 AutoForceAI PR 合并前执行。
