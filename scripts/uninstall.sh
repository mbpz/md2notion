#!/usr/bin/env bash
# 卸载通过 install.sh / pipx / pip --user 安装的 notion-md-sync
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"

removed=0

if command -v pipx >/dev/null 2>&1; then
  set +e
  pipx uninstall notion-md-sync >/dev/null 2>&1
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    echo "已从 pipx 卸载 notion-md-sync。"
    removed=1
  fi
fi

if python3 -m pip show notion-md-sync >/dev/null 2>&1; then
  python3 -m pip uninstall -y notion-md-sync
  echo "已从当前 Python 环境卸载 notion-md-sync。"
  removed=1
fi

if [[ "$removed" -eq 0 ]]; then
  echo "未检测到已安装的 notion-md-sync（pipx 与 pip 均未卸载到该包）。"
  exit 1
fi

echo "卸载完成。"
