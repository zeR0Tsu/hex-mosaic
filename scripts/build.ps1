# 构建静态站点到 dist/
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Dist = Join-Path $Root 'dist'

if (Test-Path $Dist) { Remove-Item $Dist -Recurse -Force }
New-Item -ItemType Directory -Path $Dist -Force | Out-Null

Copy-Item (Join-Path $Root 'index.html') (Join-Path $Dist 'index.html')

Write-Host "构建完成: $Dist" -ForegroundColor Green
