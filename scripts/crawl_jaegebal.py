#!/usr/bin/env python3
"""
crawl_jaegebal.py
jaegebal.com에서 서울 전체 정비사업 폴리곤 수집
- 25개 자치구 → regions/{code} → develop IDs
- 각 develops/{id} → SSR HTML에 embed된 areas(폴리곤) 파싱
결과: data/jaegebal_polygons.json

Usage: python3 scripts/crawl_jaegebal.py
"""
import json, re, time, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT  = ROOT / "data" / "jaegebal_polygons.json"
UA   = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
DELAY = 1.1  # robots.txt Crawl-delay 준수

# 서울 25개 자치구 법정동 코드
SEOUL_GU = [
    "11110","11140","11170","11200","11215","11230","11260","11290",
    "11305","11320","11350","11380","11410","11440","11470","11500",
    "11530","11545","11560","11590","11620","11650","11680","11710","11740",
]

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

def get_develop_ids(region_code):
    """regions/{code} 페이지에서 develop ID 수집"""
    html = fetch(f"https://jaegebal.com/regions/{region_code}")
    ids = set(re.findall(r'/develops/(\d+)', html))
    return sorted(int(i) for i in ids)

def parse_develop(develop_id):
    """develops/{id} 페이지에서 develop 객체 파싱"""
    html = fetch(f"https://jaegebal.com/develops/{develop_id}")
    # 앵커: \"develop\":{\"id\":NUM,...  SSR Flight payload에 embed됨
    m = re.search(r'\\"develop\\":\{(\\".*?\\"areas\\":\[\[\[.*?\]\]\])', html)
    if not m:
        return None
    block = m.group(1)
    # 필드 추출 (escaped)
    def fx(key, pat=r'\\"([^"\\]*)\\"'):
        m = re.search(r'\\"' + key + r'\\":' + pat, block)
        return m.group(1) if m else None
    def fxn(key):
        m = re.search(r'\\"' + key + r'\\":(\d+)', block)
        return int(m.group(1)) if m else None
    # areas: JSON 배열
    am = re.search(r'\\"areas\\":(\[\[\[.*?\]\]\])', block)
    areas = None
    if am:
        try:
            areas = json.loads(am.group(1).replace('\\"', '"'))
        except Exception:
            areas = None
    # location [lng,lat]
    lm = re.search(r'\\"location\\":\[([-\d.]+),([-\d.]+)\]', block)
    location = [float(lm.group(1)), float(lm.group(2))] if lm else None
    return {
        "id": fxn("id"),
        "title": fx("title"),
        "description": fx("description"),
        "region_code": fx("region_code"),
        "type": fx("type"),
        "type_display_name": fx("type_display_name"),
        "detail_type": fx("detail_type"),
        "detail_type_display_name": fx("detail_type_display_name"),
        "detail_type_display_name_short": fx("detail_type_display_name_short"),
        "stage": fx("stage"),
        "detail_stage": fx("detail_stage"),
        "location": location,
        "areas": areas,
    }

def main():
    # resume 지원: 이미 저장된 develops 스킵
    out = {"develops": {}, "meta": {"gu_scanned": 0, "generated": ""}}
    if OUT.exists():
        out = json.loads(OUT.read_text(encoding="utf-8"))
        print(f"기존 {len(out['develops'])}개 develop 재사용")
    seen_ids = set(out["develops"].keys())

    # 1. 각 자치구에서 develop ID 수집
    all_ids = set()
    for i, gu in enumerate(SEOUL_GU, 1):
        try:
            ids = get_develop_ids(gu)
            all_ids.update(ids)
            print(f"  [{i}/25] {gu}: {len(ids)}개 develop (누계 {len(all_ids)})")
        except Exception as e:
            print(f"  [{i}/25] {gu}: ERROR {e}")
        time.sleep(DELAY)

    new_ids = [i for i in sorted(all_ids) if str(i) not in seen_ids]
    print(f"\n총 develop: {len(all_ids)}개, 신규 파싱 대상: {len(new_ids)}개")

    # 2. 각 develop 상세 페이지 파싱
    ok = 0
    for i, did in enumerate(new_ids, 1):
        try:
            data = parse_develop(did)
            if data and data.get("areas") and data.get("location"):
                out["develops"][str(did)] = data
                ok += 1
                if i % 20 == 0:
                    # 20건마다 중간 저장
                    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            if i % 10 == 0 or i == len(new_ids):
                print(f"  [{i}/{len(new_ids)}] id={did} title={data['title'] if data else '?'} ok={ok}")
        except Exception as e:
            print(f"  [{i}/{len(new_ids)}] id={did} ERROR {e}")
        time.sleep(DELAY)

    out["meta"]["gu_scanned"] = len(SEOUL_GU)
    out["meta"]["generated"] = time.strftime("%Y-%m-%d %H:%M")
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\n▶ 저장: {OUT} ({OUT.stat().st_size//1024} KB)")
    print(f"  총 develop: {len(out['develops'])}개")

if __name__ == "__main__":
    main()
