# 행정동 경계선 + 마커 툴팁 명세

## 행정동 경계선

### 데이터
- 파일: `data/seoul_dong.geojson` (서울 행정동 424개 경계)
- 출처: 통계청 SGIS 행정동 경계 (공개 데이터)
- 로드: `fetch('data/seoul_dong.geojson')` → `naver.maps.Data` 레이어

### 렌더링
- API: `naver.maps.Data` (GeoJSON 폴리곤 레이어)
- 선 색상: `rgba(255, 255, 255, 0.55)` (반투명 흰색)
- 선 두께: 1px
- 채우기: 투명 (`fillOpacity: 0`)
- 항상 표시 (줌 레벨 무관)
- z-index: 마커 아래 (지도 위 폴리곤 레이어)

### 초기화
```
initMap() 완료 후 loadDongBoundary() 호출
naver.maps.Data 객체 생성 → addGeoJson() → setStyle()
```

---

## 마커 툴팁 (hover)

### 동작
- 마커에 `mouseover` 이벤트 → 툴팁 표시
- 마커에 `mouseout` 이벤트 → 툴팁 숨김
- 표시 내용: `item.name` 텍스트만

### 툴팁 DOM
- `#marker-tooltip` : position:fixed, pointer-events:none
- 마커 위치를 지도 좌표 → 화면 픽셀로 변환하여 위에 배치
- `map.getProjection().fromCoordToOffset()` 으로 좌표 변환

### 스타일
- 배경: `rgba(17,24,39,0.85)` + blur
- 텍스트: 11px, 흰색, font-weight 600
- border-radius: 6px, padding: 4px 9px
- 마커 위 8px 위치 (translateX -50%)
