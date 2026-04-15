#!/usr/bin/env python3
"""
fetch_uq120.py
urban.seoul.go.kr ArcGIS FeatureServer(UPIS_C_UQ120)에서
서울 전체 정비사업 폴리곤 2,911건을 다운로드하여 캐시.

Usage: python3 scripts/fetch_uq120.py
결과:  data/uq120_features.json
"""
import json, time, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT  = ROOT / "data" / "uq120_features.json"

BASE  = "https://urban.seoul.go.kr/proxy/proxy.jsp?"
INNER = "http://98.33.2.225:6080/arcgis/rest/services/UPIS/20200526_WFS/MapServer/12/query"
UA    = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# 우리가 관심 있는 bsnsCd 목록 (BZ106·BZ605는 UI에서도 제외됨)
TARGET_CODES = [
    "BZ101", "BZ102", "BZ103", "BZ104", "BZ105",
    "BZ107", "BZ108",
    "BZ201", "BZ202", "BZ203", "BZ204", "BZ205",
    "BZ401", "BZ402",
    "BZ501",
]

def fetch_code(sclas_cl):
    """단일 SCLAS_CL 코드에 해당하는 모든 feature 조회"""
    # proxy.jsp는 raw URL을 그대로 forwarding — 내부 URL을 %xx 인코딩하면 403
    where_enc = urllib.parse.quote(f"SCLAS_CL='{sclas_cl}'", safe="=")
    inner = (
        f"http://98.33.2.225:6080/arcgis/rest/services/UPIS/20200526_WFS/MapServer/12/query"
        f"?where={where_enc}"
        f"&outFields=PRESENT_SN,DGM_NM,SCLAS_CL,SIGNGU_SE,DGM_AR,PROPEL_CD,GRP"
        f"&outSR=4326&f=geojson"
    )
    url = "https://urban.seoul.go.kr/proxy/proxy.jsp?" + inner
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": "https://urban.seoul.go.kr/view/map/main.html",
        "Accept": "application/json,*/*",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    all_features = {}  # present_sn → feature

    for code in TARGET_CODES:
        try:
            fc = fetch_code(code)
            feats = fc.get("features", [])
            ok = 0
            for f in feats:
                p = f.get("properties", {}) or {}
                sn = p.get("PRESENT_SN")
                if sn and f.get("geometry"):
                    all_features[sn] = {
                        "present_sn": sn,
                        "dgm_nm": p.get("DGM_NM"),
                        "sclas_cl": p.get("SCLAS_CL"),
                        "signgu_se": p.get("SIGNGU_SE"),
                        "dgm_ar": p.get("DGM_AR"),
                        "propel_cd": p.get("PROPEL_CD"),
                        "grp": p.get("GRP"),
                        "geometry": f["geometry"],  # GeoJSON, EPSG:4326
                    }
                    ok += 1
            print(f"  {code}: {ok}건")
        except Exception as e:
            print(f"  {code}: ERROR {e}")
        time.sleep(0.5)

    out = {
        "meta": {"generated": time.strftime("%Y-%m-%d %H:%M"), "total": len(all_features)},
        "features": all_features,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\n▶ 저장: {OUT} ({OUT.stat().st_size // 1024} KB), 총 {len(all_features)}건")

if __name__ == "__main__":
    main()
