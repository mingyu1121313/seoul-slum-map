"""
build_isochrone.py
8개 직주 거점에 대한 대중교통 40분 등시선을 근사 GeoJSON으로 생성한다.
─────────────────────────────────────────────────────────────────
방법: 서울 지하철 평균 실효 속도(문에서 문) ≈ 22 km/h (도보+대기 포함)
      40분 × 22 km/h = 14.7 km → 직선거리 12 km 보수적 반경 사용
      (직선 ↔ 경로 비율 1.3 감안)
결과: ../data/isochrone_40min.geojson  (FeatureCollection)
"""

import json, math

RADIUS_KM = 12          # 등시선 근사 반경 (km)
SEGMENTS  = 64          # 폴리곤 꼭짓점 수 (원 근사 정밀도)

HUBS = [
    {"id": "CBD",    "name": "CBD (시청)",    "lat": 37.5665, "lng": 126.9780},
    {"id": "GBD",    "name": "GBD (강남)",    "lat": 37.4979, "lng": 127.0276},
    {"id": "YBD",    "name": "YBD (여의도)",  "lat": 37.5219, "lng": 126.9245},
    {"id": "Magok",  "name": "마곡",          "lat": 37.5585, "lng": 126.8295},
    {"id": "Seongsu","name": "성수",          "lat": 37.5445, "lng": 127.0568},
    {"id": "Pangyo", "name": "판교",          "lat": 37.3944, "lng": 127.1100},
    {"id": "Yongsan","name": "용산",          "lat": 37.5298, "lng": 126.9644},
    {"id": "Sangam", "name": "상암(DMC)",     "lat": 37.5828, "lng": 126.8896},
]

R_EARTH = 6371.0  # km


def circle_polygon(center_lat, center_lng, radius_km, segments=SEGMENTS):
    """위경도 중심 기준 geodesic 원을 다각형 좌표로 반환 [[lng, lat], ...]"""
    coords = []
    for i in range(segments + 1):
        angle = math.radians(i * 360 / segments)
        d_lat = math.degrees(radius_km / R_EARTH)
        d_lng = math.degrees(radius_km / (R_EARTH * math.cos(math.radians(center_lat))))
        pt_lat = center_lat + d_lat * math.sin(angle)
        pt_lng = center_lng + d_lng * math.cos(angle)
        coords.append([round(pt_lng, 6), round(pt_lat, 6)])
    coords[-1] = coords[0]  # 폴리곤 닫기
    return coords


def build():
    features = []
    for hub in HUBS:
        coords = circle_polygon(hub["lat"], hub["lng"], RADIUS_KM)
        feature = {
            "type": "Feature",
            "properties": {
                "hub":    hub["id"],
                "name":   hub["name"],
                "radius_km": RADIUS_KM,
                "note":   "대중교통 40분 근사치 (직선거리 12km 원형 버퍼)"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        }
        features.append(feature)
        print(f"  {hub['name']:14s}  중심 ({hub['lat']}, {hub['lng']})  반경 {RADIUS_KM} km")

    fc = {"type": "FeatureCollection", "features": features}
    out = "../data/isochrone_40min.geojson"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
    print(f"\n저장: {out}  ({len(features)}개 거점)")


if __name__ == "__main__":
    build()
