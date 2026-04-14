"""
build_slope.py
각 마커 좌표 주변 5개 지점(중심 + N/S/E/W 150m)의 고도를 open-elevation API로 조회해
최대 경사도(%)를 계산하고 layerA.json / layerB.json에 slope_pct, is_slope 필드를 추가한다.
임계값: 15% 이상 = 경사지 (is_slope: true)
"""

import json, math, time, sys
import urllib.request

ROOT = "../data"
THRESHOLD = 15          # 경사지 판정 임계값 (%)
OFFSET_M  = 150         # 샘플링 반경 (m)
BATCH     = 100         # API 1회 요청당 최대 좌표 수
RETRY     = 3

LAT_PER_M  = 1 / 111_000          # 위도 1m ≈ 0.000009 deg
LNG_PER_M  = 1 / (111_000 * math.cos(math.radians(37.5)))  # 서울 위도 기준


def sample_points(lat, lng):
    """중심 + 상하좌우 150m 오프셋 5개 반환 [(lat, lng), ...]"""
    d_lat = OFFSET_M * LAT_PER_M
    d_lng = OFFSET_M * LNG_PER_M
    return [
        (lat,          lng),
        (lat + d_lat,  lng),
        (lat - d_lat,  lng),
        (lat,          lng + d_lng),
        (lat,          lng - d_lng),
    ]


def fetch_elevations(locations):
    """
    locations: [{"latitude": f, "longitude": f}, ...]
    반환: [elevation_float, ...] (실패 시 None)
    """
    body = json.dumps({"locations": locations}).encode()
    req  = urllib.request.Request(
        "https://api.open-elevation.com/api/v1/lookup",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    for attempt in range(RETRY):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return [r["elevation"] for r in data["results"]]
        except Exception as e:
            print(f"  [retry {attempt+1}/{RETRY}] {e}", file=sys.stderr)
            time.sleep(2 ** attempt)
    return None


def max_slope_pct(elevations):
    """5개 지점 고도 → 인접 방향 최대 경사 (%)"""
    c, n, s, e, w = elevations
    d = OFFSET_M  # 거리 (m)
    slopes = [
        abs(n - c) / d * 100,
        abs(s - c) / d * 100,
        abs(e - c) / d * 100,
        abs(w - c) / d * 100,
    ]
    return round(max(slopes), 1)


def process_file(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    items = data["items"]
    valid = [(i, it) for i, it in enumerate(items) if it.get("lat") and it.get("lng")]
    print(f"  {path}: {len(valid)} / {len(items)} 유효 마커")

    # 모든 샘플 포인트를 1차원 리스트로 수집 (배치 처리를 위해)
    all_requests = []   # (item_idx, point_idx)
    all_locs     = []   # {"latitude": ..., "longitude": ...}

    for i, item in valid:
        for (la, lo) in sample_points(item["lat"], item["lng"]):
            all_requests.append(i)
            all_locs.append({"latitude": la, "longitude": lo})

    # 배치 단위로 API 호출
    all_elevations = []
    total = len(all_locs)
    for start in range(0, total, BATCH):
        batch = all_locs[start:start + BATCH]
        pct   = (start + len(batch)) / total * 100
        print(f"    고도 조회 {start + len(batch)}/{total} ({pct:.0f}%) ...", end=" ", flush=True)
        elevs = fetch_elevations(batch)
        if elevs is None:
            print("실패 — 해당 배치는 None으로 처리")
            elevs = [None] * len(batch)
        else:
            print("OK")
        all_elevations.extend(elevs)
        time.sleep(0.5)  # API 레이트 리밋 완화

    # 5개 단위로 묶어 item별 slope 계산
    for chunk_start in range(0, len(all_elevations), 5):
        chunk = all_elevations[chunk_start:chunk_start + 5]
        item_idx = all_requests[chunk_start]
        if any(v is None for v in chunk):
            items[item_idx]["slope_pct"]  = None
            items[item_idx]["is_slope"]   = False
        else:
            sp = max_slope_pct(chunk)
            items[item_idx]["slope_pct"]  = sp
            items[item_idx]["is_slope"]   = sp >= THRESHOLD

    # 집계
    flagged = sum(1 for it in items if it.get("is_slope"))
    print(f"  → 경사지 판정: {flagged} 곳 (slope_pct ≥ {THRESHOLD}%)")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  저장 완료: {path}")


if __name__ == "__main__":
    for fname in ("layerA.json", "layerB.json"):
        print(f"\n=== {fname} ===")
        process_file(f"{ROOT}/{fname}")
    print("\n완료.")
