#!/bin/zsh
# 逐帧渲染工程的 macOS 装配（幂等，可重复跑）
# 用法：把本文件放到工程根目录，chmod +x setup-macos.sh && ./setup-macos.sh
set -euo pipefail
cd "$(dirname "$0")"

need() { command -v "$1" >/dev/null 2>&1 || { echo "缺少 $1，请先安装" >&2; exit 1; }; }
need node; need npm; need ffmpeg; need ffprobe

echo "== ffmpeg 编码器自检 =="
ffmpeg -hide_banner -encoders 2>/dev/null | grep -E "libx264|libx265|aac " | head -5

echo "== Python 3.12 venv =="
command -v uv >/dev/null 2>&1 || brew install uv
[[ -d .venv ]] || uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -q pillow numpy
.venv/bin/python -V

echo "== Playwright =="
npm install --no-audit --no-fund
npx playwright install chromium

echo "== 字体（Windows 专有字体必须换；示例用 OFL 的 JetBrains Mono）=="
[[ -f "$HOME/Library/Fonts/JetBrainsMono-Regular.ttf" ]] || \
  HOMEBREW_NO_AUTO_UPDATE=1 brew install --cask font-jetbrains-mono

cat > pv-env.sh <<'ENV'
set -euo pipefail
FONT_DIR="$HOME/Library/Fonts"
ASSET_ROOT="/System/Library/AssetsV2/com_apple_MobileAsset_Font8"
export PV_F_MONO="$(find "$FONT_DIR" -maxdepth 1 -type f -name 'JetBrainsMono-Regular.ttf' -print -quit)"
export PV_F_MONO_B="$(find "$FONT_DIR" -maxdepth 1 -type f -name 'JetBrainsMono-Bold.ttf' -print -quit)"
export PV_F_CJK="$(find "$ASSET_ROOT" -path '*/AssetData/PingFang.ttc' -print -quit)"
export PV_F_SYM="/System/Library/Fonts/Supplemental/STIXTwoMath.otf"
test -f "$PV_F_MONO"; test -f "$PV_F_MONO_B"; test -f "$PV_F_CJK"; test -f "$PV_F_SYM"
ENV
source ./pv-env.sh
echo "   mono=$PV_F_MONO"
echo "   cjk =$PV_F_CJK"
echo
echo "完成。下一步：把素材放进 input/，然后 ./run.sh"
