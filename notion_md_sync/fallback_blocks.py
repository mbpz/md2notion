"""Notion 不支持 Markdown API 时，将 Markdown 以段落块形式追加。"""
from __future__ import annotations

import requests

NOTION_API_BASE = "https://api.notion.com/v1"
CHUNK_SIZE = 1800
MAX_BLOCKS_PER_REQUEST = 100  # Notion API 单次最多 100 个 block


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }


def append_markdown_as_blocks(token: str, page_id: str, text: str) -> bool:
    """将整段文本按 CHUNK_SIZE 拆成 paragraph 块追加到页面（每批最多 100 块）。"""
    page_id = page_id.replace("-", "")
    chunks = [text[i : i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
    if not chunks:
        return True
    for i in range(0, len(chunks), MAX_BLOCKS_PER_REQUEST):
        batch = chunks[i : i + MAX_BLOCKS_PER_REQUEST]
        blocks = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": ch}}]
                },
            }
            for ch in batch
        ]
        r = requests.patch(
            f"{NOTION_API_BASE}/blocks/{page_id}/children",
            headers=_headers(token),
            json={"children": blocks},
            timeout=60,
        )
        if r.status_code != 200:
            return False
    return True
