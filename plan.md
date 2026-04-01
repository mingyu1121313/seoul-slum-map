# SEOUL SLUM MAP — 재구현 계획

## 레퍼런스 측정값 (seoul-population.netlify.app)
- 헤더: 56px / 타이틀 font-size 16px, weight 300, letter-spacing 0.14em, uppercase
- 우 패널: 296px / transition 0.28s cubic-bezier(0.4,0,0.2,1)
- 패널 마을명: 22px, weight 900
- 지도 타입 토글: 상단 중앙 고정, pill 형태
- 하단 바: 40px, background #0f0f14

## 레이아웃 구조
```
[헤더 56px — SEOUL SLUM MAP + 부제]
[사이드바 220px | 네이버 지도 (나머지 전체)]
[하단 바 40px — 비움]
[우 패널 296px — 마커 클릭 시 오버레이]
```

## 헤더
- 좌: `SEOUL SLUM MAP` (weight 300, letter-spacing 0.14em, uppercase, #111827)
- 부제: `서울시 달동네 · 판자촌 위치 현황 지도` (10px, #9ca3af)

## 왼쪽 사이드바 (항상 표시)
- 레이블: "마을 선택" (10px, #9ca3af, uppercase)
- 19개 마을 리스트 아이템: 컬러 dot + 마을명 + 자치구
- 클릭 → 지도 해당 위치 이동 + 우 패널 오픈 + 해당 마커 강조

## 네이버 지도
- API: `ncpClientId` 입력 필요 (index.html 1번째 줄 교체)
- 기본 타입: 지형지도(NORMAL) / 위성지도(HYBRID) 토글
- 마커: 커스텀 HTML 원형 (14px 기본 → hover 20px)
  - 🔴 `#E53935` 불법건축물 / 🟢 `#43A047` 합법건축물
- 마커 hover → tooltip + 마커 확대
- 마커 click → selectVillage() 호출

## 우 패널 (클릭 전 숨김, 클릭 후 슬라이드인)
1. 마을명 22px / 자치구·동 11px #9ca3af / 분류 배지
2. 사진 200px (`images/{마을명}.jpg` → 없으면 placeholder)
3. 설명 13px, line-height 1.85
4. 정보 테이블: 주소 / 형성 시기 / 규모

## API Key 교체 위치
```
index.html 상단:
ncpClientId=YOUR_NAVER_CLIENT_ID  ← 본인 키로 교체
```

## 파일 구조
```
seoul-slum-map/
├── index.html
└── images/
    ├── 구룡마을.jpg
    └── ...
```
