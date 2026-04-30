# 회의요약기

## 1. 기능 개요

- **목적**: 회의록 텍스트를 붙여넣거나 TXT 파일을 업로드하면 AI가 요약·액션아이템 추출
- **사용 대상**: 충주시청 공무원 (회의 후 요약 작성)
- **처리 내용**: 텍스트 입력/파일 업로드 → 상세 수준 선택 → GPT-4o 요약 + 액션아이템 추출

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/meeting_summarizer.py` |
| 프론트엔드 페이지 | `frontend/src/pages/MeetingSummarizer.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/meeting` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| GET | `/api/meeting/modes` | 요약 모드 목록 |
| GET | `/api/meeting/system-info` | 시스템 정보 (부서, 장소, 기능 목록) |
| POST | `/api/meeting/summarize` | 텍스트 입력 요약 |
| POST | `/api/meeting/summarize-file` | TXT 파일 업로드 후 요약 |

---

## 4. 주요 데이터 흐름

1. 사용자: 텍스트 직접 입력 또는 TXT 파일 업로드
2. 상세 수준 선택: 최소/간략/표준 (3단계)
3. 입력 길이에 따라 모드 자동 조정
4. GPT-4o로 요약 + 액션아이템 추출
5. 응답: `summary`, `actions` (ActionItem 목록), `analysis_stats`

---

## 5. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `OPENAI_API_KEY` | GPT-4o 요약 |

- 충주시 부서·장소 목록이 라우터에 하드코딩됨 (system-info API)

---

## 6. 수정 시 주의사항

- 부서/장소 목록 변경 시 라우터 코드 직접 수정 필요 (현재 하드코딩)
- 프롬프트 Supabase 관리 가능 여부 확인 필요

---

## 7. 테스트 및 검증 방법

- POST `/api/meeting/summarize`에 샘플 텍스트 전송
- 응답의 `actions` 배열과 `summary` 내용 품질 확인

---

## 8. 향후 개선 과제

- 음성 회의록(오디오) 지원 (현재 텍스트/TXT만)
- 부서·장소 목록을 Supabase 또는 설정 파일로 분리
