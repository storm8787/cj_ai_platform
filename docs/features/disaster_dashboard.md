# 재난상황 대시보드

## 1. 기능 개요

- **목적**: 카카오톡 재난상황 단톡방 TXT 파일을 업로드하면, 메시지를 파싱하여 사고별로 분류하고 현황 대시보드와 일일 보고서를 자동 생성
- **사용 대상**: 재난 대응 담당 공무원
- **처리 내용**: TXT 파싱 → 메시지 저장 → 사고 재구성 → 대시보드 통계 → 일일보고 생성

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/disaster_dashboard.py` |
| 사고 재구성 서비스 | `backend/services/disaster_incident_service.py` |
| 일일보고 생성 | `backend/services/disaster_report_service.py` |
| TXT 파싱 | `backend/services/disaster_parser_service.py` |
| 상수 정의 | `backend/services/disaster_constants.py` |
| 재난상황 훅 | `frontend/src/hooks/useDisasterSession.js` |
| 재난 상수 | `frontend/src/constants/disaster.js` |
| 업로드 페이지 | `frontend/src/pages/DisasterUpload.jsx` |
| 대시보드 페이지 | `frontend/src/pages/DisasterDashboard.jsx` |
| 사고 목록 | `frontend/src/pages/DisasterIncidents.jsx` |
| 일일보고 | `frontend/src/pages/DisasterDailyReport.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/disaster` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/disaster/upload` | 카카오톡 TXT 업로드 |
| GET | `/api/disaster/uploads` | 업로드 목록 |
| POST | `/api/disaster/analyze/{upload_id}` | 업로드 분석 (메시지 파싱 → 사고 재구성) |
| GET | `/api/disaster/upload/{upload_id}/summary` | 업로드 요약 |
| GET | `/api/disaster/incidents` | 사고 목록 (필터: upload_id/status/type/emd) |
| GET | `/api/disaster/incidents/{incident_id}` | 사고 상세 + 연결 메시지 |
| GET | `/api/disaster/dashboard/overview` | 통계 (유형별/상태별/읍면동별/시간별) |
| POST | `/api/disaster/reports/daily/generate` | 일일보고 생성 (GPT-4o) |
| POST | `/api/disaster/reports/daily/export-hwpx` | 생성된 일일보고(MD)를 HWPX(한글)로 내보내기 |
| GET | `/api/disaster/reports` | 일일보고 목록 |

---

## 4. 주요 데이터 흐름

```
카카오톡 TXT 업로드
    ↓
disaster_parser_service: 메시지 파싱 (4가지 날짜 형식 지원)
    → disaster_raw_messages 테이블 저장
    ↓
disaster_incident_service: 사고 재구성
    → 위치 유사도 매칭 (difflib, 80% threshold)
    → 상태 변경 추적 (reported → in_progress → completed/closed)
    → disaster_incidents 테이블 저장
    ↓
대시보드 통계 집계 (유형/상태/읍면동/시간대별)
    ↓
일일보고 생성 (gpt-4o, GPT-4o 자연어 보고서)
```

---

## 5. 핵심 구현 세부 사항

### 메시지 파싱 (4가지 날짜 형식)

- 한국어 형식: `2025년 7월 15일 오후 3:30`
- 점 형식: `2025. 7. 15. 오후 3:30`
- 구분선: `--------- 2025년 7월 15일 월요일 ---------`
- 대괄호 형식: `[홍길동] [오후 3:30] 메시지`

### EMD(읍면동) 추출 4단계 전략 (v8 개선)

1. `[대괄호]` 표기 전처리: `[호암직동]` → `호암직동` 으로 변환 후 매칭
2. `EMD_LIST` 공식 행정동명 직접 매칭 (`backend/data/eup_myeon_dong.txt`, 25개)
3. `EMD_ALIASES` 별칭 → 공식명 변환 (예: 호암동→호암직동, 가금면→금가면)
4. `RI_TO_EMD` 리(里) → 상위 읍면동 역조회 (`backend/data/ri_to_emd.json`, 33개 리)
5. Fallback 정규식 — **공식 목록에 있는 EMD만 반환** (임의 단어 오매칭 방지)

> ⚠️ `eup_myeon_dong.txt`에 없는 읍면동은 절대 반환하지 않음.  
> "00리" 패턴은 `ri_to_emd.json` 매핑으로 상위 읍면동을 찾아 반환.

### 위치(location_raw) 추출 개선 (v12)

