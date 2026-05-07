# CLAUDE.md — Claude Code 작업 지침

Claude Code가 이 저장소에서 작업을 시작하기 전에 반드시 읽어야 하는 핵심 지침 파일입니다.

---

## 이 프로젝트

충주시 AI 플랫폼 (`storm8787/cj_ai_platform`) — 충주시청 공무원 업무용 AI 도구 모음.

---

## 먼저 읽어야 할 문서 순서

1. **이 파일 (CLAUDE.md)** — 핵심 규칙·금지사항
2. **`docs/INDEX.md`** — 전체 문서 진입점, 기능별 문서 링크
3. 수정할 기능이 있으면 → **`docs/features/해당기능.md`** 먼저 읽기
4. 배포/환경 관련 → **`docs/DEPLOYMENT.md`**, **`docs/ENVIRONMENT_VARIABLES.md`**
5. 법령 챗봇 수정 시 → **`docs/features/law_chatbot.md`** + **`docs/evaluations/law_chatbot_eval.md`**

> ⚠️ `PROJECT_DOCUMENTATION.md`는 deprecated 됩니다. **`docs/INDEX.md`를 기준으로 사용하세요.**

---
## 브랜치 규칙 (CRITICAL)

- **main 브랜치 직접 push 절대 금지**
- 모든 작업은 별도 브랜치에서 수행
- 완료 후 PR → 사용자 승인 → 머지
---

## 절대 금지 사항

### 보안
- API 키, 토큰, 비밀번호를 코드·문서에 하드코딩 금지
- 환경변수는 `backend/config.py`의 `Settings` 클래스에 선언

### 법령 챗봇 (가장 중요한 제약)
- **키워드 사전 매핑 기반 if 분기 금지**
  - 예: `if "식사" in question → 청탁금지법` 같은 코드 작성 금지
  - 예: 법령명 → 검색어 매핑 dict 추가 금지
  - 예: 특정 지명·기관명으로 점수를 하드코딩하는 boost dict 금지
- **법률 판단은 GPT planner (`legal_query_planner.py`) 가 담당**
  - 코드는 GPT 결과의 형식 검증·정규화만 수행
  - 상세 원칙 → `docs/features/law_chatbot.md`

### 개발 일반
- `requirements.txt`에 없는 패키지 import 금지 (빌드 실패)
- 실제 파일 확인 없이 추측으로 기능 구현 금지
- 문서에도 확인되지 않은 내용은 "확인 필요"로 표시

---

## 자주 하는 작업

### 새 기능 추가
1. `backend/routers/새기능.py` 작성
2. `backend/main.py`에 라우터 등록
3. `frontend/src/pages/새기능Page.jsx` 작성
4. `frontend/src/App.jsx`에 Route 추가
5. `docs/features/새기능.md` 작성
6. `docs/INDEX.md` 링크 추가

### 법령 챗봇 수정
1. `docs/features/law_chatbot.md` 확인
2. `backend/services/legal_query_planner.py` — 검색계획 로직
3. `backend/routers/law_chatbot.py` — 검색/조문선별/답변생성
4. `backend/services/korean_law_mcp_service.py` — MCP 연동
5. 수정 후: `python backend/tests/evaluate_law_chatbot.py --mode mock` (10/10 통과 확인)

### 배포 확인
- `backend/**` 변경 → main 머지 → `backend-deploy.yml` 자동 실행
- 빌드 시간: 약 15~30분 (HuggingFace 모델 다운로드 포함)
- 상세 → `docs/DEPLOYMENT.md`

---

## 문서 업데이트 기준

기능 수정 시 관련 `docs/features/*.md` 파일도 함께 업데이트.
아키텍처 변경 시 `docs/ARCHITECTURE.md` 업데이트.
환경변수 추가 시 `docs/ENVIRONMENT_VARIABLES.md` 업데이트.

---

## 금지 사항 요약표

| 금지 | 이유 |
|------|------|
| main 브랜치 직접 push | CI/CD 안정성 |
| API 키 하드코딩 | 보안 |
| 법령 챗봇에 키워드 사전 추가 | 설계 원칙 위반 |
| `requirements.txt`에 없는 패키지 import | 빌드 실패 |
| Dockerfile 수정 없이 시스템 패키지 의존 | 컨테이너 환경 |
| 문서에 실제 비밀값 기재 | 보안 |
| 확인 없이 추측으로 기능·파일명 생성 | 정확성 |
