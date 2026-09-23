# AGENTS.md — 多 Agent 协作与分支规范

> **本文件对仓库内所有 AI agent（Codex / DSH / Cursor / Claude…）与人类协作者同样有效。**
> 开工前先读它；与其它文档冲突时，以本文件为准。

---

## 一、唯一铁律

> **main 永远是正确的。**

任何改动，无论来自哪个 agent，都走同一条路：

```
从 main 开短命分支 → 改 → 推送 → 开 PR → 合入 main → 立刻删分支
```

不在 main 之外长期停留，不直接 push main，不留"半成品分支"。

---

## 二、工作目录（git worktree）与分工

本仓库用 `git worktree` 把**同一个仓库**摊成多份目录，各站一条分支。它们不是三个项目。

| 目录 | 用途 | 应处的分支 | 服务端口 |
|---|---|---|---|
| `D:\Trade\AutoForceAI` | 后端 / CRM / services / db | 临时 `codex/<主题>` | — |
| `D:\Trade\AutoForceAI\.codex-worktrees\autoforce-main-release` | 前端 UI（`apps/web-console`） | 临时 `ui/<主题>`；空闲时 detached 于最新 main | 3051 |
| `D:\Trade\afai-release` | **验收站**（只读） | 始终 `main` | **3050** |

**纪律**

1. 一个目录只服务一个用途，**不要跨目录改动**——别的 agent 可能正在那里有未提交的工作。
2. 验收站 `afai-release` **只允许 `git switch main` / `git pull`，不允许提交任何东西**。
3. 改动前先 `git fetch origin` 并让工作区干净。

---

## 三、标准流程（照抄即可）

```powershell
# 0. 进入你负责的目录（见上表）
cd D:\Trade\AutoForceAI\.codex-worktrees\autoforce-main-release

# 1. 同步 main，开短命分支（命名：<agent>/<主题>）
git fetch origin
git switch --detach origin/main          # 确保从最新 main 起步
git switch -c ui/首页改版                # 后端用 codex/<主题>，文档用 docs/<主题>

# 2. 改代码；随时提交，不要长时间停留在未提交状态
git add -A
git commit -m "feat(web-console): 首页改版——数字人调度中心信息架构与布局"

# 3. 推送并开 PR
git push -u origin HEAD
# 打开 GitHub 提示的链接 → "Compare & pull request" → 合并

# 4. 合并后清理（关键，别省）
git switch --detach origin/main
git fetch origin --prune
git branch -D ui/首页改版
git push origin --delete ui/首页改版     # 若远端分支还在
```

---

## 四、禁止事项

1. **禁止用 `git cherry-pick` 搬运功能代码。**
   它会在两条分支上生成「内容相同、SHA 不同」的重复提交——这是本仓库历史上分支混乱的主因。跨分支搬运一律用 **merge 或 PR**。
2. **禁止直接 push `main`**：main 开启分支保护后必须走 PR。
3. **禁止在别人的工作目录里改文件或提交。**
4. **禁止长期保留 release / hotfix 分支。** 需要发布快照就打 tag：
   ```powershell
   git tag -a v0.3.0 -m "首页改版 + CRM Phase2" && git push origin v0.3.0
   ```
5. **禁止 `git reset --hard` / 强推（`--force`）别人的分支。**
6. **禁止把构建产物与本地目录提交进库**（如 `tsconfig.tsbuildinfo`、`.next/`、`.codex-worktrees/`）。

---

## 五、验收与发布

- **验收**：浏览器打开 <http://localhost:3050>（内容 = main）
- **前端预览**：<http://localhost:3051>（UI 工作树自己的 dev server）
- **发布**：main 即发布线；快照用 tag，不新建长期分支

---

## 六、自检命令（任何时候都可跑）

```powershell
git -C D:\Trade\AutoForceAI worktree list        # 有哪几份代码、各站在哪条分支
git -C D:\Trade\AutoForceAI branch -vv           # 本地分支与追踪状态
git -C D:\Trade\AutoForceAI log --oneline -5 origin/main
git -C D:\Trade\AutoForceAI status --short       # 当前目录是否有未提交改动
```

判断"我该不该提交"的三个问题：

1. 我在**我的**目录里吗？（对照第二节的表）
2. 我的分支是**从最新 main** 开的吗？
3. 这个改动**只做了一件事**吗？（是 → 提交 + PR；不是 → 拆开）

---

## 七、概念速查

| 概念 | 含义 |
|---|---|
| 分支（branch） | 一条历史线 |
| 工作树（worktree） | 磁盘上摊开的一份代码，站在某条分支上；同一仓库可同时摊开多份 |
| `origin/main` | GitHub 上的主线，**唯一权威** |
| PR | 把短命分支合入 main 的正式通道，也是唯一允许的入 main 方式 |
| tag | 不可变的发布快照，替代"长期 release 分支" |
