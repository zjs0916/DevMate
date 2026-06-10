# DevMate

DevMate is an AI coding assistant that can generate and modify software projects using:

- LangChain Agent
- MCP web search through Tavily
- Local RAG over markdown/text documents
- Reusable Agent Skills
- Docker deployment

## Features

- Natural language coding assistant
- MCP search server using Streamable HTTP
- Tavily-powered web search
- Local RAG with Chroma
- Configurable model settings through `config.toml`
- Local hash embeddings for offline RAG indexing
- Project file generation into `generated_projects/`
- Reusable skills stored in `.skills/`
- LangSmith tracing support
- Docker and Docker Compose support

## Requirements

- Python 3.13
- uv
- Docker Desktop
- Tavily API key
- Model API key, for example DeepSeek-compatible OpenAI API
- LangSmith API key

## Local setup

```bash
uv sync
