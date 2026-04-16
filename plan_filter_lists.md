# 속성 필터 확장 리스트 복구/추가 플랜

## 문제
- **경사지·직주근접**: 화살표 펼쳐도 리스트 비어있음.
  원인: `buildAttrFilterBody()`가 `markersByCategory`만 순회하는데
  488건이 폴리곤화된 뒤 마커가 사라져 `slopeItems/nearItems = []`.
- **노후도·폐쇄성**: 버튼(10+/20+/30+/40+, 상/중/하)만 있고 리스트 없음.

## 수정 (index.html)

### A. `buildAttrFilterBody()` (≈L1727)
- `polygonsByCategory` 순회 추가: `itemsByPolygon.get(poly)` 로 item 수집
- 중복 방지: 이미 포함된 item은 skip (marker+polygon 양쪽 등록 케이스)

### B. 노후도 리스트
- HTML(`<!-- 노후도 필터 -->` 블록): 각 버튼에 `<span class="cat-expand" ... onclick="toggleAgeList(...)">` 추가는 레이아웃을 해치므로 **버튼 클릭 시 동일 리스트 영역 하나를 공유**하는 방식 채택
- `<div class="cat-list" id="attr-list-age">` 블록 추가
- `buildAttrFilterBody()`에서 현재 `ageFilter` 값 기준으로 `item.avg_age >= ageFilter`인 항목 수집 → 리스트 채움
- `setAgeFilter()`에서 `buildAttrFilterBody()` 호출하여 리스트 갱신
- 화살표 토글: 필터 그룹 우측에 `▶` 추가 → `toggleAttrList('age', e)` 재사용 (`cat-list` 클래스 공통)

### C. 폐쇄성 리스트 (동일 패턴)
- `<div class="cat-list" id="attr-list-enc">` 추가
- `setEnclosureFilter()`에서 선택값(`'상'|'중'|'하'`) 매칭 item 수집
- 화살표 토글 동일

### D. 카운트/배지
- `updateFilterCounts()`에 `ageCnt`, `encCnt` 추가 (이미 폴리곤 순회 중)

## 검증 (Chrome MCP)
1. `preview_start slum-map`
2. 속성 필터 아코디언 열기 → 경사지·직주근접 ▶ 클릭 → 리스트 표시 확인
3. 노후도 `10년+` 클릭 + ▶ → 해당 구간 리스트
4. 폐쇄성 `상` 클릭 + ▶ → 해당 등급 리스트
5. `preview_console_logs error` 에러 없음 확인
