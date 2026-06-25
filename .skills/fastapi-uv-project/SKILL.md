---
name: fastapi-uv-project
description: Use this skill when generating or reviewing FastAPI projects that must use uv, pyproject.toml, src layout, modular routes and services, logging instead of print, and no requirements.txt.
---

# FastAPI uv Project

## Compatibility

Python 3.13, uv, FastAPI, local filesystem project generation.

## Overview

Use this skill when the user asks DevMate to create, modify, or review a FastAPI web application.

## Instructions

When creating a FastAPI project:

- Use `pyproject.toml` and uv.
- Do not create `requirements.txt`.
- Use a `src/` based project layout.
- Keep route handlers small.
- Put business logic in separate service modules.
- Use `logging` instead of `print()`.
- Include a short README with setup and run commands.
- Prefer simple, maintainable code over clever abstractions.

## Expected project structure

```text
project-name/
├── pyproject.toml
├── README.md
└── src/
    ├── __init__.py
    ├── main.py
    ├── routes.py
    ├── services.py
    └── models.py
```

## Verification

After generating files, check that:

- `pyproject.toml` exists.
- `requirements.txt` does not exist.
- Python files use logging instead of print.
- The app can be started with `uv run uvicorn src.main:app --host 127.0.0.1 --port 8000`.
