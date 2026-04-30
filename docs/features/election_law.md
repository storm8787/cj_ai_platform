# 선거법 챗봇

## 1. 기능 개요

- **목적**: 공직선거법 관련 질문에 대해 법령·판례·해석례·지침 기반 답변 제공
- **사용 대상**: 충주시청 공무원 (선거 관련 업무 질의)
- **처리 내용**: 질문 유형 분류 → 유형별 검색 전략 적용 → RAG 기반 GPT 답변

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/election_law.py` |
| 벡터스토어 서비스 | `backend/services/vectorstore.py` |
| 프롬프트 관리 | `backend/services/prompt_service.py` |
| 프론트엔드 페이지 | `frontend/src/pages/ElectionLaw.jsx` |
| FAISS 인덱스 | `backend/data/election_law/vectorstores/` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/election-law` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/election-law/ask` | 질문 → 선거법 기반 답변 |
| GET | `/api/election-law/targets` | 검색 대상 목록 (all/law/panli/written/internet/guidance) |
| GET | `/api/election-law/status` | 벡터스토어 상태 |

---

## 4. 주요 데이터 흐름

- 질문 유형 분류: list형/단답형/정의형/기간형/일반형
- list형 질문: 다중 검색어 확장 후 통합 검색
- 검색 대상: `law`(법령), `panli`(판례), `written`(서면질의), `internet`(인터넷질의), `guidance`(지침)
- 결과 중복 제거(content hash 기준) → GPT(확인 필요) 답변 생성
- RAG 기반: VectorStoreService로 관련 조문 검색

---

## 5. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `OPENAI_API_KEY` | GPT 답변 생성 |
| `ELECTION_VECTORSTORE_PATH` | 선거법 FAISS 인덱스 경로 |

- 임베딩 모델: `jhgan/ko-sroberta-multitask` (768차원)
- FAISS 인덱스: `backend/data/election_law/vectorstores/` (다수의 `.index` 파일)

---

## 6. 수정 시 주의사항

- 임베딩 모델 변경 시 vectorstore 재빌드 필요 (차원 불일치 시 crash)
- 검색 대상(`targets`) 변경 시 프론트 `/targets` 응답과 동기화 필요
- 프롬프트는 `prompt_service.get("election_law", ...)` 패턴으로 Supabase 저장 가능

---

## 7. 테스트 및 검증 방법

- `GET /api/election-law/status`로 벡터스토어 로드 여부 확인
- 직접 질문 POST 후 references 배열에 출처가 포함되는지 확인

---

## 8. 향후 개선 과제

- 선거법 개정 시 vectorstore 재빌드 필요 (현재 수동)
- 자동 평가 케이스 추가 검토 (확인 필요)
