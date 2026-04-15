#!/usr/bin/env python3
"""
build_moatown_layer.py
jaegebal_polygons.json에서 모아타운 활성 사업 추출 →
layerA.json 추가 + polygons.json 업데이트

Usage: python3 scripts/build_moatown_layer.py
"""
import json, math
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

# 제외할 stage (취소/철회/예비)
EXCLUDE_STAGES = {'대상지철회', '선정취소', '지정해제', '선정보류', '추진준비', '신청추진'}


def areas_to_geojson(areas):
    """jaegebal areas [[[lng,lat]...]] → GeoJSON"""
    if not areas:
        return None
    rings = [[[p[0], p[1]] for p in a] for a in areas]
    if len(rings) == 1:
        return {"type": "Polygon", "coordinates": [rings[0]]}
    return {"type": "MultiPolygon", "coordinates": [[r] for r in rings]}


def polygon_area_m2(areas):
    if not areas or not areas[0]:
        return 0.0
    coords = areas[0]
    lat0 = sum(p[1] for p in coords) / len(coords)
    mpd = 111_320
    mpd_lng = mpd * math.cos(math.radians(lat0))
    xs = [p[0] * mpd_lng for p in coords]
    ys = [p[1] * mpd for p in coords]
    s = sum(xs[i] * ys[(i+1) % len(coords)] - xs[(i+1) % len(coords)] * ys[i]
            for i in range(len(coords)))
    return abs(s) / 2


def main():
    jae = json.loads((DATA / "jaegebal_polygons.json").read_text(encoding="utf-8"))
    layerA = json.loads((DATA / "layerA.json").read_text(encoding="utf-8"))
    polys = json.loads((DATA / "polygons.json").read_text(encoding="utf-8"))

    # 기존 모아타운 ID 목록 (재실행 안전)
    existing_moa_ids = {it["id"] for it in layerA["items"] if it.get("category") == "모아타운"}

    # jaegebal에서 모아타운 추출
    moa_all = [d for d in jae["develops"].values()
               if (d.get("detail_type_display_name_short") or "") == "모아타운"]

    moa_active = [d for d in moa_all
                  if not (d.get("title") or "").startswith("(가)")
                  and (d.get("detail_stage") or "") not in EXCLUDE_STAGES]

    print(f"▶ 모아타운 전체: {len(moa_all)}건, 활성: {len(moa_active)}건")

    new_items = []
    new_polys = {}
    skipped = 0

    for d in moa_active:
        loc = d.get("location")
        if not loc or len(loc) < 2:
            skipped += 1
            continue

        sid = f"moa{d['id']}"
        if sid in existing_moa_ids:
            # 이미 있으면 폴리곤/stage만 갱신
            pass

        lng, lat = float(loc[0]), float(loc[1])
        title = d.get("title") or ""
        stage = d.get("detail_stage") or ""

        item = {
            "id": sid,
            "name": title,
            "lat": lat,
            "lng": lng,
            "category": "모아타운",
            "stage": stage,
        }
        new_items.append(item)

        # 폴리곤
        areas = d.get("areas")
        geom = areas_to_geojson(areas)
        area_m2 = polygon_area_m2(areas) if areas else 0.0

        new_polys[sid] = {
            "polygon": geom,
            "zone_name": title,
            "zone_area_m2": round(area_m2, 1),
            "jaegebal_id": d.get("id"),
            "jaegebal_type": "모아타운",
            "jaegebal_stage": stage,
            "match_method": "jaegebal_moa",
        }

    print(f"  좌표 없음 스킵: {skipped}건")
    print(f"  처리 완료: {len(new_items)}건")

    # layerA 업데이트: 기존 모아타운 제거 후 새로 삽입 (재실행 안전)
    non_moa = [it for it in layerA["items"] if it.get("category") != "모아타운"]
    layerA["items"] = non_moa + new_items
    layerA["meta"]["total_모아"] = len(new_items)
    (DATA / "layerA.json").write_text(
        json.dumps(layerA, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"▶ layerA.json: {len(layerA['items'])}건 ({len(non_moa)} 기존 + {len(new_items)} 모아타운)")

    # polygons.json 업데이트: 기존 moa 항목 제거 후 삽입
    for sid in list(polys["polygons"].keys()):
        if sid.startswith("moa"):
            del polys["polygons"][sid]
    polys["polygons"].update(new_polys)

    total_matched = sum(1 for v in polys["polygons"].values() if v.get("polygon"))
    polys["meta"]["matched"] = total_matched
    polys["meta"]["unmatched"] = len(polys["polygons"]) - total_matched

    (DATA / "polygons.json").write_text(
        json.dumps(polys, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    size_kb = (DATA / "polygons.json").stat().st_size // 1024
    print(f"▶ polygons.json: {len(polys['polygons'])}건 총 ({size_kb} KB)")
    print(f"  모아타운 폴리곤: {sum(1 for v in new_polys.values() if v.get('polygon'))}건")


if __name__ == "__main__":
    main()
