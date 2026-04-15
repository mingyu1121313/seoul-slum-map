#!/usr/bin/env python3
"""
match_uq120.py
urban.seoul.go.kr UQ120 데이터로 polygons.json 미매칭 사이트 보완
- 기존 jaegebal 344건 유지, 미매칭 144건만 대상
- 매칭 우선순위: ①이름 정규화 ②좌표 contains ③200m 최근접

Usage: python3 scripts/match_uq120.py
"""
import json, re, math
from pathlib import Path
from shapely.geometry import shape, Point

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

# 카테고리 → 대상 UQ120 bsnsCd 매핑
CAT_TO_CODES = {
    "가로주택정비":          ["BZ202"],
    "재개발(주택정비형)":    ["BZ103", "BZ102"],
    "주거환경개선(정비형)":  ["BZ108", "BZ107"],
    "지역주택":              [],  # UQ120에 없음 → placeholder에서 처리
    "형성유형":              [],  # UQ120에 없음 → osm_hull에서 처리
    "주거환경개선(관리형)":  ["BZ107", "BZ108"],  # type2에서 읽힘 (UI 비표시지만 데이터 완성)
}

def normalize(s):
    if not s: return ""
    s = s.replace(" ", "").replace("·", "").replace("(", "").replace(")", "")
    for kw in ["주택재개발정비사업조합", "재개발정비사업조합", "주택재개발정비사업",
               "재개발정비사업", "주거환경개선사업", "가로주택정비사업", "주택재건축사업",
               "재정비촉진구역", "재정비촉진지구", "정비구역", "주택재개발", "주거환경개선",
               "재건축", "재개발", "구역", "지구", "사업", "조합", "일대", "가로주택"]:
        s = s.replace(kw, "")
    s = re.sub(r"제(\d)", r"\1", s)
    s = re.sub(r"\([^)]*\)", "", s)
    return s.strip()

def haversine(lng1, lat1, lng2, lat2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1); dl = math.radians(lng2 - lng1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def centroid(geom):
    """GeoJSON geometry에서 centroid [lng, lat] 반환"""
    try:
        s = shape(geom)
        c = s.centroid
        return [c.x, c.y]
    except Exception:
        return None

def load_sites():
    sites = {}
    layerA = json.loads((DATA / "layerA.json").read_text(encoding="utf-8"))
    for it in layerA["items"]:
        if it.get("lat") and it.get("lng"):
            sites[it["id"]] = {
                "id": it["id"], "name": it.get("name",""),
                "lat": float(it["lat"]), "lng": float(it["lng"]),
                "category": it.get("category",""),
            }
    type2 = json.loads((DATA / "type2.json").read_text(encoding="utf-8"))
    for it in type2.get("관리형_진행중", {}).get("items", []):
        if it.get("lat") and it.get("lng"):
            sites[it["id"]] = {
                "id": it["id"], "name": it.get("name",""),
                "lat": float(it["lat"]), "lng": float(it["lng"]),
                "category": "주거환경개선(관리형)",
            }
    layerB = json.loads((DATA / "layerB.json").read_text(encoding="utf-8"))
    for it in layerB["items"]:
        if it.get("lat") and it.get("lng"):
            sites[it["id"]] = {
                "id": it["id"], "name": it.get("name",""),
                "lat": float(it["lat"]), "lng": float(it["lng"]),
                "category": "형성유형",
            }
    return sites

def main():
    polys = json.loads((DATA / "polygons.json").read_text(encoding="utf-8"))
    uq120 = json.loads((DATA / "uq120_features.json").read_text(encoding="utf-8"))
    sites = load_sites()

    features = list(uq120["features"].values())
    print(f"▶ UQ120 features: {len(features)}건")

    # 이름 인덱스 (정규화키 → features)
    name_idx = {}
    for f in features:
        key = normalize(f.get("dgm_nm",""))
        if key:
            name_idx.setdefault(key, []).append(f)

    # Shapely shapes 사전 생성 (contains 판별용)
    shapes = {}
    for f in features:
        try:
            shapes[f["present_sn"]] = shape(f["geometry"])
        except Exception:
            pass

    # 미매칭 사이트 목록
    unmatched_ids = [sid for sid, v in polys["polygons"].items() if not v.get("polygon")]
    print(f"▶ 미매칭: {len(unmatched_ids)}건 처리 중...")

    by_method = {"name": 0, "contains": 0, "coord": 0, "skip": 0}
    new_polys = 0

    for sid in unmatched_ids:
        site = sites.get(sid)
        if not site:
            by_method["skip"] += 1
            continue

        cat = site["category"]
        target_codes = CAT_TO_CODES.get(cat, [])
        if not target_codes:
            by_method["skip"] += 1
            continue

        # 대상 코드로 후보 필터링
        candidates = [f for f in features if f.get("sclas_cl") in target_codes]

        matched = None
        method = None

        # ① 이름 정규화 매칭 (정규화 일치 + 500m 이내)
        key = normalize(site["name"])
        if key and key in name_idx:
            for f in name_idx[key]:
                if f.get("sclas_cl") in target_codes:
                    c = centroid(f["geometry"])
                    if c:
                        dist = haversine(site["lng"], site["lat"], c[0], c[1])
                        if dist < 500:
                            matched = f; method = "name_uq120"; break

        # ② 좌표 contains (사이트 포인트가 폴리곤 내부)
        if not matched:
            pt = Point(site["lng"], site["lat"])
            for f in candidates:
                sn = f.get("present_sn")
                if sn in shapes and shapes[sn].contains(pt):
                    matched = f; method = "contains_uq120"; break

        # ③ 200m 최근접 (카테고리 일치 후보만)
        if not matched:
            best_d = 201; best_f = None
            for f in candidates:
                c = centroid(f["geometry"])
                if not c: continue
                d = haversine(site["lng"], site["lat"], c[0], c[1])
                if d < best_d:
                    best_d = d; best_f = f
            if best_f:
                matched = best_f; method = "coord_uq120"

        if matched:
            geom = matched["geometry"]
            polys["polygons"][sid] = {
                "polygon": geom,
                "zone_name": matched.get("dgm_nm") or site["name"],
                "zone_area_m2": round(matched.get("dgm_ar") or 0, 1),
                "uq120_sn": matched.get("present_sn"),
                "uq120_code": matched.get("sclas_cl"),
                "uq120_propel": matched.get("propel_cd"),
                "match_method": method,
            }
            key = method.split("_")[0]
            by_method[key] = by_method.get(key, 0) + 1
            new_polys += 1

    # 메타 업데이트
    total_matched = sum(1 for v in polys["polygons"].values() if v.get("polygon"))
    polys["meta"]["matched"] = total_matched
    polys["meta"]["unmatched"] = len(polys["polygons"]) - total_matched

    outpath = DATA / "polygons.json"
    outpath.write_text(json.dumps(polys, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"▶ 저장: data/polygons.json ({outpath.stat().st_size // 1024} KB)")
    print(f"  UQ120 신규 매칭: {new_polys}건")
    print(f"    이름: {by_method.get('name',0)}건 | contains: {by_method.get('contains',0)}건 | 좌표: {by_method.get('coord',0)}건")
    print(f"  스킵(지역주택/형성유형): {by_method['skip']}건")
    print(f"  최종 매칭: {total_matched} / {len(polys['polygons'])}건")
    remaining = [(sid, v) for sid, v in polys["polygons"].items() if not v.get("polygon")]
    print(f"  잔여 미매칭: {len(remaining)}건 (placeholder 대상)")

if __name__ == "__main__":
    main()
