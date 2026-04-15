#!/usr/bin/env python3
"""
build_bldg_age.py
폴리곤 매칭된 각 사이트에 대해, 구역 내 건물 사용승인일로 노후도 계산
- avg_bldg_age: 구역 내 건물 평균 연차 (2026 기준)
- pct_30plus, pct_40plus, pct_50plus: 30/40/50년 이상 건물 비율(%)
layerA.json, type2.json, layerB.json에 필드 추가

Usage: python3 scripts/build_bldg_age.py
"""

import json, sys
from pathlib import Path
from datetime import datetime

try:
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import shape
except ImportError:
    print("pip3 install geopandas shapely")
    sys.exit(1)

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
BLDG_SHP = ROOT / "AL_D010_11_20260409/AL_D010_11_20260409.shp"
BASE_YEAR = 2026

# ── 1. 건물 SHP 로드 (A13=사용승인일, A12=건물면적만) ──────────────
print("▶ 건물 SHP 로드 중... (695k건, 시간 소요)")
cols_needed = ["A12", "A13", "geometry"]   # 면적, 사용승인일
bldg = gpd.read_file(BLDG_SHP, encoding="cp949", columns=["A12", "A13"])
print(f"  {len(bldg):,}건 로드, CRS: {bldg.crs}")

# 사용승인일 파싱 → 연차 계산
bldg["year"] = pd.to_datetime(bldg["A13"], errors="coerce").dt.year
bldg["age"] = BASE_YEAR - bldg["year"]
bldg = bldg[bldg["age"].notna() & (bldg["age"] >= 0) & (bldg["age"] < 200)].copy()
bldg["age"] = bldg["age"].astype(int)
print(f"  유효 연차 데이터: {len(bldg):,}건")

# EPSG:5186 → WGS84
print("  CRS 변환 중...")
bldg = bldg.to_crs("EPSG:4326")

# ── 2. polygons.json 로드 ──────────────────────────────────────
polygons_data = json.loads((DATA / "polygons.json").read_text(encoding="utf-8"))
polys = polygons_data["polygons"]
matched_ids = [sid for sid, v in polys.items() if v.get("polygon")]
print(f"▶ 매칭된 폴리곤 {len(matched_ids)}개에 대해 노후도 계산")

# ── 3. 각 폴리곤별 건물 나이 계산 ────────────────────────────────
# R-tree 공간 인덱스 자동 사용 (geopandas sjoin)
age_map = {}   # id → {avg_bldg_age, pct_30plus, ...}

# 폴리곤 GDF 생성
poly_rows = []
for sid in matched_ids:
    geom = shape(polys[sid]["polygon"])
    poly_rows.append({"id": sid, "geometry": geom})

gdf_polys = gpd.GeoDataFrame(poly_rows, crs="EPSG:4326")

print("  공간 조인 (폴리곤 ∩ 건물)...")
joined = gpd.sjoin(bldg[["age", "geometry"]], gdf_polys, how="inner", predicate="within")

print("  통계 집계...")
stats = joined.groupby("id")["age"].agg(
    avg_bldg_age="mean",
    count="count",
    pct_30plus=lambda x: (x >= 30).mean() * 100,
    pct_40plus=lambda x: (x >= 40).mean() * 100,
    pct_50plus=lambda x: (x >= 50).mean() * 100,
).round(1).to_dict(orient="index")

print(f"  계산 완료: {len(stats)}개 폴리곤")

# ── 4. polygons.json에 age 필드 병합 ──────────────────────────────
for sid, v in polys.items():
    if sid in stats:
        s = stats[sid]
        v["avg_bldg_age"] = float(s["avg_bldg_age"])
        v["pct_30plus"]   = float(s["pct_30plus"])
        v["pct_40plus"]   = float(s["pct_40plus"])
        v["pct_50plus"]   = float(s["pct_50plus"])
        v["bldg_count"]   = int(s["count"])
    else:
        v["avg_bldg_age"] = None
        v["pct_30plus"]   = None
        v["pct_40plus"]   = None
        v["pct_50plus"]   = None
        v["bldg_count"]   = 0

polygons_data["meta"]["bldg_age_computed"] = True
polygons_data["meta"]["base_year"] = BASE_YEAR

outpath = DATA / "polygons.json"
outpath.write_text(json.dumps(polygons_data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
size_kb = outpath.stat().st_size / 1024
print(f"▶ polygons.json 업데이트 완료 ({size_kb:.0f} KB)")

# ── 5. 샘플 출력 ──────────────────────────────────────────────────
print("\n── 샘플 노후도 ──")
for sid, v in list(polys.items())[:8]:
    age = v.get("avg_bldg_age")
    if age:
        print(f"  {sid:10s} {v.get('zone_name','')[:20]:22s} 평균 {age:.1f}년 | 30+:{v['pct_30plus']:.0f}% 40+:{v['pct_40plus']:.0f}% 50+:{v['pct_50plus']:.0f}%")
