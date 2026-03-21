"""
增强版同步：Notion Markdown API、增量（.notionsync）、并发上传。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any

import requests

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"  # 若使用 Markdown API 需 2026-03-11，当前用 block 兼容性更好


def _norm_id(pid: str) -> str:
    """规范为无连字符的 32 位 hex，供内部比较用。"""
    return (pid or "").replace("-", "").strip()


def _to_uuid(pid: str) -> str:
    """转为 Notion JSON 里 parent.page_id 等字段要求的 UUID（8-4-4-4-12）。无连字符的 32 位 hex 会补全格式。"""
    raw = (pid or "").strip()
    # 只保留 hex 字符，取最后 32 位（兼容 URL 里多带了前缀的情况）
    hex_part = "".join(c for c in raw if c in "0123456789abcdefABCDef").lower()
    if len(hex_part) >= 32:
        hex_part = hex_part[-32:]
    if len(hex_part) != 32:
        return raw  # 无法用 32 位 hex 构造 UUID，原样传出
    return f"{hex_part[0:8]}-{hex_part[8:12]}-{hex_part[12:16]}-{hex_part[16:20]}-{hex_part[20:32]}"


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def create_page_with_markdown(
    token: str,
    parent_id: str,
    title: str,
    markdown: str,
) -> str | None:
    """创建子页面并写入 Markdown。优先用 Markdown API（若可用），否则用 block API。"""
    parent_uuid = _to_uuid(parent_id)
    payload: dict[str, Any] = {
        "parent": {"page_id": parent_uuid},
        "properties": {
            "title": {
                "title": [{"text": {"content": (title or "Untitled")[:2000]}}]
            }
        },
    }
    # Notion 新版本支持创建时带 markdown；若 API 不支持则先建页再 append blocks
    # 这里先用 block 方式保证兼容：创建空页再 PATCH markdown（若版本>=2026 可改用 markdown 参数）
    r = requests.post(
        f"{NOTION_API_BASE}/pages",
        headers=_headers(token),
        json=payload,
        timeout=30,
    )
    if r.status_code != 200:
        print(f"[ERROR] create page: {r.status_code} {r.text}", file=sys.stderr)
        return None
    page_id = r.json().get("id")
    if not page_id or not markdown.strip():
        return page_id
    # 尝试 PATCH markdown（Notion 2026-03-11+）
    patch_r = requests.patch(
        f"{NOTION_API_BASE}/pages/{page_id}/markdown",
        headers={**_headers(token), "Notion-Version": "2026-03-11"},
        json={
            "type": "replace_content",
            "replace_content": {"new_str": markdown},
        },
        timeout=60,
    )
    if patch_r.status_code == 200:
        return page_id
    # 回退：用 block API 追加段落块
    from notion_md_sync.fallback_blocks import append_markdown_as_blocks
    append_markdown_as_blocks(token, page_id, markdown)
    return page_id


def create_folder_page(token: str, parent_id: str, title: str) -> str | None:
    """只创建带标题的子页面（文件夹）。"""
    parent_uuid = _to_uuid(parent_id)
    r = requests.post(
        f"{NOTION_API_BASE}/pages",
        headers=_headers(token),
        json={
            "parent": {"page_id": parent_uuid},
            "properties": {
                "title": {
                    "title": [{"text": {"content": (title or "Untitled")[:2000]}}]
                }
            },
        },
        timeout=30,
    )
    if r.status_code != 200:
        print(f"[ERROR] create folder page: {r.status_code} {r.text}", file=sys.stderr)
        return None
    return r.json().get("id")


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_sync_state(sync_file: str) -> dict[str, Any]:
    if not os.path.isfile(sync_file):
        return {"folders": {}, "files": {}, "root_page_id": ""}
    try:
        with open(sync_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"folders": {}, "files": {}, "root_page_id": ""}


def save_sync_state(sync_file: str, state: dict[str, Any]) -> None:
    with open(sync_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def ensure_folder_page(
    token: str,
    state: dict[str, Any],
    root_id: str,
    rel_dir: str,
    base_dir: str,
) -> str | None:
    """返回 rel_dir 对应的 Notion page_id；不存在则创建并写入 state。"""
    if rel_dir in state.get("folders", {}):
        return state["folders"][rel_dir]
    parent_id = root_id
    if rel_dir:
        parts = rel_dir.split(os.sep)
        for i in range(len(parts)):
            sub = os.sep.join(parts[: i + 1])
            if sub not in state.get("folders", {}):
                name = parts[i]
                page_id = create_folder_page(token, parent_id, name)
                if not page_id:
                    return None
                state.setdefault("folders", {})[sub] = page_id
            parent_id = state["folders"][sub]
    return parent_id


def sync_one_file(
    token: str,
    base_dir: str,
    rel_path: str,
    parent_page_id: str,
    state: dict[str, Any],
    state_lock: Lock,
    sync_file: str,
    force: bool,
) -> bool:
    full_path = os.path.join(base_dir, rel_path)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"[ERROR] read {rel_path}: {e}", file=sys.stderr)
        return False
    title = Path(rel_path).stem
    h = content_hash(content)
    with state_lock:
        files = state.setdefault("files", {})
        if not force and rel_path in files and files[rel_path].get("hash") == h:
            return True  # 已是最新
        page_id = files.get(rel_path, {}).get("page_id") if rel_path in files else None
    if page_id and not force:
        patch_r = requests.patch(
            f"{NOTION_API_BASE}/pages/{page_id}/markdown",
            headers={**_headers(token), "Notion-Version": "2026-03-11"},
            json={
                "type": "replace_content",
                "replace_content": {"new_str": content},
            },
            timeout=60,
        )
        if patch_r.status_code == 200:
            with state_lock:
                state.setdefault("files", {})[rel_path] = {"page_id": page_id, "hash": h}
                save_sync_state(sync_file, state)
            return True
        from notion_md_sync.fallback_blocks import append_markdown_as_blocks
        if append_markdown_as_blocks(token, page_id, content):
            with state_lock:
                state.setdefault("files", {})[rel_path] = {"page_id": page_id, "hash": h}
                save_sync_state(sync_file, state)
            return True
    new_id = create_page_with_markdown(token, parent_page_id, title, content)
    if not new_id:
        return False
    with state_lock:
        state.setdefault("files", {})[rel_path] = {"page_id": new_id, "hash": h}
        save_sync_state(sync_file, state)
    return True


def run_sync(
    base_dir: str,
    token: str,
    root_page_id: str,
    *,
    force: bool = False,
    max_workers: int = 8,
    sync_file: str | None = None,
) -> None:
    base_dir = os.path.abspath(base_dir)
    if not os.path.isdir(base_dir):
        print(f"目录不存在: {base_dir}", file=sys.stderr)
        return
    if sync_file is None:
        sync_file = os.path.join(base_dir, ".notionsync")
    root_page_id = _norm_id(root_page_id)
    state = load_sync_state(sync_file)
    state["root_page_id"] = root_page_id

    # 收集所有目录和文件
    dirs: list[str] = []
    files_list: list[tuple[str, str]] = []  # (rel_path, parent_dir_rel)
    for root, dirnames, filenames in os.walk(base_dir):
        rel_root = os.path.relpath(root, base_dir)
        if rel_root == ".":
            rel_root = ""
        # 跳过隐藏目录（如 .git、.notionsync 所在目录不算作内容）
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        if rel_root and not rel_root.startswith("."):
            dirs.append(rel_root)
        for name in filenames:
            if not name.endswith(".md") or name.startswith("."):
                continue
            rel_path = os.path.join(rel_root, name) if rel_root else name
            if rel_path.startswith("."):
                continue
            parent_rel = os.path.dirname(rel_path)
            files_list.append((rel_path, parent_rel))

    # 按层级创建/解析文件夹
    dirs.sort(key=lambda d: (d.count(os.sep), d))
    for rel_dir in dirs:
        ensure_folder_page(token, state, root_page_id, rel_dir, base_dir)
    save_sync_state(sync_file, state)

    # 每个文件的父 page_id
    def parent_id_for(rel_path: str, parent_rel: str) -> str | None:
        if not parent_rel:
            return root_page_id
        return state.get("folders", {}).get(parent_rel)

    tasks = [
        (rel_path, parent_id_for(rel_path, parent_rel))
        for rel_path, parent_rel in files_list
    ]
    tasks = [(r, p) for r, p in tasks if p is not None]

    state_lock = Lock()
    done = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
            ex.submit(
                sync_one_file,
                token,
                base_dir,
                rel_path,
                parent_id,
                state,
                state_lock,
                sync_file,
                force,
            ): (rel_path, parent_id)
            for rel_path, parent_id in tasks
        }
        for fut in as_completed(futures):
            rel_path, _ = futures[fut]
            try:
                if fut.result():
                    done += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"[ERROR] {rel_path}: {e}", file=sys.stderr)
                failed += 1
    print(f"Sync finished: {done} ok, {failed} failed.")
