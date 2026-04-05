# SEOUL SLUM MAP — 바이브코딩 플랜

## 현재 상태
- 19개 마을 핀 좌표 수정 완료
- 서울 25개 구 경계선 흰 실선 폴리라인
- 위성지도 "정보 표시" 체크박스 (HYBRID ↔ SATELLITE)
- 로드뷰: 전체화면 파노라마 + 좌하단 미니맵
- GitHub Pages + slum-seoul.xyz 커스텀 도메인

## 스택
- 정적 HTML/CSS/JS · 네이버 지도 API v3 (`submodules=panorama`)
- GitHub main → GitHub Pages 자동 배포

---

## 다음 작업: 모아타운 마커 추가

### 사용자 결정사항
| 항목 | 결정 |
|------|------|
| 마커 모양 | 사각형/마름모 (SVG 커스텀) |
| 레이어 | 달동네/모아타운 별도 토글 체크박스 |
| 기지정/신지정 구분 | 동일 스타일 (구분 없음) |
| 클릭 패널 | 위치구·대표주소·면적·지정일 표시 |

### 구현 단계

**Step 1 — 좌표 일괄 획득**
- Python 스크립트로 Naver Geocoding API 호출
- 입력: "서울특별시 {구} {지번주소}" × 122건
- 출력: `moatown_coords.json` (번호, lat, lng)

**Step 2 — 데이터 배열 생성**
- `MOATOWN_DATA` JS 배열을 index.html에 추가
- 필드: id, gu(위치구), address(대표주소), area(면적), date(지정일), lat, lng

**Step 3 — 마커 렌더링**
- 마름모 SVG 커스텀 마커 (파랑 `#3B82F6`, 테두리 흰색)
- `naver.maps.Marker` + `icon: { content: svgString }`

**Step 4 — 레이어 토글**
- 좌상단 컨트롤에 체크박스 2개 추가
  - ☑ 달동네 (기존)
  - ☑ 모아타운 (신규)
- 체크 해제 시 해당 레이어 마커 일괄 hide/show

**Step 5 — 클릭 패널**
- 기존 달동네 사이드패널 구조 재사용
- 모아타운 전용 섹션: 위치구 / 주소 / 면적 / 지정일

---

## 이후 우선순위

### P1 — 마을 사진 추가
- `images/{마을명}.jpg` 추가 시 패널 자동 표시

### P2 — 필터 기능
- 불법/합법 토글, 구별 필터

### P3 — 모바일 반응형
