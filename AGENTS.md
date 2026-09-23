# AGENTS.md — 多 Agent 协作与分支规范

> **本文件对仓库内所有 AI agent（Codex / DSH / Cursor / Claude…）与人类协作者同样有效。**
> 开工前先读它；与其它文档冲突时，以本文件为准。

---

## 一、唯一规则（记住这一条就够）

> **一个改动 = 一个分支 = 一个 PR = 合入 main。**

- 从**最新 main** 开一条短命分支 → 改 → 推送 → 开 PR → 合入 main → **立刻删分支**
- **不需要判断改动属于前端 / 后端 / 文档 / 配置**，流程完全一样
- 不需要判断"这是单端还是跨端"——**跨端改动就放在同一条分支、同一个 PR 里**
- 不直接 push main（已开分支保护时技术上也不可能），不在 main 之外长期停留

branches 命名只为人类可读，不承载规则含义：`<agent>/<主题>`，如 `ui/首页改版`、`codex/crm-portal`、`docs/xxx`。

**提交由谁触发（默认约定）**

| 动作 | 谁做 | 何时 |
|---|---|---|
| 改代码 → `commit` → `push` 到短命分支 | **agent** | 一个改动完成即做，**不必等人发话** |
| 开 PR / 合并进 main | **人**来点 | 分支推送之后 |
| 判断"这块算做完了吗" | **你** | 一句话，或授权 agent 按"能自测通过的小步"自行切分 |

- **不要攒到当天结束、或会话结束才提交。** 会话结束只是兜底时机；主要时机是"一件事做完"。
- 提交越晚风险越高：机器故障、误操作、挡住别人的合并、以及别人根本看不到你的改动。
- agent 不会自己行动，所以默认行为写在这里；也可以交代任务时补一句"做完直接提交推送"。

---

## 二、三条铁律（这是真出过事故的地方）

### 1. 未提交 = 不存在

改动只要还留在工作区（没 `commit`、没 `push`），它对**其他 agent、其他工作树、验收站、CI 全部不可见**。
别的 agent 合并代码后"发现少了一块"，根因就是这一条——**不是合并顺序问题，是那份改动从未进入 git**。

> 改完立刻提交并推送；没写完就先推 WIP 分支（`git push -u origin HEAD`），不要留在本地。

### 2. 只用 merge / PR 搬运代码，禁止 cherry-pick

cherry-pick 会在两条分支上生成「内容相同、SHA 不同」的重复提交，让人误判"改了两次 / 漏了什么"，是历史上分支混乱的主因。

### 3. 只看 commit，不看磁盘

"某个目录里有我的改动"**不算数**。只有 `git log origin/main` 里能看到那个 commit，才算真的进了主干。
验收/发布时，永远先确认**跑的是哪个 commit**。

---

## 三、常驻目录（这是运行便利，不是提交规则）

`git worktree` 把同一个仓库摊成多份目录，各站一条分支——它们不是三个项目。

| 目录 | 这里跑着什么 | 服务端口 |
|---|---|---|
| `D:\Trade\AutoForceAI` | 后端 / CRM / db 的日常开发 | — |
| `D:\Trade\AutoForceAI\.codex-worktrees\autoforce-main-release` | 前端 UI（`apps/web-console`）的日常开发 | 3051 |
| `D:\Trade\afai-release` | **验收站**：只读，始终跟随 `main` | **3050** |
| `D:\Trade\wt\<主题>` | 临时任务工作树（可选，用完即删） | 按需 |

这张表只回答"**我想跑起某个服务该去哪个目录**"，**不回答"我该不该开分支"**——那个问题永远只有一个答案：见第一条规则。

**纪律**

1. 一个目录一个用途；**不要跨目录改动**（别的 agent 可能在那里有未提交的工作）。
2. 验收站 `afai-release` **只允许 `git switch main` / `git merge --ff-only origin/main`**，不允许提交任何东西。
3. 动手前先 `git fetch origin`，并让工作区干净。

---

## 四、标准流程（照抄即可）

