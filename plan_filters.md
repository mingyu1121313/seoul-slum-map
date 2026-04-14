# 속성 필터 추가 — 경사지 / 직주근접 (2026-04)

## 목적
기존 마커(개발 방식 / 형성 유형)는 그대로 두고, **속성 필터** 그룹을
사이드바에 신설해 두 조건으로 마커를 좁혀볼 수 있게 한다.

## 결정 사항 (사용자 확정)
- 경사지 데이터: **공공 DEM 사전 처리** (런타임 계산 X)
- 직주근접 데이터: **거점별 등시선 GeoJSON** + point-in-polygon
- UI: 사이드바 **속성 필터 그룹 + 체크박스**만 추가 (마커 색·모양 그대로)
- 직주근접 컷오프: **대중교통 40분 이내 거점 1개 이상**

## 직주근접 거점 (8개)
CBD(시청) · GBD(강남) · YBD(여의도) · 마곡 · 성수 · 판교 · 용산 · 상암(DMC)

## 작업 단계

### 1. 데이터 전처리 (오프라인, 1회)
1. `scripts/build_slope.py` — 국토지리정보원 DEM(GeoTIFF) 다운로드 →
   각 마커 좌표 반경 150m 평균 경사도(%) 계산 → `layerA/B.json` 항목에
   `slope_pct` 필드 주입. 임계값 **15% 이상 = 경사지**.
2. `scripts/build_isochrone.py` — ODsay/카카오 길찾기 API로 8개 거점
   기준 40분 등시선을 1회 호출 → `data/isochrone_40min.geojson` 저장
   (FeatureCollection, properties.hub = "CBD" 등).
3. `scripts/tag_proximity.py` — 각 마커 좌표가 GeoJSON 폴리곤 1개 이상에
   포함되면 `near_job: true`, 닿는 거점 목록 `near_hubs: ["CBD","GBD"]` 추가.

### 2. 프론트엔드 (index.html)
1. 사이드바에 **속성 필터** 아코디언 추가 (acc-c-header):
   - □ 경사지 (slope_pct ≥ 15)
   - □ 직주근접 (near_job === true)
   - 모드 토글: AND / OR (기본 AND)
2. `hiddenCategories` 외에 `attrFilters = { slope:false, near:false, mode:'AND' }`
   상태를 추가하고, `applyVisibility()`에서 마커별로 조건 평가.
3. 패널(`showPanel`)에 **경사도 %**, **직주근접 거점** 행 추가.
4. 범례(legend)에 작은 안내문 한 줄 (필터 그룹 별도 색 없음).

### 3. 검증
- preview_start → 체크박스 토글 시 마커 수 변화 확인.
- 구룡마을·백사마을(경사지 다수) 켜졌을 때 표시되는지.
- CBD 인접 후암동 등 직주근접 켜졌을 때 표시되는지.

## 영향 받는 파일
- `data/layerA.json`, `data/layerB.json` (필드 추가)
- `data/isochrone_40min.geojson` (신규)
- `scripts/*.py` (신규, 재실행 가능하게)
- `index.html` (사이드바 + 필터 로직 + 패널)
