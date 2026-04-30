# 법령·자치법규 챗봇

## 1. 기능 개요

- **목적**: 충주시청 공무원이 법령·자치법규 질문에 대해 조문 근거 기반의 구체적인 답변을 받을 수 있는 AI 챗봇
- **사용 대상**: 충주시청 공무원 (내부 업무 질의)
- **처리 내용**: 사용자 질문 → GPT 검색계획 생성 → 법령/자치법규 조문 검색 → 조문 선별 → GPT 답변 생성

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/law_chatbot.py` |
| GPT 검색계획 서비스 | `backend/services/legal_query_planner.py` |
| Korean Law MCP 연동 | `backend/services/korean_law_mcp_service.py` |
| 프롬프트 관리 | `backend/services/prompt_service.py` |
| 프론트엔드 페이지 | `frontend/src/pages/LawChatbot.jsx` |
| 평가 케이스 | `backend/tests/law_chatbot_eval_cases.json` |
| 평가 스크립트 | `backend/tests/evaluate_law_chatbot.py` |
| 벡터스토어 인덱스 | `backend/data/law_chatbot/vectorstores/` |
| 벡터스토어 빌드 | `backend/scripts/build_law_vectorstore.py` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/law-chatbot` (`backend/routers/law_chatbot.py` 내부 선언)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/law-chatbot/ask` | 질문 → 법령 근거 답변 |
| POST | `/api/law-chatbot/search` | 법령 직접 검색 (단순 검색) |
| GET | `/api/law-chatbot/status` | 벡터스토어·API 연결 상태 확인 |
| GET | `/api/law-chatbot/categories` | 검색 카테고리 목록 |

### POST /ask 요청 형식

```json
{
  "question": "공무원 출장 중 개인 차량 사용 시 여비는?",
  "search_scope": "all",
  "chat_history": [
    {"role": "user", "content": "이전 질문"},
    {"role": "assistant", "content": "이전 답변"}
  ]
}
```

### POST /ask 응답 형식

```json
{
  "answer": "...",
  "references": [
    {
      "name": "공무원여비규정",
      "type": "국가법령",
      "article": "제18조 자동차운임",
      "enforcement_date": "20240101",
      "source": "law.go.kr-api",
      "url": "https://www.law.go.kr/법령/공무원여비규정"
    }
  ],
  "search_info": {
    "candidate_count": 8,
    "article_count": 4,
    "vector_count": 0,
    "detail_count": 3
  }
}
```

---

## 4. 주요 데이터 흐름

```
사용자 질문
    ↓
[1] GPT Planner (gpt-4o-mini)
    legal_query_planner.py::LegalQueryPlanner.create_plan()
    → search_plans[] (target, law_name, article_keywords, priority)
    → question_type {numeric, requires_local_law, involves_money_or_gift}
    ↓
[2] 검색 실행 (_execute_legal_search_plan)
    각 search_plan 별:
    ├─ MCP 시도: korean_law_mcp_service.search_*()
    │    └─ 실패 시 → law.go.kr 직접 API (_search_law_api_direct)
    └─ 자치법규 결과 없으면 → FAISS 벡터스토어 fallback
    ↓
[3] 후보 정렬 (_rank_candidates)
    plan.law_name 일치도 + 질문 토큰 매칭 + target 유형 일치
    사전 매핑 없음 — planner 결과만 신뢰
    ↓
[4] 조문 선별 (_select_relevant_articles)
    질문 토큰 + article_keywords + 명시적 조문번호 + 수치 패턴(numeric=true 시)
    ↓
[5] 답변 생성 (gpt-4o)
    _generate_answer()
    선별된 조문을 system prompt {context}에 삽입
```

---

## 5. 환경변수 및 외부 의존성

| 환경변수 | 역할 | 필수 여부 |
|---------|------|---------|
| `OPENAI_API_KEY` | GPT planner(gpt-4o-mini) + 답변(gpt-4o) | 필수 |
| `LAW_API_OC` | law.go.kr 직접 API 인증키 | 필수 (없으면 검색 불가) |
| `KOREAN_LAW_MCP_ENABLED` | MCP CLI 활성화 여부 (false 권장) | 선택 |
| `KOREAN_LAW_MCP_COMMAND` | MCP CLI 명령어 | 선택 |
| `KOREAN_LAW_MCP_TIMEOUT` | MCP timeout 초 | 선택 |
| `LAW_CHATBOT_VECTORSTORE_PATH` | 자치법규 FAISS 인덱스 경로 | 선택 |
| `EMBEDDING_MODEL` | 임베딩 모델 경로 (BAAI/bge-m3) | 자치법규 fallback 시 필요 |

**외부 의존성**:
- OpenAI API (gpt-4o-mini, gpt-4o)
- law.go.kr REST API (`http://www.law.go.kr/DRF/`)
- FAISS (자치법규 벡터스토어)
- BM25 (rank-bm25 라이브러리)
- FlagEmbedding (BAAI/bge-m3)

