# 모아타운 직주근접 필터 제외 버그

## 진단
- 모아타운 124건 모두 `polygons.json` pdata에 **`avg_bldg_age` 필드 누락** (`pct_30plus/40plus/50plus`, `bldg_count`도 없음)
- 원인: `scripts/build_moatown_layer.py`가 폴리곤 등록 시 건축물 노후도 병합 파이프라인을 타지 않음
- 다른 카테고리(재개발·가로주택정비 등) 예시 `la0047`: `avg_bldg_age: 34.3` 정상
- 검증: 모아타운 near_job=true 11건은 `passesFilters({near:true})` 단독 통과. 그러나 **노후도 필터(10년+/20년+ 등)를 함께 켜면** `if (!age || age < ageMin) return false` 분기에 걸려 124건 전부 제외

## 사용자 관찰 해석
"직주근접 필터에 모아타운이 모두 제외" → 사용자가 직주근접+노후도를 동시에 켰거나, 노후도 기본값 확인 필요. 노후도 버튼 `전체` 이외 상태이면 재현됨.

## 수정안 (두 단계)

### 1. UI 레벨 즉시 패치 (index.html)
`passesFiltersWith()`에서 노후도 필터 분기를 보수적으로 변경:
- 현재: `if (!age || age < ageMin) return false;` — 데이터 없으면 일괄 제외
- 변경: 데이터 없는 폴리곤(avg_bldg_age === null/undefined)은 노후도 판정 **유보**하고 통과시키지 않되, "데이터 없음" 상태와 "age < ageMin"을 구분해서 모아타운은 통과
- 더 간단한 방법: `pdata.avg_bldg_age == null` 이면 해당 필터만 skip, 나머지(직주근접 등) 필터 계속 평가

### 2. 근본 원인 해결 (빌드 파이프라인)
`build_moatown_layer.py`에 건축물 노후도 계산 추가:
- `data/buildings.json`(또는 동일 pipeline) 참조
- 모아타운 폴리곤 내 건축물 평균 연차 · 30/40/50+ 비율 · 건물 수 계산
- 재빌드 후 모아타운 pdata에 `avg_bldg_age` 등 주입

## 진행 순서
1. UI 패치로 즉시 배포 (pdata 결측 시 해당 필터만 skip)
2. 확인 후 빌드 스크립트 수정 여부 결정 (현재는 ①로 충분)

## 검증
- 직주근접 ON + 노후도 10년+ 상태에서 모아타운 11건 통과 여부
- 기존 카테고리(재개발 등)의 노후도 필터 동작 정상 여부
