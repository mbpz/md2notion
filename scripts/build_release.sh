#!/usr/bin/env bash
# 构建可分发产物，并输出可直接复制执行的安装命令。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"

cd "$ROOT_DIR"

if ! python3 -c "from build.__main__ import main" >/dev/null 2>&1; then
  echo "缺少打包依赖 build，请先执行: python3 -m pip install --user build wheel" >&2
  exit 1
fi

if ! python3 -c "import wheel" >/dev/null 2>&1; then
  echo "缺少打包依赖 wheel，请先执行: python3 -m pip install --user build wheel" >&2
  exit 1
fi

python3 -m build --no-isolation

WHEEL_PATH="$(find "$DIST_DIR" -maxdepth 1 -type f -name '*.whl' | sort | tail -n 1)"
SDIST_PATH="$(find "$DIST_DIR" -maxdepth 1 -type f -name '*.tar.gz' | sort | tail -n 1)"

echo ""
echo "构建完成:"
echo "  wheel: ${WHEEL_PATH}"
echo "  sdist: ${SDIST_PATH}"
echo ""
echo "本地安装命令:"
echo "  bash scripts/install.sh ${WHEEL_PATH}"
echo ""
echo "远程安装示例:"
echo "  curl -fsSL <install.sh-url> | bash -s -- <wheel-url>"
