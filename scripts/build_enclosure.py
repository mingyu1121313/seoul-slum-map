#!/usr/bin/env python3
"""
build_enclosure.py
폴리곤 보유 사이트별로 폐쇄성 점수(0~100) 및 등급(상/중/하) 계산.

4기준 (가중합):
  c1 경계 둘러싸임 (0.30)  : 경계 중 대로+철도+녹지 접경 길이 비율
  c2 진입로 희소성 (0.25)  : 1 - min(1, 경계 교차 도로 수 / (둘레/100m))
  c3 내부망 고립도 (0.25)  : 1 - clamp((beta - 0.8)/0.8) where beta = edges/nodes of internal subgraph
  c4 용도 이질성   (0.20)  : Shannon entropy(주거/상업/공업/녹지) / log(4) over 200m buffer ring

등급: score>=65 상, 35<=score<65 중, score<35 하. placeholder/데이터부족 → null.

Usage: python scripts/build_enclosure.py
"""
import json, math, sys, warnings
from pathlib import Path
from collections import Counter
warnings.filterwarnings("ignore")

import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
CACHE = DATA / "osm_cache"

EPSG_M = 5179  # UTM-K, meters
BUFFER_M = 200

W1, W2, W3, W4 = 0.30, 0.25, 0.25, 0.20
CUT_HI, CUT_LO = 65, 35

# ── 수동 오버라이드 (폐쇄성 화이트리스트) ──
# OSM 데이터 한계로 자동 계산이 현장과 다른 구역을 수동 보정.
# 스크립트 재실행 시 자동 계산 결과를 이 값으로 덮어씀.
# 예) 차 못 가는 좁은 골목이 OSM에 도로로 등록되어 c3 저평가되는 달동네
MANUAL_ENCLOSURE_OVERRIDE = {
    "jb03":    {"grade": "상", "score": 70.0},  # 현저2 — 인왕산 기슭 달동네
    "moa1350": {"grade": "상", "score": 70.0},  # 현저동 1-5 (동일 구역)
}

def log(*a, **kw): print(*a, **kw, flush=True)

# ── 1. polygons.json 로드 ──────────────────────────────────
pdata = json.loads((DATA / "polygons.json").read_text(encoding="utf-8"))
polys_in = pdata["polygons"]
log(f"▶ polygons.json: {len(polys_in)}건")

# ── 2. OSM 캐시 로드 ────────────────────────────────────
log("▶ OSM 캐시 로드")
major  = gpd.read_file(CACHE / "major_roads.geojson").to_crs(EPSG_M)
rails  = gpd.read_file(CACHE / "railways.geojson").to_crs(EPSG_M)
green  = gpd.read_file(CACHE / "greenery.geojson").to_crs(EPSG_M)
landuse = gpd.read_file(CACHE / "landuse.geojson").to_crs(EPSG_M)
log(f"  major {len(major)} rails {len(rails)} green {len(green)} landuse {len(landuse)}")

log("▶ drive 그래프 로드")
G = ox.load_graphml(CACHE / "drive_graph.graphml")
G_proj = ox.project_graph(G, to_crs=f"EPSG:{EPSG_M}")
_, edges = ox.graph_to_gdfs(G_proj)
edges_sindex = edges.sindex
log(f"  노드 {len(G_proj.nodes):,} 엣지 {len(edges):,}")

# landuse 4 카테고리 분류
def classify_lu(row):
    lu = row.get("landuse")
    le = row.get("leisure") if "leisure" in row.index else None
    if lu == "residential": return "res"
    if lu in ("commercial", "retail"): return "com"
    if lu == "industrial": return "ind"
    if lu in ("forest", "grass", "meadow", "recreation_ground", "cemetery", "farmland") or le == "park":
        return "green"
    return None

landuse["cat"] = landuse.apply(classify_lu, axis=1)
landuse = landuse[landuse["cat"].notna()].copy()
landuse_sindex = landuse.sindex

# 대로+철도+녹지 통합 (경계 접경용)
boundary_obstacles = gpd.GeoDataFrame(
    geometry=list(major.geometry) + list(rails.geometry) + list(green.geometry),
    crs=f"EPSG:{EPSG_M}",
)
boundary_sindex = boundary_obstacles.sindex

# ── 3. 폴리곤별 계산 ────────────────────────────────────
from shapely.geometry import LineString, MultiLineString, Point

