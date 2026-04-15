# jaegebal 폴리곤 직접 크롤링 플랜

## 왜 이전 방법이 틀렸나
의제처리구역 SHP(UQ181)는 **모든 법적 designation 통합본**이라
- 폐지·revised된 historical 구역 포함 (예: 삼선제5구역)
- 신통기획·공공재개발·모아주택 후보지 같은 jaegebal 표시 항목 **미포함**
- ⇒ 경계도 다르고 라벨도 다름

## jaegebal 데이터 발견 사항
조사 결과: **각 develop 상세 페이지(`/develops/{id}`) HTML에 폴리곤이 SSR로 embed됨**

```
"name":"신림5구역","region_code":"11620","type":"jaegebal",
"detail_type":"fast","detail_type_display_name":"신속통합기획",
"stage":"progress","detail_stage":"정비구역지정",
"location":[126.931123,37.476905],
"areas":[[[126.927921,37.476279],[126.927926,37.476180],...]]
```

각 region 페이지(`/regions/{code}`)는 그 자치구의 develop ID 37여개를 노출.
서울 25개 자치구 × 37 ≈ **약 900개 develop**.

## 실행 단계
### 1. `scripts/crawl_jaegebal.py` 작성
- 서울 25개 자치구 코드(11110~11740) 순회 → `/regions/{code}` 에서 develop ID 추출
- 각 ID에 대해 `/develops/{id}` 페이지 fetch → 정규식으로 `name/type/detail_type/stage/detail_stage/location/areas` 파싱
- Crawl-delay 1초 준수 → 약 15분 소요
- 결과: `data/jaegebal_polygons.json` (전체 develops + 폴리곤)

### 2. `scripts/match_jaegebal.py` 작성
- 내 488개 사이트와 jaegebal develops를 **좌표 근접도(200m 이내)** + **이름 fuzzy 매칭** 으로 연결
- `data/polygons.json` 재생성 (jaegebal areas 사용)

### 3. `build_bldg_age.py` 재실행 → 새 폴리곤 기준 노후도

### 4. 검증
- 삼선제5 같은 거짓 매칭 사라지는지
- jaegebal 라벨(신통/공공/모아 등)이 매칭에 반영되는지
- 형성유형은 jaegebal에 없으므로 마커 유지

### 5. 커밋 + 푸시

## 리스크
- jaegebal 약관: `robots.txt`는 `/api/` 만 차단, 페이지 크롤링 허용
- 사이트당 1초 지연 + 학술적 지도 용도 → 정상 사용 범위
