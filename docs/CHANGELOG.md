# 변경 이력

최신 변경 이력부터 역순으로 정리합니다.

---

## 2026-07 — 업무보고 작성기 대개편 (입력폼·목차편집·후처리·HWPX·프롬프트·프롬프트 관리)

**배경**: 생성 결과가 실제 공무원 업무보고 문서처럼 보이지 않는다는 문제 → 진단 후 단계적으로 개선. 실제 충주시 서식/공개 행정문서 분석 반영.

**변경 내용**:
- **입력폼**(1단계): 부서·작성자·보고일자·확인된 사실 입력 추가, 분량 라벨↔동작 정합, 사실 우선·자리표시자 규칙
- **목차 편집 UI**(2단계): 섹션 항목 이름 수정·추가·삭제·순서 변경(`custom_sections`)
- **후처리 품질**(3단계): 항목 내 모든 문장 종결어미 교정(날짜·소수 보존), 개조식 번호·행정기호 보존
- **결과 인라인 편집**(4단계): '내용 편집' 토글, 편집 결과가 복사·TXT·HWPX 반영
- **HWPX(한글) 내보내기**(5단계): `services/hwpx_writer.py` — 실제 충주시 서식(REF)을 템플릿으로 채택(`templates/hwpx/`), 본문(section0)만 생성. 여백·글꼴·기호(□·❍·-·※) 일치. 새 pip 의존성 없이 `zipfile`+`lxml`
- **프롬프트 품질**: 유형별 지시문(`REPORT_TYPE_DIRECTIVES`, 계획/대책/상황/분석/기타), 문장형/개조식 혼용(섹션 성격별), 금지표현, 허위수치 절대 금지(자리표시자 형식+temperature 0.3)
- **문장형 꼭지/줄분리(후처리 정규화)**: 서술형 챕터를 문장 수 기준 **2~3 꼭지**로 재구성(`_merge_narrative_paragraph`), 인라인 `1)2)3)` 줄분리(`_split_inline_enumeration`), 동일 라벨 반복 합치기(`_collapse_same_label`) — DB override·모델 변덕과 무관하게 항상 적용
- **프롬프트 DB 관리**: `services/prompt_defaults.py`(코드 기본값 레지스트리) + `POST /api/prompts/reset-default` + 관리자 화면 '코드 기본값으로 재설정' 버튼. DB에 저장된 옛 프롬프트가 코드 개선을 덮어쓰던(silent override) 문제 해소
- **버그픽스**: 새 프롬프트에서 `summary`가 리스트로 반환돼 `ReportResponse` 검증 실패(500)하던 문제 → summary/제목 문자열 정규화

**관련 파일**: `backend/routers/report_writer.py`, `backend/services/hwpx_writer.py`, `backend/services/prompt_defaults.py`, `backend/routers/prompt_manager.py`, `frontend/src/pages/ReportWriter.jsx`, `frontend/src/pages/PromptManager.jsx`, `docs/features/report_writer.md`, `docs/features/prompt_manager.md`

---

## 2026-05 — 재난상황 대시보드 v13: MD 표 렌더링 수정 + GPT 위치 보완 + UI 개선

**배경**: 3가지 사용자 불만 해결 — (1) 일일보고서 Markdown 표가 화면에 표시되지 않음, (2) 위치 추출 정확도 부족, (3) 읍면동별 현황 테이블이 너무 짧아 불필요한 스크롤 발생.

**변경 내용**:

### 1. 일일보고서 Markdown 렌더러 전면 재작성 (`frontend/src/pages/DisasterDailyReport.jsx`)

