# 충주시 AI 플랫폼 — 문서 진입점

> 이 파일이 프로젝트 문서의 **공식 진입점**입니다.
> `PROJECT_DOCUMENTATION.md`는 deprecated 되었습니다. 이 파일을 기준으로 사용하세요.

---

## 프로젝트 개요

**충주시 AI 플랫폼** — 충주시청 공무원 업무용 AI 도구 모음.

- 저장소: `storm8787/cj_ai_platform`
- 백엔드: FastAPI (`backend/`) → Azure Container Apps (`cj-ai-backend`)
- 프론트엔드: React + Vite (`frontend/`) → Azure Static Web Apps

---

## 문서 읽는 순서

### AI 에이전트(Claude Code 등)가 처음 이 저장소를 열었을 때

```
1. CLAUDE.md             ← 핵심 작업 규칙·금지사항
2. docs/INDEX.md         ← 지금 이 파일
3. docs/ARCHITECTURE.md  ← 전체 구조 파악
4. 수정할 기능의 docs/features/*.md
5. 필요 시 docs/DEPLOYMENT.md, docs/ENVIRONMENT_VARIABLES.md
```

### 배포 관련 작업
```
docs/DEPLOYMENT.md → docs/ENVIRONMENT_VARIABLES.md
```

### 법령 챗봇 관련 작업
```
docs/features/law_chatbot.md → docs/evaluations/law_chatbot_eval.md
```

---

## 전체 문서 목록

### 핵심 지침
| 파일 | 내용 |
|-----|------|
| `CLAUDE.md` | Claude Code 작업 지침, 금지사항, 브랜치 규칙 |
| `docs/INDEX.md` | 이 파일. 전체 문서 진입점 |
| `docs/AI_WORKING_GUIDE.md` | AI 에이전트 작업 원칙·체크리스트 |

### 프로젝트 구조
| 파일 | 내용 |
|-----|------|
| `docs/ARCHITECTURE.md` | 전체 아키텍처 (백엔드/프론트/DB/서비스) |
| `docs/DEPLOYMENT.md` | 배포 흐름 (Dockerfile, GHCR, Azure) |
| `docs/ENVIRONMENT_VARIABLES.md` | 환경변수 전체 목록 |
| `docs/CHANGELOG.md` | 주요 변경 이력 |

### 기능별 문서 (docs/features/)

| 파일 | 기능 | 프론트 경로 |
|-----|------|------------|
| `law_chatbot.md` | 법령·자치법규 챗봇 | `/law-chatbot` |
| `election_law.md` | 선거법 챗봇 | `/election-law` |
| `press_release.md` | 보도자료 생성기 | `/press-release` |
| `meeting_summarizer.md` | 회의요약기 | `/meeting-summary` |
| `kakao_promo.md` | 카카오 홍보문구 생성기 | `/kakao-promo` |
| `hwpx_converter.md` | HWPX 변환기 | `/hwpx-converter` |
| `data_validator.md` | 공공데이터 검증기 | `/data-validator` |
| `report_writer.md` | 업무보고 작성기 | `/report-writer` |
| `trip_report.md` | 출장보고 생성기 | `/trip-report` |
| `address_geocoder.md` | 주소-좌표 변환기 | `/address-geocoder` |
| `excel_merger.md` | 엑셀 취합기 | `/excel-merger` |
| `prompt_manager.md` | 프롬프트 중앙 관리 | `/prompt-manager` |
| `timeline_planner.md` | 사업 타임라인 플래너 | `/timeline` |
| `translator.md` | HWPX 번역기 | `/translator` |
| `merit_report.md` | 공적조서 생성기 | `/merit-report` |
| `data_analysis.md` | 통계분석 (Pandas Agent) | `/data-analysis` |
| `news.md` | 뉴스 뷰어 | `/news` |
| `auth.md` | 인증 시스템 | `/login` |
| `board.md` | 게시판 시스템 | `/board/*` |
| `disaster_dashboard.md` | 재난상황 대시보드 | `/disaster-*` |
| `disaster_location_extraction.md` | 재난 위치 추출 시스템 (규칙+GPT 2단계) | — |

