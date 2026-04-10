# SEOUL SLUM MAP — 플랜 (2026-04)

## 스택
정적 HTML/CSS/JS · 네이버 지도 API v3 (ncpKeyId: sg8elx2o2n) · GitHub Pages → slum-seoul.xyz

---

# 소분류 행 클릭 동작 분리

## 현재 동작
- `row.onclick` → 이름·아이콘·카운트 클릭 → `toggleCategory(cat)` (마커 숨김/표시)
- `.cat-expand` 화살표 클릭 → `toggleCatList(sid, e)` (목록 접기/펼치기)

## 변경 목표
| 클릭 대상 | 변경 전 | 변경 후 |
|-----------|--------|--------|
| 체크박스 | 마커 토글 | 마커 토글 (유지) |
| 이름·아이콘·카운트 | 마커 토글 | 목록 접기/펼치기 |
| 화살표 ▶ | 목록 접기/펼치기 | 목록 접기/펼치기 (유지) |

초기 상태: `.cat-list { max-height: 0 }` CSS 이미 적용 → 추가 작업 없음

## 변경 위치 (index.html, `makeCatSection` 함수 ~1310행)

```js
// 변경 전
row.onclick = function(e) {
  if (e.target.type === 'checkbox') return;
  if (e.target.closest && e.target.closest('.cat-expand')) return;
  toggleCategory(cat);
};

// 변경 후
row.onclick = function(e) {
  if (e.target.type === 'checkbox') return;
  toggleCatList(sid, e);
};
```

- 화살표 `.cat-expand`는 자체 `onclick`에서 `stopPropagation` 호출 → 이중 토글 없음
- 체크박스 `onchange="toggleCategory('${cat}')"` 유지
- 파일 수정: `index.html` 1310–1314행
