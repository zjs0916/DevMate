---
name: hiking-trails-web-app
description: Use this skill when generating a hiking routes website or a map-based local trails web app with FastAPI, uv, templates, static assets, and optional OpenStreetMap or Overpass API data.
---

# Hiking Trails Web App

## Compatibility

Python 3.13, uv, FastAPI, Jinja2, Leaflet.js, OpenStreetMap or Overpass API.

## Overview

Use this skill when the user asks for a website that displays nearby hiking routes, trails, maps, difficulty filters, or route cards.

## Instructions

When creating a hiking routes website:

- Use the `fastapi-uv-project` conventions.
- Generate a multi-file project, not a single script.
- Include `pyproject.toml`, `README.md`, Python application code, templates, and static assets where useful.
- Use FastAPI for the backend.
- Use Jinja2 templates for the main page if rendering server-side HTML.
- Use Leaflet.js or simple map-ready frontend structure when map display is requested.
- Include sample trail data so the app works without external APIs.
- If external data is used, keep it optional and document API behavior clearly.

## Suggested files

```text
hiking-trails/
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
        ├── app.js
        └── style.css
```

## Quality checks

- The generated app should include at least several sample trails.
- The UI should show trail name, location, difficulty, distance, and estimated time.
- The README should explain how to run the app with uv.
- The project should avoid `print()` in Python source files.
