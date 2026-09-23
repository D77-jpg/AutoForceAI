<#
.SYNOPSIS
  为一个「跨端任务」创建独立工作树（从最新 origin/main 起步）。

.DESCRIPTION
  适用场景：一次改动同时涉及前端（apps/web-console）与后端（services/**），
  且希望与常驻工位隔离（多个 agent 并行时推荐）。

  脚本会：
    1. git fetch 并从最新 origin/main 建分支 task/<主题>
    2. 工作树落在仓库之外（默认 D:\Trade\wt\<主题>），不会污染 git status
    3. 自动为前端复用已有 node_modules（Junction），否则新工作树跑不起来

.NOTES
  兼容 Windows PowerShell 5.1 与 PowerShell 7+（文件以 UTF-8 BOM 保存）。
  这里刻意不使用 $ErrorActionPreference='Stop'：git 会把正常进度写到 stderr，
  'Stop' 会将其误判为致命错误并中断脚本；改为逐步显式检查 $LASTEXITCODE。

.EXAMPLE
  .\scripts\wt-new.ps1 -Topic crm-portal
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Topic,
  [string]$Repo = 'D:\Trade\AutoForceAI',
  [string]$WorktreeRoot = 'D:\Trade\wt',
  [string]$DepSource = 'D:\Trade\afai-release\apps\web-console\node_modules'
)

$ErrorActionPreference = 'Continue'

$branch = "task/$Topic"
$path = Join-Path $WorktreeRoot $Topic

if (Test-Path $path) {
  throw "目录已存在：$path`n如果那是上次遗留的任务工作树，先跑： .\scripts\wt-done.ps1 -Topic $Topic"
}

Write-Host '[1/3] 同步 origin ...'
git -C $Repo fetch origin --prune
if ($LASTEXITCODE -ne 0) { throw 'git fetch 失败，请检查网络/凭据后重试。' }

if (-not (Test-Path $WorktreeRoot)) {
  New-Item -ItemType Directory -Path $WorktreeRoot -Force | Out-Null
}

Write-Host "[2/3] 从 origin/main 创建分支 $branch 与工作树 $path ..."
git -C $Repo worktree add -b $branch $path origin/main
if ($LASTEXITCODE -ne 0) { throw "git worktree add 失败（分支 $branch 或目录可能已被占用）。" }

# 前端依赖复用：新工作树没有 node_modules，用 Junction 指向已有依赖
$webConsole = Join-Path $path 'apps\web-console'
$nm = Join-Path $webConsole 'node_modules'
if ((Test-Path $webConsole) -and -not (Test-Path $nm) -and (Test-Path $DepSource)) {
  Write-Host '[3/3] 复用前端依赖（Junction）...'
  New-Item -ItemType Junction -Path $nm -Target $DepSource | Out-Null
} else {
  Write-Host '[3/3] 跳过依赖复用（目标已存在或依赖源缺失）'
}

Write-Host ''
Write-Host "OK 工作树就绪：$path"
Write-Host "   分支：$branch（基于最新 origin/main）"
Write-Host ''
Write-Host '   下一步：前后端改动都提交到这个分支，一个 PR 一起合入 main。'
Write-Host "   完成后：.\scripts\wt-done.ps1 -Topic $Topic -DeleteBranch"
