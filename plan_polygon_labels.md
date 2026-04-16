# 폴리곤 라벨 표시 (jaegebal.com 스타일)

## 목표
각 폴리곤 위에 `[카테고리 축약]` + `[사업지 이름]` + `[진행 단계]` 2줄 라벨을 띄워 jaegebal.com 레퍼런스 UI 재현.

## UI 스펙
- **형태**: 2줄 박스 + 카테고리 색 상단바(3px)
  - 1행: 축약 카테고리(볼드, 11px) + 사업지명(`item.address`, 11px)
  - 2행: 진행 단계(`item.stage`, 10px, 회색)
- **배경**: 흰색 + 1px 테두리(카테고리 색 20% 알파), shadow `0 1px 4px rgba(0,0,0,.2)`
- **위치**: 폴리곤 centroid(paths 평균)에 anchor 중앙 정렬
- **상호작용**: pointer-events: none (폴리곤 클릭 방해 X)

## 카테고리 축약
```
재개발(주택정비형) → 재개발
가로주택정비       → 가로주택
모아타운          → 모아
지역주택          → 지주택
주거환경개선(정비형)→ 주거환경
자연발생          → 자연발생
집단이주          → 집단이주
신발생            → 신발생
```

## 줌/가시성 규칙
- 줌 ≥ 14 에서만 라벨 표시 (전체 뷰에서는 숨김)
- 카테고리 필터(`hiddenCategories`) 연동: 숨겨진 카테고리의 라벨도 숨김
- 속성 필터(노후도/폐쇄성 등) 적용 시 필터 탈락 폴리곤의 라벨도 숨김

## 구현 단계
1. `CAT_CONFIG`에 `short` 필드 추가(위 축약표)
2. `createPolygon()` 내부에서 `naver.maps.Marker`로 HTML 라벨 생성
   - centroid 계산 헬퍼 `getPolygonCentroid(paths)` 추가
   - `labelsByCategory[cat]` 배열에 저장(필터 연동용)
3. 줌 이벤트 리스너 `zoom_changed`에서 `map.getZoom() >= 14` 토글
4. 기존 카테고리/속성 필터 함수들(1679, 1790, 1935 라인대) 에서 `labelsByCategory` 도 동일하게 setMap(null/map) 처리
5. CSS 클래스 `.poly-label` 추가 (박스/상단바/폰트)

## 수정 파일
- `index.html` 단일 파일만 수정 (CSS + JS 추가, 데이터 변경 없음)
