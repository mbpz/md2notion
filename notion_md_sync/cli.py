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


def _env(key: str, default: str = "") -> str:
    v = os.environ.get(key, default).strip()
    if key == "ROOT_PAGE_ID":
        return v
    return v


def main() -> None:
    parser = argparse.ArgumentParser(
        description="本地 Markdown 目录 → Notion，保持目录层级，支持增量同步与并发上传。"
    )
    parser.add_argument(
        "dir",
        nargs="?",
        default=os.environ.get("MARKDOWN_DIR", "./markdown"),
        help="要同步的 Markdown 根目录（默认: ./markdown 或环境变量 MARKDOWN_DIR）",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="强制重新上传所有文件（忽略 .notionsync 中的 hash）",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=8,
        metavar="N",
        help="并发上传线程数（默认: 8）",
    )
    parser.add_argument(
        "--token",
        "-t",
        default=os.environ.get("NOTION_TOKEN", ""),
        help="Notion Integration Token（或环境变量 NOTION_TOKEN）",
    )
    parser.add_argument(
        "--page-id",
        "-p",
        default=os.environ.get("ROOT_PAGE_ID", ""),
        help="Notion 父页面 ID（或环境变量 ROOT_PAGE_ID）",
    )
    args = parser.parse_args()

    if not args.token:
        print("请设置 NOTION_TOKEN 或使用 --token", file=sys.stderr)
        sys.exit(1)
    if not args.page_id:
        print("请设置 ROOT_PAGE_ID 或使用 --page-id", file=sys.stderr)
        sys.exit(1)

    from notion_md_sync.sync import run_sync

    run_sync(
        args.dir,
        args.token,
        args.page_id,
        force=args.force,
        max_workers=args.workers,
    )


if __name__ == "__main__":
    main()
