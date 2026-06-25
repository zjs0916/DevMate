---
name: fastapi-healthcheck-api
description: Use this skill when creating a FastAPI health check API with uv, pyproject.toml, src layout, logging instead of print, and no requirements.txt.
---

# fastapi-healthcheck-api

## Instructions

# FastAPI Health Check API Skill

Use this skill when creating a simple FastAPI health check API project.

## Project Structure

```
project-name/
├── pyproject.toml          # Dependencies and project metadata (NO requirements.txt)
├── README.md               # Run instructions
├── src/
│   ├── __init__.py
│   └── main.py             # FastAPI app with / and /health endpoints
```

## Step-by-Step Workflow

### 1. Create project directory and files

```
project-name/
├── pyproject.toml
├── README.md
└── src/
    ├── __init__.py
    └── main.py
```

### 2. pyproject.toml template

```toml
[project]
name = "healthcheck-api"
version = "0.1.0"
description = "A simple FastAPI health check API"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
]

[tool.uv]
dev-dependencies = []
```

### 3. src/__init__.py

Leave empty or add a docstring:

```python
"""Health check API package."""
```

### 4. src/main.py

```python
"""FastAPI health check application."""

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

app = FastAPI(title="HealthCheck API", version="0.1.0")


@app.get("/")
async def root() -> JSONResponse:
    """Return a friendly landing response pointing at the health endpoint."""
    logger.info("Root endpoint called")
    return JSONResponse(
        content={"message": "DevMate healthcheck API", "health": "/health"}
    )


@app.get("/health")
async def health() -> JSONResponse:
    """Return a simple health check response."""
    logger.info("Health check endpoint called")
    return JSONResponse(content={"status": "healthy"})


def run() -> None:
    """Run the FastAPI application with uvicorn."""
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    run()
```

### 5. README.md

```markdown
# HealthCheck API

A minimal FastAPI health check service.

## Setup

```bash
# Install dependencies
uv sync

# Run the server
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000
```

The API will be available at `http://127.0.0.1:8000`.

Once running, you can visit:

- `/` — landing JSON pointing at the health endpoint
- `/health` — health check (`{"status": "healthy"}`)
- `/docs` — interactive Swagger UI

## Endpoints

| Method | Path       | Description                       |
|--------|------------|-----------------------------------|
| GET    | `/`        | Landing JSON with API info        |
| GET    | `/health`  | Health check                      |
| GET    | `/docs`    | Interactive API docs (Swagger UI) |

## Development

```bash
# Run with auto-reload
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```
```

### 6. Run the project

```bash
cd project-name
uv sync          # Install dependencies from pyproject.toml
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000  # Start the server
```

## Key Rules

- **uv only** — Never use pip or conda. Use `uv sync` and `uv run`.
- **pyproject.toml only** — Never create or recommend requirements.txt.
- **src layout** — Put application code under `src/`.
- **logging over print** — Always use `logging.getLogger(__name__)` instead of `print()`.
- **Keep route handlers small** — Simple JSONResponse returns for `/` and `/health`.
- **No pytest, no test files** — Keep it minimal unless asked otherwise.
