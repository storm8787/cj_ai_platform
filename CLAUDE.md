# CLAUDE.md — Claude Code 작업 지침

이 파일은 Claude Code가 이 저장소에서 작업할 때 항상 먼저 읽어야 하는 규칙 파일입니다.

---

## 저장소 개요

**충주시 AI 플랫폼** (`storm8787/cj_ai_platform`)

충주시청 공무원이 업무에서 사용하는 AI 도구 모음입니다.
- 백엔드: FastAPI (`backend/`)
- 프론트엔드: React + Vite (`frontend/`)
- 배포: Azure Container Apps (백엔드) + Azure Static Web Apps (프론트엔드)
- CI/CD: GitHub Actions

상세 아키텍처 → `docs/ARCHITECTURE.md`
배포 절차 → `docs/DEPLOYMENT.md`
기능 맵 → `docs/FEATURE_MAP.md`
법령 챗봇 심화 가이드 → `docs/LAW_CHATBOT_GUIDE.md`

---

## 브랜치 규칙 (CRITICAL)

- **main 브랜치에 직접 push 금지**
- 모든 작업은 별도 브랜치에서 진행
- 완료 후 PR 생성 → 사용자 승인 후 머지

---

## 코딩 규칙

### 전역
- 비밀키·API 키를 코드에 절대 하드코딩하지 말 것
- 환경변수는 `backend/config.py`의 `Settings` 클래스에 선언 (pydantic-settings)
- 새 라우터 추가 시 `backend/main.py`에 등록 필요

### 법령 챗봇 (가장 중요한 제약)
- **키워드 사전 매핑(if 분기) 절대 금지**
  - 예: `if "식사" in question → 청탁금지법` 같은 코드 작성 금지
  - 예: 법령명 → 검색어 매핑 dict 추가 금지
  - 예: 특정 지명·기관명으로 점수를 하드코딩하는 boost dict 금지
- **법률 판단은 GPT planner(`legal_query_planner.py`)가 담당**
  - 코드는 GPT 결과의 형식 검증·정규화만 수행
  - `question_type` 메타데이터(numeric, requires_local_law, involves_money_or_gift)를 통해 동작 결정
- 상세 설계 원칙 → `docs/LAW_CHATBOT_GUIDE.md`

---

## 자주 하는 작업별 가이드

### 새 기능(라우터) 추가
1. `backend/routers/새기능.py` 작성
2. `backend/main.py`에 `from routers import 새기능` 후 `app.include_router(...)` 추가
3. `frontend/src/pages/새기능Page.jsx` 작성
4. `frontend/src/App.jsx`에 라우트 추가

### 배포 확인
- `backend/**` 변경 후 main 머지 → `backend-deploy.yml` 자동 실행
- 빌드·배포 시간: 약 15~30분 (Dockerfile에 HuggingFace 모델 다운로드 포함)
- 자세한 내용 → `docs/DEPLOYMENT.md`

### 법령 챗봇 수정
1. 검색계획 로직 변경 → `backend/services/legal_query_planner.py`
2. 검색/조문선별/답변생성 로직 → `backend/routers/law_chatbot.py`
3. MCP 연동 → `backend/services/korean_law_mcp_service.py`
4. 수정 후 평가: `python backend/tests/evaluate_law_chatbot.py --mode mock`
5. 자세한 내용 → `docs/LAW_CHATBOT_GUIDE.md`

---

## 환경변수 설정

로컬: `backend/.env` 파일 생성 (`.gitignore`에 포함됨)
배포: Azure Portal → Container App → 환경 변수

전체 목록 → `docs/ENVIRONMENT_VARIABLES.md`

---

## 테스트

```bash
# 법령 챗봇 mock 평가 (API 키 불필요)
cd backend && python tests/evaluate_law_chatbot.py --mode mock

# 법령 챗봇 planner 평가 (OPENAI_API_KEY 필요)
cd backend && python tests/evaluate_law_chatbot.py --mode planner

# GitHub Actions로 실행
# .github/workflows/law-chatbot-eval.yml → workflow_dispatch 수동 트리거
```

---

## 금지 사항 요약

| 금지 | 이유 |
|------|------|
| main 브랜치 직접 push | CI/CD 안정성 |
| API 키 하드코딩 | 보안 |
| 법령 챗봇에 키워드 사전 추가 | 설계 원칙 위반 |
| `requirements.txt`에 없는 패키지 import | 빌드 실패 |
| Dockerfile 수정 없이 시스템 패키지 의존 | 컨테이너 환경 |
