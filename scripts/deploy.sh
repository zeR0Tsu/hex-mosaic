#!/usr/bin/env bash
# 提交并推送到 main，触发 GitHub Pages 部署
# 用法: bash scripts/deploy.sh "提交说明"
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MSG="${1:-deploy: 更新站点}"

cd "$ROOT"
bash scripts/build.sh

git add -A
if git diff --cached --quiet; then
  echo "没有需要提交的改动"
else
  git commit -m "$MSG"
fi

git push origin main

REMOTE="$(git remote get-url origin)"
SLUG="$(echo "$REMOTE" | sed -E 's#.*[:/]([^/]+/[^/]+?)(\.git)?$#\1#')"
USER="${SLUG%%/*}"
REPO="${SLUG##*/}"

echo
echo "已推送。Pages 地址: https://${USER,,}.github.io/${REPO}/"
echo "部署进度: https://github.com/${SLUG}/actions"
