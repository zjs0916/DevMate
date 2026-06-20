# DevMate：AI 编程助手

DevMate 是一个 AI 驱动的编程助手，可以根据用户的自然语言需求生成和修改软件项目。

本项目实现了：

- 基于 DeepAgents / LangGraph 的多轮 Agent
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

## 当前实现状态

DevMate 当前版本已经升级为一个可多轮交互的 DeepAgents 编程助手。

核心实现包括：

- **DeepAgents runtime**：使用 `create_deep_agent` 构建 Agent，而不是普通单轮 `create_agent`。
- **Interactive CLI**：支持 `--interactive` 多轮对话模式，可以在同一会话中连续完成任务。
- **MCP Search**：通过 MCP Streamable HTTP 调用 `search_web` 工具，并使用 Tavily 获取网络搜索结果。
- **Local RAG**：使用 Chroma 存储本地知识库，并使用 FastEmbed 本地语义 embedding 进行文档检索。
- **FastEmbed Embeddings**：默认使用 `BAAI/bge-small-en-v1.5`，不依赖 OpenAI embedding 付费 API。
- **Boundary-Aware Chunking**：文档切分按 Markdown 标题 → 段落 → 句子三层边界感知策略，避免硬截断语义单元。
- **Standard Agent Skills**：Skills 使用标准目录结构：`.skills/<skill-name>/SKILL.md`。
- **Skills Semantic Search**：`search_skills` 使用 FastEmbed + Chroma 向量检索，支持语义匹配（如"构建接口"可匹配"create API endpoint"）。
- **Skills Save / Reuse**：Agent 可以保存 Skill，并在后续对话中通过 `search_skills` / `read_skill` 复用。
- **Docker Interactive Runtime**：Docker Compose 支持交互式 Agent 会话。
- **LangSmith Tracing**：提供端到端 Trace、Skills 保存 Trace、Skills 搜索/读取/复用 Trace。

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
- DeepAgents
- FastEmbed

## 项目结构

```text
DevMate/
├── src/devmate/
│   ├── agent.py
│   ├── config.py
│   ├── fastembed_embeddings.py
│   ├── file_tools.py
│   ├── index_docs.py
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

真实 API key 不应该写入 `config.toml`。本地运行时请复制一份：

```bash
cp config.toml config.local.toml
```

然后在 `config.local.toml` 中填写真实 key。

示例配置：

```toml
[model]
ai_base_url = "https://api.deepseek.com"
api_key = "your_chat_model_api_key_here"
model_name = "deepseek-v4-flash"

# FastEmbed local semantic embedding.
# FastEmbed 不需要 embedding API key。
# 下面两个字段保留是为了兼容 OpenAI-style embedding 配置。
embedding_base_url = "https://api.openai.com/v1"
embedding_api_key = "your_embedding_api_key_here"
embedding_model_name = "BAAI/bge-small-en-v1.5"
embedding_provider = "fastembed"
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

聊天模型和 embedding 模型分开配置：

```text
Chat model: DeepSeek / OpenAI-compatible chat API
Embedding model: FastEmbed local semantic embedding
Vector store: Chroma
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

### 4. 运行 DevMate Agent

推荐使用多轮交互模式：

```bash
PYTHONPATH=src uv run python -m devmate.main --config config.local.toml --interactive
```

进入后可以连续输入多轮任务：

```text
You: 请列出当前可用 skills
You: 请读取 hiking-trails-web-app skill，并总结它适合什么任务
You: /exit
```

也可以使用单轮模式：

```bash
PYTHONPATH=src uv run python -m devmate.main --config config.local.toml "请构建一个展示附近徒步路线的网站项目，必须实际创建项目文件，使用 uv，不要使用 requirements.txt。"
```

生成的项目文件会写入：

```text
generated_projects/
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

为了避免依赖外部 embedding API，本项目默认使用 FastEmbed 本地语义 embedding：

```text
src/devmate/fastembed_embeddings.py
```

文档切分采用三层边界感知策略：先按 Markdown 标题拆分，再按段落（`\n\n`）拆分，再按句子结束符拆分，最后才退化为字符截断。这样确保每个 chunk 保持完整的语义单元，提升检索质量。

## Agent Skills 技能系统

项目实现了 Skills 工具：

```text
src/devmate/skills.py
```

支持：

- `save_skill`：保存 skill 文件，并自动写入 `.skills/.chroma` 向量索引
- `list_skills`：列出所有已保存的 skill
- `read_skill`：按名称读取 skill 内容
- `search_skills`：使用 FastEmbed + Chroma 语义检索，找到语义最相近的 skill

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

## 代码质量检查

已完成 Ruff / PEP 8 风格检查：

```bash
uv run ruff check src
```

检查结果：

```text
All checks passed!
```

该检查用于确认 `src/` 下 Python 代码符合基础代码规范要求。

