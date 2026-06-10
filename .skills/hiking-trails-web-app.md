# hiking-trails-web-app

## Description
Build a FastAPI-based web app with an interactive map (Leaflet.js) for displaying and filtering nearby hiking trails.

## Procedure
# FastAPI + Leaflet 徒步路线展示网站

## 说明
构建一个基于 FastAPI + Leaflet.js 交互式地图的徒步路线展示 web 应用，支持按难度过滤、搜索和地理邻近查询。

## 项目结构
```
hiking-trails/
├── pyproject.toml
├── README.md
└── src/
    ├── __init__.py
    ├── main.py          # FastAPI 应用 + uvicorn 启动
    ├── routes.py        # 路由 (页面 + JSON API)
    ├── models.py        # Trail dataclass
    ├── services.py      # 业务逻辑 + 模拟数据集 + Haversine 距离计算
    └── templates/
        └── index.html   # 单页应用 (Leaflet.js 地图 + 侧边栏 + 搜索过滤)
```

## 关键依赖 (pyproject.toml)
- fastapi
- uvicorn[standard]
- jinja2
- aiofiles

## 实现要点
1. **src/services.py** — 模拟徒步路线数据集 (`list[Trail]`)，提供 `get_all_trails()`, `filter_trails()`, `haversine_km()`
2. **src/models.py** — 使用 `@dataclass` 定义 `Trail` 模型，含 `difficulty_color` 和 `difficulty_label` 属性
3. **src/routes.py** — `GET /` (页面), `GET /api/trails` (JSON列表+过滤), `GET /api/trails/{id}` (单条详情)
4. **src/templates/index.html** — 单页面应用，包含 Leaflet.js 交互地图、按难度颜色区分标记、搜索框、侧边栏路线列表
5. **src/main.py** — `uvicorn.run()` 启动，logging 配置
6. 使用 `logging` 而非 `print`

## 启动命令
```bash
uv sync
uv run python -m src.main
```

## API 设计
- `GET /` — HTML 页面
- `GET /api/trails?difficulty=moderate&search=云南&near_lat=27.18&near_lng=100.08&max_distance_km=500` — 过滤后的 JSON
- `GET /api/trails/1` — 单条 JSON
