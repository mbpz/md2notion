#!/usr/bin/env bash
# 兼容旧用法：转调 CLI 内置卸载命令。
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"

if command -v notion-md-sync >/dev/null 2>&1; then
  exec notion-md-sync uninstall -y
fi

echo "未找到 notion-md-sync 命令，尝试直接卸载 Python 包..."
python3 -m pip uninstall -y notion-md-sync
