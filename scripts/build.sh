#!/usr/bin/env bash
# 构建静态站点到 dist/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"

rm -rf "$DIST"
mkdir -p "$DIST"
cp "$ROOT/index.html" "$DIST/index.html"

echo "构建完成: $DIST"
