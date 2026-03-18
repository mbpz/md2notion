#!/usr/bin/env python3
"""
基础版：本地多层目录 Markdown → Notion，保持目录结构。
使用前：pip install notion-client tqdm，配置 NOTION_TOKEN 和 ROOT_PAGE_ID。
"""
import os
from notion_client import Client
from tqdm import tqdm

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "your_notion_token")
ROOT_PAGE_ID = os.environ.get("ROOT_PAGE_ID", "your_root_page_id").replace("-", "")

notion = Client(auth=NOTION_TOKEN)


def create_page(title: str, parent_id: str) -> str:
    page = notion.pages.create(
        parent={"page_id": parent_id},
        properties={
            "title": {
                "title": [
                    {"text": {"content": title[:2000]}}
                ]
            }
        },
    )
    return page["id"]


def append_text_blocks(page_id: str, text: str) -> None:
    """Notion 单段 rich_text content 有长度限制，按 1800 字符分块。"""
    chunk_size = 1800
    chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
    blocks = []
    for chunk in chunks:
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": chunk}}
                ]
            },
        })
    notion.blocks.children.append(page_id, children=blocks)


def upload_md(file_path: str, parent_page: str) -> None:
    name = os.path.basename(file_path).replace(".md", "")
    page_id = create_page(name, parent_page)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    append_text_blocks(page_id, content)


def walk_dir(base_dir: str, parent_page: str) -> None:
    items = sorted(os.listdir(base_dir))
    for item in tqdm(items, desc=os.path.basename(base_dir) or "root"):
        path = os.path.join(base_dir, item)
        if os.path.isdir(path):
            folder_page = create_page(item, parent_page)
            walk_dir(path, folder_page)
        elif item.endswith(".md"):
            upload_md(path, parent_page)


def main() -> None:
    base_dir = os.environ.get("MARKDOWN_DIR", "./markdown")
    if not os.path.isdir(base_dir):
        print(f"目录不存在: {base_dir}")
        return
    walk_dir(base_dir, ROOT_PAGE_ID)
    print("Import finished.")


if __name__ == "__main__":
    main()
