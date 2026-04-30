# 법령·자치법규 챗봇 가이드

## 개요

충주시청 공무원이 법령·자치법규 질문에 대해 조문 근거 기반의 답변을 받을 수 있는 AI 챗봇.

- 엔드포인트: `POST /api/law-chatbot/ask`
- 프론트엔드: `frontend/src/pages/LawChatbot.jsx`
- 라우터: `backend/routers/law_chatbot.py`
- 검색계획 서비스: `backend/services/legal_query_planner.py`
- MCP 서비스: `backend/services/korean_law_mcp_service.py`

---

## 핵심 설계 원칙

### 1. 키워드 사전 매핑 금지

코드가 법률 판단을 해서는 안 된다. 다음과 같은 패턴은 **절대 금지**:

```python
# ❌ 금지 — 코드가 법령을 결정하는 if 분기
if "식사" in question or "음식물" in question:
    search_target = "청탁금지법"

# ❌ 금지 — 특정 단어로 점수를 올리는 하드코딩 boost dict
BOOST_MAP = {"충주": 20, "조례": 15, "위원회": 10}

# ❌ 금지 — 법령명 → 검색어 매핑 사전
LAW_ALIAS = {"청탁금지법": "부정청탁 및 금품등 수수의 금지에 관한 법률"}
```

### 2. GPT Planner가 법률 판단 담당

모든 법령 관련 판단은 `LegalQueryPlanner.create_plan()`이 GPT를 호출해서 수행.
코드는 GPT 결과의 **형식 검증과 정규화만** 수행.

### 3. question_type 메타데이터로 동작 결정

GPT planner가 반환하는 `question_type` 필드로 코드 동작을 조절:

```json
{
  "question_type": {
    "numeric": true,           // 금액·기간·횟수 등 수치가 필요한 질문
    "requires_local_law": true, // 자치법규(조례·규칙)가 필요한 질문
    "involves_money_or_gift": true  // 금품·경품·선물 제공 관련 질문
  }
}
```

- `numeric=true` → 조문 선별 시 수치 패턴이 있는 조문에 +10점 가산
- `requires_local_law=true` → FAISS 벡터스토어 fallback 활성화
- `involves_money_or_gift=true` → planner가 공직선거법(기부행위) 검색계획 포함

---

## 처리 흐름 상세

### Step 1: GPT Planner 호출

`legal_query_planner.py::LegalQueryPlanner.create_plan()`

GPT(gpt-4o-mini)가 다음을 반환:
```json
{
  "issue_summary": "공무원 자가용 출장 시 여비 지급 기준",
  "search_confidence": "high",
  "question_type": {"numeric": true, "requires_local_law": false, "involves_money_or_gift": false},
  "search_plans": [
    {
      "target": "law",
      "law_name": "공무원여비규정",
      "article_keywords": ["자가용", "자동차운임", "운임", "제18조"],
      "reason": "공무원 여비 지급 기준을 직접 규정하는 대통령령",
      "priority": 1
    },
    ...
  ]
}
```

**target 분류 기준:**
- `law`: 법률, 대통령령(시행령), 부령(시행규칙) 모두 포함
- `ordin`: 지방자치단체 조례·규칙
- `admrul`: 훈령, 예규, 고시, 지침 등 행정기관 내부규범
- `all`: 불명확하거나 여러 대상을 검색해야 하는 경우

### Step 2: 검색 실행

`law_chatbot.py::_execute_legal_search_plan()`

각 search_plan에 대해:
1. `_search_by_plan()` → law_name + article_keywords 조합으로 검색
2. 검색 경로:
   - 1순위: `korean_law_mcp_service.search_*()`  → MCP CLI (현재 rc=1 실패)
   - 2순위: `_search_law_api_direct()` → law.go.kr XML API (실제 동작 경로)
3. 자치법규 질문이고 API 결과 없으면: FAISS 벡터스토어 fallback

### Step 3: 조문 선별

`_select_relevant_articles()` — 각 법령의 전체 조문 중 관련 조문 선별

점수 계산 (사전 매핑 없이 순수 텍스트 매칭):
- (a) 질문 토큰 + article_keywords가 조문 제목/번호/본문에 포함: +8/+5/+3
- (b) 명시적 조문번호 직접 언급 ("제17조" 등): +20
- (c) `numeric_question=true`이고 조문에 수치 패턴 있음: +10

### Step 4: 답변 생성

`_generate_answer()` — gpt-4o로 최종 답변 생성

선별된 조문을 system prompt의 `{context}` 자리에 삽입.
모델: `gpt-4o` (ANSWER_MODEL 상수)

답변 형식:
1. 결론
2. 근거 (📌 법령명 조문번호: 내용)
3. 실무 유의사항 (⚠️)
4. 참고 법령 목록 (📋)

---

## 핵심 상수 (law_chatbot.py)

```python
ANSWER_MODEL = "gpt-4o"
MAX_SEARCH_PLANS = 6        # 실행할 검색계획 최대 수
MAX_CANDIDATES_PER_PLAN = 4  # 계획당 후보 법령 최대 수
MAX_DETAIL_DOCS = 5          # 전문 조회할 최대 법령 수
MAX_ARTICLES_FOR_ANSWER = 12 # GPT에게 전달할 최대 조문 수
MAX_CONTEXT_CHARS = 60000    # GPT 컨텍스트 최대 길이
VECTOR_SCORE_MIN = 0.30      # 벡터 유사도 최소 임계값
VECTOR_SCORE_RELATIVE = 0.85 # 동적 임계값 (최고 점수의 85%)
```

