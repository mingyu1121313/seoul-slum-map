"""
tag_proximity.py
등시선 GeoJSON(isochrone_40min.geojson)과 layerA/B.json을 읽어
각 마커가 1개 이상의 등시선 폴리곤 안에 들어오면 near_job:true, near_hubs:[...] 추가.
순수 표준 라이브러리 ray-casting 알고리즘 사용 (shapely 불필요).
"""

import json

DATA = "../data"


def point_in_polygon(px, py, polygon):
    """
    ray-casting 알고리즘.
    polygon: [[lng, lat], ...] (GeoJSON 좌표 순서)
    px=경도, py=위도
    """
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        intersect = ((yi > py) != (yj > py)) and \
                    (px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi)
        if intersect:
            inside = not inside
        j = i
    return inside


def load_isochrones():
    with open(f"{DATA}/isochrone_40min.geojson", encoding="utf-8") as f:
        fc = json.load(f)
    polys = []
    for feat in fc["features"]:
        ring = feat["geometry"]["coordinates"][0]
        polys.append({
            "hub":  feat["properties"]["hub"],
            "name": feat["properties"]["name"],
            "ring": ring,
        })
    return polys


def tag_file(path, polys):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    near_count = 0
    for item in data["items"]:
        lat = item.get("lat")
        lng = item.get("lng")
        if not lat or not lng:
            item["near_job"]  = False
            item["near_hubs"] = []
            continue

        matched = []
        for p in polys:
            if point_in_polygon(lng, lat, p["ring"]):
                matched.append(p["hub"])

        item["near_job"]  = len(matched) > 0
        item["near_hubs"] = matched
        if matched:
            near_count += 1

    print(f"  {path}: 직주근접 {near_count} / {len(data['items'])} 마커")
    for p in polys:
        cnt = sum(1 for it in data["items"] if p["hub"] in it.get("near_hubs", []))
        print(f"    {p['name']:14s}: {cnt}개")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  저장: {path}")


if __name__ == "__main__":
    polys = load_isochrones()
    print(f"등시선 {len(polys)}개 로드")
    for fname in ("layerA.json", "layerB.json"):
        print(f"\n=== {fname} ===")
        tag_file(f"{DATA}/{fname}", polys)
    print("\n완료.")
