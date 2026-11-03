# 本地预览：http://localhost:8080
param([int]$Port = 8080)

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "预览地址: http://localhost:$Port" -ForegroundColor Green
python -m http.server $Port
