#!/usr/bin/env python3
"""
fetch_osm_seoul.py
osmnx로 서울 전역 OSM 데이터 캐시:
  - drive_graph.graphml : drive_service 네트워크 (내부망 closeness, 진입로 카운트용)
  - major_roads.geojson : primary/secondary/trunk/motorway + links (경계 둘러싸임용)
  - railways.geojson    : railway=rail/light_rail/subway
  - greenery.geojson    : landuse in (forest, park, grass, meadow) + leisure=park
  - landuse.geojson     : landuse in (residential, commercial, industrial, retail, forest, park, grass)

한 번만 실행. 이미 파일이 있으면 스킵.
Usage: python scripts/fetch_osm_seoul.py [--force]
"""
import sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")

import osmnx as ox

ROOT = Path(__file__).parent.parent
CACHE = ROOT / "data" / "osm_cache"
CACHE.mkdir(parents=True, exist_ok=True)

PLACE = "Seoul, South Korea"
FORCE = "--force" in sys.argv

ox.settings.use_cache = True
ox.settings.log_console = True
ox.settings.requests_timeout = 600

# 1. Drive network (graph)
graph_path = CACHE / "drive_graph.graphml"
if FORCE or not graph_path.exists():
    print(f"▶ drive_service 그래프 다운로드 (서울 전역)...")
    G = ox.graph_from_place(PLACE, network_type="drive_service", simplify=True)
    ox.save_graphml(G, graph_path)
    print(f"  노드 {len(G.nodes):,} 엣지 {len(G.edges):,} → {graph_path.name}")
else:
    print(f"✓ {graph_path.name} 캐시됨")

# 2. Major roads (for boundary wrapping)
major_path = CACHE / "major_roads.geojson"
if FORCE or not major_path.exists():
    print("▶ 대로 피처 다운로드...")
    tags = {"highway": ["motorway", "trunk", "primary", "secondary",
                        "motorway_link", "trunk_link", "primary_link", "secondary_link"]}
    gdf = ox.features_from_place(PLACE, tags)
    gdf = gdf[gdf.geometry.type.isin(["LineString", "MultiLineString"])]
    gdf[["geometry"]].to_file(major_path, driver="GeoJSON")
    print(f"  {len(gdf):,}건 → {major_path.name}")
else:
    print(f"✓ {major_path.name} 캐시됨")

# 3. Railways
rail_path = CACHE / "railways.geojson"
if FORCE or not rail_path.exists():
    print("▶ 철도 피처 다운로드...")
    tags = {"railway": ["rail", "light_rail", "subway", "monorail"]}
    gdf = ox.features_from_place(PLACE, tags)
    gdf = gdf[gdf.geometry.type.isin(["LineString", "MultiLineString"])]
    gdf[["geometry"]].to_file(rail_path, driver="GeoJSON")
    print(f"  {len(gdf):,}건 → {rail_path.name}")
else:
    print(f"✓ {rail_path.name} 캐시됨")

# 4. Greenery (parks & forests)
green_path = CACHE / "greenery.geojson"
if FORCE or not green_path.exists():
    print("▶ 녹지 피처 다운로드...")
    tags = {
        "landuse": ["forest", "grass", "meadow", "recreation_ground"],
        "leisure": ["park", "nature_reserve"],
        "natural": ["wood"],
    }
    gdf = ox.features_from_place(PLACE, tags)
    gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
    gdf[["geometry"]].to_file(green_path, driver="GeoJSON")
    print(f"  {len(gdf):,}건 → {green_path.name}")
else:
    print(f"✓ {green_path.name} 캐시됨")

# 5. Landuse (for entropy)
landuse_path = CACHE / "landuse.geojson"
if FORCE or not landuse_path.exists():
    print("▶ 용도 피처 다운로드...")
    tags = {
        "landuse": ["residential", "commercial", "retail", "industrial",
                    "forest", "grass", "meadow", "recreation_ground",
                    "cemetery", "farmland"],
        "leisure": ["park"],
    }
    gdf = ox.features_from_place(PLACE, tags)
    gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
    # 범주 태그 유지
    keep_cols = [c for c in ["landuse", "leisure", "geometry"] if c in gdf.columns]
    gdf[keep_cols].to_file(landuse_path, driver="GeoJSON")
    print(f"  {len(gdf):,}건 → {landuse_path.name}")
else:
    print(f"✓ {landuse_path.name} 캐시됨")

print("\n✅ OSM 캐시 완료")
