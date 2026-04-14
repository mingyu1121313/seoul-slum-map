"""
build_proximity_odsay.py
────────────────────────────────────────────────────────────────
ODsay Open API로 각 마커 → 8개 직주 거점 간 실제 대중교통 시간을 계산해
layerA/B.json에 near_minutes, near_hubs, near_job 필드를 주입한다.

전략:
  • 직선거리 7.9km 이하인 마커-거점 쌍만 API 호출 (총 990건 이내)
    → 10km 이상 = 확실히 40분 초과 (백사마을→성수 10km=57분 검증됨)
  • 결과는 data/odsay_cache.json에 캐시 → 재실행 시 재사용
  • DAILY_LIMIT=950 hard cap (1000건 제한 여유)
────────────────────────────────────────────────────────────────
"""

import json, math, time, sys, os
import urllib.request, urllib.parse

ROOT         = "../data"
KEY_FILE     = "odsay_key.txt"
CACHE_FILE   = f"{ROOT}/odsay_cache.json"
CUTOFF_MIN   = 40      # 직주근접 판정 시간 (분)
MAX_KM       = 7.9     # 직선거리 사전 필터 (km)
DAILY_LIMIT  = 950     # 일일 호출 hard cap
SLEEP_S      = 0.25    # API 호출 간격 (초)

HUBS = [
    {"id": "CBD",     "name": "CBD (시청)",    "lat": 37.5665, "lng": 126.9780},
    {"id": "GBD",     "name": "GBD (강남)",    "lat": 37.4979, "lng": 127.0276},
    {"id": "YBD",     "name": "YBD (여의도)",  "lat": 37.5219, "lng": 126.9245},
    {"id": "Magok",   "name": "마곡",          "lat": 37.5585, "lng": 126.8295},
    {"id": "Seongsu", "name": "성수",          "lat": 37.5445, "lng": 127.0568},
    {"id": "Pangyo",  "name": "판교",          "lat": 37.3944, "lng": 127.1100},
    {"id": "Yongsan", "name": "용산",          "lat": 37.5298, "lng": 126.9644},
    {"id": "Sangam",  "name": "상암(DMC)",     "lat": 37.5828, "lng": 126.8896},
]


