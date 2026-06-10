# hiking-trails-web-app

## Description
Build a FastAPI-based web app with an interactive map (Leaflet.js) for displaying and filtering nearby hiking trails.

## Procedure
# FastAPI + Leaflet 徒步路线展示网站

## 项目结构
```
hiking-trails/
├── pyproject.toml
├── README.md
└── src/
    ├── __init__.py
    ├── main.py          # FastAPI 应用入口, uvicorn 启动
    ├── routes.py        # 路由处理器 (API + 页面渲染)
    ├── models.py        # dataclass 数据模型
    ├── services.py      # 业务逻辑层 (数据获取/过滤)
    └── templates/
        └── index.html   # Jinja2 模板, 含 Leaflet.js 地图
```

## 关键依赖 (pyproject.toml)
- fastapi
- uvicorn[standard]
- jinja2
- aiofiles

## 实现要点
1. **src/services.py** — 使用模拟数据模拟真实API，提供 `get_all_trails()` 和 `filter_trails()` 
2. **src/routes.py** — 保持路由精简，页面路由返回HTML，数据路由返回JSON
3. **src/models.py** — 使用 `@dataclass` 定义数据模型
4. **src/templates/index.html** — 单页面应用，包含：
   - Leaflet.js 交互式地图，带自定义难度颜色标记
   - 侧边栏路线列表，点击卡片自动定位地图
   - 按难度过滤按钮
5. **main.py** — `if __name__ == "__main__"` 中使用 `uvicorn.run()`
6. 使用 `logging` 而非 `print`

## 启动方式
```bash
cd hiking-trails
uv sync
uv run python -m src.main
```

## API 设计模式
- `GET /` — HTMX/Jinja2 渲染页面
- `GET /trails` — JSON 数据接口，支持 query params 过滤
- `GET /trails/{id}` — 单条路线详情 JSON

## 前端交互
- Leaflet.js + OpenStreetMap 瓦片
- 点击标记或卡片弹出信息
- 过滤按钮控制地图标记和列表的显隐
- CSS 响应式布局 (桌面/移动)
