#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch_geocoder.html 생성기
layerA_raw.json + type2(정비형/관리형) + type1(layerB) 데이터를
브라우저용 Naver Maps JS 배치 지오코더 HTML로 만든다.
"""
import json, os, re

BASE = os.path.dirname(os.path.abspath(__file__))

# ── 1. 데이터 로드 ──────────────────────────────────────────────────
with open(os.path.join(BASE, "data", "layerA_raw.json"), encoding="utf-8") as f:
    raw = json.load(f)

with open(os.path.join(BASE, "data", "type2.json"), encoding="utf-8") as f:
    t2 = json.load(f)

with open(os.path.join(BASE, "data", "type1.json"), encoding="utf-8") as f:
    t1 = json.load(f)

# ── 2. 각 데이터셋 → [{id, name, query, ...}] ──────────────────────

FORMATION_TYPE = {
    "mh01": "신발생",
    "mh02": "집단이주",
    "mh03": "집단이주",
    "mh04": "집단이주",
    "mh05": "신발생",
    "mh06": "신발생",
    "mh07": "자연발생",
    "mh08": "자연발생",
    "mh09": "집단이주",
}

def clean_addr(addr):
    addr = re.sub(r'\s*일대$', '', addr.strip())
    addr = re.split(r',\s*\d', addr)[0].strip()
    return addr

# 레이어A 메인 (layerA_raw: 538건)
layer_a_main = []
for it in raw["items"]:
    addr = it["address"]
    if not addr.startswith("서울"):
        addr = f"서울특별시 {it['gu']} {addr}"
    layer_a_main.append({
        "id":       it["id"],
        "gu":       it["gu"],
        "name":     it["name"],
        "address":  it["address"],
        "category": it["category"],
        "stage":    it["stage"],
        "status":   it["status"],
        "query":    clean_addr(addr)
    })

# 레이어A 정비형 (type2: 18건)
layer_a_jb = []
for it in t2["정비형_진행중"]["items"]:
    layer_a_jb.append({
        "id":       it["id"],
        "gu":       it["gu"],
        "name":     it["name"],
        "address":  it["address"],
        "category": "주거환경개선사업",
        "stage":    "",
        "status":   "운영",
        "query":    clean_addr(it["address"])
    })

# 레이어A 관리형 (type2: 83건, 동단위)
layer_a_nb = []
for it in t2["관리형_진행중"]["items"]:
    layer_a_nb.append({
        "id":      it["id"],
        "gu":      it["gu"],
        "dong":    it["dong"],
        "name":    it["name"],
        "address": it["address"],
        "category": "주거환경개선사업",
        "subcategory": "관리형",
        "status":  it.get("status", "진행중"),
        "query":   it["address"]  # 동단위 → 대표좌표
    })

# 레이어B (type1: 31건)
layer_b = []
for it in t1["items"]:
    addr = it["address"]
    # "/" 로 나뉜 경우 첫 번째 주소만 사용
    addr = addr.split('/')[0].strip()
    # 서울 접두어 없으면 gu만 붙이기 (dong은 address에 이미 포함된 경우 많음)
    if not addr.startswith("서울"):
        addr = f"서울특별시 {it['gu']} {addr}"
    layer_b.append({
        "id":             it["id"],
        "gu":             it["gu"],
        "dong":           it.get("dong", ""),
        "name":           it["name"],
        "address":        it["address"],
        "formation_type": it.get("formation_type", "미분류"),
        "area_m2":        it.get("area_m2"),
        "formed":         it.get("formed", ""),
        "households":     it.get("households", ""),
        "status":         it.get("status", ""),
        "note":           it.get("note", ""),
        "source":         it.get("source", ""),
        "query":          clean_addr(addr)
    })

# ── 3. JSON 직렬화 (HTML 내 인라인) ────────────────────────────────
def jdump(obj):
    return json.dumps(obj, ensure_ascii=False)

# ── 4. HTML 생성 ────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>서울 저층주거지 배치 지오코더</title>
<script src="https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=sg8elx2o2n&submodules=geocoder"></script>
<style>
  body {{ font-family: monospace; padding: 20px; background: #111; color: #ccc; }}
  h2 {{ color: #fff; }}
  .bar {{ background: #333; height: 18px; width: 100%; border-radius: 4px; margin: 6px 0; }}
  .bar-inner {{ background: #0a0; height: 100%; border-radius: 4px; transition: width .3s; }}
  #log {{ height: 220px; overflow-y: auto; border: 1px solid #333; padding: 8px;
          font-size: 11px; margin: 8px 0; background: #0a0a0a; }}
  button {{ background: #2a2; color: #fff; border: none; padding: 10px 28px;
            cursor: pointer; font-size: 14px; border-radius: 4px; margin: 4px; }}
  button:disabled {{ background: #444; cursor: not-allowed; }}
  .ok {{ color: #0f0; }} .err {{ color: #f55; }} .info {{ color: #88f; }}
  .section {{ border: 1px solid #333; padding: 10px; margin: 8px 0; border-radius: 4px; }}
</style>
</head>
<body>
<h2>🗺 서울 저층주거지 배치 지오코더</h2>
<p style="color:#999">총 4개 데이터셋을 순서대로 지오코딩합니다. 완료 후 각 JSON 파일을 <b>data/</b> 폴더에 저장하세요.</p>

<div class="section">
  <b style="color:#fff">레이어A — 정비사업 (538+18건)</b>
  <div class="bar"><div class="bar-inner" id="bar-a" style="width:0%"></div></div>
  <span id="prog-a" style="color:#aaa">대기</span>
</div>
<div class="section">
  <b style="color:#fff">레이어A — 주거환경개선 관리형 (83건, 동단위)</b>
  <div class="bar"><div class="bar-inner" id="bar-nb" style="width:0%"></div></div>
  <span id="prog-nb" style="color:#aaa">대기</span>
</div>
<div class="section">
  <b style="color:#fff">레이어B — 무허가정착지 (31건)</b>
  <div class="bar"><div class="bar-inner" id="bar-b" style="width:0%"></div></div>
  <span id="prog-b" style="color:#aaa">대기</span>
</div>

<button id="btn-start" onclick="startAll()">▶ 전체 시작</button>
<div id="log"></div>

<script>
const LAYER_A_MAIN = {jdump(layer_a_main)};
const LAYER_A_JB   = {jdump(layer_a_jb)};
const LAYER_A_NB   = {jdump(layer_a_nb)};
const LAYER_B      = {jdump(layer_b)};

// 지오코딩 실패 항목 수동 좌표 (Naver Maps 직접 조회)
const MANUAL_COORDS = {{
  'mh01': {{ lat: 37.4756413, lng: 127.0648603 }},  // 구룡마을
  'mh03': {{ lat: 37.4820257, lng: 127.0484294 }},  // 재건마을
  'mh04': {{ lat: 37.4522593, lng: 127.0676012 }},  // 헌인마을
  'mh06': {{ lat: 37.4797030, lng: 127.0472213 }},  // 달터마을
  'mh10': {{ lat: 37.6199200, lng: 127.0630160 }},  // 녹천마을
  'mh21': {{ lat: 37.4853090, lng: 126.9424280 }},  // 은천동4-1-2구역
  'mh23': {{ lat: 37.6760661, lng: 127.0632206 }},  // 희망촌
}};

function log(msg, cls='') {{
  const d = document.getElementById('log');
  d.innerHTML += `<div class="${{cls}}">${{msg}}</div>`;
  d.scrollTop = d.scrollHeight;
}}

function sleep(ms) {{ return new Promise(r => setTimeout(r, ms)); }}

function geocodeOne(query) {{
  return new Promise(resolve => {{
    naver.maps.Service.geocode({{ query }}, (status, res) => {{
      if (status === naver.maps.Service.Status.OK && res.v2.addresses.length > 0) {{
        const a = res.v2.addresses[0];
        resolve({{ lat: parseFloat(a.y), lng: parseFloat(a.x) }});
      }} else {{
        resolve(null);
      }}
    }});
  }});
}}

async function geocodeBatch(items, barId, progId) {{
  const results = [];
  let ok = 0, fail = 0;
  const total = items.length;
  for (let i = 0; i < total; i++) {{
    const item = items[i];
    // 수동 좌표 우선 적용
    const manual = MANUAL_COORDS[item.id];
    let r = manual ? manual : await geocodeOne(item.query);
    if (r) {{
      item.lat = r.lat; item.lng = r.lng;
      item.geocode_status = manual ? 'manual' : 'ok';
      ok++;
    }} else {{
      item.lat = null; item.lng = null; item.geocode_status = 'fail';
      fail++;
      log(`FAIL [${{i+1}}/${{total}}] ${{item.name}} / ${{item.query}}`, 'err');
    }}
    results.push(item);
    const pct = Math.round((i+1)/total*100);
    document.getElementById(barId).style.width = pct + '%';
    document.getElementById(progId).textContent = `${{i+1}}/${{total}} (성공 ${{ok}}, 실패 ${{fail}})`;
    if ((i+1) % 20 === 0) log(`→ ${{i+1}}/${{total}} 완료`, 'info');
    await sleep(80);
  }}
  log(`✓ 완료: 성공 ${{ok}}, 실패 ${{fail}}`, 'ok');
  return results;
}}

function downloadJSON(filename, data) {{
  const blob = new Blob([JSON.stringify(data, null, 2)], {{type:'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
}}

async function startAll() {{
  document.getElementById('btn-start').disabled = true;
  log('=== 레이어A 정비사업 시작 ===', 'info');

  // A-main + A-jb 합산
  const allA = [...LAYER_A_MAIN, ...LAYER_A_JB];
  const aResults = await geocodeBatch(allA, 'bar-a', 'prog-a');

  // layerA.json 생성
  const aMain = aResults.filter(x => x.id.startsWith('la'));
  const aJb   = aResults.filter(x => x.id.startsWith('jb'));

  log('=== 관리형 시작 ===', 'info');
  const nbResults = await geocodeBatch(LAYER_A_NB, 'bar-nb', 'prog-nb');

  log('=== 레이어B 시작 ===', 'info');
  const bResults = await geocodeBatch(LAYER_B, 'bar-b', 'prog-b');

  // ── layerA.json 구성 ──
  const layerA = {{
    meta: {{
      total_정비: aMain.length + aJb.length,
      total_관리: nbResults.length,
      updated: "2026-04",
      note: "정비형(재개발/가로주택/지역주택/주거환경개선사업 정비형) + 관리형(동단위 대표좌표)"
    }},
    items: [...aMain, ...aJb],
    items_관리형: nbResults
  }};

  // ── layerB.json 구성 ──
  const layerB = {{
    meta: {{
      type: "무허가정착지",
      total: bResults.length,
      updated: "2026-04",
      note: "자연발생/집단이주/신발생 분류. 31개 목표 중 현재 9건."
    }},
    items: bResults
  }};

  log('=== 다운로드 시작 ===', 'info');
  downloadJSON('layerA.json', layerA);
  await sleep(500);
  downloadJSON('layerB.json', layerB);

  log('✅ 완료! layerA.json, layerB.json 을 data/ 폴더에 저장하세요.', 'ok');
  document.getElementById('btn-start').disabled = false;
}}
</script>
</body>
</html>"""

out_path = os.path.join(BASE, "batch_geocoder.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

total_queries = len(layer_a_main) + len(layer_a_jb) + len(layer_a_nb) + len(layer_b)
print(f"생성 완료: batch_geocoder.html")
print(f"  레이어A 정비: {len(layer_a_main)+len(layer_a_jb)}건")
print(f"  레이어A 관리형: {len(layer_a_nb)}건")
print(f"  레이어B: {len(layer_b)}건")
print(f"  총 지오코딩 대상: {total_queries}건")
print(f"\nbatch_geocoder.html 을 브라우저로 열고 '▶ 전체 시작' 클릭하면 자동 처리됩니다.")
