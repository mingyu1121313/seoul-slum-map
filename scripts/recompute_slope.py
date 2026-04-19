#!/usr/bin/env python3
"""
recompute_slope.py
is_slope 이중 조건 재계산:
  is_slope = relief_m >= 15 AND (slope_pct is None OR slope_pct >= 5)
- relief 단독 기준의 false positive (평지인데 경사지로 분류) 제거
- slope_pct 미측정 항목은 relief만 체크해 false negative 방지
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
RELIEF_MIN = 15
SLOPE_MIN  = 5  # %

def recompute(items):
    flipped_off = []
    flipped_on  = []
    for it in items:
        relief = it.get('relief_m')
        slope  = it.get('slope_pct')
        cur    = it.get('is_slope', False)
        if relief is None:
            new = False
        else:
            slope_ok = (slope is None) or (slope >= SLOPE_MIN)
            new = relief >= RELIEF_MIN and slope_ok
        if cur and not new: flipped_off.append((it.get('id'), it.get('name'), relief, slope))
        if not cur and new: flipped_on.append((it.get('id'), it.get('name'), relief, slope))
        it['is_slope'] = new
    return flipped_off, flipped_on

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    for fname in ['layerA.json', 'layerB.json']:
        p = DATA / fname
        d = json.loads(p.read_text(encoding='utf-8'))
        items = d.get('items', []) if isinstance(d, dict) else d
        off, on = recompute(items)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'{fname}: True→False {len(off)}건, False→True {len(on)}건')
        if off:
            print('  제외된 (평지로 재분류):')
            for x in off[:8]: print('   ', x)
        slope_count = sum(1 for it in items if it.get('is_slope'))
        print(f'  최종 is_slope=True: {slope_count} / {len(items)}')

if __name__ == '__main__':
    main()
