#!/usr/bin/env python3
"""
add_placeholder_circles.py
polygons.json에서 아직 polygon이 없는 모든 사이트에
150m 반경 32각형 원형 placeholder 추가.
(주로 지역주택 38건 + UQ120/OSM에서도 실패한 잔여분)

Usage: python3 scripts/add_placeholder_circles.py
"""
import json, math
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"


def circle_polygon(lat, lng, radius_m=150, n=32):
    """32각형 원형 GeoJSON Polygon"""
    R = 6371000
    dphi = 2 * math.pi / n
    coords = []
    for i in range(n):
        angle = i * dphi
        dlat = (radius_m / R) * math.cos(angle)
        dlng = (radius_m / R) * math.sin(angle) / math.cos(math.radians(lat))
        coords.append([lng + math.degrees(dlng), lat + math.degrees(dlat)])
    coords.append(coords[0])
    area_m2 = math.pi * radius_m ** 2
    return {"type": "Polygon", "coordinates": [coords]}, round(area_m2, 1)


def load_all_sites():
    """모든 사이트 ID → {name, lat, lng} 매핑"""
    sites = {}
    layerA = json.loads((DATA / "layerA.json").read_text(encoding="utf-8"))
    for it in layerA["items"]:
        if it.get("lat") and it.get("lng"):
            sites[it["id"]] = {"name": it.get("name", ""), "lat": float(it["lat"]), "lng": float(it["lng"])}
    type2 = json.loads((DATA / "type2.json").read_text(encoding="utf-8"))
    for it in type2.get("관리형_진행중", {}).get("items", []):
        if it.get("lat") and it.get("lng"):
            sites[it["id"]] = {"name": it.get("name", ""), "lat": float(it["lat"]), "lng": float(it["lng"])}
    layerB = json.loads((DATA / "layerB.json").read_text(encoding="utf-8"))
    for it in layerB["items"]:
        if it.get("lat") and it.get("lng"):
            sites[it["id"]] = {"name": it.get("name", ""), "lat": float(it["lat"]), "lng": float(it["lng"])}
    return sites


def main():
    polys = json.loads((DATA / "polygons.json").read_text(encoding="utf-8"))
    sites = load_all_sites()

    unmatched = [sid for sid, v in polys["polygons"].items() if not v.get("polygon")]
    print(f"▶ placeholder 대상: {len(unmatched)}건")

    ok = 0
    for sid in unmatched:
        s = sites.get(sid)
        if not s:
            print(f"  {sid}: 좌표 없음, 스킵")
            continue

        geom, area = circle_polygon(s["lat"], s["lng"])
        polys["polygons"][sid] = {
            "polygon": geom,
            "zone_name": s["name"],
            "zone_area_m2": area,
            "match_method": "circle_placeholder",
            "approximate": True,
        }
        ok += 1

    # 메타 업데이트
    total_matched = sum(1 for v in polys["polygons"].values() if v.get("polygon"))
    polys["meta"]["matched"] = total_matched
    polys["meta"]["unmatched"] = len(polys["polygons"]) - total_matched

    outpath = DATA / "polygons.json"
    outpath.write_text(json.dumps(polys, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"▶ 저장: {outpath} ({outpath.stat().st_size // 1024} KB)")
    print(f"  circle_placeholder 추가: {ok}건")
    print(f"  최종 매칭: {total_matched} / {len(polys['polygons'])}건")

    # 여전히 누락된 항목 확인
    still_missing = [sid for sid, v in polys["polygons"].items() if not v.get("polygon")]
    if still_missing:
        print(f"  ⚠ 여전히 누락: {still_missing}")
    else:
        print("  ✓ 전체 488건 모두 polygon 확정")


if __name__ == "__main__":
    main()
