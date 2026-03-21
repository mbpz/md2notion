#!/usr/bin/env bash
# 一键安装 notion-md-sync：优先安装打包产物（wheel / sdist），其次安装当前目录，最后回退到 git。
set -euo pipefail

REPO_URL="${NOTION_MD_SYNC_REPO:-https://github.com/mbpz/md2notion.git}"
REF="${NOTION_MD_SYNC_REF:-master}"
GIT_SPEC="git+${REPO_URL}@${REF}"
PACKAGE_SPEC="${1:-${NOTION_MD_SYNC_PACKAGE_SPEC:-}}"

export PATH="${HOME}/.local/bin:${PATH}"

die() {
  echo "错误: $*" >&2
  exit 1
}

# 从仓库内执行 bash scripts/install.sh 时，改为安装当前目录（无需联网拉 git）
discover_local_repo_root() {
  local src="${BASH_SOURCE[0]:-}"
  [[ -n "$src" && "$src" != "-" && -f "$src" ]] || return 1
  local sd root
  sd="$(cd "$(dirname "$src")" && pwd)"
  root="$(cd "$sd/.." && pwd)"
  [[ -f "$root/pyproject.toml" ]] || return 1
  printf '%s' "$root"
}

need_python() {
  command -v python3 >/dev/null 2>&1 || die "未找到 python3，请先安装 Python 3.9+（https://www.python.org/downloads/）"
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' \
    || die "需要 Python 3.9 或更高版本"
}

ensure_pipx() {
  command -v pipx >/dev/null 2>&1 && return 0
  echo "正在安装 pipx（用于独立的命令行工具环境）..."
  python3 -m pip install --user -q pipx
  python3 -m pipx ensurepath >/dev/null 2>&1 || true
}

install_with_pipx() {
  local spec=$1
  ensure_pipx
  command -v pipx >/dev/null 2>&1 || return 1
  # --force：已安装时覆盖升级，避免 upgrade 子命令在部分环境下异常
  pipx install --force "$spec"
}

install_with_pip_user() {
  local spec=$1
  echo "使用 pip --user 安装（可执行文件一般在 ~/.local/bin，请确保该目录在 PATH 中）..."
  python3 -m pip install --user -U "$spec"
}

main() {
  need_python
  local install_spec=$GIT_SPEC
  if local_root=$(discover_local_repo_root); then
    install_spec=$local_root
    echo "检测到本地仓库，从目录安装: $install_spec"
  fi
  if [[ -n "$PACKAGE_SPEC" ]]; then
    install_spec=$PACKAGE_SPEC
    echo "使用打包产物安装: $install_spec"
  fi

  if install_with_pipx "$install_spec"; then
    echo ""
    echo "安装完成。请先配置 NOTION_TOKEN、ROOT_PAGE_ID，然后运行:"
    echo "  notion-md-sync ./markdown"
    echo "卸载命令:"
    echo "  notion-md-sync uninstall"
    echo ""
    echo "若提示找不到命令，请重新打开终端，或执行: export PATH=\"\$HOME/.local/bin:\$PATH\""
    exit 0
  fi
  echo "pipx 不可用，改用 pip --user..."
  install_with_pip_user "$install_spec"
  echo ""
  echo "安装完成。请先配置 NOTION_TOKEN、ROOT_PAGE_ID，然后运行:"
  echo "  notion-md-sync ./markdown"
  echo "卸载命令:"
  echo "  notion-md-sync uninstall"
}

main "$@"