def haversine(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def load_api_key():
    path = os.path.join(os.path.dirname(__file__), KEY_FILE)
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def call_odsay(api_key, from_lat, from_lng, to_lat, to_lng):
    """
    ODsay searchPubTransPath 호출.
    반환: 총 이동 시간(분, int) 또는 None (경로 없음 / 오류)
    """
    encoded_key = urllib.parse.quote(api_key, safe='')
    url = (
        f"https://api.odsay.com/v1/api/searchPubTransPath"
        f"?apiKey={encoded_key}"
        f"&lang=0"
        f"&SX={from_lng}&SY={from_lat}"
        f"&EX={to_lng}&EY={to_lat}"
        f"&SearchType=0"
        f"&SearchPathType=0"
    )
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "Referer": "https://slum-seoul.xyz",
            "Origin":  "https://slum-seoul.xyz",
            "User-Agent": "Mozilla/5.0",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            paths = data.get("result", {}).get("path", [])
            if not paths:
                return None
            return int(paths[0]["info"]["totalTime"])
    except Exception as e:
        print(f"    ODsay 오류: {e}", file=sys.stderr)
        return None


def run():
    api_key = load_api_key()
    cache   = load_cache()

    # 마커 로드
    a = json.load(open(f"{ROOT}/layerA.json", encoding="utf-8"))
    b = json.load(open(f"{ROOT}/layerB.json", encoding="utf-8"))
    all_items = []
    for src, items in [("A", a["items"]), ("B", b["items"])]:
        for item in items:
            if item.get("lat") and item.get("lng"):
                all_items.append((src, item))

    # 호출 필요한 (item_id, hub_id) 쌍 목록 생성
    pairs_needed = []
    for (src, item) in all_items:
        item_id = item["id"]
        for h in HUBS:
            dist = haversine(item["lat"], item["lng"], h["lat"], h["lng"])
            if dist <= MAX_KM:
                key = f"{item_id}:{h['id']}"
                if key not in cache:
                    pairs_needed.append((item_id, item, h, dist))

    total_needed = len(pairs_needed)
    already_done = sum(
        1 for src, item in all_items
        for h in HUBS
        if f"{item['id']}:{h['id']}" in cache
    )

    print(f"캐시 완료: {already_done}건")
    print(f"오늘 호출 필요: {total_needed}건 (일일 한도: {DAILY_LIMIT}건)")

    if total_needed == 0:
        print("모두 완료 — 태깅 단계로 진행")
    elif total_needed > DAILY_LIMIT:
        print(f"  → 오늘은 {DAILY_LIMIT}건만 처리, 내일 재실행 필요")
        pairs_needed = pairs_needed[:DAILY_LIMIT]

    # API 호출
    call_count = 0
    for item_id, item, h, dist in pairs_needed:
        key = f"{item_id}:{h['id']}"
        minutes = call_odsay(api_key, item["lat"], item["lng"], h["lat"], h["lng"])
        cache[key] = minutes
        call_count += 1
        status = f"{minutes}분" if minutes is not None else "경로없음"
        print(f"  [{call_count}/{len(pairs_needed)}] {item.get('name','')[:20]:20s} → {h['id']:8s} {dist:.1f}km = {status}")
        save_cache(cache)
        time.sleep(SLEEP_S)

    print(f"\nODsay 호출 완료: {call_count}건")

    # ── 태깅 ────────────────────────────────────
    print("\n태깅 시작...")
    for src_letter, data_obj in [("A", a), ("B", b)]:
        for item in data_obj["items"]:
            item_id = item.get("id")
            if not item_id or not item.get("lat"):
                item["near_minutes"] = {}
                item["near_hubs"]    = []
                item["near_job"]     = False
                continue

            minutes_map = {}
            for h in HUBS:
                key   = f"{item_id}:{h['id']}"
                dist  = haversine(item["lat"], item["lng"], h["lat"], h["lng"])
                if dist > MAX_KM:
                    # 직선거리 초과 → 확실히 불가
                    minutes_map[h["id"]] = None
                elif key in cache:
                    minutes_map[h["id"]] = cache[key]  # 분 or None
                else:
                    minutes_map[h["id"]] = None  # 아직 미조회

            near_hubs = [hub_id for hub_id, mins in minutes_map.items()
                         if mins is not None and mins <= CUTOFF_MIN]

            item["near_minutes"] = {k: v for k, v in minutes_map.items() if v is not None}
            item["near_hubs"]    = near_hubs
            item["near_job"]     = len(near_hubs) > 0

    # 저장
    with open(f"{ROOT}/layerA.json", "w", encoding="utf-8") as f:
        json.dump(a, f, ensure_ascii=False, indent=2)
    with open(f"{ROOT}/layerB.json", "w", encoding="utf-8") as f:
        json.dump(b, f, ensure_ascii=False, indent=2)

    # 집계 리포트
    near_a = sum(1 for it in a["items"] if it.get("near_job"))
    near_b = sum(1 for it in b["items"] if it.get("near_job"))
    print(f"layerA 직주근접: {near_a}/{len(a['items'])}")
    print(f"layerB 직주근접: {near_b}/{len(b['items'])}")

    # 검증 케이스
    print("\n[직주근접 검증]")
    checks = [("백사", False), ("구룡", None), ("사근동", None), ("꽃담", None)]
    for keyword, expected in checks:
        for it in list(a["items"]) + list(b["items"]):
            if keyword in it.get("name", ""):
                print(f"  {it['name'][:30]:30s} near_job={it.get('near_job')}  hubs={it.get('near_hubs')}  minutes={it.get('near_minutes')}")
                break

    print("\n완료.")


if __name__ == "__main__":
    run()
