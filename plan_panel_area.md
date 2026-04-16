# 정보 패널에 면적 표기 추가

## 데이터
- `data/polygons.json` 각 폴리곤에 이미 `zone_area_m2` 필드 존재
- 커버리지: 603/612 (98.5%)
- 단위: m² (천 단위 콤마 + "m²" 접미사)

## 표시 형식
```
면적  59,283 m²
```
단독 숫자만. 평 변환 없음.

## 수정 지점 (index.html showPanel)

### Layer A 블록 (≈ line 2957 자치구 다음)
```js
if (pdata && pdata.zone_area_m2) {
  const a = Math.round(pdata.zone_area_m2).toLocaleString();
  rows += `<tr><td>면적</td><td>${a} m²</td></tr>`;
}
```
`자치구` 다음, `경사도` 전에 삽입.

### Layer B 블록 (≈ line 2988 동 다음)
동일한 조건·포맷으로 `동` 다음, `경사도` 전에 삽입.

## 처리
- `zone_area_m2`가 없거나 0이면 행 생략 (placeholder 구역 대응)
- 소수점 반올림 후 `toLocaleString()`으로 천단위 콤마

## 검증
- 프리뷰에서 showPanel 직접 호출해 면적 행이 경사도 위에 나오는지 확인
- 크롬 MCP에서 임의 폴리곤(la0063: 49,893 m²) 클릭해 실제 표시 확인
