# Markdown → Notion 同步工具

把本地**多层目录 Markdown** 自动导入到 Notion，并保持**目录结构 → Notion 页面层级**。

## 效果示例

本地目录：

```
knowledge/
  ai/
    agent.md
    prompt.md
  startup/
    idea.md
    growth.md
```

导入后 Notion 结构：

```
Knowledge (根页面)
   ├── ai
   │     ├── agent
   │     └── prompt
   └── startup
         ├── idea
         └── growth
```

---

## 环境要求

- Python 3.9+
- Notion Integration（见下方配置）

## 一键安装（推荐）

在 macOS / Linux 终端执行（需已安装 **Python 3.9+**；脚本会自动尝试安装 **pipx**）：

```bash
curl -fsSL https://raw.githubusercontent.com/mbpz/md2notion/master/scripts/install.sh | bash
```

安装完成后可直接使用全局命令 `notion-md-sync`（若提示找不到命令，请重新打开终端，或执行 `export PATH="$HOME/.local/bin:$PATH"`）。

**卸载：**

```bash
curl -fsSL https://raw.githubusercontent.com/mbpz/md2notion/master/scripts/uninstall.sh | bash
```

**自定义仓库或分支**（例如 fork 或固定某次发布）：

```bash
export NOTION_MD_SYNC_REPO="https://github.com/你的用户/md2notion.git"
export NOTION_MD_SYNC_REF="master"
curl -fsSL https://raw.githubusercontent.com/mbpz/md2notion/master/scripts/install.sh | bash
```

**已克隆本仓库时本地安装**（与远程安装二选一即可）：

```bash
cd md2notion
bash scripts/install.sh
```

---

## 安装依赖（手动 / 开发）

```bash
pip install -r requirements.txt
# 或安装为可执行包（获得 notion-md-sync 命令）
pip install -e .
```

---

## 一、创建 Notion Integration

1. 打开 [Notion Integrations](https://www.notion.so/my-integrations)
2. 新建 Integration，复制 **Internal Integration Token** → `NOTION_TOKEN`
3. 在 Notion 中打开要作为「根页面」的页面 → **Share** → **Invite** 你的 Integration
4. 复制该页面的 **Page ID**（URL 中 `notion.so/xxx/` 后面那串，可带或不带 `-`）→ `ROOT_PAGE_ID`

---

## 二、两种使用方式

### 方式 A：基础脚本（简单全量导入）

适合小规模、一次性导入，不关心增量与并发。

```bash
export NOTION_TOKEN="secret_xxx"
export ROOT_PAGE_ID="your-root-page-id"
# 可选：指定目录，默认 ./markdown
export MARKDOWN_DIR="./knowledge"

python import_md_to_notion.py
```

- 会递归扫描 `MARKDOWN_DIR` 下所有 `.md` 文件与子目录
- 每个目录 → Notion 子页面，每个 `.md` → 子页面并写入正文（纯段落块）

### 方式 B：增强 CLI（推荐：增量 + 并发 + Markdown 解析）

适合经常更新、文件较多的知识库。

```bash
# 一条命令同步（使用环境变量 NOTION_TOKEN、ROOT_PAGE_ID）
notion-md-sync ./markdown

# 或指定参数
notion-md-sync ./knowledge --token "$NOTION_TOKEN" --page-id "$ROOT_PAGE_ID"

# 强制全量重新上传
notion-md-sync ./markdown --force

# 提高并发（默认 8）
notion-md-sync ./markdown --workers 16
```

若未安装为包，可直接运行入口脚本：

```bash
python notion-md-sync ./markdown
# 或
python -m notion_md_sync.cli ./markdown
```

**增强版特性：**

| 功能 | 说明 |
|------|------|
| **增量同步** | 用 `hash(md 内容)` 记录在 `./markdown/.notionsync`，只上传新增或改动的文件 |
| **并发上传** | 使用线程池（默认 8），适合 1000+ 文件 |
| **Markdown API** | 若 Notion API 支持（2026-03-11+），优先用原生 Markdown 写入（标题、代码块、表格等）；否则回退为段落块 |

---

## 三、配置方式

- **环境变量**：`NOTION_TOKEN`、`ROOT_PAGE_ID`、可选 `MARKDOWN_DIR`
- **CLI 参数**：`--token`、`--page-id`、`dir` 位置参数
- 可复制 `.env.example` 为 `.env`，在 shell 里 `source .env` 或使用 `python-dotenv` 等加载

---

## 四、目录与状态文件

- 默认同步目录：`./markdown`（可通过环境变量或 CLI 参数修改）
- 增强版会在同步目录下生成 **`.notionsync`**（JSON），记录：
  - 每个文件夹对应的 Notion 页面 ID
  - 每个已同步文件的 `page_id` 与内容 hash  
  不要手动改该文件；删除后下次会按「全量」重新创建页面（不会删 Notion 上已有页面）。

---

## 五、后续可扩展

- **Markdown → 向量库 / RAG**：Notion 作为中间层，再通过 Notion API 或导出把内容同步到向量库做 AI 检索。
- **更强解析**：在增强版中接入完整 Markdown → Notion block 转换（标题、列表、代码块、表格等），在 API 不支持原生 Markdown 时也能还原格式。

---

## License

MIT
