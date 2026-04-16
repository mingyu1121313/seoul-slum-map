# 주거환경 라벨 주소 축약 (동+번지 통일)

## 문제
- 라벨 `[주거환경] 서울특별시 서대문...` → 박스에서 잘림
- 원인: `data/layerA.json` 주거환경개선사업 18건의 `address` 필드만 `"서울특별시 XX구 XX동 XXX번지"` 풀주소
- 다른 576건은 `"XX동 XXX"` 형식 → 라벨 포맷 불일치

## 해결 전략
**라벨 생성 시점에 주소 축약(데이터 원본은 보존)**
- 툴팁·상세창은 기존 풀주소 유지
- 라벨만 다른 카테고리와 동일한 `"XX동 XXX"` 포맷으로 통일

## 구현
1. `index.html` 헬퍼 함수 추가 (`createPolygonLabel` 바로 위)
   ```js
   function shortenAddrForLabel(addr) {
     if (!addr) return '';
     // "서울특별시 XX구 " 또는 "서울 XX구 " 접두사 제거
     let s = addr.replace(/^서울(특별시|시)?\s*\S+구\s*/, '');
     // 꼬리 "번지" 제거 (예: "현저동 1-5번지" → "현저동 1-5")
     s = s.replace(/번지\s*$/, '');
     return s.trim();
   }
   ```
2. `createPolygonLabel` 내 `const addr = item.address || item.name || ''` → `const addr = shortenAddrForLabel(item.address || item.name || '')`

## 수정 파일
- `index.html` 단일 파일

## 기대 결과
- 주거환경 라벨: `[주거환경] 현저동 1-5` (박스 안에 들어감)
- 다른 카테고리 라벨 영향 없음 (이미 "XX동 XXX" 형식이라 regex가 no-op)
- 툴팁/상세창 풀주소 유지

## 검증
- Chrome MCP로 서대문 독립문 근처 줌 15 이동
- 주거환경 18건 라벨이 "XX동 번지"로 표시되는지 확인
- 기존 라벨 영향 없음(샘플 5개) 확인
- 상세 클릭 시 툴팁 풀주소 유지 확인
