#!/usr/bin/env python3
"""
notion-md-sync CLI：一条命令把本地 Markdown 目录同步到 Notion，保持层级，增量 + 并发。
用法:
  notion-md-sync ./markdown
  notion-md-sync ./knowledge --force --workers 16
"""
from __future__ import annotations

import argparse
import os
import sys

from notion_md_sync import __version__
from notion_md_sync.self_manage import uninstall_self


def _env(key: str, default: str = "") -> str:
    v = os.environ.get(key, default).strip()
    if key == "ROOT_PAGE_ID":
        return v
    return v


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="本地 Markdown 目录 → Notion，保持目录层级，支持增量同步与并发上传。"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    sync_parser = subparsers.add_parser(
        "sync",
        help="同步 Markdown 目录到 Notion",
    )
    sync_parser.add_argument(
        "dir",
        nargs="?",
        default=os.environ.get("MARKDOWN_DIR", "./markdown"),
        help="要同步的 Markdown 根目录（默认: ./markdown 或环境变量 MARKDOWN_DIR）",
    )
    sync_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="强制重新上传所有文件（忽略 .notionsync 中的 hash）",
    )
    sync_parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=8,
        metavar="N",
        help="并发上传线程数（默认: 8）",
    )
    sync_parser.add_argument(
        "--token",
        "-t",
        default=os.environ.get("NOTION_TOKEN", ""),
        help="Notion Integration Token（或环境变量 NOTION_TOKEN）",
    )
    sync_parser.add_argument(
        "--page-id",
        "-p",
        default=os.environ.get("ROOT_PAGE_ID", ""),
        help="Notion 父页面 ID（或环境变量 ROOT_PAGE_ID）",
    )

    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="卸载当前机器上的 notion-md-sync",
    )
    uninstall_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="跳过二次确认，直接执行卸载",
    )

    return parser


def _normalize_argv(argv: list[str]) -> list[str]:
    if not argv:
        return ["sync"]
    if argv[0] in {"sync", "uninstall", "--help", "-h", "--version"}:
        return argv
    if argv[0].startswith("-"):
        return ["sync", *argv]
    return ["sync", *argv]


def _run_sync(args: argparse.Namespace) -> int:
    if not args.token:
        print("请设置 NOTION_TOKEN 或使用 --token", file=sys.stderr)
        return 1
    if not args.page_id:
        print("请设置 ROOT_PAGE_ID 或使用 --page-id", file=sys.stderr)
        return 1

    from notion_md_sync.sync import run_sync

    run_sync(
        args.dir,
        args.token,
        args.page_id,
        force=args.force,
        max_workers=args.workers,
    )
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args(_normalize_argv(sys.argv[1:]))

    if args.command == "uninstall":
        sys.exit(uninstall_self(confirm=not args.yes))

    sys.exit(_run_sync(args))


if __name__ == "__main__":
    main()
