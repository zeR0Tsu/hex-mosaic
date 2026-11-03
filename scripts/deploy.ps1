param([string]$Message = "deploy: 更新站点")

# 提交并推送到 main，触发 GitHub Pages 部署
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& (Join-Path $PSScriptRoot 'build.ps1')

git add -A
$staged = git diff --cached --name-only
if (-not $staged) {
    Write-Host "没有需要提交的改动" -ForegroundColor Yellow
} else {
    git commit -m $Message
}

git push origin main

$remote = (git remote get-url origin).Trim()
$slug = $remote -replace '.*[:/]([^/]+/[^/]+?)(\.git)?$', '$1'
$user, $repo = $slug.Split('/')

Write-Host ""
Write-Host "已推送。Pages 地址: https://$($user.ToLower()).github.io/$repo/" -ForegroundColor Green
Write-Host "部署进度: https://github.com/$slug/actions"
