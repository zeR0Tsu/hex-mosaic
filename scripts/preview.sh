#!/usr/bin/env bash
# 本地预览：http://localhost:8080
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-8080}"

cd "$ROOT"
echo "预览地址: http://localhost:$PORT"
python3 -m http.server "$PORT"