**v12 수정** (`disaster_parser_service.py`):
- **별칭 EMD 중복 제거**: `_fmt_loc()` 헬퍼 — `칠금동→칠금금릉동` 별칭이 loc에 이미 있으면 제거 후 공식명만 사용 (예: `칠금금릉동 칠금동 금릉로` → `칠금금릉동 금릉로`)
- **trailing 비위치 단어 차단**: compound match 결과에도 `_trim_location_tail()` 적용 (예: `용탄교 주변 수위` → `용탄교 주변`)
- **키워드 prefix 정제**: 키워드(산책로·등산로 등) 앞의 prefix에 `_trim_location_tail` 적용 → `교현천 하천변 수위 상승으로 산책로`에서 `수위 이후` 제거 → `교현천 하천변 산책로`
- **자연 지형명 fallback** (`_NATURAL_GEO_PATTERN`): `삼탄천`, `충주천` 등 천/강 계열 단어가 문장 앞에 오면 우선 추출
- **리(里) 단위 위치 추출** (step 1d): `RI_TO_EMD`에 등록된 리(里)가 first_sentence에 나오면 세부 위치로 추출 (예: `신니면 백현리 절개지...` → `신니면 백현리`)
- **조직명 오인 방지 강화**: `LOCATION_HINT_PATTERNS` space-word group 최소 2자로 변경 (`{1,15}` → `{2,15}`) → `119 및 도` 처럼 단일 한글자가 터미널 직전에 붙는 오매칭 방지
- `_LOCATION_TAIL_STOPS`에 `수위`, `상승`, `하강`, `지속`, `급격히` 추가

**v12 위치 탐색 순서 (읍면동 이후 텍스트)**:
1. 복합 위치 (`_COMPOUND_LOC_PATTERN`: `X 앞 Y`, `X 옆 Y`)
2. LOCATION_KEYWORDS (prefix를 `_trim_location_tail`로 정제)
3. 자연 지형명 (`_NATURAL_GEO_PATTERN`: 천/강 등)
4. RI_TO_EMD 등록 리(里) 단위

**v11 수정** (이전):
- `_ORG_CTX_PATTERN`: `도로과와 자원순환과에서는` 같은 행정기관 컨텍스트 감지 → 그 이전 텍스트만 사용
- `_clip_for_location()`: 행정기관 절단 + 첫 줄 + 100자 제한

### 사고 유형 분류 우선순위 (v8: 겨울 재난 추가 + v9: 계절 자동 필터)

#### 계절별 분류 필터 (v9 신규)

메시지 타임스탬프의 **월(month)**을 읽어 계절에 맞지 않는 유형을 자동으로 건너뜁니다.

| 월 | 계절 | 적용 유형 |
|----|------|----------|
| 4–10월 | 여름 | 겨울 전용 유형(`cold_wave`, `heavy_snow`, `icing`) **제외** |
| 12, 1, 2월 | 겨울 | 여름 전용 유형(`drainage`, `flood`) **제외** |
| 3, 11월 | 전환기 | 모든 유형 허용 (키워드 우선순위대로 판단) |

> 예시: 7월 메시지에 "폭설"이라는 단어가 있어도 `heavy_snow`가 아닌 다음 매칭 유형으로 분류.

#### 유형별 우선순위 및 계절

| 유형 코드 | 한글 | 대표 키워드 | 계절 |
|-----------|------|------------|------|
| `landslide` | 산사태·토사유출 | 산사태, 토사, 낙석, 눈사태 | 연중 |
| `tree_fall` | 나무전도 | 나무전도, 수목전도, 나무 쓰러 | 연중 |
| `cold_wave` | 한파·동파 | 한파, 동파, 수도동파, 동결 | **겨울 전용** |
| `heavy_snow` | 폭설·제설 | 폭설, 제설, 적설, 눈 쌓임 | **겨울 전용** |
| `icing` | 도로결빙 | 결빙, 빙판, 블랙아이스 | **겨울 전용** |
| `drainage` | 배수·맨홀·양수 | 맨홀, 역류, 배수, 양수 | **여름 전용** |
| `flood` | 침수·범람 | 침수, 범람, 수위, 하천 | **여름 전용** |
| `sinkhole` | 싱크홀·노면파손 | 싱크홀, 함몰, 노면파손 | 연중 |
| `rescue` | 수색·구조 | 실종, 수색, 인명구조 | 연중 |
| `facility` | 시설물 이상 | 시설물, 교량, 정전, 균열 | 연중 |
| `road_control` | 도로통제 | 통제, 차단, 통행제한 | 연중 |
| `inspection` | 기타/미분류 | (해당 없음) | - |

### 사고 상태 분류 (우선순위 순)

