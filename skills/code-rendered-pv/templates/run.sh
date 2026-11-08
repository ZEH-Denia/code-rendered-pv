#!/bin/zsh
# 一键出片（按工程的 build.py 步骤名传参）
#   ./run.sh            → all
#   ./run.sh check      → 只做环境检查
#   ./run.sh pages      → 只重做网页截图（改了 HTML 里的文字后必须跑这个）
#   ./run.sh render     → 只重渲染（改了 PIL 侧的内容后够了）
#   ./run.sh all --4k   → 另出 4K
set -euo pipefail
cd "$(dirname "$0")"
[[ -f pv-env.sh ]] && source ./pv-env.sh
step="${1:-all}"; shift || true
echo "== step: $step =="
exec .venv/bin/python build.py "$step" "$@"
