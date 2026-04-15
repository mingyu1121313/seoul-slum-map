# 모아타운 지도 통합 플랜

## 교차 검증 결과
| | 건수 |
|---|---|
| jaegebal 모아타운 전체 | 134 |
| jaegebal 활성 (예비(가)/취소/철회/해제 제외) | **124** |
| local moatown_array.js | 122 |
| 양쪽 매칭 | 91 |
| **로컬 누락** (jaegebal→local) | **33** |
| local만 존재 (구버전/표기 불일치) | 32 |

우선순위: jaegebal 124건 기준. local 32건은 동 이름 표기 차이가 대부분.

## 현재 상태
- `moatown_array.js`: 122건 독립 파일, 지도 미연동
- `layerA.json` / `CAT_CONFIG`: 모아타운 없음 → **지도에 미표시**
- `jaegebal_polygons.json`: 모아타운 134건 폴리곤 이미 보유

## 단계별 작업

### 1. `scripts/build_moatown_layer.py` 신규 작성
- `jaegebal_polygons.json`에서 `detail_type_short == '모아타운'` 추출
- 활성 124건 필터링 ((가) 접두 + 취소/철회/해제/선정보류 제외)
- 좌표: `location` 필드 그대로 사용 (이미 수집됨)
- jaegebal `areas` → GeoJSON Polygon 변환
- 출력: `data/moatown_items.json` (id, name, lat, lng, stage, polygon)

### 2. `data/layerA.json` 업데이트
- 124건을 `category: '모아타운'`으로 기존 470건에 추가 → 594건
- `id` 규칙: `moa{jaegebal_id}` (기존 la/lh 접두와 충돌 방지)
- `stage` 필드 추가 (관리지역고시 / 관리계획수립 / 대상지선정 등)

### 3. `data/polygons.json` 업데이트
- `match_method: "jaegebal_moa"` + polygon 직접 삽입 (UQ120 매칭 불필요)

### 4. `index.html` 수정 (4곳)
- `CAT_CONFIG`: `'모아타운': { color: '#16A34A', layer: 'A', shape: 'circle', size: 11 }` 추가
- `LAYER_A_ORDER`: 가로주택 다음에 삽입
- `getCategoryA()`: 모아타운 반환 조건 추가
- 사이드바: 모아타운 체크박스 row 추가

### 5. 검증 & 배포
- 모아타운 124개 폴리곤 지도 표시 확인
- 사이드바 체크박스 토글 동작 확인
- 커밋 → push → slum-seoul.xyz 배포

## 진행 상황별 분포 (jaegebal 124건)
관리지역고시 42 · 대상지선정 27 · 관리계획수립 27 · 위원회심의 7 · 조합설립인가 4 · 기타 17
