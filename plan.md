# SEOUL SLUM MAP — 바이브코딩 플랜

## 현재 상태
- 19개 달동네 마커 정상 표시
- 서울 25개 구 경계선 흰 실선 폴리라인
- 위성/지형/로드뷰 전환, 정보 표시 토글
- GitHub Pages + slum-seoul.xyz 커스텀 도메인

## 스택
- 정적 HTML/CSS/JS · 네이버 지도 API v3 (`submodules=panorama,geocoder`)
- GitHub main → GitHub Pages 자동 배포

---

## 즉시 배포 (모아타운 마커 수정)

### 문제
- 라이브 사이트: 구버전 — geocoding 방식이라 마커 0개
- 원인: localStorage 캐시 없으면 API 호출 122번 → 실패

### 수정 내용 (로컬 완료, push 대기)
- `MOATOWN_DATA` 122개에 `lat`/`lng` 직접 내장 (Nominatim 지오코딩)
- `createMoatownMarkers()` 단순화 — geocoding/localStorage 제거
- 로딩 토스트 제거

### 할 일
- [ ] `main` push → GitHub Pages 자동 배포
- [ ] slum-seoul.xyz에서 마커 122개 표시 확인

---

## 다음 우선순위

### P1 — 마커 UX 개선 (결정 필요)
- 겹친 마커 분산 여부 (화곡동 등 동일 동 6개 이상 겹침)
- date 포맷: `"22.01.20."` → `"2022년 1월 20일"` 변환 여부

### P2 — 마을 사진 추가
- `images/{마을명}.jpg` 추가 시 패널 자동 표시

### P3 — 필터 기능
- 구별 필터, 지정연도 필터

### P4 — 모바일 반응형
