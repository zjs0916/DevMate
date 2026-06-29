# DevMate：交互式 AI 编程助手

DevMate 是一个面向项目生成和代码任务执行的交互式 AI 编程助手。用户可以用自然语言描述需求，DevMate 会结合本地知识库、语义检索、MCP 搜索工具和文件生成工具，自动创建或修改软件项目。

当前版本支持本地运行和 Docker Compose 运行，并支持多轮交互模式。

---

## 项目简介

DevMate 的目标不是做一个单次问答脚本，而是做一个可以持续交互的 AI coding agent。

它可以完成：

* 根据自然语言需求生成多文件项目
* 将生成结果写入 `generated_projects/`
* 使用本地 RAG 检索项目规范和开发约束
* 使用 FastEmbed `BAAI/bge-small-en-v1.5` 做本地语义 embedding（无需 Ollama）
* 使用 Chroma 存储本地向量索引
* 通过 MCP Streamable HTTP 调用网络搜索工具
* 使用 Tavily 做外部信息搜索
* 使用 `.skills/` 保存和复用任务经验
* 使用 Docker Compose 启动交互式 Agent 会话
* 使用 LangSmith 追踪 Agent 执行过程

---

## 核心能力

### 多轮交互式 Agent

DevMate 支持交互式命令行模式：

```bash
PYTHONPATH=src uv run python -m devmate.main --config config.local.toml --interactive
```

进入后可以连续输入任务：

```text
DevMate> 请构建一个展示附近徒步路线的网站项目，必须创建项目文件，使用 uv，不要使用 requirements.txt。
DevMate> 给这个项目增加一个 /api/trails endpoint 返回 JSON。
DevMate> exit
```

这比单次 query 更适合展示 Agent 的连续执行能力。

---

### 本地语义检索

DevMate 使用：

* FastEmbed `BAAI/bge-small-en-v1.5` 作为默认本地语义 embedding 模型（384 维，无需 Ollama）
* Chroma 作为本地向量数据库
* `docs/` 作为本地知识库来源

索引后会生成：

```text
.chroma/
```

Agent 可以通过本地知识库理解项目规范、技术要求和已有开发约束。

---

### MCP 搜索工具

项目包含一个 MCP Search Server：

```text
src/devmate/mcp_search_server.py
```

该服务通过 MCP Streamable HTTP 暴露搜索工具，Agent 可以在需要时调用 Tavily 搜索外部信息。

---

### Skills 技能系统

项目支持将可复用经验保存在 `.skills/` 目录下：

```text
.skills/
├── fastapi-healthcheck-api/
├── fastapi-uv-project/
└── hiking-trails-web-app/
```

Agent 可以：

* 保存 skill
* 列出 skill
* 读取 skill
* 通过语义检索匹配最相关 skill
* 在后续任务中复用已有经验

---

### 项目文件生成

DevMate 可以实际创建项目文件，而不是只输出代码片段。

所有生成结果默认写入：

```text
generated_projects/
```

文件工具会限制写入路径，避免 Agent 写出项目工作区之外。

---

## 技术栈

* Python 3.13
* uv
* LangChain
* LangGraph / DeepAgents
* MCP Streamable HTTP
* FastMCP
* Tavily
* Chroma
* FastEmbed
* BAAI/bge-small-en-v1.5 semantic embeddings（384 维，本地运行无需 Ollama）
* DeepSeek / OpenAI-compatible chat model
* LangSmith
* Docker
* Docker Compose

---

## 项目结构

```text
DevMate/
├── src/devmate/
│   ├── agent.py                  # Agent 构建和执行逻辑
│   ├── config.py                 # TOML 配置加载
│   ├── fastembed_embeddings.py   # 可选 FastEmbed embedding 后端
│   ├── file_tools.py             # 文件创建和修改工具
│   ├── index_docs.py             # 本地文档索引入口
│   ├── main.py                   # CLI / interactive 入口
│   ├── mcp_client.py             # MCP client 工具加载
│   ├── mcp_search_server.py      # MCP search server
│   ├── model.py                  # Chat model / embedding model 创建
│   ├── rag.py                    # 本地 RAG 检索逻辑
│   └── skills.py                 # Skills 保存、读取、检索
├── docs/                         # 本地知识库文档
├── .skills/                      # Agent skills
├── generated_projects/           # Agent 生成的项目
├── config.toml                   # 示例配置
├── config.local.toml             # 本地私有配置，不提交
├── config.docker.toml            # Docker 私有配置，不提交
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## 运行前准备

### 安装 uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 配置说明

项目使用 TOML 文件管理配置。

真实 API key 不应该提交到 GitHub。建议复制一份本地配置：

```bash
cp config.toml config.local.toml
```

然后在 `config.local.toml` 中填写真实 key。

本地运行推荐配置（默认使用 FastEmbed，无需安装 Ollama）：

```toml
[model]
ai_base_url = "https://api.deepseek.com"
api_key = "your_deepseek_api_key_here"
model_name = "deepseek-v4-flash"