def compute_enclosure(poly_m):
    perimeter = poly_m.length
    if perimeter <= 0:
        return None, dict()

    # c1: 경계 둘러싸임 — boundary 5m 버퍼와 장애물 교차 길이
    boundary = poly_m.boundary
    border_buf = boundary.buffer(8)
    cand_idx = list(boundary_sindex.intersection(border_buf.bounds))
    wrap_len = 0.0
    if cand_idx:
        cand = boundary_obstacles.iloc[cand_idx]
        merged = unary_union(cand.geometry.values)
        # linear obstacles: intersect with border_buf then measure length
        # polygonal greenery: intersect boundary with polygon (contact edge)
        try:
            inter = boundary.intersection(merged.buffer(8))
            wrap_len = inter.length if hasattr(inter, "length") else 0
        except Exception:
            wrap_len = 0.0
    c1 = min(1.0, wrap_len / perimeter) if perimeter > 0 else 0

    # c2: 진입로 희소성
    cand_e = list(edges_sindex.intersection(poly_m.buffer(5).bounds))
    crossings = 0
    if cand_e:
        cand_edges = edges.iloc[cand_e]
        for geom in cand_edges.geometry:
            if geom is None: continue
            if geom.crosses(boundary) or (geom.intersects(boundary) and not poly_m.contains(geom)):
                crossings += 1
    density_per_100m = crossings / (perimeter / 100.0) if perimeter > 0 else 0
    # 2/100m = 완전 개방. 0 = 완전 폐쇄
    c2 = max(0.0, 1.0 - density_per_100m / 2.0)

    # c3: 내부망 고립도 — 폴리곤 내부 엣지 그래프
    inner_idx = list(edges_sindex.intersection(poly_m.bounds))
    n_nodes = 0; n_edges = 0
    if inner_idx:
        inner_edges = edges.iloc[inner_idx]
        node_set = set()
        for (u, v, k), geom in zip(inner_edges.index, inner_edges.geometry):
            if geom is None: continue
            if poly_m.contains(geom) or poly_m.intersects(geom) and poly_m.buffer(-1).intersects(geom):
                node_set.add(u); node_set.add(v)
                n_edges += 1
        n_nodes = len(node_set)
    if n_nodes >= 3:
        beta = n_edges / n_nodes
        c3 = max(0.0, min(1.0, (1.6 - beta) / 0.8))
    else:
        c3 = 0.7  # 내부 도로 거의 없음 → 고립

    # c4: 주변 200m 용도 이질성
    ring = poly_m.buffer(BUFFER_M).difference(poly_m)
    ring_cands = list(landuse_sindex.intersection(ring.bounds))
    cat_area = Counter()
    if ring_cands:
        sub = landuse.iloc[ring_cands]
        for geom, cat in zip(sub.geometry, sub["cat"]):
            if geom is None: continue
            try:
                a = ring.intersection(geom).area
                if a > 0:
                    cat_area[cat] += a
            except Exception:
                pass
    total = sum(cat_area.values())
    if total > 0:
        H = 0.0
        for cat in ("res","com","ind","green"):
            p = cat_area.get(cat, 0) / total
            if p > 0:
                H -= p * math.log(p)
        c4 = H / math.log(4)
    else:
        c4 = 0.0

    score = 100 * (W1*c1 + W2*c2 + W3*c3 + W4*c4)
    return score, {"c1": round(c1,3), "c2": round(c2,3), "c3": round(c3,3), "c4": round(c4,3),
                   "n_nodes": n_nodes, "perimeter_m": round(perimeter,0)}


def grade(score):
    if score is None: return None
    if score >= CUT_HI: return "상"
    if score >= CUT_LO: return "중"
    return "하"


unclassified = []
computed_raw = {}  # sid -> (raw_score, detail)

for sid, v in polys_in.items():
    if not v.get("polygon"):
        continue
    mm = v.get("match_method", "")
    if mm == "circle_placeholder":
        v["enclosure_score"] = None
        v["enclosure_grade"] = None
        unclassified.append({
            "id": sid,
            "zone_name": v.get("zone_name"),
            "match_method": mm,
            "category": v.get("jaegebal_type") or v.get("jaegebal_detail_type"),
        })
        continue
    try:
        geom_wgs = shape(v["polygon"])
        gs = gpd.GeoSeries([geom_wgs], crs="EPSG:4326").to_crs(EPSG_M)
        poly_m = gs.iloc[0]
        if poly_m.is_empty or poly_m.area <= 0:
            raise ValueError("empty polygon")
        score, detail = compute_enclosure(poly_m)
        computed_raw[sid] = (score, detail)
        if len(computed_raw) % 50 == 0:
            log(f"  {len(computed_raw)}건 처리...")
    except Exception as e:
        log(f"  ! {sid}: {e}")
        v["enclosure_score"] = None
        v["enclosure_grade"] = None

# 분위 기반 선형 보정 → 65/35 절대 컷이 의미 있도록
raws = sorted([r for r, _ in computed_raw.values()])
if raws:
    p40 = raws[int(len(raws) * 0.40)]
    p80 = raws[int(len(raws) * 0.80)]
    span = max(1e-6, p80 - p40)
    log(f"  calibration: p40={p40:.1f} → 35, p80={p80:.1f} → 65 (span {span:.1f})")

    def calibrate(raw):
        return max(0.0, min(100.0, (raw - p40) / span * 30 + 35))
else:
    p40 = p80 = 0
    def calibrate(raw): return raw

grades_count = Counter()
for sid, (raw, detail) in computed_raw.items():
    adj = calibrate(raw)
    polys_in[sid]["enclosure_score"] = round(adj, 1)
    polys_in[sid]["enclosure_score_raw"] = round(raw, 1)
    polys_in[sid]["enclosure_grade"] = grade(adj)
    polys_in[sid]["enclosure_detail"] = detail
    grades_count[polys_in[sid]["enclosure_grade"]] += 1

computed = len(computed_raw)

# ── 수동 오버라이드 적용 ──
for sid, ov in MANUAL_ENCLOSURE_OVERRIDE.items():
    if sid in polys_in:
        before = polys_in[sid].get("enclosure_grade")
        polys_in[sid]["enclosure_grade"] = ov["grade"]
        polys_in[sid]["enclosure_score"] = ov["score"]
        log(f"  override: {sid} {before} → {ov['grade']} ({ov['score']})")

pdata["meta"]["enclosure_computed"] = True
pdata["meta"]["enclosure_weights"] = {"c1": W1, "c2": W2, "c3": W3, "c4": W4}
pdata["meta"]["enclosure_cuts"] = {"hi": CUT_HI, "lo": CUT_LO}
pdata["meta"]["enclosure_calibration"] = {"p40_raw": round(p40,1), "p80_raw": round(p80,1)}

# 저장
(DATA / "polygons.json").write_text(
    json.dumps(pdata, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
)
(DATA / "enclosure_unclassified.json").write_text(
    json.dumps({"total": len(unclassified), "items": unclassified}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

log(f"\n✅ 완료: 계산 {computed}건, 미분류 {len(unclassified)}건")
log(f"   등급 분포: {dict(grades_count)}")
