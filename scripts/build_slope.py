"""
build_slope.py  (v2 — relief 방식)
────────────────────────────────────────────────────────────────
각 마커 주변 600m 내 16개 지점(8방위 × 2거리)의 고도를 open-elevation API로 수집해
'주변 최저점 대비 고도차(relief)'를 계산한다.

  relief_m = center_elev − min(surrounding_16)
  is_slope  = relief_m >= 30

이전 slope_pct(국소 경사도) 방식은 언덕 정상부처럼 평탄한 마을을 놓쳤으나,
relief 방식은 주변 평지 대비 상대 고도를 보므로 경사지 판정이 더 정확하다.
────────────────────────────────────────────────────────────────
"""

import json, math, time, sys
import urllib.request, urllib.error

ROOT      = "../data"
THRESHOLD = 30          # relief 임계값 (m)
RADII     = [300, 600]  # 샘플링 거리 (m)
DIRS      = [            # 8방위 (lat 방향, lng 방향)
    (1, 0), (1, 1), (0, 1), (-1, 1),
    (-1, 0), (-1, -1), (0, -1), (1, -1),
]
BATCH     = 100
RETRY     = 3

LAT_PER_M = 1 / 111_000
LNG_PER_M = 1 / (111_000 * math.cos(math.radians(37.5)))

# 결과 검증용 기준 케이스 (마커 id 또는 이름 일부)
VERIFY_CASES = {
    "구룡": True,   # 경사지 O
    "백사": True,   # 경사지 O
    "양지": True,   # 경사지 O
    "두레": False,  # 경사지 X
    "꽃담": True,   # 경사지 O (사근동)
    "정릉": True,   # 경사지 O
}

# ── 수동 오버라이드 (경사지 판정) ──
# relief 단독 기준이 borderline(15-30m)이면서 slope_pct가 낮은(<5%) 평지를
# 경사지로 잘못 분류한 경우 수동으로 false 처리.
MANUAL_SLOPE_OVERRIDE = {
    "la0432": False,  # 공덕6구역 (relief 15·slope 4% — 평지 위성영상 확인)
}


def sample_points(lat, lng):
    """중심 + 8방위×2거리 = 17개 좌표 반환 [(lat,lng), ...]"""
    pts = [(lat, lng)]
    for dist in RADII:
        for (dlat, dlng) in DIRS:
            # 대각선은 sqrt(2) 로 나눠 실제 거리 유지
            scale = 1 / math.sqrt(dlat**2 + dlng**2 + 1e-9)
            pts.append((
                lat + dlat * scale * dist * LAT_PER_M,
                lng + dlng * scale * dist * LNG_PER_M,
            ))
    return pts  # 17개


def fetch_elevations(locations):
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
                return [r["elevation"] for r in json.loads(resp.read())["results"]]
        except Exception as e:
            print(f"  [retry {attempt+1}] {e}", file=sys.stderr)
            time.sleep(2 ** attempt)
    return None


def process_file(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # items + items_관리형 모두 수집 (관리형은 layerA에만 존재)
    all_items = list(data.get("items", []))
    if "items_관리형" in data:
        all_items.extend(data["items_관리형"])

    # 이미 relief_m가 있는 항목은 스킵 (수동 보정·기존 결과 보존)
    valid = [it for it in all_items
             if it.get("lat") and it.get("lng") and "relief_m" not in it]
    print(f"  {path}: 신규 처리 대상 {len(valid)} / 전체 {len(all_items)}")

    if not valid:
        print(f"  → 처리할 항목 없음, 검증만 수행")

    # 전체 샘플 포인트 수집 (item 인덱스 대신 dict 레퍼런스로 추적)
    all_refs = []   # item dict 참조
    all_locs = []   # {"latitude": ..., "longitude": ...}
    N_PTS = 1 + len(RADII) * len(DIRS)  # 17

    for item in valid:
        for (la, lo) in sample_points(item["lat"], item["lng"]):
            all_refs.append(item)
            all_locs.append({"latitude": la, "longitude": lo})

    # 배치 API 호출
    all_elevs = []
    total = len(all_locs)
    for start in range(0, total, BATCH):
        batch = all_locs[start:start + BATCH]
        pct   = (start + len(batch)) / total * 100
        print(f"    고도 {start+len(batch)}/{total} ({pct:.0f}%) ...", end=" ", flush=True)
        elevs = fetch_elevations(batch)
        if elevs is None:
            print("FAIL (None)")
            elevs = [None] * len(batch)
        else:
            print("OK")
        all_elevs.extend(elevs)
        time.sleep(0.4)

    # N_PTS 단위로 묶어서 relief 계산 (item dict 레퍼런스로 직접 기록)
    for chunk_start in range(0, len(all_elevs), N_PTS):
        chunk    = all_elevs[chunk_start:chunk_start + N_PTS]
        item_ref = all_refs[chunk_start]
        if any(v is None for v in chunk):
            item_ref["relief_m"] = None
            item_ref["is_slope"] = False
        else:
            center   = chunk[0]
            surround = chunk[1:]
            relief   = round(center - min(surround))
            item_ref["relief_m"] = relief
            item_ref["is_slope"] = relief >= THRESHOLD

    # 집계
    flagged = sum(1 for it in all_items if it.get("is_slope"))
    print(f"  → 경사지(누적): {flagged} / {len(all_items)} (relief ≥ {THRESHOLD}m)")

    # 검증 케이스 출력
    print("  [검증]")
    for it in all_items:
        key = it.get("name", "")
        for kw, expected in VERIFY_CASES.items():
            if kw in key:
                actual = it.get("is_slope", False)
                mark = "OK" if actual == expected else "FAIL"
                print(f"    {mark} {key[:30]:30s} relief={it.get('relief_m')}m  is_slope={actual}  expected={expected}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  저장: {path}")


if __name__ == "__main__":
    for fname in ("layerA.json", "layerB.json"):
        print(f"\n=== {fname} ===")
        process_file(f"{ROOT}/{fname}")
    print("\n완료.")