embedding_provider = "fastembed"
embedding_model_name = "BAAI/bge-small-en-v1.5"
embedding_dimensions = 384

[search]
tavily_api_key = "your_tavily_api_key_here"

[langsmith]
langchain_tracing_v2 = true
langchain_api_key = "your_langsmith_api_key_here"

[skills]
skills_dir = ".skills"

[mcp]
host = "127.0.0.1"
port = 8765
endpoint = "/mcp"
required = true
```

> **注意：** 如果修改了 `embedding_provider`、`embedding_model_name` 或 `embedding_dimensions`，必须重建 Chroma 索引，否则会发生维度冲突：
>
> ```bash
> rm -rf .chroma .skills/.chroma
> PYTHONPATH=src uv run python -m devmate.index_docs --config config.local.toml
> ```
>
> `BAAI/bge-small-en-v1.5` 的向量维度是 **384**；如果切换为 Ollama `bge-m3`，其常见维度为 **1024**，两者不兼容，不能复用旧索引。

### 可选：使用 Ollama bge-m3（1024 维）

如果需要更高质量的语义检索，可以切换为 Ollama：

```bash
brew install ollama
brew services start ollama
ollama pull bge-m3
```

然后在配置中修改：

```toml
embedding_provider = "ollama"
embedding_model_name = "bge-m3"
embedding_base_url = "http://127.0.0.1:11434"
embedding_api_key = "not-needed-for-ollama"
embedding_dimensions = 1024
```

切换后需要重建 Chroma 索引（见上方注意事项）。

---

## 本地运行方式

### 安装依赖

```bash
uv sync
```

### 索引本地文档

```bash
PYTHONPATH=src uv run python -m devmate.index_docs --config config.local.toml
```

成功后会看到类似输出：

```text
Indexed 32 document chunks from docs into .chroma.
```

这说明本地 RAG 知识库已经建立完成。

---

### 启动 MCP 搜索服务

打开第一个终端：

```bash
cd ~/Downloads/DevMate

export NO_PROXY="127.0.0.1,localhost,::1"
export no_proxy="$NO_PROXY"

DEVMATE_CONFIG=config.local.toml PYTHONPATH=src uv run python -m devmate.mcp_search_server
```

保持这个终端不要关闭。

---

### 启动交互式 DevMate

打开第二个终端：

```bash
cd ~/Downloads/DevMate

export NO_PROXY="127.0.0.1,localhost,::1"
export no_proxy="$NO_PROXY"

PYTHONPATH=src uv run python -m devmate.main --config config.local.toml --interactive
```

进入交互模式后输入任务：

```text
DevMate> 请构建一个展示附近徒步路线的网站项目，必须创建项目文件，使用 uv，不要使用 requirements.txt。
```

DevMate 生成项目文件后，会自动调用 `start_fastapi_preview`，在后台启动 uvicorn 并返回可访问的 URL，例如：

```text
Preview started at http://127.0.0.1:8000 (logs: generated_projects/hiking-trails/.devmate/preview.log)
```

**不需要退出 DevMate 会话**，直接在浏览器中打开返回的 URL 即可访问生成的网站。

如果 preview 自动启动失败，可以手动 fallback：

```bash
cd generated_projects/<project-name>
uv sync
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000
```

退出：

```text
DevMate> exit
```

---

## 单次任务模式

除了交互模式，也可以使用单次 query：

```bash
PYTHONPATH=src uv run python -m devmate.main --config config.local.toml "请构建一个展示附近徒步路线的网站项目，必须创建项目文件，使用 uv，不要使用 requirements.txt。"
```

不过项目展示时更推荐交互模式，因为它更能体现 Agent 的连续任务执行能力。

---

## Docker Compose 运行方式

Docker Compose 版本用于展示完整交互式运行环境，包含四个服务：

| 服务 | 作用 |
|------|------|
| `mcp-search` | Streamable HTTP MCP 搜索服务（Tavily），监听 `:8765` |
| `preprocess-corpus` | 一次性任务，把 `rag_eval/raw/` 里的原始文件生成 corpus |
| `index-docs` | 一次性任务，构建本地 Chroma 向量库 |
| `devmate` | 交互式 Agent，通过 `http://mcp-search:8765/mcp` 调用搜索 |