---

## Korean Law MCP 현황

`korean-law-mcp` npm 패키지는 JSON-RPC stdio 프로토콜 MCP 서버.
현재 코드가 CLI 형태로 호출하므로 항상 rc=1 실패 반환.

```
[법령 챗봇 로그]
[korean-law-mcp] CLI 실패 rc=1 | cmd=korean-law search_law --query ...
[법령 챗봇] 직접 API fallback 성공: target=law, query=..., count=5
```

→ 위 로그는 정상. law.go.kr 직접 API가 실제 검색 경로.

**fast-fail 설계:**
- 연속 3회 실패 → 5분간 MCP 호출 완전 skip
- `_FAIL_THRESHOLD = 3`, `_FAIL_BACKOFF_SEC = 300`
- 목적: 매 검색마다 timeout 대기 비용 방지

**MCP 비활성화 방법** (빠른 응답이 중요한 경우):
```env
KOREAN_LAW_MCP_ENABLED=false
```

---

## 벡터스토어 (충주시 자치법규)

경로: `backend/data/law_chatbot/vectorstores/`

| 파일 | 내용 |
|-----|------|
| `index.faiss` | FAISS 인덱스 (BGE-M3 임베딩) |
| `index.pkl` | 텍스트 + 메타데이터 |
| `bm25_corpus.pkl` | BM25 토큰화 코퍼스 |

검색 방식: Dense (FAISS) + Sparse (BM25) 하이브리드 → RRF 결합

벡터스토어가 없거나 로드 실패 시 자치법규 관련 fallback 검색 불가.

**벡터스토어 재빌드:**
```bash
cd backend
python scripts/build_law_vectorstore.py
```

---

## 평가 시스템

### 평가 케이스 (`tests/law_chatbot_eval_cases.json`)

10개 케이스, 카테고리:
- 여비, 정보공개, 수의계약, 청탁금지법, 지방보조금
- 도로법, 육아휴직수당, 개인정보, 자치법규-연임, 경품

각 케이스 구조:
```json
{
  "id": "TC-001",
  "question": "...",
  "required_keywords": ["..."],
  "required_any_of": [["...", "..."]],
  "forbidden_phrases": ["..."],
  "fail_if_only": ["..."]
}
```

### 평가 실행

```bash
# mock (API 키 불필요, 평가 로직 검증용)
python tests/evaluate_law_chatbot.py --mode mock

# planner (OPENAI_API_KEY 필요, GPT 검색계획 품질 평가)
python tests/evaluate_law_chatbot.py --mode planner

# live (실행 중인 서버 필요, 전체 답변 품질 평가)
python tests/evaluate_law_chatbot.py --mode live --base-url http://localhost:8000

# 특정 케이스만
python tests/evaluate_law_chatbot.py --mode mock --cases TC-001 TC-004
```

### GitHub Actions 평가

`.github/workflows/law-chatbot-eval.yml` → workflow_dispatch 수동 트리거

---

## 자주 묻는 질문 / 트러블슈팅

### Q: 챗봇이 "정확한 정보를 찾지 못했습니다"라고 답변

- `LAW_API_OC` 환경변수 설정 확인 (`/api/law-chatbot/status` 로 `api.connected` 확인)
- `api.connected: false`면 law.go.kr API 키가 없거나 잘못된 것

### Q: 자치법규 검색이 안 됨

1. API를 통한 조례 검색이 실패하는 경우, FAISS 벡터스토어 fallback 동작 확인
2. 벡터스토어 파일(`data/law_chatbot/vectorstores/index.faiss`) 존재 여부 확인
3. `/api/law-chatbot/status`에서 `vectorstore.loaded` 확인

### Q: 답변에 수치(금액 등)가 없음

GPT planner의 `question_type.numeric` 필드가 제대로 설정되는지 확인.
법령 원문에 해당 수치가 포함된 조문이 검색·선별되어야 함.

### Q: 법령 챗봇에 새 법령 추가가 필요

새 법령은 추가 코딩 없이 자동 검색됨. law.go.kr API가 국가법령 전체를 포함.
자치법규의 경우 벡터스토어에 포함되어 있지 않으면 API 검색으로만 찾을 수 있음.

### Q: planner가 엉뚱한 법령을 검색 계획에 포함

planner 시스템 프롬프트 수정 가능 위치:
- 기본값: `legal_query_planner.py::_DEFAULT_LEGAL_QUERY_PLANNER_PROMPT`
- Supabase 오버라이드: `prompt_service.get("law_chatbot", "legal_query_planner_prompt")`

수정 원칙: 프롬프트 내 판단 기준 개선. 코드에 새 분기/사전 추가 금지.

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/law-chatbot/ask` | 질문 → 법령 근거 답변 |
| POST | `/api/law-chatbot/search` | 단순 법령 검색 |
| GET | `/api/law-chatbot/status` | 벡터스토어·API 연결 상태 |
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