## MCP 搜索测试

已完成 MCP Streamable HTTP 搜索工具测试。

测试目标：

- 验证 MCP Search Server 可以正常启动。
- 验证 MCP Client 可以通过 Streamable HTTP 连接到 MCP Server。
- 验证 Agent 可加载并调用 `search_web` 工具。
- 验证 `search_web` 工具可以返回 Tavily Web Search 结果。

测试环境：

```text
MCP URL: http://127.0.0.1:8765/mcp/
Loaded MCP tools: search_web
Search tool: search_web
```

测试查询：

```text
latest FastAPI project structure best practices
```

测试结果：

```text
Search result preview returned Tavily web search results successfully, including an answer, source URLs, snippets, and raw search result metadata.
```

该测试证明 DevMate 可以通过 MCP Streamable HTTP 调用网络搜索服务，并成功获取 Tavily 搜索结果。

## RAG 知识库测试

已完成本地知识库 RAG 检索测试。

测试目标：

- 验证 `docs/` 目录中的 markdown 文档可以被读取和切分。
- 验证文档切片可以生成 embeddings 并写入本地 Chroma 向量库。
- 验证 `search_knowledge_base` 可以根据查询返回本地知识库内容。

索引命令：

```bash
PYTHONPATH=src uv run python -m devmate.index_docs --config config.local.toml --docs-dir docs --persist-dir .chroma
```

检索命令：

```bash
PYTHONPATH=src uv run python -c 'from devmate.config import load_config; from devmate.rag import search_knowledge_base; import sys; config = load_config("config.local.toml"); result = search_knowledge_base("project guidelines", config=config, persist_dir=".chroma", k=3); sys.stdout.write(result[:2000] + "\n")'
```

测试查询：

```text
project guidelines
```

测试结果：

```text
RAG returned local knowledge base results successfully, including source metadata from docs/internal_project_guidelines.md and relevant document content.
```

该测试证明 DevMate 可以索引本地文档，并通过 `search_knowledge_base` 完成本地知识库检索。

## 端到端徒步网站生成测试

已完成“附近徒步路线网站”端到端生成测试。

测试输入：

```text
请构建一个展示附近徒步路线的网站项目，必须实际创建项目文件，使用 uv，不要使用 requirements.txt。
```

测试结果：

```text
DevMate successfully generated a multi-file hiking routes website project under generated_projects/.
The generated output includes Python application code, pyproject.toml, README documentation, templates, and static web assets where applicable.
```

由于 `generated_projects/` 是运行产物并被 `.gitignore` 排除，端到端测试证据已记录在：

```text
docs/e2e_hiking_website_test.md
```

该测试证明 Agent 可以完成从用户自然语言需求到实际项目文件生成的端到端流程。

## Docker Compose 测试

已完成 Docker Compose 构建与运行测试。

测试内容：

- `docker compose up --build -d` 可以成功构建并启动服务。
- `mcp-search` 服务可以在 Docker Compose 环境中运行。
- `index-docs` 可以在 Docker Compose 环境中完成本地文档索引。
- `devmate` 服务可以通过 `docker compose run --rm devmate` 进入交互式 Agent 会话。

测试结果：

```text
Docker Compose build and run completed successfully. The Agent was tested successfully inside the container environment using uv run.
```

测试证据已记录在：

```text
docs/docker_compose_test.md
```

该测试证明 DevMate 可以通过 Docker Compose 完成容器化构建与运行。

## Skills 保存与复用 trace

已完成 Agent Skills 保存与复用 LangSmith Trace 验证。

Trace 链接：

- Skills save trace: https://smith.langchain.com/public/eba3cdd6-2a34-4d40-9008-9f7df0b924b6/r
- Skills search / read / reuse trace: https://smith.langchain.com/public/5cd351ff-1046-434a-9310-ec7046056372/r?scroll_to=output

验证内容：

- 第一轮 Trace 中可看到 Agent 调用 `save_skill` 工具，保存 `fastapi-healthcheck-api` Skill。
- 第二轮 Trace 中可看到 Agent 调用 `search_skills` 和 `read_skill` 工具，检索并读取已保存的 Skill。
- 第二轮基于复用的 Skill 生成 `generated_projects/healthcheck-api` 项目。
- 本地验证确认 `.skills/fastapi-healthcheck-api/SKILL.md` 已生成。
- 本地验证确认 `generated_projects/healthcheck-api/` 包含 `pyproject.toml`、`README.md` 和 `src/main.py`。

本地验证结果：

```text
.skills/fastapi-healthcheck-api/SKILL.md
generated_projects/healthcheck-api/README.md
generated_projects/healthcheck-api/pyproject.toml
generated_projects/healthcheck-api/src/__init__.py
generated_projects/healthcheck-api/src/main.py
