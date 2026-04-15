#!/usr/bin/env python3
"""
build_osm_hull.py
형성유형(layerB) 미매칭 사이트에 대해 OSM Overpass API로
반경 300m 내 building footprint 수집 후 concave hull 생성.

Usage: python3 scripts/build_osm_hull.py
"""
import json, time, urllib.request, math
from pathlib import Path
from shapely import concave_hull
from shapely.geometry import shape, MultiPolygon, Polygon, mapping, MultiPoint
from shapely.ops import unary_union

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
UA   = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
RADIUS = 300  # m


def overpass_buildings(lat, lng, radius=RADIUS):
    """반경 내 OSM building polygon footprint 수집"""
    query = f"""
[out:json][timeout:30];
(
  way(around:{radius},{lat},{lng})[building];
  relation(around:{radius},{lat},{lng})[building];
);
out geom;
""".strip()
    data = query.encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL, data=data,
        headers={"User-Agent": UA, "Content-Type": "text/plain"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


def osm_way_to_polygon(element):
    """OSM way geometry → Shapely Polygon"""
    geom = element.get("geometry", [])
    coords = [(g["lon"], g["lat"]) for g in geom if "lon" in g]
    if len(coords) < 3:
        return None
    try:
        return Polygon(coords)
    except Exception:
        return None


def osm_to_geojson(shp):
    """Shapely → GeoJSON dict"""
    return mapping(shp)


def hull_from_buildings(polys_list, lat, lng, ratio=0.3):
    """건물 폴리곤 목록 → concave hull (or fallback to 150m circle)"""
    if not polys_list:
        return None
    try:
        union = unary_union(polys_list)
        buffered = union.buffer(0.00005)  # ~5m buffer
        hull = concave_hull(buffered, ratio=ratio)
        return hull
    except Exception:
        return None


def circle_polygon(lat, lng, radius_m=150, n=32):
    """fallback: 원형 근사 Polygon"""
    R = 6371000
    dphi = 2 * math.pi / n
    coords = []
    for i in range(n):
        angle = i * dphi
        dlat = (radius_m / R) * math.cos(angle)
        dlng = (radius_m / R) * math.sin(angle) / math.cos(math.radians(lat))
        coords.append((lng + math.degrees(dlng), lat + math.degrees(dlat)))
    coords.append(coords[0])
    return Polygon(coords)


def main():
    polys = json.loads((DATA / "polygons.json").read_text(encoding="utf-8"))
    layerB = json.loads((DATA / "layerB.json").read_text(encoding="utf-8"))

    site_map = {it["id"]: it for it in layerB["items"]}
    b_ids = set(site_map.keys())

    unmatched = [
        sid for sid in b_ids
        if sid in polys["polygons"] and not polys["polygons"][sid].get("polygon")
    ]
    print(f"▶ 형성유형 미매칭: {len(unmatched)}건")

    ok = 0
    fallback = 0

    for sid in unmatched:
        s = site_map[sid]
        lat = float(s["lat"]); lng = float(s["lng"])
        name = s.get("name", sid)

        try:
            result = overpass_buildings(lat, lng, RADIUS)
            elements = result.get("elements", [])
            bldg_polys = [p for e in elements if e.get("type") == "way" for p in [osm_way_to_polygon(e)] if p]
            print(f"  {name}: {len(bldg_polys)}개 건물 →", end=" ")

            if bldg_polys:
                hull = hull_from_buildings(bldg_polys, lat, lng)
            else:
                hull = None

            if hull is None or hull.is_empty:
                hull = circle_polygon(lat, lng, 150)
                method = "circle_placeholder"
                fallback += 1
                print("fallback 원형")
            else:
                method = "osm_hull"
                ok += 1
                print(f"hull ({hull.geom_type})")

            polys["polygons"][sid] = {
                "polygon": osm_to_geojson(hull),
                "zone_name": name,
                "zone_area_m2": round(hull.area * 111320 * 111320 * math.cos(math.radians(lat)), 1),
                "match_method": method,
                "approximate": True,
            }
        except Exception as e:
            print(f"  {name}: ERROR {e} → circle fallback")
            hull = circle_polygon(lat, lng, 150)
            polys["polygons"][sid] = {
                "polygon": osm_to_geojson(hull),
                "zone_name": name,
                "zone_area_m2": 0,
                "match_method": "circle_placeholder",
                "approximate": True,
            }
            fallback += 1

        time.sleep(1.2)  # Overpass rate limit 준수

    # 메타 업데이트
    total_matched = sum(1 for v in polys["polygons"].values() if v.get("polygon"))
    polys["meta"]["matched"] = total_matched
    polys["meta"]["unmatched"] = len(polys["polygons"]) - total_matched

    outpath = DATA / "polygons.json"
    outpath.write_text(json.dumps(polys, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\n▶ 저장: {outpath} ({outpath.stat().st_size // 1024} KB)")
    print(f"  OSM hull: {ok}건 | 원형 fallback: {fallback}건")
    print(f"  최종 매칭: {total_matched} / {len(polys['polygons'])}건")


if __name__ == "__main__":
    main()
