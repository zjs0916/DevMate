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
* 使用 Ollama `bge-m3` 做真正语义 embedding
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

* Ollama `bge-m3` 作为本地语义 embedding 模型
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
* Ollama
* bge-m3 semantic embeddings
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

### 安装 Ollama

macOS 可以使用 Homebrew：

```bash
brew install ollama
brew services start ollama
```

下载本地语义 embedding 模型：

```bash
ollama pull bge-m3
```

确认模型存在：

```bash
ollama list
```

应该可以看到：

```text
bge-m3:latest
```

---

## 配置说明

项目使用 TOML 文件管理配置。

真实 API key 不应该提交到 GitHub。建议复制一份本地配置：

```bash
cp config.toml config.local.toml
```

然后在 `config.local.toml` 中填写真实 key。

本地运行推荐配置：

```toml
[model]
ai_base_url = "https://api.deepseek.com"
api_key = "your_deepseek_api_key_here"
model_name = "deepseek-v4-flash"

embedding_provider = "ollama"
embedding_model_name = "bge-m3"
embedding_base_url = "http://127.0.0.1:11434"
embedding_api_key = "not-needed-for-ollama"
embedding_dimensions = 1024

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
```

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

Docker Compose 版本用于展示完整交互式运行环境。

如果 Ollama 运行在 Mac 本机，而不是 Docker 容器里，Docker 配置需要使用：

```toml
embedding_base_url = "http://host.docker.internal:11434"
```

因此建议复制一份 Docker 专用配置：

```bash
cp config.local.toml config.docker.toml
```

然后把 `config.docker.toml` 中的 embedding 地址改成：

```toml
embedding_base_url = "http://host.docker.internal:11434"
```

---

### 构建 Docker 镜像

```bash
docker compose build
```

### 运行交互式 DevMate

```bash
docker compose run --rm devmate
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

Docker Compose 的重点是：

* `stdin_open: true`
* `tty: true`
* `PYTHONPATH=src`
* 自动启动 MCP Search Server
* 启动 `devmate.main --interactive`

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

运行生成项目：

```bash
cd generated_projects/hiking-trails
uv sync
uv run python -m src.main
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

本地 RAG 的流程是：

```text
docs/
  ↓
文档切分
  ↓
Ollama bge-m3 semantic embedding
  ↓
Chroma vector store
  ↓
search_knowledge_base 工具
  ↓
Agent 任务执行
```

文档索引入口：

```text
src/devmate/index_docs.py
```

检索逻辑：

```text
src/devmate/rag.py
```

本项目的文档切分采用边界感知策略，优先按 Markdown 标题、段落和句子切分，避免直接硬截断语义单元。

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

如果从 384 维 embedding 切换到 1024 维 embedding，旧向量库可能会维度冲突。

可以删除旧索引后重新建立：

```bash
rm -rf .chroma .skills/.chroma
PYTHONPATH=src uv run python -m devmate.index_docs --config config.local.toml
```

---

### Ollama 没启动

如果 embedding 请求失败，先确认 Ollama 服务运行：

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

面试或项目展示时，可以按这个顺序演示：

1. 展示 DevMate 架构：Agent + RAG + MCP + Skills + 文件生成
2. 启动 Ollama 和 bge-m3 embedding
3. 运行 `index_docs`
4. 使用 Docker Compose 启动交互式 Agent
5. 输入自然语言需求
6. 展示 `generated_projects/` 中实际生成的项目文件
7. 启动生成项目并在浏览器访问
8. 展示 LangSmith trace，说明模型调用、工具调用和文件写入过程

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
* Ollama bge-m3 真实语义 embedding
* Chroma 本地向量库
* MCP Search Server
* Tavily 搜索工具
* 本地 RAG 检索
* Skills 保存和复用
* 项目文件自动生成
* 生成项目可本地启动访问

DevMate 现在可以作为一个完整的 AI coding agent 项目进行展示。
