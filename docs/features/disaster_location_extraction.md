# 재난대시보드 — 위치 추출 시스템

`/disaster-*` 라우트에서 사용하는 재난 메시지 위치 추출 아키텍처 문서입니다.

---

## 개요

카카오톡 재난 상황 메시지에서 **사건 발생 위치**를 추출하는 2단계 파이프라인:

1. **규칙 기반 정규표현식 추출** — 빠르고 비용 없음, 명시적 위치에 강함
2. **GPT 배치 보완** — 규칙이 놓친 위치를 `gpt-4o-mini` 한 번의 배치 호출로 보완

---

## 단계 1: 규칙 기반 추출

**파일**: `backend/services/disaster_parser_service.py`

### 추출 우선순위 (함수: `extract_location_raw`)

| 단계 | 방식 | 예시 |
|------|------|------|
| 1a | `LOCATION_HINT_PATTERNS` 복합 패턴 | `"칠금동 남산아파트 앞"` |
| 1b | `LOCATION_KEYWORDS` prefix 키워드 | `"아파트", "병원", "터널"` 앞 문맥 |
| 1c | `_NATURAL_GEO_PATTERN` 자연지명 | `"달천", "남산봉"` |
| 1d | `RI_PATTERN` + `RI_TO_EMD` 역조회 | `"목행리 → 목행동"` |

### LOCATION_KEYWORDS (주요 항목)

도로·교통 관련:
- 교차로, 사거리, 삼거리, 고가도로, 지하도, 육교, 터널, 나들목

건물·시설:
- 아파트, 마트, 병원, 요양병원, 의원, 학교, 주민센터, 복지관, 경로당, 파출소, 소방서

자연·지형:
- 하천, 저수지, 수문, 고개, 고속도로

### LOCATION_HINT_PATTERNS

`[emd] [공백+단어 2~15개] [terminal_keyword]` 형식으로 매칭:

```python
terminal_keywords = (
    "앞|옆|근처|인근|부근|일대|주변|"
    "아파트|학교|병원|주민센터|파출소|소방서|저수지|터널|고개|광장|나들목|..."
)
```

### 후처리: `_trim_location_tail`

위치 문자열 말미의 조치 단어 제거:
```
"긴급", "처리", "조치", "확인", "수위", "상승", "하강" 등
```

### `_fmt_loc` — 별칭 중복 방지

```python
def _fmt_loc(emd: str, emd_text: str, loc: str) -> str:
    # 별칭 EMD가 공식명에 포함되면 loc만 반환 (칠금동→칠금금릉동 중복 방지)
    if emd_text and emd_text.startswith(emd):
        return loc
    return f"{emd_text or emd} {loc}".strip()
```

---

## 단계 2: GPT 배치 보완

**배경**: 규칙 기반 추출이 `location_raw == emd` (읍면동만 남음) 상태일 때, 즉 구체적 위치를 찾지 못했을 때 실행.

### 함수: `enrich_locations_with_gpt`

**파일**: `backend/services/disaster_parser_service.py`

```python
async def enrich_locations_with_gpt(
    incidents: List[Dict],
    openai_service,
) -> List[Dict]:
```

**동작 방식**:

1. `location_raw == emd` 또는 `location_raw`가 없는 사건만 필터링
2. 배치 프롬프트 구성:
   ```
   1. [칠금동] 아파트 화재 발생, 소방차 출동
   2. [직동] 하천 수위 상승
   ```
3. `gpt-4o-mini` 단일 호출 (model, max_tokens=400, temperature=0.1)
4. 응답 파싱: `"N: 위치"` 형식
5. DB 업데이트 (변경된 항목만)

**실패 처리**: 예외 발생 시 원본 데이터 유지 (non-blocking)

### 함수: `_enrich_incident_locations_gpt`

**파일**: `backend/routers/disaster_dashboard.py`

```python
async def _enrich_incident_locations_gpt(supabase, upload_id: str) -> None:
```

분석 완료 후 DB에서 사건 목록을 읽어 GPT 보완 후 업데이트.

### 호출 시점 (`analyze_disaster_chat` 엔드포인트)

```python
result = _run_analysis(supabase, upload_id)  # 동기 분석

try:
    await _enrich_incident_locations_gpt(supabase, upload_id)  # 비동기 GPT 보완
except Exception as gpt_e:
    logger.warning("GPT location enrichment failed (non-fatal): ...")

return result
```

---

## 평가

**테스트 파일**: `backend/tests/evaluate_location_extraction.py`

```bash
cd backend
python3 tests/evaluate_location_extraction.py
```

**현재 결과**: 28/28 PASS

| 카테고리 | 케이스 | 결과 |
|----------|--------|------|
| 기본 | 8 | ✅ |
| 컨텍스트 차단 | 3 | ✅ |
| 조직명 오인 방지 | 2 | ✅ |
| 복합 위치 | 3 | ✅ |
| 별칭·중복 방지 | 2 | ✅ |
| 비위치 제거 | 3 | ✅ |
| 리(里) 단위 | 2 | ✅ |
| EMD만 존재 시 | 3 | ✅ |
| 대괄호 형식 | 2 | ✅ |

---

## 관련 파일

| 파일 | 역할 |
|------|------|
| `backend/services/disaster_parser_service.py` | 위치 추출 규칙 + GPT 보완 함수 |
| `backend/routers/disaster_dashboard.py` | API 엔드포인트, GPT 보완 호출 |
| `backend/services/disaster_constants.py` | EMD 목록, 별칭 매핑 |
| `backend/tests/evaluate_location_extraction.py` | 28개 케이스 평가 스크립트 |
| `backend/tests/fixtures/disaster_location_test_kakao.txt` | 테스트 샘플 메시지 |

---

## 버전 이력

| 버전 | 날짜 | 주요 변경 |
|------|------|-----------|
| v13 | 2026-05 | GPT 배치 보완 추가, LOCATION_KEYWORDS 확장, 28/28 테스트 PASS |
| v12 | 2026-05 | `_NATURAL_GEO_PATTERN` 추가, `_fmt_loc` 별칭 중복 방지, 위치 추출 28케이스 테스트 신설 |
| v7.1 | 2026-05 | EMD 별칭 인식, `_trim_location_tail` 후처리, 3단계 위치 매칭 |
