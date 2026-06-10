# DevMate：AI 编程助手

DevMate 是一个 AI 驱动的编程助手，可以根据用户的自然语言需求生成和修改软件项目。

本项目实现了：

- 基于 LangChain 的 Agent
- 基于 MCP Streamable HTTP 的网络搜索工具
- Tavily 网络搜索集成
- 基于本地文档的 RAG 检索
- 可复用的 Agent Skills 技能系统
- 项目文件自动生成
- Docker / Docker Compose 部署
- LangSmith 可观测性追踪

## 项目功能

DevMate 支持以下能力：

- 使用自然语言描述编程需求
- Agent 自动判断是否需要搜索网络
- 通过 MCP Server 调用 Tavily 搜索工具
- 检索 `docs/` 目录中的本地项目规范
- 根据用户需求生成多文件项目
- 将生成结果写入 `generated_projects/`
- 保存和复用常见任务模式到 `.skills/`
- 使用 LangSmith 追踪 Agent 执行过程
- 使用 Docker Compose 一键运行

## 技术栈

- Python 3.13
- uv
- LangChain
- LangGraph
- MCP Streamable HTTP
- FastMCP
- Tavily
- Chroma
- DeepSeek / OpenAI-compatible Chat Model
- LangSmith
- Docker

## 项目结构

```text
DevMate/
├── src/devmate/
│   ├── agent.py
│   ├── config.py
│   ├── file_tools.py
│   ├── index_docs.py
│   ├── local_embeddings.py
│   ├── main.py
│   ├── mcp_client.py
│   ├── mcp_search_server.py
│   ├── model.py
│   ├── rag.py
│   └── skills.py
├── docs/
├── .skills/
├── config.toml
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
└── README.md
```

## 配置说明

项目使用 `config.toml` 管理配置项。

真实 API key 不应该写入 `config.toml`，本地运行时请复制一份：

```bash
cp config.toml config.local.toml
```

然后在 `config.local.toml` 中填写真实 key。

示例：

```toml
[model]
ai_base_url = "https://api.deepseek.com"
api_key = "your_model_api_key_here"
model_name = "deepseek-v4-flash"
embedding_model_name = "local-hash"
embedding_provider = "hash"
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
```

## 本地运行方式

### 1. 安装依赖

```bash
uv sync
```

### 2. 索引本地文档

```bash
PYTHONPATH=src uv run python -m devmate.index_docs --config config.local.toml
```

成功后会生成本地 Chroma 向量库：

```text
.chroma/
```

### 3. 启动 MCP 搜索服务

打开第一个终端：

```bash
DEVMATE_CONFIG=config.local.toml PYTHONPATH=src uv run python -m devmate.mcp_search_server
```

该服务会通过 MCP Streamable HTTP 暴露 `search_web` 工具。

### 4. 运行 DevMate Agent

> 注意：本地运行 DevMate Agent 时，如果 MCP 连接出现 `502 Bad Gateway`，可能是 VPN / 代理影响了 `127.0.0.1` 或 `localhost`。请先关闭 VPN，或在 VPN / 代理设置中绕过 `127.0.0.1` 和 `localhost`。

打开第二个终端：

```bash
PYTHONPATH=src uv run python -m devmate.main --config config.local.toml "请构建一个展示附近徒步路线的网站项目，必须实际创建项目文件，使用 uv，不要使用 requirements.txt。"
```

生成的项目文件会写入：

```text
generated_projects/
```

## Docker 运行方式

> 注意：Docker 构建或运行时需要从 Docker Hub / GitHub / 模型服务 / Tavily 等外部服务下载或请求数据。如果遇到 `connection reset by peer`、镜像拉取失败、API 连接失败等网络错误，可以尝试打开 VPN / 代理后重新运行 Docker 命令。

### 1. 准备环境变量

复制环境变量模板：

```bash
cp .env.example .env
```

然后在 `.env` 中填写真实 API key。

示例：

```env
DEVMATE_MODEL_BASE_URL=https://api.deepseek.com
DEVMATE_MODEL_API_KEY=your_deepseek_api_key_here
DEVMATE_MODEL_NAME=deepseek-v4-flash
DEVMATE_TAVILY_API_KEY=your_tavily_api_key_here
DEVMATE_LANGCHAIN_API_KEY=your_langsmith_api_key_here
```

### 2. 构建 Docker 镜像

```bash
docker compose build
```

### 3. 索引本地文档

```bash
docker compose run --rm index-docs
```

### 4. 运行 DevMate

```bash
docker compose run --rm devmate
```

### 5. 停止服务

```bash
docker compose down
```

## MCP 网络搜索

项目实现了一个 MCP Search Server：

```text
src/devmate/mcp_search_server.py
```

该 Server 使用 FastMCP，并通过 Streamable HTTP 暴露搜索工具：

```text
search_web
```

Agent 通过 MCP Client 加载该工具：

```text
src/devmate/mcp_client.py
```

搜索服务使用 Tavily API。

## RAG 本地文档检索

项目实现了本地 RAG 流程：

```text
src/devmate/rag.py
src/devmate/index_docs.py
docs/
```

流程包括：

1. 读取 `docs/` 下的 markdown / text 文档
2. 切分文档
3. 生成 embedding
4. 写入 Chroma 向量库
5. Agent 通过 `search_knowledge_base` 工具检索本地知识

为了避免依赖外部 embedding API，本项目实现了本地 hash embedding：

```text
src/devmate/local_embeddings.py
```

## Agent Skills 技能系统

项目实现了 Skills 工具：

```text
src/devmate/skills.py
```

支持：

- `save_skill`
- `list_skills`
- `read_skill`
- `search_skills`

Skills 默认保存在：

```text
.skills/
```

该路径可以通过 `config.toml` 配置：

```toml
[skills]
skills_dir = ".skills"
```

## 文件生成能力

Agent 可以通过文件工具实际创建项目文件：

```text
src/devmate/file_tools.py
```

所有生成文件都会被限制在：

```text
generated_projects/
```

避免写出项目目录之外的路径。

## 代码质量检查

运行：

```bash
uv run ruff check src
```

项目遵守以下规则：

- 使用 Python 3.13
- 使用 uv 管理依赖
- 使用 `pyproject.toml`
- 不使用 `requirements.txt`
- Python 源码中避免直接 console output，使用 logging
- API key 不提交到 GitHub
- 运行产物不提交到 GitHub

## 安全说明

以下文件不会提交到 GitHub：

```text
.env
config.local.toml
.chroma/
generated_projects/
.DS_Store
__pycache__/
```

## 交付内容

本项目交付内容包括：

- GitHub 仓库链接
- LangSmith 成功 Trace 链接

LangSmith Trace 应能展示：

- Agent run
- 模型调用
- MCP 工具调用
- Tavily `search_web`
- 本地 RAG `search_knowledge_base`
- 文件生成工具调用
- Skills 工具调用

## 示例请求

```text
请构建一个展示附近徒步路线的网站项目，必须实际创建项目文件，使用 uv，不要使用 requirements.txt。
```

运行后，DevMate 会生成一个多文件 Web 项目，并写入 `generated_projects/`。

## LangSmith Trace

端到端测试 Trace：

- Hiking website generation trace: https://smith.langchain.com/public/70d6b0ac-86e3-425a-8d73-dc57aa917d0d/r

该 Trace 用于证明 Agent 端到端运行成功，并包含：
- Agent 对话流程
- LLM 调用
- MCP `search_web` 工具调用
- Tavily 搜索结果
- RAG / 本地知识库检索
- 文件生成相关步骤
