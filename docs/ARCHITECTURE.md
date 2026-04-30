# 아키텍처 문서

## 시스템 구성 개요

```
[사용자 브라우저]
       │
       ▼
[Azure Static Web Apps]        ← React + Vite (frontend/)
       │ API 호출 (HTTPS)
       ▼
[Azure Container Apps]         ← FastAPI (backend/)
       │
       ├─ OpenAI API (gpt-4o / gpt-4o-mini)
       ├─ law.go.kr REST API (국가법령정보센터)
       ├─ Supabase (PostgreSQL)
       ├─ DeepL API (번역)
       ├─ Kakao API (지도/주소 변환)
       └─ GitHub API (뉴스 Gist 저장)
```

---

## 백엔드 (backend/)

### 기술 스택

| 항목 | 내용 |
|------|------|
| 프레임워크 | FastAPI 0.109.2 |
| Python | 3.11 |
| 서버 | Uvicorn |
| AI | OpenAI gpt-4o, gpt-4o-mini |
| 임베딩 | BAAI/bge-m3 (BGE-M3), jhgan/ko-sroberta-multitask |
| 벡터스토어 | FAISS (faiss-cpu) + BM25 (rank-bm25) |
| DB | Supabase (supabase Python SDK) |
| HTTP 클라이언트 | httpx (openai 패키지 transitive dep) |
| 설정 관리 | pydantic-settings |

### 디렉토리 구조

```
backend/
├── main.py                    # FastAPI 앱 생성, 라우터 등록
├── config.py                  # Settings 클래스 (pydantic-settings)
├── requirements.txt
├── Dockerfile
├── routers/                   # 기능별 API 엔드포인트
│   ├── law_chatbot.py         # 법령·자치법규 챗봇 (핵심)
│   ├── election_law.py        # 선거법 챗봇
│   ├── press_release.py       # 보도자료 생성기
│   ├── disaster_dashboard.py  # 재난상황 대시보드
│   ├── auth.py                # 인증
│   ├── board.py               # 게시판
│   └── ... (17개 추가 라우터)
├── services/                  # 비즈니스 로직
│   ├── legal_query_planner.py # GPT 기반 법령 검색계획 생성
│   ├── korean_law_mcp_service.py  # Korean Law MCP CLI 연동
│   ├── vectorstore.py         # FAISS 벡터스토어
│   ├── openai_service.py      # OpenAI 공통 클라이언트
│   ├── prompt_service.py      # Supabase 프롬프트 관리
│   └── ... (기타 서비스)
├── tests/
│   ├── evaluate_law_chatbot.py    # 평가 스크립트
│   └── law_chatbot_eval_cases.json  # 10개 평가 케이스
├── data/
│   ├── law_chatbot/vectorstores/  # 충주시 자치법규 FAISS 인덱스
│   ├── election_law/vectorstores/ # 선거법 FAISS 인덱스
│   └── vectorstores/              # 보도자료 FAISS 인덱스
└── scripts/
    └── build_law_vectorstore.py   # 벡터스토어 빌드 스크립트
```

### 라우터 등록 패턴

`backend/main.py`에서 prefix와 tags를 지정하여 등록:

```python
app.include_router(law_chatbot.router)               # prefix는 라우터 내부에 정의
app.include_router(press_release.router, prefix="/api/press-release")
```

법령 챗봇은 라우터 파일 내에서 `prefix="/api/law-chatbot"`을 직접 선언.

---

## 프론트엔드 (frontend/)

### 기술 스택

| 항목 | 내용 |
|------|------|
| 프레임워크 | React 18 |
| 번들러 | Vite |
| 스타일링 | Tailwind CSS |
| 라우팅 | React Router v6 |
| HTTP | fetch API (api.js 래퍼) |
| 배포 | Azure Static Web Apps |

### 디렉토리 구조

