# 一键部署 + 触发 —— 登录完成后直接跑这个
# 用法: pwsh -File deploy.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[1/6] 检查登录状态..." -ForegroundColor Cyan
& gh auth status 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) {
    Write-Host "  还没登录。先运行: gh auth login --web --scopes repo,workflow" -ForegroundColor Yellow
    Write-Host "  然后把浏览器里给的 8 位码输入 github.com/login/device" -ForegroundColor Yellow
    exit 1
}

Write-Host "[2/6] 初始化 git 仓库..." -ForegroundColor Cyan
if (-not (Test-Path ".git")) { & git init -q }
& git add -A
& git -c user.email="bot@local" -c user.name="bot" commit -q -m "init" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "  (无新变更)" -ForegroundColor DarkGray }

Write-Host "[3/6] 创建公开仓库并推送..." -ForegroundColor Cyan
$repoName = "gh-flood"
& gh repo create $repoName --public --source . --push --remote origin 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) {
    Write-Host "  仓库可能已存在，尝试直接推送..." -ForegroundColor Yellow
    & git branch -M main
    & gh repo view $repoName --json name 2>$null | Out-Null
    & git push -u origin main 2>&1 | Out-Host
}

Write-Host "[4/6] 确认 Actions 已启用..." -ForegroundColor Cyan
& gh api "repos/$((& gh api user --jq .login))/gh-flood/actions/permissions" 2>&1 | Out-Host

Write-Host "[5/6] 触发 workflow (20 job, 每 job 100 线程, 混合接口)..." -ForegroundColor Cyan
& gh workflow run run.yml -f conc=100 -f dur=1500 -f mode=mix 2>&1 | Out-Host
Start-Sleep -Seconds 8

Write-Host "[6/6] 运行状态:" -ForegroundColor Cyan
& gh run list --limit 3 2>&1 | Out-Host

Write-Host ""
Write-Host "后续查看实时日志:" -ForegroundColor Green
Write-Host "  gh run watch" -ForegroundColor Green
Write-Host "或在浏览器打开:" -ForegroundColor Green
Write-Host ("  https://github.com/" + (& gh api user --jq .login) + "/gh-flood/actions") -ForegroundColor Green