### 평가 문서 (docs/evaluations/)
| 파일 | 내용 |
|-----|------|
| `law_chatbot_eval.md` | 법령 챗봇 자동 평가 구조 및 실행 방법 |

---

## 백엔드 주요 파일 맵

```
backend/
├── main.py                        ← 라우터 등록 진입점
├── config.py                      ← 환경변수 Settings 클래스
├── requirements.txt               ← Python 패키지 의존성
├── Dockerfile                     ← 컨테이너 빌드
├── routers/                       ← 기능별 API 엔드포인트
│   ├── law_chatbot.py             ← 법령 챗봇 (핵심)
│   ├── election_law.py            ← 선거법 챗봇
│   ├── press_release.py           ← 보도자료
│   └── ... (17개 추가)
├── services/                      ← 비즈니스 로직
│   ├── legal_query_planner.py     ← GPT 기반 법령 검색계획
│   ├── korean_law_mcp_service.py  ← Korean Law MCP 연동
│   ├── vectorstore.py             ← FAISS 벡터스토어
│   ├── openai_service.py          ← OpenAI 공통 클라이언트
│   └── prompt_service.py          ← Supabase 프롬프트 관리
├── tests/
│   ├── evaluate_law_chatbot.py    ← 법령 챗봇 자동 평가
│   └── law_chatbot_eval_cases.json
└── data/                          ← FAISS 인덱스, 참조 데이터
```

---

## 프론트엔드 주요 파일 맵

```
frontend/src/
├── App.jsx              ← 라우트 정의
├── context/
│   └── AuthContext.jsx  ← 인증 상태 전역 관리
├── components/
│   └── Layout.jsx       ← 공통 레이아웃
├── services/
│   └── api.js           ← 백엔드 API 호출 함수
└── pages/               ← 31개 페이지 컴포넌트
```

---

## GitHub Actions 워크플로우

| 파일 | 트리거 | 역할 |
|-----|--------|------|
| `.github/workflows/backend-deploy.yml` | main push + `backend/**` | Docker 빌드 → GHCR → Azure 배포 |
| `.github/workflows/azure-static-web-apps-*.yml` | (자동) | 프론트엔드 Azure SWA 배포 |
| `.github/workflows/law-chatbot-eval.yml` | workflow_dispatch | 법령 챗봇 자동 평가 |
| `.github/workflows/scrape_news.yml` | (자동) | 뉴스 스크래핑 |

---

## 데이터베이스 (Supabase)

주요 테이블:

| 테이블 | 용도 |
|--------|------|
| `user_profiles` | 사용자 계정·역할·소속 |
| `boards` | 게시판 글 (notice/archive/qna) |
| `board_answers` | QnA 답변 |
| `prompts` | AI 프롬프트 중앙 관리 |
| `prompt_history` | 프롬프트 변경 이력 |
| `disaster_uploads` | 재난상황 파일 업로드 |
| `disaster_raw_messages` | 파싱된 카카오톡 메시지 |
| `disaster_incidents` | 재구성된 사고 목록 |
| `disaster_incident_messages` | 사고-메시지 연결 |
| `disaster_daily_reports` | 재난 일일보고 |
| `usage_logs` | API 사용 로그 |

Supabase Storage 버킷: `boards` (게시판 첨부파일)

---

## 외부 의존 서비스

| 서비스 | 용도 | 환경변수 |
|--------|------|---------|
| OpenAI API | 대부분의 AI 기능 | `OPENAI_API_KEY` |
| law.go.kr API | 법령 챗봇 국가법령 검색 | `LAW_API_OC` |
| Supabase | DB, Auth, Storage | `SUPABASE_URL`, `SUPABASE_KEY` |
| DeepL API | HWPX 번역기 | `DEEPL_API_KEY` |
| Kakao Maps API | 주소-좌표 변환 | `KAKAO_API_KEY` |
| GitHub API | 뉴스 Gist 저장 | `GITHUB_TOKEN`, `GIST_ID` |
