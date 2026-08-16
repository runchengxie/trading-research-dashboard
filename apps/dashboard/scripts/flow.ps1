# scripts/flow.ps1
# 独立 worktree 开发流程的辅助脚本。
#
# 用法:
#   ./scripts/flow.ps1 start <任务名>    基于 origin/main 创建独立 worktree 与 feat 分支
#   ./scripts/flow.ps1 finish <worktree目录>  合并后清理 worktree，删除本地与远端分支

param(
  [Parameter(Mandatory = $true, Position = 0)]
  [ValidateSet("start", "finish")]
  [string]$Action,

  [Parameter(Mandatory = $true, Position = 1)]
  [string]$Name
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

function Get-RepoName {
  $url = git remote get-url origin
  if ($url) {
    return ($url -split "/")[-1] -replace "\.git$", ""
  }
  return Split-Path -Leaf (Get-Location)
}

$repo = Get-RepoName

if ($Action -eq "start") {
  $branch = "feat/$Name"
  $dir = Join-Path (Split-Path -Parent (Get-Location)) "$repo-$Name"

  git fetch origin
  $dirty = @(git status --porcelain)
  if ($dirty.Count -gt 0) {
    Write-Error "当前工作区有未提交改动，请先提交或清理再创建 worktree。"
  }
  if (Test-Path -LiteralPath $dir) {
    Write-Error "目标目录已存在: $dir"
  }

  git worktree add "$dir" -b $branch origin/main

  Write-Host ""
  Write-Host "worktree: $dir"
  Write-Host "分支:     $branch"
  Write-Host "在 $dir 内修改并提交后，执行以下命令推送并开 PR:"
  Write-Host "  git push -u origin $branch"
  Write-Host "  gh pr create --base main --head $branch --title <标题> --body <说明>"
}
else {
  $dir = $Name
  if (-not (Test-Path -LiteralPath $dir)) {
    Write-Error "目录不存在: $dir"
  }
  $branch = git -C $dir symbolic-ref --short HEAD

  git -C $dir status
  $unmerged = @(git log origin/main..$branch --oneline)
  if ($unmerged.Count -gt 0) {
    Write-Warning "以下提交尚未合并到 main:"
    $unmerged | ForEach-Object { Write-Host "  $_" }
  }

  git worktree remove --force $dir
  git ls-remote --exit-code origin $branch *> $null
  if ($LASTEXITCODE -eq 0) {
    git push origin --delete $branch
  }
  git branch -d $branch

  Write-Host "已清理 worktree 与分支 $branch"
}