- `isTableSep(line)`: 공백 제거 후 `|`, `-`, `:` 만 남으면 구분선 판별 — 모든 Markdown 표 형식 처리
- `parseRow(line)`: `|`로 분할 후 1:-1 슬라이스 + trim
- `renderInline(text)`: `**굵게**`, `` `인라인코드` `` 지원
- 블록 단위 파싱: 표 내 빈 줄 1개 허용 (GPT 출력 특성 대응)
- 코드 펜스(` ``` `), 순서 있는 리스트(`1. 2.`), 구분선(`---`) 추가 지원

### 2. GPT 배치 위치 보완 (`backend/services/disaster_parser_service.py`, `backend/routers/disaster_dashboard.py`)

- `enrich_locations_with_gpt()`: `gpt-4o-mini` 단일 배치 호출로 `location_raw == emd`인 사건들의 위치 보완
- `_enrich_incident_locations_gpt()`: 분석 완료 후 비동기 호출, 실패해도 결과에 영향 없음
- `LOCATION_KEYWORDS` 확장: 병원, 학교, 주민센터, 아파트, 저수지, 터널, 나들목 등 15개 추가
- `LOCATION_HINT_PATTERNS` terminal 키워드 확장

### 3. 읍면동 현황 테이블 레이아웃 수정 (`frontend/src/pages/DisasterDashboard.jsx`)

- `EmdRankTable` 내부 `max-h-72` 제거 → `flex-1 overflow-y-auto min-h-0` 래퍼 적용
- 카드에 `min-h-[300px]` 추가 — 인접 카드 높이에 맞게 자동 늘어남

### 4. 신규 문서 추가

- `docs/features/disaster_location_extraction.md`: 위치 추출 2단계 파이프라인 상세 문서 (규칙 기반 + GPT 보완)

**테스트**: `python3 backend/tests/evaluate_location_extraction.py` → 28/28 PASS

---

## 2026-05 — 재난상황 대시보드 위치 추출 정확도 개선 + 일일보고서 표 형식 (v12)

**배경**: 위치 추출 오탐(행정기관 컨텍스트 이후 도로명 오인, trailing 비위치 단어 포함, 별칭 EMD 중복) 및 일일보고서 Markdown 표 호환성 문제.

**변경 내용**:

### 위치 추출 개선 (`backend/services/disaster_parser_service.py`)

- `_NATURAL_GEO_PATTERN` 추가: `^([가-힣]{2,8}(?:천|강|저수지|호수|봉))` — 문두 자연지명(천·강·봉 등) 즉시 캡처
- `LOCATION_HINT_PATTERNS` 공백-단어 그룹 최솟값 `{1,15}` → `{2,15}` (단일 글자 가짜 매칭 방지)
- `_LOCATION_TAIL_STOPS` 확장: `"수위", "상승", "하강", "지속", "급격히"` 추가
- `_fmt_loc(emd, emd_text, loc)` 헬퍼 추가: 별칭 EMD 중복 방지 (칠금동→칠금금릉동 공식명 기준 단일 표기)
- `extract_location_raw()` 재작성:
  - 1a. 복합 패턴 + `_trim_location_tail` 적용
  - 1b. 키워드 prefix → `_trim_location_tail(prefix)` 클린징 후 사용
  - 1c. `_NATURAL_GEO_PATTERN` (자연지명 문두 매칭)
  - 1d. `RI_PATTERN` + `RI_TO_EMD` 검증 (리(里) 단위 역조회)

### 일일보고서 표 형식 개선 (`backend/services/disaster_report_service.py`)

- `_md_table()`: `|---|---|` → `| --- | --- |` (공백 포함 표준 Markdown 형식으로 변경)

### 테스트 추가 (`backend/tests/`)

- `evaluate_location_extraction.py` 신규: 28개 케이스 전용 위치 추출 정확도 평가 (28/28 PASS)
- `fixtures/disaster_location_test_kakao.txt` 신규: 다양한 위치 표현 패턴 포함 120개 샘플 메시지
- `evaluate_disaster_dashboard.py` 업데이트: 테스트 항목 9→10개

---

## 2026-05 — 재난상황 대시보드 분류기·UI 개선 (v7.1)

**배경**: 기존 분류기 정확도 미흡 (EMD 별칭 미인식, 사건 과분리 44건, rescue 유형 미지원), 대시보드 UI가 단순 표/카드 수준이었음.

**변경 내용**:

### 분류기 개선 (`backend/services/`)

- `disaster_constants.py`
  - `EMD_ALIASES`: 카카오톡 줄임 표기 → 공식 행정동 코드 매핑 (호암동→호암직동 등 10개)
  - `EMD_FALLBACK_BLACKLIST`: 비지명 한자어 fallback 매칭 오탐 방지
  - `INCIDENT_TYPE_LABELS`에 `rescue: "수색·구조"` 추가
- `disaster_parser_service.py`
  - EMD 추출 3단계: EMD_LIST → EMD_ALIASES → fallback regex (최소 2글자 제약)
  - `rescue` 유형 분류 규칙 추가 (실종·수색·인명구조)
  - `tree_fall` 패턴 확장 (`나무.*쓰러|수목.*쓰러|쓰러진.*나무`)
  - `drainage` 규칙을 `flood` 앞으로 이동 (맨홀역류→drainage 정확 분류)
  - `monitoring` 상태: "설치 완료" 포함 (안전봉 설치 후 completed 오분류 방지)
  - `in_progress` 상태: "수색중" 추가
  - `_trim_location_tail()`: 위치 문자열 말미 조치 단어 제거 ("긴급", "처리" 등)
  - `_find_emd_text_form()`: 별칭 포함 EMD 텍스트 형태 역탐색 헬퍼
- `disaster_incident_service.py`
  - 유형 호환 그룹 `_TYPE_COMPAT` 도입 (flood↔drainage↔road_control 등)
  - 위치 매칭 3단계: 빈 위치(0.81)→접두어 매칭(0.85)→SequenceMatcher(≥0.80)
  - EMD 없는 메시지: 재난 키워드 있으면 직전 사건에 부착, 없으면 버림 (사건 과분리 방지)

### 백엔드 API 확장 (`backend/routers/disaster_dashboard.py`)

- `GET /api/disaster/dashboard/overview` 응답에 신규 필드 추가:
  - `active_count`, `done_count`, `affected_emd_count`, `top_type`, `top_type_label`
  - `by_type_labeled`, `by_status_labeled` (한글 라벨 키)
  - `recent_incidents` (최근 10건, type_label·status_label 포함)
  - `emd_map_data` (읍면동별 위경도·사건수·진행중 수)
  - `EMD_COORDS` 충주시 25개 읍면동 위경도 좌표 내장

### 프론트엔드 UI 개편 (`frontend/src/`)

- `pages/DisasterDashboard.jsx` 전면 재설계:
  - 요약 카드 5개 (총 사건·진행중·완료종결·발생읍면동·최다유형)
  - 지도 영역: 카카오맵(VITE_KAKAO_MAP_KEY 있을 때) / EMD 도트맵 fallback
  - 최근 사건 카드 (유형·상태 필터)
  - 유형별·상태별·읍면동별 수평 바 차트 (외부 라이브러리 미사용)
- `constants/disaster.js`: `rescue: "수색·구조"` 추가

### 테스트 및 검증 (`backend/tests/`)

- `fixtures/disaster_sample_kakao.txt` 신규 작성 (75메시지, 9유형, 12개 EMD)
- `evaluate_disaster_dashboard.py` 신규 작성 (7개 항목 자동 검증, PASS:6/WARN:1/FAIL:0)

---

## 2026-04 — 문서 체계 전면 개편 (v9)

- `PROJECT_DOCUMENTATION.md` deprecated → `docs/INDEX.md` 중심 구조로 전환
- `CLAUDE.md` 신규 작성 (Claude Code 핵심 작업지침)
- `docs/INDEX.md` 신규 작성 (문서 진입점)
- `docs/features/` 하위에 20개 기능별 문서 신규 작성
- `docs/evaluations/law_chatbot_eval.md` 신규 작성
- `docs/CHANGELOG.md` 신규 작성

---

## 2026-04 — 법령 챗봇 v9 (키워드 사전 매핑 전면 제거)

**배경**: 코드에 하드코딩된 법령 사전이 설계 원칙 위반이라는 사용자 판단.

**변경 내용**:
- `backend/routers/law_chatbot.py`
  - `_NUMERIC_Q_KEYWORDS` frozenset 삭제
  - `_rank_candidates()` 내 지역/기관명 boost dict 삭제 ("충주", "조례", "위원회" 등)
  - `_select_relevant_articles()` 내 boost dict 삭제
  - `_looks_like_local_question()`, `_is_numeric_question()`, `_normalize_ordin_query()` 삭제
  - `numeric_question` 파라미터: planner의 `question_type.numeric`으로 대체
- `backend/services/legal_query_planner.py`
  - `question_type` 메타데이터 필드 추가 (`numeric`, `requires_local_law`, `involves_money_or_gift`)
  - `_normalize_question_type()` 정규화 메서드 추가
  - planner 시스템 프롬프트에 충주시 자치법규 명시 규칙 추가
  - `involves_money_or_gift=true` 시 공직선거법 검색계획 포함 규칙 추가
- `backend/services/korean_law_mcp_service.py`
  - MCP fast-fail 설계 추가 (연속 3회 실패 → 5분간 skip)
  - `search_ordinance()`, `get_ordinance_text()`에서 강제 "충주시" prefix 제거
- **평가 시스템 신설**:
  - `backend/tests/law_chatbot_eval_cases.json` (10개 케이스)
  - `backend/tests/evaluate_law_chatbot.py` (mock/planner/live 3가지 모드)
  - `.github/workflows/law-chatbot-eval.yml`

---

## 2026-04 — law.go.kr 직접 API 복구 (MCP 프로토콜 불일치 hotfix)

**배경**: `korean-law-mcp` npm 패키지가 JSON-RPC stdio MCP 서버인데, 코드가 CLI 형태(`korean-law search_law --query ...`)로 호출 → 항상 rc=1 실패 → 챗봇 완전 무응답.

**변경 내용**:
- `backend/routers/law_chatbot.py`에 law.go.kr 직접 API fallback 복구
  - `_search_law_api_direct()`, `_fetch_full_text_from_law_api()`, `_parse_search_xml()` 복원
- MCP 시도 → 실패 시 직접 API 호출 이중화 구조 확립

---

## 2026-04 — 법령 챗봇 v8 (GPT Planner 아키텍처 도입)

**변경 내용**:
- 기존 키워드 추출 + Agentic 재검색 루프 구조 폐기
- GPT(gpt-4o-mini) planner가 `search_plans[]` 생성 → 조문 단위 검색 구조로 전환
- `backend/services/legal_query_planner.py` 신규 작성
- `backend/services/korean_law_mcp_service.py` 신규 작성 (MCP CLI 연동 시도)
- 직접 API fallback 제거 (나중에 복구됨, 위 항목 참고)
- 답변 system prompt에 수치형 답변 원칙 추가 (항목 9~11)

---

## 과거 이력 (버전별 요약)

| 버전 | 주요 변경 내용 |
|-----|--------------|
| v7.1 | 재난상황 단톡 대시보드 추가 (카카오톡 TXT → 사고 분류 → 일일보고) |
| v7.0 | HWPX 변환기, 재난상황 기반 기능 추가 |
| v6.0 | 프롬프트 중앙 관리 시스템 (Supabase 기반) |
| v5.1 | 임베딩 모델 분리 (법령챗봇: bge-m3 1024차원, 기타: ko-sroberta 768차원) |
| v5.0 | 출장보고 생성기, 타임라인 플래너 추가 |
| v4.x | 게시판 시스템, 인증(Supabase Auth) 추가 |
| v3.x | 법령 챗봇 초기 버전, 선거법 챗봇 |
| v2.x | 보도자료 생성기, 회의요약기, 번역기 |
| v1.0 | 초기 플랫폼 (보도자료, 뉴스 기능) |
