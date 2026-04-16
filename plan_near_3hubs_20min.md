# 직주근접 기준 재정의 (3도심 · 20분)

## 변경 요지
- **기준 시간**: 대중교통 40분 → **20분**
- **대상 거점**: 8개 → **GBD · CBD · YBD 3곳만** (용산/성수/마곡/판교/상암 제외)
- **아코디언 UI**: 통과 목록을 GBD / CBD / YBD 3개 하위 그룹으로 분리 리스트업
- **중복 노출**: 한 지역이 여러 도심에 20분 이내면 해당 그룹 모두에 표시

## 1. 데이터 재생성 (scripts/build_proximity_odsay.py)
- `HUBS` 배열에서 Magok · Seongsu · Pangyo · Yongsan · Sangam **제거** → GBD/CBD/YBD 3개만 남김
- `CUTOFF_MIN = 40` → `CUTOFF_MIN = 20`
- `MAX_KM = 7.9` → `MAX_KM = 5.0` (20분이면 직선 5km 이내가 현실적)
- 스크립트 재실행: 기존 캐시 재사용하여 layerA/B.json의 `near_minutes`/`near_hubs`/`near_job` 재태깅
  - `near_minutes`: `{GBD: 18, CBD: 19}` 형태, 3개 도심만
  - `near_hubs`: 20분 이내 도심 배열
  - `near_job`: 1곳 이상 20분 이내이면 true

## 2. UI 변경 (index.html)
- 라벨: `직주근접<span>거점 40분 이내</span>` → `직주근접<span>3도심 20분 이내</span>`
- 리스트 태그 필터 `m <= 40` → `m <= 20` (현재 2268줄)
- 팝업 표시 로직은 `near_hubs` 기준이므로 자동 반영됨

## 3. 직주근접 아코디언을 3그룹으로 재구성 (index.html)
- `attr-list-near` 컨테이너 안에 GBD / CBD / YBD 세 개의 서브 아코디언 생성
  - 각 서브 아코디언 헤더: `GBD (강남) · N건` 등 도심명 + 건수
  - 클릭 시 펼침/접힘 (개발방식·형성유형 아코디언과 동일 패턴)
- `buildAttrFilterBody()`의 nearList 구성 로직 교체:
  - `nearItems`를 `byHub = { GBD: [], CBD: [], YBD: [] }`로 분류
  - 한 마커가 여러 도심에 해당하면 각 그룹에 **중복** push
  - 각 그룹 내부는 해당 도심까지의 분 수 오름차순 정렬
  - 태그 표시: `GBD 18분` 형식 (해당 도심 분 수만)
- 서브 아코디언 펼침 상태 유지를 위해 `expandedSubNear` 같은 상태 저장 필요

## 4. 검증
- 재태깅 후 GBD/CBD/YBD 각 몇 건인지 콘솔 리포트 확인
- 필터 ON 시 지도 마커 · 카운트 배지 · 리스트 3그룹 · 필터 통과 목록 모두 일치하는지 확인