```powershell
# 0. 进入你要工作的目录（见第三节）
cd D:\Trade\AutoForceAI\.codex-worktrees\autoforce-main-release

# 1. 从最新 main 开一条短命分支
git fetch origin
git switch --detach origin/main
git switch -c ui/首页改版

# 2. 改代码；随即提交并推送（未提交 = 不存在）
git add -A
git commit -m "feat(web-console): 首页改版——数字人调度中心信息架构与布局"
git push -u origin HEAD

# 3. 到 GitHub 开 PR → 合并
#    保护开启后，这是进入 main 的唯一通道

# 4. 合并后清理（别省）
git fetch origin --prune
git switch --detach origin/main
git branch -D ui/首页改版
git push origin --delete ui/首页改版     # 若远端还在
```

多 agent 并行、或想在常驻工位之外隔离地改一个跨端任务时，用脚本开临时工作树：

```powershell
.\scripts\wt-new.ps1 -Topic crm-portal        # → D:\Trade\wt\crm-portal（仓库外，自动复用前端依赖）
# ...前后端一起改、提交、推送、开 PR...
.\scripts\wt-done.ps1 -Topic crm-portal -DeleteBranch
```

> 脚本以 **UTF-8 BOM** 保存：无 BOM 的 UTF-8 `.ps1` 会被 Windows PowerShell 5.1 按 ANSI(GBK) 解析，中文注释直接导致语法错误。改脚本时务必保留 BOM。

---

## 五、合并前后自检（防止"少了一块"）

```powershell
# 1. 现在跑的到底是哪个 commit？（验收站）
git -C D:\Trade\afai-release rev-parse --short HEAD

# 2. 我关心的那次改动进 main 了吗？（把 <sha> 换成你的提交号；退出码 0 = 已进）
git -C D:\Trade\AutoForceAI merge-base --is-ancestor <sha> origin/main
Write-Output $LASTEXITCODE

# 3. main 上最近发生了什么？（每个 agent 的提交都该在这里看到）
git -C D:\Trade\AutoForceAI log --oneline -15 origin/main

# 4. 我的分支落后 main 吗？落后就先合并 main 再继续
git -C D:\Trade\AutoForceAI log --oneline HEAD..origin/main
```

**验收/发布时的判断标准**：`afai-release` 的 HEAD 必须是 main 的最新 commit，且 main 的 log 里能看到所有参与者的提交。任何"我在那个目录里改过"的说法都**不作为依据**。

---

## 六、并行协作的注意事项

- **避免两个 agent 同时改同一个文件**（冲突最贵的来源）；同一文件请串行。
- **小步快跑**：分支活几分钟到几小时，尽快合并；分支活得越久，冲突越大。
- 落后 main 时先 `git merge origin/main`（或 rebase）**在你的分支上**解决冲突，**不要强推、不要 `reset --hard` 别人的分支**。
- 合并顺序无所谓：只要都进了 main 就都在。有冲突时由**后合并的人**负责解决。

---

## 七、禁止事项

1. **禁止 cherry-pick 搬运功能代码**（见铁律 2）。
2. **禁止直接 push `main`**。
3. **禁止在别人的工作目录里改文件或提交**。
4. **禁止让改动长期停留在未提交状态**（见铁律 1）。
5. **禁止长期保留 release / hotfix 分支**——发布快照用 tag：
   ```powershell
   git tag -a v0.3.0 -m "首页改版 + CRM Phase2" && git push origin v0.3.0
   ```
6. **禁止强推（`--force`）已共享的分支 / `reset --hard` 别人的分支**。
7. **禁止把构建产物与本地目录提交进库**（`tsconfig.tsbuildinfo`、`.next/`、`.codex-worktrees/`）。

---

## 八、概念速查

| 概念 | 含义 |
|---|---|
| 分支（branch） | 一条历史线；本仓库里它的单位是「一次改动」 |
| 工作树（worktree） | 磁盘上摊开的一份代码，站在某条分支上；同一仓库可同时摊开多份 |
| `origin/main` | GitHub 上的主线，**唯一权威** |
| PR | 合入 main 的唯一通道 |
| tag | 不可变的发布快照，替代"长期 release 分支" |
| 验收站 | `D:\Trade\afai-release`，只读跟随 main，端口 3050 |
