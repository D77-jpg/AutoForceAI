# 阶段 2 双仓库兼容性记录（Integration API v1）

> 本文件是 CI 门禁检查项：文件必须存在，且两仓库 commit 与契约哈希必须与当前发布一致。
> 任何一侧契约变更前，必须先更新本文件并走完两端回归。

## 冻结契约

- 契约文件：`Genesis_CRM/docs/integration/integration-v1.openapi.yaml`
- 契约版本：**1.0**
- 契约 SHA-256：`7798eb621795e8dc405ff56c0fdfb806622ec5a6144d85d6e839ee85d9061679`
  （计算时点：Genesis_CRM @ e2e3486）

## 兼容 commit（发布基线）

| 仓库 | 分支 | 兼容 commit | 说明 |
|---|---|---|---|
| Genesis_CRM | `codex/genesis-integration-release` | `e2e3486` 起 | Integration API v1 冻结实现（13/13 契约测试）；仅追加 CI 门禁 |
| AutoForceAI | `codex/phase2-release-ready` | 见分支 HEAD | 阶段 2 全量（Wave A–D + 2.9 五项 P0 + §3.6 worker 保护） |

## 链路验收状态

- health / upsert / outcomes / stats 四端点契约测试：Genesis 13/13，AutoForceAI 75/75（含 39 项 2.9 新增）。
- 本地端到端（真实 Genesis 开发库）：保存→测试→启用、线索交付、成交回流均已验证；
  试运行凭证（最小 scope、单 project）已签发并完成冒烟投递。
- 稳定错误码表见 `PHASE2_GENESIS_CRM_INTEGRATION_PLAN.md` §契约一致性清单。
