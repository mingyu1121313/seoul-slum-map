# 라벨 재배치 성능 개선 (줌/드래그 렉 제거)

## 측정 결과 (현 상태)
- `relayoutLabels()` 1회 실행: **860~970 ms** (라벨 612개 전수 처리)
- `zoom_changed` + `dragend` 마다 호출 → 조작 중 화면 멈춤

## 병목 원인
1. **뷰포트 컬링 없음**: 화면 밖 라벨도 매번 `fromCoordToOffset` + `setIcon` 처리
2. **변경 없는 라벨도 setMap 재호출**: 이미 숨긴/표시된 상태인데 반복 호출
3. **충돌 검사 O(N²)**: 612개 후보 전부 서로 비교
4. **디바운스 16ms 너무 짧음**: 드래그 관성 이벤트가 여러 번 호출

## 해결 전략
1. **뷰포트 컬링**
   - `map.getBounds()` 먼저 구해서 bounds 밖 라벨은 `setMap(null)`만 하고 skip
   - 마진 50m 정도 여유 (panning 직후 튀는 것 방지)
2. **상태 기반 setMap 스킵**
   - 라벨에 `_onMap` 플래그 추가 → 같은 상태면 `setMap` 호출 자체 스킵
3. **공간 그리드 인덱싱**
   - placed 박스를 64px 셀 그리드에 등록
   - 충돌 검사를 해당 셀 + 인접 8셀로만 제한 → O(N) 근접
4. **디바운스 상향 + idle 이벤트**
   - `setTimeout 16 → 120 ms`
   - `dragend` 대신 `idle` 리스너로 통합(zoom/drag 끝나고 한 번만)
5. **카테고리 숨김 최적화**
   - 이미 `_onMap=false`이면 setMap 재호출 안 함

## 기대 효과
- 뷰포트 내 ~150개만 처리 → O(N²) 612² → O(N) 150 근접
- 1회 실행 **~50 ms 이하** 목표
- 드래그 중에도 즉각 반응

## 수정 파일
- `index.html` 단일 파일
  - `relayoutLabels()` 본체 (1685~1766)
  - `scheduleRelayout()` 디바운스 (setTimeout 16 → 120)
  - 이벤트 리스너 `zoom_changed`/`dragend` → `idle` 통합

## 검증
- Chrome MCP로 줌 14↔15↔16 연속 전환 시 relayout avgMs < 80
- 드래그 후 idle 한 번만 호출되는지 확인
- 겹침 0건, +N 배지 유지 (기능 회귀 없음)
