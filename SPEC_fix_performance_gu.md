# 성능·마커·경계선 수정 명세

## 문제 원인

| 증상 | 원인 |
|------|------|
| 확대 시 렉·축소 불가·마커 사라짐 | 행정동 Polyline 수천 개 동시 렌더링 → GPU/메모리 포화 |
| 마커 클릭 불가 | Polyline 이벤트 레이어가 마커 위를 덮어 클릭 차단 |
| 마커 위치 오류 | 브라우저 캐시(layerB.json 구버전 로드) 또는 잘못된 좌표 |
| 경계선 없어짐 | 이전 배포에서 경계 표시 코드 누락 가능성 |

---

## 해결 계획

### 1. 행정구 GeoJSON 확보
- 소스: `southkorea/seoul-maps` GitHub (공개 데이터, 서울 25개 자치구)
- 저장: `data/seoul_gu.geojson`
- 파일 크기 목표: 100~200KB (동 파일 880KB 대비 1/5 이하)

### 2. 경계선 교체 — `loadDongBoundary()` → `loadGuBoundary()`
- 기존 seoul_dong.geojson 로드 제거
- Polyline 수: ~수천 개 → 25~50개
- 선 스타일: strokeColor `rgba(255,255,255,0.65)`, strokeWeight 1.5px
- `clickable: false` 유지 (마커 클릭 차단 방지)

### 3. 마커 클릭 차단 방지
- Polyline `zIndex` 명시적으로 마커보다 낮게 설정 (zIndex: 1)
- 마커 zIndex: 10 이상으로 명시

### 4. layerB.json 캐시 무효화
- fetch URL에 쿼리스트링 버전 파라미터 추가
  `fetch('data/layerB.json?v=' + Date.now())`
- 웹 직접 테스트로 좌표 반영 확인

### 5. 웹 테스트 순서
1. 배포 전 로컬 preview로 Polyline 수·렉 확인
2. 배포 후 강제 새로고침(Ctrl+Shift+R)으로 캐시 무효화
3. 마커 좌표 콘솔 출력으로 신규 좌표 반영 확인
4. 줌 인/아웃 10회 이상 반복 → 렉 없음 확인
5. 마커 클릭 → 사이드바 열림 확인

---

## 파일 변경 범위
- `data/seoul_gu.geojson` 신규 추가
- `index.html` — loadDongBoundary → loadGuBoundary, fetch 캐시 버스팅, zIndex 조정