- `closed`: "해제|통행 재개|개통|상황 종료"
- `completed`: "복구 완료|처리 완료|제설 완료|염화칼슘 살포 완료|..."
- `in_progress`: "조치중|수색중|작업중|제설중|..."
- `monitoring`: "모니터링|설치 완료|이상없음"
- `reported`: (기본값 / "~예정")

### 사고 병합 로직 (상태 흐름 기반 그룹핑)

- 같은 `(emd, incident_type, location)` 메시지는 하나의 사건으로 병합
- 유형 호환 그룹: `flood ↔ drainage ↔ road_control`, `landslide ↔ road_control`, etc.
- 위치 유사도 ≥ 80% (`difflib.SequenceMatcher`)
- 접두어 매칭: "목행용탄동" vs "목행용탄동 용탄교 진입로" → 0.85점 처리
- `closed` 상태를 만나면 사건 종결 → 이후 같은 위치 메시지는 새 사건으로 인식

### 동시 분석 방지

- `analysis_status` 필드: `uploaded` → `analyzing` → `analyzed`
- `analyzing` 중 중복 호출 시 **409 Conflict** 반환

### 대시보드 overview API 응답 필드 (v7.1+)

| 필드 | 설명 |
|------|------|
| `total` | 전체 사건 수 |
| `active_count` | 진행중 사건 수 |
| `done_count` | 완료/종결 사건 수 |
| `affected_emd_count` | 사건 발생 읍면동 수 |
| `top_type` / `top_type_label` | 최다 발생 유형 코드·라벨 |
| `by_type` / `by_type_labeled` | 유형별 집계 (코드키 / 한글라벨키) |
| `by_status` / `by_status_labeled` | 상태별 집계 |
| `by_emd` | 읍면동별 집계 |
| `recent_incidents` | 최근 업데이트 사건 10건 (type_label, status_label 포함) |
| `active_incidents` | 진행중·발생·모니터링 사건 전체 (상한 없음) |
| `done_incidents` | 최근 완료·종결 사건 5건 |
| `emd_map_data` | 읍면동별 위경도·사건수·진행중 수 목록 (25개 전체 EMD 항상 포함) |

---

## 6. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `OPENAI_API_KEY` | 일일보고 GPT-4o 생성 |
| `SUPABASE_URL`, `SUPABASE_KEY` | 모든 데이터 저장 |
| `VITE_KAKAO_MAP_KEY` (프론트) | 카카오맵 표시 (없으면 EMD 도트맵 fallback) |

**Supabase 테이블**:
- `disaster_uploads`: 업로드 파일 정보 + 분석 상태
- `disaster_raw_messages`: 파싱된 메시지
- `disaster_incidents`: 재구성된 사고 목록
- `disaster_incident_messages`: 사고-메시지 연결 테이블
- `disaster_daily_reports`: 일일보고 저장

---

## 7. 수정 시 주의사항

- 일일보고 생성 모델: `gpt-4o` (다른 기능의 `gpt-4o-mini`와 다름)
- **일일보고 출력 형식: Markdown (.md)** — GPT 프롬프트와 폴백 템플릿 모두 MD 형식으로 생성
  - 본문 구조(8단계): 총괄 → 유형별 발생현황 → 조치상황 → 읍면동별 발생현황 → 주요 사건 → 미조치·조치중 사건 → 향후 조치계획 → 참고사항
  - 유형별 발생현황, 조치상황: Markdown 표(`| col | col |`) 형식
  - 주요 사건: `읍면동 | 재난유형 | 상태 | 요약` 표 형식, 읍면동별 정렬
- **상태 집계 정합성** (`_aggregate`): 총계 = `reported + in_progress + completed + monitoring + no_issue + closed`.
  - `completed`(하위호환) = `completed + closed`(총괄·DB 카운트용). `no_issue`(이상없음)는 **완료 건수에 포함하지 않음**(별도 표기).
- **주요 사건 상한**: `MAX_INCIDENTS_IN_REPORT = 50`. 초과분은 읍면동별 발생현황으로 흡수.
- **향후 조치계획 창작 금지**: 조치중/모니터링/미조치 상태 기반 문장만 생성. 데이터에 없는 원인·피해·복구·예산·협조는 생성하지 않음.
- **HWPX 내보내기**: `daily_report_to_hwpx_bytes()` — 생성된 MD를 `_md_report_to_sections()`로 파싱 후 `services/hwpx_writer.build_hwpx`로 변환(표는 텍스트 라인으로 평탄화, 표 미지원).
- **보고자 이름(개인정보)**: 보고서 본문/GPT 프롬프트에 미포함. 사건 목록 화면은 마스킹 표기(`홍○○`), `/incidents` API는 원본 유지.
- 프롬프트: `prompt_service.get("disaster_report", ...)` 패턴 (DB 우선 → 코드 fallback).
  - 관리 키: `system_prompt`, `summary_prompt`, `body_prompt`. `services/prompt_defaults.py`에 등록되어 관리자 '프롬프트 관리'에서 **코드 기본값 노출·수정·재설정** 가능.
  - `body_prompt` 플레이스홀더: `{report_date} {total} {type_breakdown} {status_breakdown} {emd_breakdown} {incident_list}`
  - ⚠️ DB에 구버전 프롬프트가 저장돼 있으면 코드 개선이 반영 안 됨 → 관리자 화면에서 '코드 기본값으로 재설정' 필요
