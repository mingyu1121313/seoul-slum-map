#!/usr/bin/env python3
"""
match_jaegebal.py
내 488개 사이트와 jaegebal develops를 매칭하여 polygons.json 재생성
- 1차: 이름 유사도 (공백/'구역'/'제N' 등 정규화 후 매칭)
- 2차: 좌표 최근접 (200m 이내)
결과: data/polygons.json (build_bldg_age 는 이후 재실행)

Usage: python3 scripts/match_jaegebal.py
"""
import json, re, math
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
JAE  = DATA / "jaegebal_polygons.json"

def normalize(s):
    if not s: return ""
    s = s.replace(" ", "").replace("·", "")
    # 흔한 접미사 제거
    for kw in ["주택재개발정비사업조합", "재개발정비사업조합", "주택재개발정비사업",
               "재개발정비사업", "주거환경개선사업", "가로주택정비사업", "주택재건축사업",
               "재정비촉진구역", "재정비촉진지구", "정비구역", "주택재개발", "주거환경개선",
               "재건축", "재개발", "구역", "지구", "사업", "조합", "일대"]:
        s = s.replace(kw, "")
    # 제1, 제2 → 1, 2
    s = re.sub(r"제(\d)", r"\1", s)
    # (가), (제) 등 괄호 제거
    s = re.sub(r"\([^)]*\)", "", s)
    return s.strip()

def haversine(lng1, lat1, lng2, lat2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1); dl = math.radians(lng2 - lng1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def load_sites():
    sites = []
    layerA = json.loads((DATA / "layerA.json").read_text(encoding="utf-8"))
    for it in layerA["items"]:
        if it.get("lat") and it.get("lng"):
            sites.append({"id": it["id"], "name": it.get("name",""),
                          "lat": float(it["lat"]), "lng": float(it["lng"]),
                          "category": it.get("category",""), "source": "layerA"})
    t2 = json.loads((DATA / "type2.json").read_text(encoding="utf-8"))
    for it in t2["관리형_진행중"]["items"]:
        if it.get("lat") and it.get("lng"):
            sites.append({"id": it["id"], "name": it.get("name",""),
                          "lat": float(it["lat"]), "lng": float(it["lng"]),
                          "category": "주거환경개선(관리형)", "source": "type2"})
    layerB = json.loads((DATA / "layerB.json").read_text(encoding="utf-8"))
    for it in layerB["items"]:
        if it.get("lat") and it.get("lng"):
            sites.append({"id": it["id"], "name": it.get("name",""),
                          "lat": float(it["lat"]), "lng": float(it["lng"]),
                          "category": "형성유형", "source": "layerB"})
    return sites

def areas_to_geojson(areas):
    """jaegebal areas [[[lng,lat]...], ...] → GeoJSON Polygon/MultiPolygon"""
    if not areas: return None
    rings = [[[p[0], p[1]] for p in a] for a in areas]
    if len(rings) == 1:
        return {"type": "Polygon", "coordinates": [rings[0]]}
    return {"type": "MultiPolygon", "coordinates": [[r] for r in rings]}

def polygon_area_m2(areas):
    """간단한 planar approximation (Shoelace × cos(lat))"""
    if not areas or not areas[0]: return 0.0
    coords = areas[0]
    lat0 = sum(p[1] for p in coords) / len(coords)
    mpd_lat = 111_320
    mpd_lng = 111_320 * math.cos(math.radians(lat0))
    xs = [p[0] * mpd_lng for p in coords]
    ys = [p[1] * mpd_lat for p in coords]
    s = 0.0
    n = len(coords)
    for i in range(n):
        j = (i+1) % n
        s += xs[i]*ys[j] - xs[j]*ys[i]
    return abs(s) / 2

def main():
    jae = json.loads(JAE.read_text(encoding="utf-8"))
    develops = list(jae["develops"].values())
    print(f"▶ jaegebal develops: {len(develops)}개")

    # 이름 정규화 인덱스
    name_idx = {}
    for d in develops:
        key = normalize(d.get("title",""))
        if key: name_idx.setdefault(key, []).append(d)

    sites = load_sites()
    print(f"▶ 내 사이트: {len(sites)}개")

    out_polys = {}
    by_method = {"name": 0, "coord": 0, "unmatched": 0}

    for s in sites:
        matched = None
        method = None
        # 1차: 이름 매칭 (정규화 일치 + 좌표 500m 이내)
        key = normalize(s["name"])
        if key and key in name_idx:
            for d in name_idx[key]:
                if d["location"]:
                    dist = haversine(s["lng"], s["lat"], d["location"][0], d["location"][1])
                    if dist < 500:
                        matched = d; method = "name"; break
        # 2차: 좌표 최근접 (200m 이내)
        if not matched:
            best = None; best_d = 201
            for d in develops:
                if not d.get("location"): continue
                dist = haversine(s["lng"], s["lat"], d["location"][0], d["location"][1])
                if dist < best_d:
                    best = d; best_d = dist
            if best:
                matched = best; method = "coord"

        if matched:
            poly_geo = areas_to_geojson(matched["areas"])
            area_m2 = polygon_area_m2(matched["areas"])
            out_polys[s["id"]] = {
                "polygon": poly_geo,
                "zone_name": matched.get("title") or s["name"],
                "zone_area_m2": round(area_m2, 1),
                "jaegebal_id": matched.get("id"),
                "jaegebal_type": matched.get("type_display_name"),
                "jaegebal_detail_type": matched.get("detail_type_display_name_short") or matched.get("detail_type_display_name"),
                "jaegebal_stage": matched.get("detail_stage"),
                "match_method": method,
            }
            by_method[method] += 1
        else:
            out_polys[s["id"]] = {"polygon": None, "zone_name": None, "zone_area_m2": None}
            by_method["unmatched"] += 1

    out = {
        "meta": {
            "generated": jae["meta"].get("generated",""),
            "total_sites": len(sites),
            "matched": by_method["name"] + by_method["coord"],
            "unmatched": by_method["unmatched"],
            "source": "jaegebal.com crawl (develops/{id} SSR areas)",
        },
        "polygons": out_polys,
    }
    outpath = DATA / "polygons.json"
    outpath.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_kb = outpath.stat().st_size / 1024
    print(f"▶ 저장: data/polygons.json ({size_kb:.0f} KB)")
    print(f"  이름 매칭: {by_method['name']}건")
    print(f"  좌표 매칭: {by_method['coord']}건")
    print(f"  미매칭:    {by_method['unmatched']}건")

    # 카테고리별 매칭률
    from collections import Counter
    cat_total = Counter(); cat_matched = Counter()
    for s in sites:
        cat_total[s["category"]] += 1
        if out_polys[s["id"]]["polygon"]:
            cat_matched[s["category"]] += 1
    print("\n── 카테고리별 매칭률 ──")
    for cat in sorted(cat_total.keys()):
        t, m = cat_total[cat], cat_matched[cat]
        print(f"  {cat:25s} {m:3d}/{t:3d} ({m/t*100 if t else 0:.0f}%)")

if __name__ == "__main__":
    main()