---

## 6. 핵심 상수 (law_chatbot.py)

```python
ANSWER_MODEL = "gpt-4o"
MAX_SEARCH_PLANS = 6        # 실행할 검색계획 최대 수
MAX_CANDIDATES_PER_PLAN = 4  # 계획당 후보 법령 최대 수
MAX_DETAIL_DOCS = 5          # 전문 조회할 최대 법령 수
MAX_ARTICLES_FOR_ANSWER = 12 # GPT에 전달할 최대 조문 수
MAX_CONTEXT_CHARS = 60000    # GPT 컨텍스트 최대 길이
VECTOR_SCORE_MIN = 0.30      # 벡터 유사도 최소 임계값
VECTOR_SCORE_RELATIVE = 0.85 # 동적 임계값 (최고 점수의 85%)
```

---

## 7. 수정 시 주의사항

### 절대 금지 (설계 원칙 위반)

```python
# ❌ 금지 — 특정 키워드가 있으면 특정 법령을 결정하는 if 분기
if "식사" in question or "음식물" in question:
    target_law = "청탁금지법"

# ❌ 금지 — 지역·기관명으로 점수를 하드코딩하는 boost dict
BOOST = {"충주": 20, "조례": 15, "위원회": 10}

# ❌ 금지 — 법령명 매핑 dict
LAW_ALIAS = {"청탁금지법": "부정청탁 및 금품등 수수의 금지에 관한 법률"}
```

### 올바른 수정 방법

- **검색 품질 개선** → `legal_query_planner.py`의 GPT 시스템 프롬프트 수정
- **조문 선별 개선** → `_select_relevant_articles()`에서 planner 결과(`article_keywords`, `question_type`) 활용 방식 조정
- **후보 정렬 개선** → `_rank_candidates()`에서 plan.law_name 기반 점수 계산 로직 조정
- **새 answer 원칙 추가** → `_DEFAULT_ANSWER_SYSTEM` 또는 Supabase 프롬프트 업데이트

### MCP 관련

`korean-law-mcp` npm 패키지는 JSON-RPC stdio MCP 서버. CLI 형태 호출은 항상 rc=1 실패.
- 로그 `[korean-law-mcp] CLI 실패 rc=1` → 정상 (law.go.kr API가 실제 동작 경로)
- MCP 완전 비활성화: `KOREAN_LAW_MCP_ENABLED=false`

### fast-fail

연속 3회 MCP 실패 → 5분간 MCP 호출 skip (`_FAIL_THRESHOLD=3`, `_FAIL_BACKOFF_SEC=300`)

---

## 8. 테스트 및 검증 방법

```bash
# mock 평가 (API 키 불필요)
cd backend
python tests/evaluate_law_chatbot.py --mode mock

# planner 평가 (OPENAI_API_KEY 필요)
python tests/evaluate_law_chatbot.py --mode planner

# live 평가 (실행 중인 서버 필요)
python tests/evaluate_law_chatbot.py --mode live --base-url http://localhost:8000

# 특정 케이스만
python tests/evaluate_law_chatbot.py --mode mock --cases TC-001 TC-004
```

상태 확인: `GET /api/law-chatbot/status`
- `vectorstore.loaded`: FAISS 인덱스 로드 여부
- `api.connected`: law.go.kr API 연결 여부

자세한 평가 구조 → `docs/evaluations/law_chatbot_eval.md`

---

## 9. 향후 개선 과제

- **MCP 정상화**: `korean-law-mcp`를 JSON-RPC stdio 프로토콜로 올바르게 호출하는 방식 구현
  - 현재 law.go.kr 직접 API가 실질 검색 경로이므로 서비스에는 영향 없음
- **벡터스토어 갱신**: 충주시 자치법규 신규·개정 조례 반영을 위한 정기 재빌드 필요
  - `python scripts/build_law_vectorstore.py` 실행 필요
- **httpx 명시적 의존성**: `requirements.txt`에서 주석 처리(`#httpx==0.27.0`)되어 있음
  - `openai` 패키지의 transitive dep으로 동작 중이나 버전 고정 안 됨
