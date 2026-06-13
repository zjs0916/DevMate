# hiking-trails-web-app

## Description
Build a FastAPI-based web app with an interactive map (Leaflet.js) for displaying and filtering nearby hiking trails, using uv for dependency management.

## Procedure
# FastAPI + Leaflet 徒步路线展示网站

## 说明
构建一个基于 FastAPI + Leaflet.js 交互式地图的徒步路线展示 web 应用，支持按难度过滤、搜索和地理邻近查询。

## 项目结构
```
hiking-trails/
├── pyproject.toml          # 项目依赖配置
├── README.md
└── src/
    ├── __init__.py
    ├── main.py              # FastAPI 应用 + uvicorn 启动
    ├── routes.py            # 路由 (页面 + JSON API)
    ├── models.py            # Trail dataclass
    ├── services.py          # 业务逻辑 + 数据集 + Haversine 距离计算 + OSM API
    └── templates/
        └── index.html       # 单页应用 (Leaflet.js 地图 + 侧边栏 + 搜索过滤)
```

## 关键依赖 (pyproject.toml)
- fastapi>=0.115.0
- uvicorn[standard]>=0.32.0
- jinja2>=3.1.0
- aiofiles>=24.1.0
- httpx>=0.28.0

## 关键实现细节

### models.py
```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Trail:
    id: int
    name: str
    difficulty: str  # easy, moderate, hard
    lat: float
    lng: float
    length_km: float
    elevation_gain_m: int
    duration_hours: float
    description: str
    tags: list[str] = field(default_factory=list)
    image_url: Optional[str] = None

    @property
    def difficulty_color(self) -> str:
        return {"easy": "green", "moderate": "orange", "hard": "red"}.get(self.difficulty, "gray")

    @property
    def difficulty_label(self) -> str:
        return {"easy": "简单", "moderate": "中等", "hard": "困难"}.get(self.difficulty, "未知")

    @property
    def emoji(self) -> str:
        return {"easy": "🟢", "moderate": "🟡", "hard": "🔴"}.get(self.difficulty, "⚪")
```

### services.py 要点
- 内建 15-20 条真实路线数据集（使用中国著名徒步路线）
- `haversine_km()` 计算经纬度距离
- `filter_trails()` 支持多维度过滤（难度/搜索/地理邻近）
- `fetch_osm_trails()` 可选集成 OpenStreetMap Overpass API 实时查询

### routes.py 要点
- `GET /` — HTML 页面
- `GET /api/trails?difficulty=moderate&search=大理&near_lat=25.5&near_lng=100.2&max_distance_km=200&source=demo`
- `GET /api/trails/{id}` — 单条 JSON

### index.html 前端要点
- Leaflet.js 开源地图，OpenStreetMap 瓦片
- 路线按难度着色（自定义 divIcon 标记）
- 侧边栏卡片列表，支持点击高亮并平移地图
- 浏览器 Geolocation API 定位
- 带防抖的实时搜索
- 响应式布局（移动端上下排列）
- 加载状态和空状态展示

## 启动命令
```bash
cd hiking-trails
uv sync
uv run python -m src.main
```

## 使用 uv 而非 pip/requirements.txt
- 所有依赖声明在 pyproject.toml 中
- 使用 `uv sync` 安装依赖
- 使用 `uv run python -m` 启动
