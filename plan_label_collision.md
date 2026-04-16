# 폴리곤 라벨 겹침 해소 (수직 스택 배치)

## 문제
줌 15에서 화면에 보이는 라벨 150개 중 136쌍이 겹침. 같은 주소를 다른 사업이 동시 추진(예: 천연동 89-16 = 가로주택 + 모아), 인접 폴리곤(예: 청량리동 199/205/435), 큰 폴리곤 안 작은 폴리곤 포함관계 케이스.

## 해결 전략 (사용자 확정)
- **방식**: 겹치는 라벨을 수직 스택(위/아래 오프셋)으로 모두 표시
- **스택 순서**: 폴리곤 넓이 작은 것이 위(세부 사업이 잘 보이게)
- **클러스터당 최대**: 5개. 초과 시 +N 배지로 표시
- **겹침 판정**: DOM bounding box 실제 충돌만(최소 이동)

## 알고리즘
1. **사전 계산**: 폴리곤 paths 로 spherical excess 면적 산출 → `label._area` 저장
2. **레이아웃 함수 `relayoutLabels()`** (줌 변경/필터 변경 시 호출):
   - 화면 안에 있는 visible 라벨만 수집(getMap 체크)
   - 각 라벨 anchor position을 px 좌표로 변환(map.getProjection().fromCoordToOffset)
   - 라벨을 `_area` 오름차순 정렬(작은 게 위)
   - 그리드 인덱싱(예: 80px 셀)으로 후보군 좁힘
   - 충돌 검사 → 충돌하면 위로 22px씩 push (히스토리 저장)
   - 같은 anchor에 5개 누적되면 6번째부터 setMap(null) + 클러스터 marker `+N` 생성
3. **anchor 오프셋 적용**: `naver.maps.Marker.setIcon(...anchor 변경)` 또는 `Marker.setOptions({icon: {anchor: new Point(60, 14 - offsetY)}})`
4. **클러스터 +N 마커**: 작고 둥근 회색 배지, 클릭 시 가까운 사이드바 패널 열기

## 트리거 지점
- `applyVisibility()` 끝 → `relayoutLabels()` 호출
- `zoom_changed` 리스너 → 기존 `updateLabelVisibilityByZoom` 후 → `relayoutLabels()`
- `idle` 이벤트도 추가(panning 중에도 갱신될 수 있게)

## 구현 단계
1. `createPolygon` → `_area` 산출 후 label 객체에 부착
2. `relayoutLabels()` 함수 작성(grid + collision push)
3. `_offsetY` 상태 관리, anchor 동적 변경 헬퍼 `setLabelOffset(label, offsetY)`
4. 클러스터 +N 마커 풀(`overflowMarkers[]`) 관리
5. CSS `.poly-cluster-more` 추가(작은 회색 원형 badge)

## 수정 파일
- `index.html` 단일 파일

## 검증
- Chrome MCP로 줌 15 + 종로/중구 일대 → 겹침 0건 확인
- 스택 5개 한계 + 클러스터 배지 출현 확인
- 카테고리/속성 필터 토글 후에도 정상 재배치 확인
