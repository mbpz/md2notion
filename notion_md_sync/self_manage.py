from __future__ import annotations

import os
import shutil
import subprocess
import sys


PACKAGE_NAME = "notion-md-sync"


def _run_command(cmd: list[str]) -> int:
    try:
        return subprocess.run(cmd, check=False).returncode
    except FileNotFoundError:
        return 127


def _package_installed(python_cmd: str) -> bool:
    return _run_command([python_cmd, "-m", "pip", "show", PACKAGE_NAME]) == 0


def uninstall_self(*, confirm: bool = True) -> int:
    if confirm:
        answer = input("确认卸载 notion-md-sync? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("已取消卸载。")
            return 1

    removed = False
    pipx = shutil.which("pipx")
    if pipx:
        rc = _run_command([pipx, "uninstall", PACKAGE_NAME])
        if rc == 0:
            print("已从 pipx 卸载 notion-md-sync。")
            removed = True

    python_cmd = sys.executable or shutil.which("python3") or "python3"
    if _package_installed(python_cmd) and _run_command(
        [python_cmd, "-m", "pip", "uninstall", "-y", PACKAGE_NAME]
    ) == 0:
        print("已从当前 Python 环境卸载 notion-md-sync。")
        removed = True

    if not removed:
        print("未检测到可卸载的 notion-md-sync。")
        return 1

    local_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
    if local_bin not in os.environ.get("PATH", ""):
        print('提示: 若你之前手动加过 PATH，可保留 `export PATH="$HOME/.local/bin:$PATH"`。')
    print("卸载完成。")
    return 0
