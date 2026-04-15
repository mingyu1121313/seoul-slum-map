# 폐쇄성 필터 플랜 (확정)

## 대상
- 폴리곤 보유 612건 중 **`circle_placeholder` 81건 제외** → ~531건 계산
- placeholder 제외분은 `data/enclosure_unclassified.json`에 별도 저장 (수동 분류용)
- polygons.json 각 항목에 필드 추가: `enclosure_score` (0~100), `enclosure_grade` ("상"|"중"|"하"|null)

## 기준 (4개, 가중합)
| # | 기준 | 가중 | 계산 |
|---|------|------|------|
| 1 | 경계 둘러싸임 | 0.30 | 폴리곤 경계 중 대로(OSM primary/secondary/trunk/motorway)·철도·녹지(park/forest) 접경 길이 비율 |
| 2 | 진입로 희소성 | 0.25 | 1 − min(1, 경계 교차 도로 수 / (둘레 100m)) |
| 3 | 내부망 고립도 | 0.25 | 1 − normalize(avg closeness_centrality), 사이트 내부 도로 그래프 (osmnx + networkx) |
| 4 | 주변 200m 용도 이질성 | 0.20 | Shannon entropy(주거/상업/공업/녹지 4종, OSM landuse) / log(4) |

각 기준 0~1 정규화 → 가중합 × 100 = `enclosure_score`

## 등급 컷 (절대)
- score ≥ 65 → **상**
- 35 ≤ score < 65 → **중**
- score < 35 → **하**
- 미산정 → **null** (필터 "데이터 없음" 체크박스)

## 데이터 소스
- 도로·철도·녹지·용도: OSM (osmnx `graph_from_place` + `features_from_place`, 자동 캐시)
- 범위: "Seoul, South Korea" place 전체

## 파이프라인
1. `scripts/fetch_osm_seoul.py` — osmnx로 서울 driveable graph + landuse/major_roads/rail features 캐시 → `data/osm_cache/*.geojson`
2. `scripts/build_enclosure.py` — 폴리곤 보유 항목 루프, 4기준 계산
   - 경계 교차·버퍼 교차는 shapely로 직접
   - 내부 closeness는 `ox.truncate_graph_polygon` + `networkx.closeness_centrality`
3. 결과 → `polygons.json`에 merge (build_bldg_age.py와 동일 패턴)
4. placeholder 항목 목록 → `data/enclosure_unclassified.json` (id, zone_name, lat, lng, match_method)

## UI
- 사이드바 속성 필터 아코디언에 체크박스 3개: `폐쇄성 상` / `중` / `하`
- 필터 로직은 기존 `attrFilters` 패턴 확장, 경사지·직주근접과 AND/OR 공용
- `enclosure_grade: null` 항목은 선택 시 숨김 (기존과 동일)