```
frontend/src/
├── App.jsx              # 라우트 정의
├── main.jsx             # 엔트리포인트
├── index.css            # 글로벌 스타일
├── context/
│   └── AuthContext.jsx  # 로그인 상태 전역 관리
├── components/
│   └── Layout.jsx       # 공통 레이아웃 (사이드바 포함)
├── hooks/
│   └── useDisasterSession.js
├── services/
│   └── api.js           # 백엔드 API 호출 함수 모음
├── constants/
│   └── disaster.js      # 재난상황 상수
└── pages/               # 28개 페이지 컴포넌트
    ├── LawChatbot.jsx
    ├── ElectionLaw.jsx
    ├── Dashboard.jsx
    └── ...
```

### 인증 흐름

- `AuthContext.jsx`가 로그인 상태 관리
- `ProtectedRoute` 컴포넌트로 인증 필요 페이지 보호
- `/login` 외 모든 라우트가 인증 필요

---

## 법령 챗봇 처리 흐름 (핵심)

```
사용자 질문
    │
    ▼
[1] GPT Planner (gpt-4o-mini)
    legal_query_planner.py
    → search_plans[] 생성
    → question_type 메타데이터 생성
    │
    ▼
[2] 검색 실행
    law_chatbot.py::_execute_legal_search_plan()
    각 plan별:
      ├─ MCP 시도 (korean_law_mcp_service.py)
      │   └─ 실패 시 → law.go.kr 직접 API (httpx)
      └─ 자치법규 fallback: FAISS 벡터스토어
    │
    ▼
[3] 조문 선별
    _select_relevant_articles()
    점수 기준: 질문 토큰 + article_keywords + 조문번호 + 수치 패턴(numeric=true 시)
    │
    ▼
[4] 답변 생성 (gpt-4o)
    _generate_answer()
    조문 컨텍스트를 system prompt에 삽입
```

---

## 데이터 흐름 — 벡터스토어

자치법규 검색에 FAISS 벡터스토어 사용:

```
[build_law_vectorstore.py 실행 (오프라인)]
    → 충주시 자치법규 텍스트 수집
    → BGE-M3 임베딩
    → FAISS 인덱스 저장 (data/law_chatbot/vectorstores/)
    → BM25 코퍼스 저장 (bm25_corpus.pkl)

[런타임]
    → _load_vectorstore() (지연 로딩)
    → Dense (FAISS) + Sparse (BM25) 하이브리드 검색
    → RRF (Reciprocal Rank Fusion) 스코어 결합
```

---

## MCP (Korean Law MCP)

`korean-law-mcp` npm 패키지는 실제로는 JSON-RPC stdio MCP 서버임.
CLI 형태(`korean-law search_law --query ...`) 호출은 작동하지 않음 → rc=1 반환.

현재 실제 검색 경로: **law.go.kr 직접 API (fallback)**

`KoreanLawMCPService`의 fast-fail 설계:
- 연속 3회 실패 → 5분간 MCP 호출 skip
- 목적: 매 검색마다 timeout 대기 비용 방지

---

## CI/CD

### backend-deploy.yml

트리거: `backend/**` 변경 후 main 머지

```
1. Checkout
2. GHCR 로그인
3. Docker build & push
   → ghcr.io/storm8787/cj-ai-backend:latest
   → ghcr.io/storm8787/cj-ai-backend:{SHA}
4. Azure Container Apps update
   → cj-ai-backend (rg-cj-ai-platform)
```

### azure-static-web-apps-agreeable-smoke-0b02cf31e.yml

Azure Static Web Apps 자동 배포 (프론트엔드).

### law-chatbot-eval.yml

수동 트리거 (`workflow_dispatch`):
- mock / planner 모드 선택
- 특정 케이스 ID 지정 가능
- 결과 JSON 아티팩트 30일 보관

---

## 보안 고려사항

- API 키는 Azure Container Apps 환경변수에 저장
- GitHub Secrets: `GHCR_TOKEN`, `AZURE_CREDENTIALS`, `OPENAI_API_KEY`, `LAW_API_OC`
- CORS: `Settings.CORS_ORIGINS` 환경변수로 허용 도메인 제한
- 인증: Supabase Auth 기반 (auth.py 라우터)
