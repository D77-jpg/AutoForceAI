<#
.SYNOPSIS
  收尾一个「跨端任务」工作树（配合 scripts/wt-new.ps1 使用）。

.DESCRIPTION
  脚本会：
    1. 拒绝删除「有未提交改动」的工作树（防误丢）
    2. 先断开前端 node_modules 的 Junction（只删链接，不碰真实依赖）
    3. git worktree remove 移除工作树
    4. -DeleteBranch 时同时删除本地与远端分支（确认 PR 已合并后再用）

.NOTES
  兼容 Windows PowerShell 5.1 与 PowerShell 7+（文件以 UTF-8 BOM 保存）。
  刻意不使用 $ErrorActionPreference='Stop'（git 的正常进度会走 stderr），
  改为逐步显式检查 $LASTEXITCODE。

.EXAMPLE
  .\scripts\wt-done.ps1 -Topic crm-portal -DeleteBranch
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Topic,
  [switch]$DeleteBranch,
  [string]$Repo = 'D:\Trade\AutoForceAI',
  [string]$WorktreeRoot = 'D:\Trade\wt'
)

$ErrorActionPreference = 'Continue'

$branch = "task/$Topic"
$path = Join-Path $WorktreeRoot $Topic

if (-not (Test-Path $path)) {
  throw "工作树不存在：$path"
}

# 防误丢：有未提交改动就停下
$dirty = git -C $path status --short
if ($dirty) {
  Write-Host 'X 该工作树还有未提交改动，已停止删除：' -ForegroundColor Yellow
  $dirty | ForEach-Object { Write-Host "    $_" }
  Write-Host '  请先提交并推送，或人工确认后自行处理。'
  exit 1
}

# 先断开 Junction（rmdir 只删链接，绝不触碰目标依赖目录）
$nm = Join-Path $path 'apps\web-console\node_modules'
if (Test-Path $nm) {
  cmd /c rmdir "$nm" | Out-Null
  Write-Host '已断开前端依赖 Junction（真实依赖未受影响）'
}

git -C $Repo worktree remove $path
if ($LASTEXITCODE -ne 0) { throw "git worktree remove 失败：$path（可能仍有改动或未被 git 忽略的文件）。" }
Write-Host "OK 已移除工作树：$path"

if ($DeleteBranch) {
  # 本地分支
  if (git -C $Repo branch --list $branch) {
    git -C $Repo branch -D $branch | Out-Null
    Write-Host "OK 已删除本地分支：$branch"
  }

  # 远端分支：先探测是否存在，避免 "remote ref does not exist" 报错
  $remoteRef = git -C $Repo ls-remote --heads origin $branch
  if ($LASTEXITCODE -ne 0) {
    Write-Host '! 无法访问远端（网络或凭据问题），已跳过远端分支删除。' -ForegroundColor Yellow
    Write-Host "  稍后请手动确认：git push origin --delete $branch"
  } elseif ($remoteRef) {
    git -C $Repo push origin --delete $branch | Out-Null
    Write-Host "OK 已删除远端分支：origin/$branch"
  } else {
    Write-Host "   远端无 origin/$branch（未推送过），跳过"
  }
} else {
  Write-Host "   分支 $branch 仍保留。确认 PR 已合并后，用 -DeleteBranch 删除。"
}

if (Test-Path $path) {
  Write-Host "! 目录仍有残留（可能是被忽略的文件）：$path —— 请人工确认后删除。" -ForegroundColor Yellow
}
