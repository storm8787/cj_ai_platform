# 게시판 시스템

## 1. 기능 개요

- **목적**: 공지사항·자료실·QnA 게시판 운영 (내부 소통공간)
- **사용 대상**: 충주시청 전 공무원 (일반 사용자 + 관리자)
- **처리 내용**: Supabase 기반 CRUD + Supabase Storage 파일 업로드

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/board.py` |
| 게시판 서비스 | `backend/services/supabase_service.py` |
| 공지 페이지 | `frontend/src/pages/NoticeBoard.jsx` |
| 자료실 페이지 | `frontend/src/pages/ArchiveBoard.jsx` |
| QnA 페이지 | `frontend/src/pages/QnaBoard.jsx` |
| 상세 보기 | `frontend/src/pages/BoardDetail.jsx` |
| 글쓰기 | `frontend/src/pages/BoardWrite.jsx` |
| 수정 | `frontend/src/pages/BoardEdit.jsx` |

---

## 3. 게시판 종류

| 유형 | 경로 | 글쓰기 권한 | 특징 |
|-----|------|-----------|------|
| `notice` | `/board/notice` | admin만 | 공지사항 |
| `archive` | `/board/archive` | admin만 | 자료실 (파일 첨부) |
| `qna` | `/board/qna` | 모든 사용자 | 질문·답변 |

---

## 4. 주요 API 엔드포인트

API prefix: `/api/board` (main.py에서 등록)

| 메서드 | 경로 | 설명 | 권한 |
|-------|------|------|------|
| GET | `/api/board/list/{board_type}` | 글 목록 (페이지네이션) | 인증 |
| GET | `/api/board/detail/{board_id}` | 글 상세 + 답변 | 인증 |
| POST | `/api/board/create` | 글 작성 | 인증 (유형별 권한) |
| POST | `/api/board/create-with-file` | 파일 첨부 글 작성 | 인증 |
| PUT | `/api/board/update/{board_id}` | 글 수정 | 작성자/admin |
| DELETE | `/api/board/delete/{board_id}` | 글 삭제 | 작성자/admin |
| POST | `/api/board/answer/{board_id}` | QnA 답변 작성 | admin |
| DELETE | `/api/board/answer/{answer_id}` | 답변 삭제 | admin |
| GET | `/api/board/status` | 서비스 상태 | 인증 |

---

## 5. 주요 데이터 흐름

```
글 작성 (파일 포함):
파일 업로드 → Supabase Storage (boards 버킷)
→ UUID 파일명으로 저장 (원본 파일명은 DB 별도 저장)
→ Supabase boards 테이블에 글 정보 + 파일 URL 저장

글 조회:
boards 테이블에서 목록/상세 조회
→ board_answers 테이블에서 QnA 답변 조회
→ 조회수(view_count) 업데이트
```

---

## 6. Supabase 테이블·버킷

```
boards (
  id, board_type, title, content,
  author_id, file_url, file_name,
  created_at, view_count
)

board_answers (
  id, board_id, content,
  author_id, created_at
)
```

Storage 버킷: `boards` (파일 첨부)

---

## 7. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | Supabase API 키 |

---

## 8. 수정 시 주의사항

- 파일명: UUID로 변환 저장 (한글 파일명 지원)
- notice/archive 글쓰기: admin 권한 체크 필수
- 조회수 업데이트는 상세 조회 시 자동 처리
- Supabase RLS 활성화 시 정책 설정 필요

---

## 9. 테스트 및 검증 방법

- admin 계정으로 공지사항 작성 확인
- 일반 계정으로 QnA 작성 → admin 답변 확인
- 파일 첨부 후 Supabase Storage boards 버킷에 UUID 파일 저장 확인

---

## 10. 향후 개선 과제

- 파일 첨부 용량 제한 설정
- 게시판 검색 기능
- 첨부 파일 다운로드 통계
