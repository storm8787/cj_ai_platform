# 보도자료 생성기

## 1. 기능 개요

- **목적**: 입력한 행사·정책 정보를 바탕으로 충주시 보도자료 형식의 문서 자동 생성
- **사용 대상**: 충주시청 홍보 담당 공무원
- **처리 내용**: 유사 보도자료 RAG 검색 → GPT로 보도자료 생성 → Supabase 사용 로그

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/press_release.py` |
| 벡터스토어 서비스 | `backend/services/vectorstore.py` |
| 프롬프트 관리 | `backend/services/prompt_service.py` |
| 프론트엔드 페이지 | `frontend/src/pages/PressRelease.jsx` |
| FAISS 인덱스 | `backend/data/vectorstores/press_release_faiss.index` |
| 메타데이터 | `backend/data/vectorstores/documents_metadata.pkl` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/press-release` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/press-release/search-similar` | 유사 보도자료 검색 |
| POST | `/api/press-release/generate` | 보도자료 생성 (RAG + GPT) |
| GET | `/api/press-release/status` | 벡터스토어 상태 |

---

## 4. 주요 데이터 흐름

1. 사용자 입력 (행사명, 부서, 날짜, 주요 내용 등)
2. 유사 보도자료 벡터 검색 (FAISS, ko-sroberta-multitask 768차원)
3. 검색된 유사 보도자료를 컨텍스트로 GPT에 전달
4. GPT(gpt-4o)로 보도자료 생성
5. Supabase에 사용 로그 저장

---

## 5. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `OPENAI_API_KEY` | GPT 보도자료 생성 |
| `SUPABASE_URL`, `SUPABASE_KEY` | 사용 로그 저장 |
| `VECTORSTORE_PATH` | FAISS 인덱스 경로 (`/app/data/vectorstores`) |
| `EMBEDDING_MODEL` | 임베딩 모델명 (ko-sroberta-multitask) |

- 임베딩 모델: `jhgan/ko-sroberta-multitask` (768차원)

---

## 6. 수정 시 주의사항

- 임베딩 모델 변경 시 vectorstore 재빌드 필요
- 프롬프트: `prompt_service.get("press_release", "system_prompt", default=_DEFAULT_SYSTEM)` 패턴
- Supabase 로그 테이블: `usage_logs`

---

## 7. 테스트 및 검증 방법

- `GET /api/press-release/status`로 벡터스토어 상태 확인
- POST `/generate` 후 응답에 `references` 배열과 보도자료 텍스트 포함 여부 확인

---

## 8. 향후 개선 과제

- 유사 보도자료 DB 업데이트 (현재 수동 재빌드 필요)
- 생성 보도자료 HWPX 내보내기 기능 (현재 텍스트만)
