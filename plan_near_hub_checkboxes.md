# 직주근접 GBD/CBD/YBD 개별 체크박스

## 목표
기존 "직주근접" 1개 체크박스 → 상위 + 하위 3개(GBD/CBD/YBD) 체크박스 계층.
하위 체크는 **OR** 조합(하나라도 20분 내면 통과). 상위는 3개 동시 토글.

## 동작 규칙
- 상위 ☑ → 3개 모두 ☑ / 상위 ☐ → 3개 모두 ☐
- 하위 3개 모두 ☑ → 상위 ☑, 전부 ☐ → 상위 ☐, 일부만 ☑ → 상위는 체크된 상태(indeterminate 미사용, 단순 체크)
- 하위 중 하나라도 ☑면 필터 ON, 해당 거점 20분 내 구역만 통과
- 속성 배지 `81`: **3거점 합집합 고정** (체크 무관)

## 데이터 구조
`attrFilters.near` (bool) 유지 + `attrFilters.nearHubs: Set` 신설
- `near=true` 그리고 `item.near_hubs`에 `nearHubs` 중 하나라도 포함되면 통과
- `near=false`면 nearHubs 무시

## 수정 지점

### passesFiltersWith
```js
if (nearOn) {
  const hubs = f.nearHubs || new Set(['GBD','CBD','YBD']);
  const itemHubs = (item && item.near_hubs) || [];
  const hit = item.near_job && itemHubs.some(h => hubs.has(h));
  // slope와 AND/OR 결합 — 기존 near 자리에 hit 주입
}
```

### HTML (near-hub-row)
```html
<div class="near-hub-row">
  <input type="checkbox" class="near-hub-chk" id="chk-near-GBD" checked
         onchange="toggleNearHubChk('GBD', this.checked)">
  <span class="near-hub-label" onclick="toggleNearHub('GBD', event)">GBD<sub>강남</sub></span>
  <span class="near-hub-count">11</span>
  <span class="cat-expand" onclick="toggleNearHub('GBD', event)">▶</span>
</div>
```
(체크박스 클릭 시 이벤트 버블 방지, 다른 영역은 기존 아코디언 토글 유지)

### JS
- `toggleAttr('near', checked)`: nearHubs 3개 set/clear + 하위 체크박스 DOM 동기화
- `toggleNearHubChk(hub, checked)`: nearHubs 갱신 → size에 따라 near bool + 상위 체크박스 동기화
- `countPure({ near: true })` → 내부에서 nearHubs = 전체 3개로 고정 (배지는 81 유지)

## 검증
- 크롬 MCP: GBD만 체크 → 통과 목록 11건, CBD만 → 62건(예상), 셋 다 체크 → 81건
- 배지 81/11/... 고정, 상단 612·통과목록만 반응
