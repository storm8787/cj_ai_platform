# 기능 맵 — 기능 ↔ 파일 대응표

## 백엔드 라우터 ↔ 프론트엔드 페이지 대응

| 기능명 | 백엔드 라우터 | API prefix | 프론트엔드 페이지 | 프론트 라우트 |
|-------|-------------|-----------|----------------|------------|
| 법령·자치법규 챗봇 | `routers/law_chatbot.py` | `/api/law-chatbot` | `pages/LawChatbot.jsx` | `/law-chatbot` |
| 선거법 챗봇 | `routers/election_law.py` | `/api/election-law` | `pages/ElectionLaw.jsx` | `/election-law` |
| 보도자료 생성기 | `routers/press_release.py` | `/api/press-release` | `pages/PressRelease.jsx` | `/press-release` |
| 공적조서 생성기 | `routers/merit_report.py` | `/api/merit-report` | `pages/MeritReport.jsx` | `/merit-report` |
| 통계분석 | `routers/data_analysis.py` | `/api/data-analysis` | `pages/DataAnalysis.jsx` | `/data-analysis` |
| 번역기 | `routers/translator.py` | `/api/translator` | `pages/Translator.jsx` | `/translator` |
| 주소-좌표 변환 | `routers/address_geocoder.py` | `/api/geocoder` | `pages/AddressGeocoder.jsx` | `/address-geocoder` |
| 카카오 홍보문구 | `routers/kakao_promo.py` | `/api/kakao-promo` | `pages/KakaoPromo.jsx` | `/kakao-promo` |
| 엑셀 취합기 | `routers/excel_merger.py` | `/api/excel-merger` | `pages/ExcelMerger.jsx` | `/excel-merger` |
| 회의요약기 | `routers/meeting_summarizer.py` | `/api/meeting` | `pages/MeetingSummarizer.jsx` | `/meeting-summary` |
| 업무보고 작성 | `routers/report_writer.py` | `/api/report-writer` | `pages/ReportWriter.jsx` | `/report-writer` |
| 공공데이터 검증기 | `routers/data_validator.py` | `/api/data-validator` | `pages/DataValidator.jsx` | `/data-validator` |
| 출장보고 생성기 | `routers/trip_report.py` | `/api/trip-report` | `pages/TripReport.jsx` | `/trip-report` |
| 타임라인 플래너 | `routers/timeline_planner.py` | (내부 정의) | `pages/TimelinePlanner.jsx` | `/timeline` |
| 프롬프트 관리 | `routers/prompt_manager.py` | (내부 정의) | `pages/PromptManager.jsx` | `/prompt-manager` |
| HWPX 변환기 | `routers/hwpx_converter.py` | (내부 정의) | `pages/HwpxConverter.jsx` | `/hwpx-converter` |
| 재난상황 대시보드 | `routers/disaster_dashboard.py` | `/api/disaster` | `pages/DisasterDashboard.jsx` | `/disaster-dashboard` |
| 재난상황 업로드 | `routers/disaster_dashboard.py` | `/api/disaster` | `pages/DisasterUpload.jsx` | `/disaster-upload` |
| 재난상황 현황 | `routers/disaster_dashboard.py` | `/api/disaster` | `pages/DisasterIncidents.jsx` | `/disaster-incidents` |
| 재난일보 | `routers/disaster_dashboard.py` | `/api/disaster` | `pages/DisasterDailyReport.jsx` | `/disaster-report` |
| 뉴스 뷰어 | `routers/news.py` | `/api/news` | `pages/NewsViewer.jsx` | `/news` |
| 인증 | `routers/auth.py` | `/api/auth` | `pages/Login.jsx` | `/login` |
| 게시판 (공지) | `routers/board.py` | `/api/board` | `pages/NoticeBoard.jsx` | `/board/notice` |
| 게시판 (자료) | `routers/board.py` | `/api/board` | `pages/ArchiveBoard.jsx` | `/board/archive` |
| 게시판 (QnA) | `routers/board.py` | `/api/board` | `pages/QnaBoard.jsx` | `/board/qna` |
| 헬스체크 | `routers/health.py` | `/api` | — | — |
| 대시보드 | — | — | `pages/Dashboard.jsx` | `/` |
| 소개 | — | — | `pages/About.jsx` | `/about` |

---

## 서비스 ↔ 라우터 의존 관계

| 서비스 파일 | 사용하는 라우터 | 역할 |
|-----------|--------------|------|
| `services/legal_query_planner.py` | `law_chatbot.py` | GPT 기반 법령 검색계획 생성 |
| `services/korean_law_mcp_service.py` | `law_chatbot.py` | Korean Law MCP CLI 연동 (+ fallback) |
| `services/vectorstore.py` | `election_law.py`, `press_release.py` | FAISS 벡터스토어 검색 |
| `services/openai_service.py` | 여러 라우터 | OpenAI 공통 클라이언트 |
| `services/prompt_service.py` | `law_chatbot.py`, `election_law.py` 등 | Supabase 저장 프롬프트 관리 |
| `services/supabase_service.py` | `board.py`, `auth.py` 등 | Supabase DB 접근 |
| `services/disaster_incident_service.py` | `disaster_dashboard.py` | 재난 사고 데이터 처리 |
| `services/disaster_report_service.py` | `disaster_dashboard.py` | 재난일보 생성 |
| `services/disaster_parser_service.py` | `disaster_dashboard.py` | 재난 데이터 파싱 |
| `services/kordoc_service.py` | (확인 필요) | kordoc 문서 변환 서비스 |
| `services/disaster_constants.py` | `disaster_dashboard.py` | 재난 상수 정의 |

---

## 데이터 파일 위치

| 파일/디렉토리 | 설명 |
|------------|------|
| `data/law_chatbot/vectorstores/index.faiss` | 충주시 자치법규 FAISS 인덱스 |
| `data/law_chatbot/vectorstores/index.pkl` | FAISS 인덱스 메타데이터 |
| `data/law_chatbot/vectorstores/bm25_corpus.pkl` | BM25 코퍼스 |
| `data/election_law/vectorstores/` | 선거법 관련 FAISS 인덱스들 |
| `data/vectorstores/` | 보도자료 관련 FAISS 인덱스 |
| `data/eup_myeon_dong.txt` | 읍면동 목록 데이터 |
| `data/public_data_standards.json` | 공공데이터 표준 정보 |

---

## GitHub Actions 워크플로우

| 파일 | 트리거 | 역할 |
|-----|--------|------|
| `.github/workflows/backend-deploy.yml` | main push + `backend/**` | 백엔드 Docker 빌드 → GHCR push → Azure 배포 |
| `.github/workflows/azure-static-web-apps-agreeable-smoke-0b02cf31e.yml` | (확인 필요) | 프론트엔드 Azure Static Web Apps 배포 |
| `.github/workflows/law-chatbot-eval.yml` | workflow_dispatch | 법령 챗봇 자동 평가 |
| `.github/workflows/scrape_news.yml` | (확인 필요) | 뉴스 스크래핑 |
| `.github/workflows/azure-aca-deploy.yml.disabled` | 비활성화됨 | 구 ACA 배포 워크플로우 |