- TXT 파일 인코딩: UTF-8 / CP949 자동 감지
- 빈 배열 insert 방지: `if incident_rows: insert(...)` 가드 필요 (없으면 crash)
- 개인정보: 일일보고 GPT 프롬프트에 보고자 이름 포함하지 않도록 주의
- 프론트엔드: `useDisasterSession()` 훅 사용 (sessionStorage 리액티브)
- 상수 변경 시: `backend/services/disaster_constants.py`와 `frontend/src/constants/disaster.js` 양쪽 모두 업데이트 필요
- 일일보고 페이지: 미리보기(MD 렌더링) / Markdown 원문 탭 전환 + `.md` 파일 다운로드 버튼

---

## 8. 테스트 및 검증 방법

### 자동화 검증 스크립트

```bash
cd /home/user/cj_ai_platform
python backend/tests/evaluate_disaster_dashboard.py
```

10개 항목을 자동 검증 (PASS/WARN/FAIL 결과):
1. TXT 파싱 (메시지 수, 날짜 파싱)
2. EMD 추출 (별칭 포함)
3. 사고 유형 분류 (rescue, drainage, flood 등)
4. 상태 분류 (closed, in_progress, completed 등)
5. 사건 병합 (유형 호환 그룹, 위치 유사도)
6. 유형·지역 커버리지
7. 겨울 샘플 검증
8. Overview 통계 구조
9. 위치 유사도 임계값 동작
10. 위치 추출 정확도 (별칭 중복·trailing 비위치·조직명 오인 등 10개 케이스)

**전용 위치 추출 평가** (`backend/tests/evaluate_location_extraction.py`):
- 28개 케이스 검증: 기본/컨텍스트차단/복합위치/별칭중복/비위치제거/리단위/EMD만/대괄호

**샘플 데이터**:
- `backend/tests/fixtures/disaster_sample_kakao.txt` — 충주시 15개 읍면동, 18가지 사고, 116개 메시지
- `backend/tests/fixtures/disaster_sample_winter_kakao.txt` — 겨울 특보 샘플
- `backend/tests/fixtures/disaster_location_test_kakao.txt` — 위치 추출 패턴 집중 샘플 (v12 신규)

### 수동 확인

- 카카오톡 TXT 파일 업로드 후 `/api/disaster/analyze/{id}` 호출
- `GET /api/disaster/incidents` 응답에서 사고 분류·상태 확인
- `GET /api/disaster/dashboard/overview` 통계 데이터 및 `emd_map_data` 확인
- 일일보고 생성 후 `report_text` 내용 품질 확인

---

## 9. 대시보드 UI 구성 (v10)

`frontend/src/pages/DisasterDashboard.jsx`

- **요약 카드 5개**: 총 사건·진행중(빨간 하이라이트)·완료종결·발생읍면동·최다유형
- **진행중 사건 패널** (`ActiveIncidentPanel`): 상태 점 + 유형/상태 뱃지 + 위치 + 요약 + 시간, 6건 후 확장/축소
- **읍면동 랭킹 테이블** (`EmdRankTable`): 미니 바 + 진행중 있으면 빨간 행 하이라이트
- **최근 완료 사건 목록** (`DoneIncidentList`): 완료/종결 상위 5건
- **차트 2개**: 유형별·상태별 수평 바 차트 (외부 라이브러리 미사용)

> 지도 미사용 이유: 외부 라이브러리(Leaflet 등) 없이 실제 지형 배경을 구현하기 어렵고,  
> CSS 그리드 기반 대체 지도는 실제 지도로 오인될 수 있어 v10에서 지도 없는 대시보드로 재설계.

---

## 10. 향후 개선 과제

- 파싱 규칙 외 형식의 카카오톡 메시지 처리 (신규 버전 대응)
- 사고 유형 분류 정확도 개선 (현재 키워드 기반)
- 실시간 업데이트 (WebSocket 또는 polling)
- 지도에서 사건 클릭 시 상세 화면 연동
