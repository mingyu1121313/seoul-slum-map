# 속성 필터 v2 — 경사·직주근접 재정의 (2026-04)

## 배경: v1 검증 실패 사례
| 마커 | 사용자 판정 | v1 결과 | 원인 |
|------|------------|---------|------|
| 사근동 꽃담벽화마을 | 경사지 | slope 10% (X) | 정점 부근 국소 경사만 봐서 누락 |
| 정릉골 | 경사지 | 미검출 (X) | 동일 |
| 두레마을 | 평지 | — | OK |
| 구룡·백사·양지 | 경사지 | 일부 누락 | 동일 |
| 백사마을→성수 | 직주근접 X (실 57분) | near (O) | 직선 12km 원이 너무 너그러움 |

## 결정 사항 (사용자 확정)
- 경사: **'주변 최저점 대비 고도차(relief)' 방식**, 임계값 **30m 이상**
- 직주근접: **ODsay Open API 실제 대중교통 라우팅**, 컷오프 40분
- UI: 필터 아코디언 안에 **이름 + 주소 + 태그** 평면 리스트

## 1. 경사지 재계산 — `scripts/build_slope.py` 재작성
1. 각 마커 반경 **600m 내 16개 지점** 샘플 (4방위 × 4단계 거리: 150·300·450·600m)
2. open-elevation 배치 호출로 모든 지점 고도 수집
3. `relief = center_elev − min(surrounding_16)`
4. 필드 갱신:
   - `relief_m` (정수)
   - `is_slope = relief_m >= 30`
   - 기존 `slope_pct`는 호환 위해 유지하되 판정엔 미사용
5. 검증 마커 6개 자동 출력 (구룡·백사·양지·정릉골·사근동·두레)로 결과 확인

## 2. 직주근접 재계산 — `scripts/build_proximity_odsay.py` 신규
1. `.env` 또는 `scripts/odsay_key.txt`에서 ODsay API 키 로드 (사용자 제공)
2. 8개 거점 좌표를 출발지로 두고, 각 마커를 도착지로 `searchPubTransPath` 호출
   - 호출 수: **유효 마커 470 + 18 = 488 × 8 = 3,904건** (1일 5,000건 이내)
   - `Content-Type: application/json`, `searchPathType=0`(전체)
   - 반환 `result.path[0].info.totalTime` → 분 단위
3. 각 마커에 필드 주입:
   - `near_minutes`: { "CBD": 32, "GBD": 41, ... } (분, 정수)
   - `near_hubs`:    [<= 40분인 hub id 목록]
   - `near_job`:     `len(near_hubs) > 0`
4. **레이트 리밋 보호**: 호출당 250ms sleep, 응답 캐시 `data/odsay_cache.json`
5. 실패한 호출은 None 처리, 재실행 시 캐시 사용
6. 기존 `data/isochrone_40min.geojson`은 삭제 (더 이상 안 씀)

## 3. 프론트엔드 — `index.html` 수정
1. 패널 `직주근접` 행을 거점명 + 분으로 표시
   - 예: `용산 28분, CBD 35분`
2. **필터 아코디언에 마커 리스트 추가**
   - `attr-filter-row` 옆 `cat-expand` 화살표 추가 → 클릭하면 매칭 마커 리스트 펼침
   - 리스트 아이템: `<이름>` + `<주소>` + `<태그>` (경사지는 `relief 35m`, 직주근접은 `용산 28분`)
   - 클릭 시 `showPanel()` + `map.panTo()` (기존 `cat-list-item` 동작 그대로)
3. 필터 토글 시 리스트도 다시 렌더 (현재 활성 필터 기준 매칭만 노출)
4. `buildSidebar()` 내 acc-c 본문 빌드 함수 분리: `buildAttrFilterBody(data)`

## 4. 검증
1. 데이터 전처리: `python scripts/build_slope.py && python scripts/build_proximity_odsay.py`
2. 자동 검증 출력으로 6개 케이스가 사용자 판정과 일치하는지 확인
3. 프리뷰: 경사지/직주근접 체크 → 리스트에서 백사마을·구룡마을·정릉골·사근동 표시 확인
4. 백사마을 패널: 직주근접에 성수가 없어야 함 (57분이라 컷오프 초과)

## 영향 받는 파일
- `scripts/build_slope.py` (재작성)
- `scripts/build_proximity_odsay.py` (신규, 기존 build_isochrone/tag_proximity 대체)
- `data/layerA.json`, `data/layerB.json` (필드 갱신)
- `data/odsay_cache.json` (신규, gitignore)
- `data/isochrone_40min.geojson` (삭제)
- `index.html` (패널 분 표시 + 필터 아코디언 리스트)

## 사용자에게 필요한 것
- **ODsay Open API 키 1개** — https://lab.odsay.com 회원가입 후 발급
- 키 경로: `scripts/odsay_key.txt` (1줄)
