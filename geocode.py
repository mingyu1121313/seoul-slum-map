#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Naver Geocoding REST API를 이용한 서울 저층주거지 좌표 일괄 처리
Output: data/layerA.json, data/layerB.json
"""

import json, time, re, sys, os
import urllib.request, urllib.parse, urllib.error

CLIENT_ID     = "sg8elx2o2n"
CLIENT_SECRET = "ZuWMFDjXLAP41bj5kkVoosq16pfQQ4WkkdyB0mT7"
GEOCODE_URL   = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"
BASE          = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(BASE, "data", "geocode_progress.json")

# ────────────────────────────────────────────────
# 지오코딩 코어
# ────────────────────────────────────────────────
def geocode(address: str):
    """주소 → (lat, lng) 또는 None. 실패시 None 반환."""
    clean = re.sub(r'\s*일대$', '', address.strip())
    # 복수 지번 "427, 435" → 첫 번째만
    clean = re.split(r',\s*\d', clean)[0].strip()

    query = urllib.parse.urlencode({"query": clean})
    url   = f"{GEOCODE_URL}?{query}"
    req   = urllib.request.Request(url)
    req.add_header("X-NCP-APIGW-API-KEY-ID", CLIENT_ID)
    req.add_header("X-NCP-APIGW-API-KEY",    CLIENT_SECRET)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
        addrs = data.get("addresses", [])
        if addrs:
            return float(addrs[0]["y"]), float(addrs[0]["x"])   # lat, lng
        return None
    except Exception as e:
        print(f"  [ERR] {address} → {e}", file=sys.stderr)
        return None


def geocode_with_retry(address: str, retries=2):
    for attempt in range(retries + 1):
        result = geocode(address)
        if result:
            return result
        if attempt < retries:
            time.sleep(1)
    return None

# ────────────────────────────────────────────────
# 진행 상황 저장/로드
# ────────────────────────────────────────────────
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_progress(cache: dict):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)

# ────────────────────────────────────────────────
# LAYER A — 레이어A 통합 (layerA_raw + type2 정비형)
# ────────────────────────────────────────────────
def build_layerA():
    cache = load_progress()

    # 1) layerA_raw.json 로드
    with open(os.path.join(BASE, "data", "layerA_raw.json"), encoding="utf-8") as f:
        raw = json.load(f)
    items = raw["items"]

    # 2) type2 정비형 18건 추가
    with open(os.path.join(BASE, "data", "type2.json"), encoding="utf-8") as f:
        t2 = json.load(f)
    for it in t2["정비형_진행중"]["items"]:
        items.append({
            "id":       it["id"],
            "gu":       it["gu"],
            "name":     it["name"],
            "address":  it["address"],
            "category": "주거환경개선사업",
            "stage":    it.get("stage", ""),
            "status":   it.get("status", "운영"),
            "lat":      None,
            "lng":      None
        })

    total = len(items)
    geocoded = 0
    failed   = 0

    print(f"\n[레이어A] 총 {total}건 지오코딩 시작")

    for i, it in enumerate(items):
        # 서울 gu 접두어가 없으면 붙이기
        addr = it["address"]
        if not addr.startswith("서울"):
            addr = f"서울특별시 {it['gu']} {addr}"

        # 캐시 확인
        if addr in cache:
            result = cache[addr]
        else:
            result = geocode_with_retry(addr)
            cache[addr] = result
            save_progress(cache)
            time.sleep(0.12)   # rate limit 대응

        if result:
            it["lat"] = result[0]
            it["lng"] = result[1]
            it["geocode_status"] = "ok"
            geocoded += 1
        else:
            it["lat"] = None
            it["lng"] = None
            it["geocode_status"] = "fail"
            failed += 1
            print(f"  [FAIL {i+1}/{total}] {it['name']} / {addr}")

        if (i + 1) % 50 == 0:
            print(f"  → {i+1}/{total} 완료 (성공 {geocoded}, 실패 {failed})")

    # 관리형 83건: 동 단위 → 대표좌표 추가 (별도 섹션)
    관리형_items = []
    for it in t2["관리형_진행중"]["items"]:
        dong_addr = it["address"]  # e.g. "서울특별시 강북구 미아동"
        if dong_addr in cache:
            result = cache[dong_addr]
        else:
            result = geocode_with_retry(dong_addr)
            cache[dong_addr] = result
            save_progress(cache)
            time.sleep(0.12)

        entry = {
            "id":       it["id"],
            "gu":       it["gu"],
            "dong":     it["dong"],
            "name":     it["name"],
            "address":  it["address"],
            "category": "주거환경개선사업",
            "subcategory": "관리형",
            "status":   it.get("status", "진행중"),
            "lat":      result[0] if result else None,
            "lng":      result[1] if result else None,
            "geocode_status": "dong_approx" if result else "fail",
            "img_ref":  it.get("img_ref", "")
        }
        관리형_items.append(entry)

    out = {
        "meta": {
            "total_정비": total,
            "total_관리": len(관리형_items),
            "geocoded": geocoded,
            "failed": failed,
            "updated": "2026-04",
            "note": "정비형(재개발/가로주택/지역주택/주거환경개선사업 정비형) + 관리형(동단위 대표좌표)"
        },
        "items": items,
        "items_관리형": 관리형_items
    }

    out_path = os.path.join(BASE, "data", "layerA.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n[레이어A] 완료 → data/layerA.json")
    print(f"  정비형 {total}건: 성공 {geocoded}, 실패 {failed}")
    print(f"  관리형 {len(관리형_items)}건: 동단위 대표좌표")
    return cache


# ────────────────────────────────────────────────
# LAYER B — 무허가정착지 (type1.json)
# ────────────────────────────────────────────────
# 형성경위 분류 (논문 기준: 자연발생/집단이주/신발생)
FORMATION_TYPE = {
    "mh01": "신발생",      # 구룡마을: 1980년대 자연발생적 무허가 정착
    "mh02": "집단이주",    # 백사마을: 1967년 청계천·용산 철거민 강제이주
    "mh03": "집단이주",    # 재건마을: 영동대교 빈민 강제이주
    "mh04": "집단이주",    # 헌인마을: 한센병 완치자 사회복귀 정착촌
    "mh05": "신발생",      # 수정마을: 구룡마을 인근 소규모 무허가
    "mh06": "신발생",      # 달터마을: 근린공원 내 무허가 점유
    "mh07": "자연발생",    # 현저동: 일제강점기 도시빈민 정착
    "mh08": "자연발생",    # 사근동 꽃담: 청계천변 판자촌
    "mh09": "집단이주",    # 정릉골: 청계천·북아현동 판자촌 정리 후 이주
}

def build_layerB(cache):
    with open(os.path.join(BASE, "data", "type1.json"), encoding="utf-8") as f:
        t1 = json.load(f)

    items = []
    geocoded = 0
    failed   = 0

    print(f"\n[레이어B] 총 {len(t1['items'])}건 지오코딩 시작")

    for it in t1["items"]:
        addr = it["address"]
        if not addr.startswith("서울"):
            addr = f"서울특별시 {it['gu']} {it['dong']} {addr}"

        if addr in cache:
            result = cache[addr]
        else:
            result = geocode_with_retry(addr)
            cache[addr] = result
            save_progress(cache)
            time.sleep(0.12)

        entry = {
            "id":            it["id"],
            "gu":            it["gu"],
            "dong":          it.get("dong", ""),
            "name":          it["name"],
            "address":       it["address"],
            "formation_type": FORMATION_TYPE.get(it["id"], "미분류"),
            "area_m2":       it.get("area_m2"),
            "formed":        it.get("formed", ""),
            "households":    it.get("households", ""),
            "status":        it.get("status", ""),
            "note":          it.get("note", ""),
            "source":        it.get("source", ""),
            "lat":           result[0] if result else None,
            "lng":           result[1] if result else None,
            "geocode_status": "ok" if result else "fail"
        }
        items.append(entry)

        if result:
            geocoded += 1
        else:
            failed += 1
            print(f"  [FAIL] {it['name']} / {addr}")

    out = {
        "meta": {
            "type": "무허가정착지",
            "total": len(items),
            "geocoded": geocoded,
            "failed": failed,
            "updated": "2026-04",
            "note": "자연발생/집단이주/신발생 분류. 31개 목표 중 현재 9건."
        },
        "items": items
    }

    out_path = os.path.join(BASE, "data", "layerB.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n[레이어B] 완료 → data/layerB.json")
    print(f"  {len(items)}건: 성공 {geocoded}, 실패 {failed}")


# ────────────────────────────────────────────────
# 메인
# ────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== 서울 저층주거지 지오코딩 시작 ===")
    print(f"Client ID: {CLIENT_ID}")
    cache = build_layerA()
    build_layerB(cache)
    print("\n=== 전체 완료 ===")
