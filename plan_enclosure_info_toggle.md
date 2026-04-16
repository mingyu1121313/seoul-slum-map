# 폐쇄성 기준 설명 토글 (ⓘ 버튼)

## 목표
"폐쇄성" 라벨 옆에 ⓘ 버튼을 두고, 클릭하면 계산 기준·가중치·등급 컷·데이터 소스를
상세히 설명하는 접이식 박스를 펼쳐준다. 리스트(`attr-list-enc`) 토글과 독립.

## 수정 지점 (index.html)

### 1. 라벨 수정
기존 부제 "경계·진입로·내부망·용도 가중합"은 유지하고, 그 옆에 ⓘ 버튼 추가:
```html
<span class="enc-info-btn" id="enc-info-btn"
      onclick="toggleEncInfo(event)"
      title="계산 기준 보기">&#9432;</span>
```

### 2. 설명 박스 (라벨 div 바로 아래 추가)
```html
<div class="enc-info-box" id="enc-info-box" style="display:none;">
  <b>폐쇄성 점수</b> (0~100) = 4개 지표 가중합<br>
  • <b>c1 경계 둘러싸임 (30%)</b> — 구역 경계 중 대로·철도·녹지 접경 길이 비율<br>
  • <b>c2 진입로 희소성 (25%)</b> — 경계 가로지르는 도로 수 (100m당 2개 이상=0, 0개=만점)<br>
  • <b>c3 내부망 고립도 (25%)</b> — 내부 도로 β지수(엣지/노드). 격자=낮음, 막다른 골목=높음<br>
  • <b>c4 용도 이질성 (20%)</b> — 주변 200m 반경 용도(주거·상업·공업·녹지) Shannon 엔트로피<br>
  <b>등급</b> — 원점수를 전국 분위수(p40→35, p80→65)로 보정 후:
  <span style="color:#dc2626;font-weight:700;">상</span> ≥65 ·
  <span style="color:#f59e0b;font-weight:700;">중</span> 35~65 ·
  <span style="color:#16a34a;font-weight:700;">하</span> &lt;35<br>
  <b>데이터 소스</b> — OpenStreetMap 도로망·철도·녹지·토지용도 (osmnx)<br>
  ※ OSM 도로 태깅 한계로 달동네 골목이 격자로 잡히는 등 실측과 다를 때 수동 보정 적용
</div>
```

### 3. CSS
- `.enc-info-btn`: 12px, #6b7280 색, 커서 포인터, margin-left 4px
- `.enc-info-box`: font-size 10.5px, line-height 1.55, background #f9fafb, padding 8px 10px, border-radius 6px, margin-top 6px, color #374151

### 4. JS
```js
function toggleEncInfo(e) {
  e.stopPropagation();
  const box = document.getElementById('enc-info-box');
  box.style.display = box.style.display === 'none' ? 'block' : 'none';
}
```

## 검증
- ⓘ 클릭 시 회색 박스 펼침/접힘, 리스트 토글(▶)과 독립 동작
- 모바일 폭에서도 줄바꿈 자연스러움
- 크롬 MCP 배포 사이트 확인
