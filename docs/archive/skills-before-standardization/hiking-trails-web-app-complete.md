# hiking-trails-web-app-complete

## Description
Build a complete FastAPI + Leaflet.js hiking trails web app with uv, pyproject.toml, responsive map, filtering, and geolocation.

## Procedure
# FastAPI + Leaflet 徒步路线展示网站

## 项目结构
```
hiking-trails/
├── pyproject.toml          # fastapi, uvicorn, jinja2, httpx
├── README.md
└── src/
    ├── __init__.py
    ├── main.py              # FastAPI 应用入口 + uvicorn 启动
    ├── routes.py            # GET /  + GET /api/trails + GET /api/trails/{id}
    ├── models.py            # Trail dataclass（difficulty_color, difficulty_label, emoji, to_dict）
    ├── services.py          # 内置数据集 + haversine_km + filter_trails + fetch_osm_trails
    └── templates/
        └── index.html       # Leaflet.js 地图 + 侧边栏卡片 + 搜索过滤 + 定位
```

## 关键依赖
- fastapi>=0.115.0, uvicorn[standard]>=0.32.0, jinja2>=3.1.0, httpx>=0.28.0

## 核心功能
1. 内置 15 条中国著名徒步路线数据集
2. Haversine 距离计算 + 多维度过滤（难度/搜索/地理邻近）
3. Leaflet.js 交互式地图 + 难度着色标记
4. 浏览器 Geolocation API 定位附近路线
5. 响应式布局（桌面侧边栏/移动端上下排列）
6. 可选 OSM Overpass API 实时查询

## 启动命令
```bash
cd hiking-trails
uv sync
uv run python -m src.main
```

## 注意事项
- 使用 `uv` 而非 pip
- pyproject.toml 声明依赖，不创建 requirements.txt
- 使用 logging 而非 print
- 业务逻辑放在 services.py 中，路由保持精简
