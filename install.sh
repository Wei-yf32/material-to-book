#!/usr/bin/env bash
# material-to-book 安装脚本（macOS / Linux）
#
# 用法：
#   ./install.sh              # 装依赖 + 复制到 ~/.dsh/skills + 体检
#   ./install.sh --check      # 只体检
#   ./install.sh --skip-deps  # 只复制
#   PYTHON=python3.12 ./install.sh   # 指定解释器

set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="${DEST:-$HOME/.dsh/skills/material-to-book}"
PY="${PYTHON:-$(command -v python3 || command -v python)}"
SKIP_DEPS=0
CHECK=0

for a in "$@"; do
  case "$a" in
    --check) CHECK=1 ;;
    --skip-deps) SKIP_DEPS=1 ;;
    *) echo "未知参数：$a"; exit 2 ;;
  esac
done

if [ -z "$PY" ]; then
  echo "找不到 python3。装一个 3.10+ 的版本，或用 PYTHON=/path/to/python ./install.sh"
  exit 1
fi

echo "material-to-book 安装"
echo "源目录：$HERE"
echo "解释器：$PY ($("$PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])'))"

if [ "$CHECK" = "1" ]; then
  exec "$PY" "$HERE/scripts/doctor.py"
fi

if [ "$SKIP_DEPS" = "0" ] && [ -f "$HERE/requirements.txt" ]; then
  echo "安装依赖…"
  "$PY" -m pip install -r "$HERE/requirements.txt" || {
    echo "pip 安装失败：这个解释器可能没有 pip，换一个完整版 Python 再试。"
    exit 1
  }
fi

mkdir -p "$(dirname "$DEST")"
if [ "$(cd "$HERE" && pwd)" = "$(cd "$DEST" 2>/dev/null && pwd)" ]; then
  echo "已在安装位置，跳过复制。"
else
  if [ -d "$DEST" ]; then
    BAK="$DEST.bak-$(date +%Y%m%d%H%M%S)"
    echo "已有旧版本，备份到 $BAK"
    mv "$DEST" "$BAK"
  fi
  echo "复制到 $DEST"
  cp -R "$HERE" "$DEST"
  rm -rf "$DEST/.git" "$DEST/__pycache__" "$DEST/scripts/__pycache__"
fi

echo "体检…"
"$PY" "$DEST/scripts/doctor.py"
code=$?
echo ""
if [ "$code" = "0" ]; then
  echo "装好了。新开一个 DSH 会话，说「把这个文件夹的资料整理成一份讲义」即可。"
else
  echo "装好了但缺件，按上面的提示补齐后重跑：./install.sh --check"
fi
exit "$code"