四个服务共享同一个镜像（`devmate:local`），并把仓库目录挂载进容器，
因此 `generated_projects/`、`.chroma/`、`.fastembed_cache/` 与宿主机共享。

> **关于配置：** 仓库中提交的 `config.toml` 只是**示例配置**，里面的
> `api_key` / `tavily_api_key` / `langchain_api_key` 都是占位符。要真正调用
> LLM、Tavily 搜索或 LangSmith 追踪，需要通过 `config.local.toml`、
> `config.docker.toml`（均不提交）或环境变量提供**真实 API key**。详见下方
> [使用自定义配置](#使用自定义配置)。

> **关于 FastEmbed 模型：** 首次 Docker 运行默认允许联网下载 FastEmbed
> embedding 模型（`HF_HUB_OFFLINE=0`）。下载成功后会缓存到宿主机的
> `.fastembed_cache/`（通过 bind mount 共享），后续运行直接复用。若想强制完全
> 离线运行（例如演示离线 RAG），可在模型缓存就绪后设置 `HF_HUB_OFFLINE=1`：
>
> ```bash
> HF_HUB_OFFLINE=1 DEVMATE_CONFIG=config.docker.toml docker compose run --rm devmate
> ```

---

### 构建 Docker 镜像

```bash
docker compose build
```

### 运行交互式 DevMate

```bash
# 启动 mcp-search 与 index-docs（依赖项），并进入交互式 devmate
docker compose run --rm devmate
```

`devmate` 通过 `depends_on` 在启动前等待 `mcp-search` 健康检查通过、
`index-docs` 建库完成。如需单独查看依赖服务：

```bash
docker compose up --build -d mcp-search index-docs
docker compose logs --tail=120 mcp-search
docker compose logs --tail=120 index-docs
```

进入后应该看到：

```text
DevMate interactive mode. Type 'exit' or 'quit' to stop.
DevMate>
```

然后可以直接输入任务：

```text
DevMate> 请构建一个展示附近徒步路线的网站项目，必须创建项目文件，使用 uv，不要使用 requirements.txt。
```

### 使用自定义配置

如需覆盖默认配置（例如填入真实 API key 或切换 embedding 方案），可通过 `DEVMATE_CONFIG` 环境变量指定：

```bash
cp config.docker.example.toml config.docker.toml
# 编辑 config.docker.toml，填入真实 API key
DEVMATE_CONFIG=config.docker.toml docker compose run --rm devmate
```

`config.docker.example.toml` 提供了默认（FastEmbed）和 Ollama 两种 embedding 的配置示例。如果切换为 Ollama，需要将 embedding 地址改为 `http://host.docker.internal:11434`，因为 Docker 容器内的 `127.0.0.1` 指向容器自身，不是 Mac 本机。

Docker Compose 的重点是：

* `stdin_open: true` / `tty: true` — 支持交互式输入
* `preprocess-corpus` 服务先生成 `rag_eval/corpus/` 和 manifest
* `index-docs` 服务在预处理成功后构建本地知识库（Chroma 向量库）
* `mcp-search` 服务独立运行 MCP Search Server，`devmate` 通过服务名
  `mcp-search` 连接（`DEVMATE_MCP_HOST=mcp-search`）
* 支持 `DEVMATE_CONFIG` 环境变量覆盖配置文件路径（所有服务共享同一份 config）

**注意：** Docker Compose 负责启动 `mcp-search`、`preprocess-corpus`、`index-docs` 和 `devmate`。
在 Docker 环境中，preview 会自动启动 uvicorn 并返回 URL，但不会尝试打开宿主机浏览器（容器无法控制宿主机）。
如需访问生成的网站，需要将 Docker 容器端口映射到宿主机，或使用本地运行模式（自动打开浏览器仅在本地模式下有效）。

---

## 生成项目示例

示例任务：

```text
请构建一个展示附近徒步路线的网站项目，必须创建项目文件，使用 uv，不要使用 requirements.txt。
```

DevMate 会生成类似目录：

```text
generated_projects/
└── hiking-trails/
    ├── pyproject.toml
    ├── README.md
    └── src/
        ├── __init__.py
        ├── main.py
        ├── routes.py
        ├── models.py
        ├── services.py
        ├── templates/
        │   └── index.html
        └── static/
            └── style.css
```

DevMate 在生成项目后会自动启动 preview，返回可直接访问的 URL。

如需手动运行生成项目：

```bash
cd generated_projects/hiking-trails
uv sync
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000
```

浏览器访问：

```text
http://127.0.0.1:8000
```

如果项目提供 API endpoint，也可以测试：

```bash
curl http://127.0.0.1:8000/api/trails
```

---

## 本地 RAG 工作流程

DevMate 的本地 RAG 由三步组成：

```text
raw txt / md / pdf
  -> preprocessing
  -> UTF-8 corpus txt + manifest
  -> Chroma index
  -> search_knowledge_base
```

核心入口：

* `scripts/preprocess_corpus.py`：把原始 `.txt` / `.md` / `.pdf` 转成 UTF-8 corpus。
* `src/devmate/index_docs.py`：切分 corpus 并写入 Chroma。
* `scripts/test_rag_retrieval.py`：读取外部 eval cases，直接调用 `search_knowledge_base` 做 RAG-only 检索验证。

文档切分优先使用 Markdown 标题，其次使用段落和句子；超长段落再按字符切分。索引 metadata 会记录来源文件、chunk index、稳定 chunk id、内容 hash，以及 manifest 可提供的 PDF 页码信息。

---

## Generic RAG preprocessing

把原始文件放在：

```text
rag_eval/raw/
```

运行预处理：

```bash
PYTHONPATH=src uv run python scripts/preprocess_corpus.py \
    --raw-dir rag_eval/raw \
    --output-dir rag_eval/corpus \
    --manifest rag_eval/corpus_manifest.jsonl \
    --recursive \
    --clean-output
```

输出：

```text
rag_eval/corpus/
rag_eval/corpus_manifest.jsonl
```

预处理规则是确定性的：编码容错读取、去 BOM、统一换行、去不可见控制字符、压缩多余空行；PDF 使用 `pypdf` 抽取文本并做通用页码/重复页眉页脚清理。脚本不翻译、不总结、不改写正文，也不会把文件改成固定标准名。`.md` 和 `.pdf` 会输出为同 stem 的 `.txt`；如果输出文件名冲突，会追加稳定短 hash。

常用参数：

* `--include "*.txt" --include "*.pdf"`：限制输入类型或路径。
* `--exclude "__MACOSX/*"`：排除额外路径。
* `--recursive`：递归扫描 raw 目录。
* `--clean-output`：重建 corpus 输出目录。

`rag_eval/raw/`、`rag_eval/corpus/`、`rag_eval/corpus_manifest.jsonl` 都是本地数据或生成产物，不提交到 Git。

---

## Indexing

RAG eval 建议使用独立索引目录，避免影响 Agent 默认的 `.chroma`：

```bash
PYTHONPATH=src uv run python -m devmate.index_docs \
    --config config.local.toml \
    --docs-dir rag_eval/corpus \
    --persist-dir .chroma_rag_eval \
    --manifest rag_eval/corpus_manifest.jsonl \
    --chunk-size 900 \
    --chunk-overlap 120 \
    --reset
```

`--reset` 会先删除旧索引，避免旧 Chroma metadata、chunk 参数或 embedding 维度残留。索引签名记录 embedding provider、model、dimensions、chunk 参数和 corpus manifest hash；这些输入变化后应重建索引。

---

## Evaluation

`scripts/test_rag_retrieval.py` 是 RAG-only eval：不构建 Agent、不启动 MCP、不调用 Tavily，只调用 `search_knowledge_base`。

默认读取：

```text
rag_eval/eval_cases.example.json
```

运行：

```bash
PYTHONPATH=src uv run python scripts/test_rag_retrieval.py \
    --config config.local.toml \
    --persist-dir .chroma_rag_eval \
    --eval-cases rag_eval/eval_cases.example.json \
    --k 4
```

Eval case 支持：

* `question`
* `expected_source`：要求 top source 文件名精确匹配。
* `expected_source_contains`：要求 top source 文件名包含指定字符串。
* `expected_keywords_all`：全部关键词都要出现。
* `expected_keywords_any`：至少出现一个关键词。
* `expected_keyword_groups`：AND-of-ORs，每组至少命中一个关键词。

检索失败或 source 检查失败会返回非 0。关键词缺失默认是 warning；加 `--strict-keywords` 后会返回非 0。示例 eval cases 可以引用本地示例数据集，例如中文小说文本或规则手册 PDF；用户也可以为任意 corpus 提供自己的 `eval_cases.json`。

---

## Multilingual note

默认 FastEmbed `BAAI/bge-small-en-v1.5` 轻量、易部署，适合英文项目文档和一般 coding docs。中文或多语言 corpus 建议使用多语言 embedding，例如 Ollama `bge-m3`（常见 1024 维）。这是模型选择问题，不是针对某个数据集的补丁。

切换 embedding provider、model 或 dimensions 后必须重建索引：

```bash
rm -rf .chroma .chroma_rag_eval .skills/.chroma
```

本地多语言 eval 示例：

```bash
brew services start ollama
ollama pull bge-m3
cp config.rag_eval.ollama.example.toml config.rag_eval.ollama.toml

PYTHONPATH=src uv run python scripts/preprocess_corpus.py \
    --raw-dir rag_eval/raw \
    --output-dir rag_eval/corpus \
    --manifest rag_eval/corpus_manifest.jsonl \
    --recursive \
    --clean-output

PYTHONPATH=src uv run python -m devmate.index_docs \
    --config config.rag_eval.ollama.toml \
    --docs-dir rag_eval/corpus \
    --persist-dir .chroma_rag_eval \
    --manifest rag_eval/corpus_manifest.jsonl \
    --reset

PYTHONPATH=src uv run python scripts/test_rag_retrieval.py \
    --config config.rag_eval.ollama.toml \
    --persist-dir .chroma_rag_eval \
    --eval-cases rag_eval/eval_cases.example.json \
    --k 4 \
    --strict-keywords
```

Docker 容器调用 Mac 本机 Ollama 时，配置里的 `embedding_base_url` 应使用 `http://host.docker.internal:11434`。

---

## Docker RAG path

```bash
docker compose run --rm preprocess-corpus
docker compose run --rm index-docs
docker compose run --rm devmate
```

`preprocess-corpus` 和 `index-docs` 都是 one-shot job；`devmate` 只在 `index-docs` 成功完成后启动，不会和 indexing 同时写 `.chroma`。

---

## Skills 工作流程

Skills 的作用是保存可复用的开发经验。

```text
.skills/
  ↓
Skill markdown 文件
  ↓
Semantic embedding
  ↓
Chroma skill index
  ↓
search_skills / read_skill
  ↓
Agent 复用历史经验
```

支持的工具包括：

* `save_skill`
* `list_skills`
* `read_skill`
* `search_skills`

例如，用户要求创建 FastAPI + uv 项目时，Agent 可以检索已有 skill，并复用之前总结过的目录结构、依赖管理方式和启动命令。

---

## MCP 搜索工作流程

MCP Search Server 位于：

```text
src/devmate/mcp_search_server.py
```

MCP Client 位于：

```text
src/devmate/mcp_client.py
```

流程是：

```text
Agent
  ↓
MCP Client
  ↓
MCP Streamable HTTP
  ↓
MCP Search Server
  ↓
Tavily Search API
  ↓
搜索结果返回 Agent
```

如果 MCP 连接出现：

```text
502 Bad Gateway
```

通常是 VPN 或代理影响了本地 `127.0.0.1` / `localhost` 请求。可以尝试：

```bash
export NO_PROXY="127.0.0.1,localhost,::1"
export no_proxy="$NO_PROXY"
```

---

## 常见问题

### No module named devmate

如果看到：

```text
ModuleNotFoundError: No module named 'devmate'
```

通常是没有设置 `PYTHONPATH=src`，或者不在项目根目录运行。

正确方式：

```bash
cd ~/Downloads/DevMate
PYTHONPATH=src uv run python -m devmate.main --config config.local.toml --interactive
```

---

### Docker 里连不上 Ollama

如果本机能连接 Ollama，但 Docker 里连接失败，检查 `config.docker.toml`：

```toml
embedding_base_url = "http://host.docker.internal:11434"
```

Docker 容器里的 `127.0.0.1` 指的是容器自己，不是 Mac 本机。

---

### Chroma 维度冲突

切换 `embedding_provider`、`embedding_model_name` 或 `embedding_dimensions` 后，旧向量库维度与新模型不兼容，必须重建索引：

```bash
rm -rf .chroma .skills/.chroma
PYTHONPATH=src uv run python -m devmate.index_docs --config config.local.toml
```

说明：
- 默认 `BAAI/bge-small-en-v1.5`（fastembed）向量维度为 **384**
- 可选 `bge-m3`（ollama）常见向量维度为 **1024**
- 两者不兼容，切换后必须删除旧索引再重建

---

### MCP server 未启动（mcp.required = true 时会报错）

默认配置 `mcp.required = true`，如果 MCP Search Server 未启动，程序会直接报错：

```text
MCP server is required but search_web tool could not be loaded.
Start the MCP server or set mcp.required=false for local fallback mode.
```

**验收/正式模式**：保持 `required = true`，确保 MCP 搜索能力可用。启动方式见"启动 MCP 搜索服务"章节。

**本地调试（无 Tavily key）**：在配置文件中设置：

```toml
[mcp]
required = false
```

或通过环境变量覆盖：

```bash
DEVMATE_MCP_REQUIRED=false PYTHONPATH=src uv run python -m devmate.main --config config.local.toml --interactive
```

`required = false` 时，MCP 不可用只会打印 warning，Agent 继续以无网络搜索模式运行。

---

### Ollama 没启动（仅使用 Ollama provider 时需要）

默认配置使用 FastEmbed，不需要 Ollama。仅当 `embedding_provider = "ollama"` 时，才需要确认 Ollama 服务运行：

```bash
brew services start ollama
ollama list
```

确认能看到：

```text
bge-m3:latest
```

---

## 代码质量检查

运行：

```bash
uv run ruff check src
```

项目约束：

* 使用 Python 3.13
* 使用 uv 管理依赖
* 使用 `pyproject.toml`
* 不使用 `requirements.txt`
* API key 不提交到 GitHub
* 运行产物不提交到 GitHub
* 本地缓存和向量库不提交到 GitHub

---

## 安全说明

以下文件不应该提交到 GitHub：

```text
.env
config.local.toml
config.docker.toml
.chroma/
.skills/.chroma/
.fastembed_cache/
generated_projects/
**/.venv/
__pycache__/
.DS_Store
```

提交前建议检查：

```bash
git status
git check-ignore -v config.local.toml
git check-ignore -v config.docker.toml
git grep -n "sk-\|api_key\|deepseek\|tavily\|langchain_api_key"
```

如果 `git grep` 搜到真实 API key，需要删除并重新生成 key。

---

## 推荐演示流程

项目演示或评审时，可以按这个顺序演示：

1. 展示 DevMate 架构：Agent + RAG + MCP + Skills + 文件生成
2. 运行 `index_docs`（默认使用 FastEmbed，无需启动 Ollama）
3. 使用 Docker Compose 启动交互式 Agent
4. 输入自然语言需求
5. 展示 `generated_projects/` 中实际生成的项目文件
6. 启动生成项目并在浏览器访问
7. 展示 LangSmith trace，说明模型调用、工具调用和文件写入过程

---

## 示例请求

```text
请构建一个展示附近徒步路线的网站项目，必须创建项目文件，使用 uv，不要使用 requirements.txt。
```

```text
给这个项目增加一个 /api/trails endpoint，返回所有路线的 JSON 数据。
```

```text
请列出当前可用 skills，并说明哪个 skill 最适合生成 FastAPI 项目。
```

```text
请读取 hiking-trails-web-app skill，并基于它生成一个新的户外路线展示网站。
```

---

## 当前状态

当前版本已经完成：

* 交互式 CLI
* Docker Compose 交互运行
* FastEmbed BAAI/bge-small-en-v1.5 本地语义 embedding（384 维，无需 Ollama）
* Chroma 本地向量库
* MCP Search Server
* Tavily 搜索工具
* 本地 RAG 检索
* Skills 保存和复用
* 项目文件自动生成
* 生成项目可本地启动访问

DevMate 现在可以作为一个完整的 AI coding agent 项目进行展示。
