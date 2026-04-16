# 폐쇄성 수동 오버라이드 (현저동)

## 배경
- 현저동(jb03, moa1350)은 실측상 달동네 + 산으로 둘러싸임 + 차 못 가는 골목 + 대로·학교로 단절
- 자동 계산 결과: 49.5점 / **중** (c1 0.225, c2 0.0, c3 0.0, c4 0.497)
- 원인: OSM 도로망이 차 못 다니는 좁은 골목까지 잡아서 c3=0, 인왕산 녹지 OSM 태깅이 구역 경계에 직접 붙지 않아 c1 저평가
- 해결: 직주근접(`MANUAL_NEAR_OVERRIDE`)과 동일한 화이트리스트 패턴

## 수정 대상 (둘 다 같은 구역)
- `jb03` 현저2
- `moa1350` 현저동 1-5

## 목표 값
- `enclosure_grade`: "중" → **"상"**
- `enclosure_score`: 49.5 → **70** (상 등급 컷 65 넘는 적정값)
- `enclosure_score_raw`: 그대로 유지 (참고용)
- `enclosure_detail`: 그대로 유지

## 수정 지점 2곳
1. **`data/polygons.json`** 직접 패치 — 즉시 반영
2. **`scripts/build_enclosure.py`** 말미에 `MANUAL_ENCLOSURE_OVERRIDE` 블록 추가 — 재빌드 시 자동 재적용

### 스크립트 오버라이드 스니펫
```python
MANUAL_ENCLOSURE_OVERRIDE = {
    "jb03":    {"grade": "상", "score": 70.0},
    "moa1350": {"grade": "상", "score": 70.0},
}
for sid, ov in MANUAL_ENCLOSURE_OVERRIDE.items():
    if sid in polys_in:
        polys_in[sid]["enclosure_grade"] = ov["grade"]
        polys_in[sid]["enclosure_score"] = ov["score"]
```
`polygons.json` 저장 직전에 삽입.

## 검증
- 속성 필터 "폐쇄성 상" 카운트 107 → 109 (2건 증가)
- 지도 폴리곤 클릭 시 상세 패널에 "상 (70)" 표시
- 크롬 MCP로 배포 사이트에서 확인
