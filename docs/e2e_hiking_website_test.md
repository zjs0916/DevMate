# End-to-End Test: Hiking Website Generation

## Test Prompt

```text
请构建一个展示附近徒步路线的网站项目，必须实际创建项目文件，使用 uv，不要使用 requirements.txt。
```

## Test Goal

- Verify that DevMate can run an end-to-end coding task from a natural-language request.
- Verify that the Agent creates actual project files under `generated_projects/`.
- Verify that the generated project uses `uv` and `pyproject.toml` instead of `requirements.txt`.
- Verify that the generated project includes application code and supporting web files.

## Run Command

```bash
PYTHONPATH=src uv run python -m devmate.main --config config.local.toml "请构建一个展示附近徒步路线的网站项目，必须实际创建项目文件，使用 uv，不要使用 requirements.txt。"
```

## Generated Files

```text
generated_projects/README.md
generated_projects/hiking-trails/README.md
generated_projects/hiking-trails/pyproject.toml
generated_projects/hiking-trails/src/__init__.py
generated_projects/hiking-trails/src/main.py
generated_projects/hiking-trails/src/models.py
generated_projects/hiking-trails/src/routes.py
generated_projects/hiking-trails/src/services.py
generated_projects/hiking-trails/src/templates/index.html
generated_projects/nearby-hiking-trails/README.md
generated_projects/nearby-hiking-trails/pyproject.toml
generated_projects/nearby-hiking-trails/src/__init__.py
generated_projects/nearby-hiking-trails/src/main.py
generated_projects/nearby-hiking-trails/src/services.py
generated_projects/nearby-hiking-trails/src/templates/index.html
generated_projects/nearby-hiking-trails/static/app.js
generated_projects/nearby-hiking-trails/static/style.css
generated_projects/pyproject.toml
generated_projects/src/__init__.py
generated_projects/src/main.py
generated_projects/src/models.py
generated_projects/src/routes.py
generated_projects/src/services.py
generated_projects/src/templates/index.html
```

## Result

DevMate successfully generated a multi-file hiking routes website project under `generated_projects/`.

The generated output includes Python application code, `pyproject.toml`, README documentation, templates, and static web assets where applicable.
