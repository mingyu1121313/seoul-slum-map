# 필터 추가 플랜: 노후도 + 폐쇄성 (v3 확정)

## 대상 범위: 571곳
- **개발 방식 553** = layerA.json 470 + type2.json 관리형 83
- **형성 유형 18** = layerB.json 18
- 각 항목에 `avg_bldg_age`, `enclosure_score`, `enclosure_grade` 필드 추가

---

## 1. 노후도 (방식 B 확정)

**데이터 소스:** 국가공간정보포털 GIS건물통합정보 (SHP, 시도별)
- URL: https://data.nsdi.go.kr/dataset/12623
- 핵심 필드: `USEAPR_DAY` (사용승인일) → 준공년도 추출

**파이프라인:**
1. 서울 SHP 다운 → `ogr2ogr`로 서울만 추출 → GeoJSON 변환
2. Python 스크립트: 571곳 각 폴리곤에 대해
   - 폴리곤 내부 건물의 평균 연차 = `avg_bldg_age`
   - 30년+, 40년+, 50년+ 비율도 함께 저장
3. 결과를 layerA/B/type2 items에 merge

**UI (결정 필요):**
- [ ] A안: 마커 색상만 (연차 구간별 색상)
- [ ] B안: 사이드바 슬라이더 (30/40/50년+ 필터)
- [ ] C안: A+B 둘 다

---

## 2. 폐쇄성 (3기준 종합, 3등급 확정)

**기준 3종 (가중 합산):**
| 기준 | 가중치 | 계산 |
|------|--------|------|
| 경계 둘러싸임 비율 | 0.4 | 폴리곤 경계 중 대로(4차선+)·철도·산 접경 비율 |
| 진입로 밀도 | 0.3 | 역가중 = 1 − (진입도로 수 / 경계 길이 100m당) |
| 주변 200m 용도 이질성 | 0.3 | 버퍼 내 비주거 용도지역 비율 |

**데이터:**
- 도로·철도·건물 진입로: OSM (overpass API 또는 shapefile)
- 산·녹지: 서울 생태·녹지현황 / OSM `landuse=forest`
- 용도지역: 서울 열린데이터광장 "도시계획 용도지역"

**파이프라인:**
1. `scripts/build_enclosure.py` — 571곳 루프
2. 기준별 0~1 정규화 → 가중합 → 0~100 점수
3. 3등급 컷: 상위 33% = 상, 중위 34% = 중, 하위 33% = 하
4. 결과 merge → `enclosure_score`, `enclosure_grade` 필드

**UI:**
- 사이드바 속성 필터에 "폐쇄성 높음(상)" / "폐쇄성 중간(중)" / "폐쇄성 낮음(하)" 체크박스 추가
- 기존 경사지·직주근접 필터와 동일 패턴

---

## 남은 질문 1개
**노후도 UI 방식 A/B/C 중 선택?** (추천: C — 색상+슬라이더 둘 다)

---

# 3. 마커 → 폴리곤 전환 (jaegebal 방식)

## 크롤링 결과
- jaegebal은 Naver Maps v3 + `naver.maps.Polygon` 사용 (우리와 동일 스택)
- `/api/develops?min_lat&max_lat&min_lng&max_lng`로 bbox 단위 polygon 패치 (auth gated)
- Zustand 상태에 `selectedPolygonId`로 hover/click 관리
- 기법 복제는 가능, 데이터는 별도 확보 필요

## 데이터 소스 (확정)
**서울시 의제처리구역 위치정보** (서울 열린데이터광장 OA-20957) — Shapefile 제공
- 정비구역·재정비촉진지구 폴리곤 공식 데이터
- 보조: 서울도시공간포털 도시계획조회(정비사업구역계) urban.seoul.go.kr

## 파이프라인
1. SHP 1회 다운 → QGIS/ogr2ogr로 서울 필터 → GeoJSON 변환
2. Python 매칭 스크립트: 571개 사이트의 (id, 주소, 지번) ↔ SHP 속성(사업명/고시번호/지번) 조인
3. 매칭 성공 항목에 `polygon: {type: "Polygon", coordinates: [...]}` 필드 삽입
4. 매칭 실패 항목은 `polygon: null` (기존 lat/lng 마커 유지)
5. `data/polygons.json` 별도 파일로 분리 저장 (용량 관리)

## 렌더링 (확정)
- **있는 것만 폴리곤** + 나머지는 기존 마커
- **카테고리별 색상 테두리 + 반투명 fill** (재개발=#ff2c40, 가로주택=#2c8aff, 주거환경=#ffa500, 지역주택=#7c4dff, 형성유형=#00a86b)
- `strokeWeight: 3`, `strokeOpacity: 0.9`, `fillOpacity: 0.2`
- **폴리곤 중심에 구역명 라벨만** (기존 점 마커 제거)
- **클릭** → 기존 사이드바 상세 확대 + 해당 폴리곤 `fillOpacity: 0.4`로 강조

## 구현 파일
- `scripts/build_polygons.py` — SHP 매칭 → polygons.json 생성
- `index.html` — `renderPolygons(items)` 함수 추가, 기존 `renderMarkers()`와 병행
- `data/polygons.json` — 신규

## 예상 매칭률
- 주거환경개선사업 정비형 18곳: **90%+** (공식 고시 구역)
- 재개발 221곳: **80~90%** (조합 단계 대부분 등록)
- 가로주택 166곳: **60~70%** (소규모는 고시 누락 많음)
- 관리형 83곳, 지역주택 65곳, 형성유형 18곳: **30~50%** (비공식 구역, 수동 작업 필요)
