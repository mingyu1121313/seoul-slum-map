#!/usr/bin/env python3
"""
build_polygons.py
571개 사이트(layerA + type2 관리형 + layerB)의 lat/lng 포인트를
의제처리구역 SHP와 공간 조인 → data/polygons.json 생성

Usage: python3 scripts/build_polygons.py
"""

import json, sys, math
from pathlib import Path

try:
    import geopandas as gpd
    from shapely.geometry import Point, mapping
    import pandas as pd
except ImportError:
    print("pip3 install geopandas shapely")
    sys.exit(1)

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
SHP  = ROOT / "UQ181_의제처리구역_202602/shp파일/UPIS_C_UQ181.shp"

# ── 1. 의제처리구역 로드 ─────────────────────────────────────────
print("▶ 의제처리구역 SHP 로드 중...")
zones = gpd.read_file(SHP, encoding="cp949")
# EPSG:5174 → WGS84
zones = zones.to_crs("EPSG:4326")
print(f"  {len(zones)}개 구역 로드 (CRS: {zones.crs})")

# ── 1-1. legacy 광역 zone 제거 (토지구획정리/택지개발/MLSFC_CL=None/50ha+) ──
before = len(zones)
EXCLUDE_KW = ("토지구획정리", "토지구획", "택지개발")
mask_legacy_name = zones["DGM_NM"].fillna("").str.contains("|".join(EXCLUDE_KW))
mask_no_class    = zones["MLSFC_CL"].isna()
mask_too_big     = zones["DGM_AR"].fillna(0) > 500_000   # 50 ha
mask_drop = mask_legacy_name | mask_no_class | mask_too_big
zones = zones[~mask_drop].reset_index(drop=True)
print(f"  legacy 광역 zone 제거: {before} → {len(zones)} ({before-len(zones)}건 제외)")

# ── 2. 571개 사이트 수집 ─────────────────────────────────────────
sites = []

# layerA.json (470건)
layerA = json.loads((DATA / "layerA.json").read_text(encoding="utf-8"))
for item in layerA["items"]:
    if item.get("lat") and item.get("lng"):
        sites.append({
            "id": item["id"],
            "name": item.get("name", ""),
            "category": item.get("category", ""),
            "lat": float(item["lat"]),
            "lng": float(item["lng"]),
            "source": "layerA"
        })

# type2.json 관리형 (83건)
type2 = json.loads((DATA / "type2.json").read_text(encoding="utf-8"))
for item in type2["관리형_진행중"]["items"]:
    if item.get("lat") and item.get("lng"):
        sites.append({
            "id": item["id"],
            "name": item.get("name", ""),
            "category": "주거환경개선(관리형)",
            "lat": float(item["lat"]),
            "lng": float(item["lng"]),
            "source": "type2_관리형"
        })

# type2 정비형은 layerA와 중복 — 건너뜀

# layerB.json (18건)
layerB = json.loads((DATA / "layerB.json").read_text(encoding="utf-8"))
for item in layerB["items"]:
    if item.get("lat") and item.get("lng"):
        sites.append({
            "id": item["id"],
            "name": item.get("name", ""),
            "category": "형성유형",
            "lat": float(item["lat"]),
            "lng": float(item["lng"]),
            "source": "layerB"
        })

print(f"▶ 사이트 {len(sites)}개 수집 (layerA/type2관리형/layerB)")
no_coord = 470 + 83 + 18 - len(sites)
if no_coord:
    print(f"  ⚠ 좌표 없는 항목 {no_coord}개 스킵")

# ── 3. 사이트 GeoDataFrame 생성 ──────────────────────────────────
gdf_sites = gpd.GeoDataFrame(
    sites,
    geometry=[Point(s["lng"], s["lat"]) for s in sites],
    crs="EPSG:4326"
)

# ── 4. 공간 조인: 포인트 → 의제처리구역 ─────────────────────────
print("▶ 공간 조인 실행 중...")
joined = gpd.sjoin(
    gdf_sites,
    zones[["DGM_NM", "MLSFC_CL", "SCLAS_CL", "DGM_AR", "geometry"]],
    how="left",
    predicate="within"
)

# 중복 매칭 시 가장 작은 구역(DGM_AR) 선택
joined = joined.sort_values("DGM_AR").groupby("id").first().reset_index()
print(f"  매칭 성공: {joined['index_right'].notna().sum()}건 / 전체 {len(joined)}건")

# ── 5. 매칭된 사이트에 폴리곤 geometry 삽입 ─────────────────────
print("▶ 폴리곤 GeoJSON 추출 중...")
matched_ids = joined[joined["index_right"].notna()]["id"].tolist()

# 각 사이트 id → 의제처리구역 polygon geometry 매핑
id_to_polygon = {}
for _, row in joined.iterrows():
    if pd.notna(row.get("index_right")):
        zone_geom = zones.iloc[int(row["index_right"])].geometry
        if zone_geom and not zone_geom.is_empty:
            # simplify for smaller file (~2m tolerance in degrees ≈ 0.00002)
            simplified = zone_geom.simplify(0.0002, preserve_topology=True)
            id_to_polygon[row["id"]] = {
                "polygon": mapping(simplified),
                "zone_name": row.get("DGM_NM", ""),
                "zone_area_m2": round(float(row["DGM_AR"]), 1) if pd.notna(row.get("DGM_AR")) else None
            }
    else:
        id_to_polygon[row["id"]] = {"polygon": None, "zone_name": None, "zone_area_m2": None}

# ── 6. 저장 ─────────────────────────────────────────────────────
out = {
    "meta": {
        "generated": "2026-04-15",
        "total_sites": len(sites),
        "matched": len(matched_ids),
        "unmatched": len(sites) - len(matched_ids),
        "source": "서울시 의제처리구역 위치정보 (OA-20957, 202602)"
    },
    "polygons": id_to_polygon
}

outpath = DATA / "polygons.json"
outpath.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
size_kb = outpath.stat().st_size / 1024
print(f"▶ 저장 완료: data/polygons.json ({size_kb:.0f} KB)")
print(f"  매칭: {len(matched_ids)}건 / 미매칭(마커 유지): {len(sites)-len(matched_ids)}건")

# ── 7. 매칭 결과 요약 ────────────────────────────────────────────
by_cat = {}
for _, row in joined.iterrows():
    cat = row.get("category", "?")
    matched = pd.notna(row.get("index_right"))
    if cat not in by_cat:
        by_cat[cat] = {"matched": 0, "total": 0}
    by_cat[cat]["total"] += 1
    if matched:
        by_cat[cat]["matched"] += 1

print("\n── 카테고리별 매칭률 ──")
for cat, v in sorted(by_cat.items()):
    pct = v["matched"] / v["total"] * 100 if v["total"] else 0
    print(f"  {cat:25s} {v['matched']:3d}/{v['total']:3d} ({pct:.0f}%)")
