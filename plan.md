# SEOUL SLUM MAP — 플랜 (2026-04)

## 스택
정적 HTML/CSS/JS · 네이버 지도 API v3 (ncpKeyId: sg8elx2o2n) · GitHub Pages → slum-seoul.xyz

---

# 조합 해산·청산 항목 제거

## 배경
정보몽땅 엑셀 원본(layerA.json)의 `stage` 필드가 **`조합해산`** 또는 **`조합청산`**인 항목은
사업이 공식 종료된 곳이므로 지도에서 제거.

## 삭제 대상
| 카테고리 | 건수 |
|----------|------|
| 재개발(주택정비형) | 81건 |
| 가로주택정비 | 5건 |
| **합계** | **86건** |

삭제 후 잔여: 556 - 86 = **470건**

## 변경 파일
- `data/layerA.json` — `stage`가 `조합해산` 또는 `조합청산`인 item 86개 제거
- `meta.total` 수정 불필요 (런타임에 JS가 동적 계산)

## 구현 방법
Python 스크립트로 필터링 후 덮어쓰기:
```python
items = [i for i in data['items'] if i.get('stage') not in ('조합해산', '조합청산')]
```
