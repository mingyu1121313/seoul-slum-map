# 모아타운 경사지 필드 재빌드

## 현황
- `data/polygons.json`의 모아타운 124건 모두 `enclosure_grade` 및 `avg_bldg_age` 필드 존재 (이미 정상)
- 그러나 `data/layerA.json`의 모아타운 items 124건은 `is_slope`, `relief_m` 필드 없음
- 결과: 경사지 리스트 190건에 모아타운 0건 포함 → 사용자 불만

## 근본 원인
- `scripts/build_slope.py`는 `relief_m` 없는 item만 신규 처리 (캐시 보존)
- 모아타운 124건 추가 후 해당 스크립트가 재실행되지 않아 필드 미부여

## 수정안 (빌드 재실행 1회)
1. `cd scripts && python build_slope.py`
   - open-elevation API로 모아타운 124건 × 17 샘플점 = 2108건 호출
   - 배치 100건 × 0.4s sleep ≈ 약 1분 예상
   - 기존 `relief_m` 있는 500여 건은 스킵됨 (덮어쓰지 않음)
2. `layerA.json` 저장 (검증 케이스 자동 출력)

## 검증
- 실행 후 모아타운 124건 중 `is_slope=true` 몇 건인지 리포트
- 기존 경사지 190건 수치 변화 확인 (증가만 가능)
- 크롬 MCP로 배포 사이트에서 경사지 배지/리스트 갱신 확인

## 주의
- API 실패 시 해당 배치 item은 `is_slope=false`로 저장 (중단 없이 계속)
- UI 코드 수정 불필요 — 데이터만 업데이트
