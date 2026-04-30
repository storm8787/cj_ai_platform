# 업무보고 작성기

## 1. 기능 개요

- **목적**: 입력한 키워드·내용을 바탕으로 공문 형식의 업무보고 문서 자동 생성
- **사용 대상**: 충주시청 공무원 (계획보고, 대책보고, 상황보고, 분석보고 등)
- **처리 내용**: 보고서 유형 선택 → 내용 입력 → GPT-4o로 섹션별 보고서 생성

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/report_writer.py` |
| 프롬프트 관리 | `backend/services/prompt_service.py` |
| 프론트엔드 페이지 | `frontend/src/pages/ReportWriter.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/report-writer` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| GET | `/api/report-writer/structures` | 보고서 유형 및 템플릿 목록 |
| POST | `/api/report-writer/generate` | 보고서 생성 |
| GET | `/api/report-writer/status` | 서비스 상태 |

---

## 4. 주요 데이터 흐름

1. 사용자: 보고서 유형 선택 (4개 카테고리, 각 3~4개 세부 유형)
2. 내용 입력 (부서명, 주요 내용, 배경 등)
3. GPT-4o로 섹션별 보고서 생성
4. 후처리: 용어 교정, 마크다운 제거, 쉼표 삽입
5. 응답: `sections` 배열 (title, order, content)

---

## 5. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `OPENAI_API_KEY` | GPT-4o 보고서 생성 |

---

## 6. 수정 시 주의사항

- 보고서 유형별 작성 스타일: 서술형/나열형/효과형/방안형/분석형
- 프롬프트: `prompt_service.get("report_writer", ...)` 패턴으로 Supabase 관리 가능
- 후처리 로직 (용어 교정, 마크다운 제거) 라우터 내에 있음

---

## 7. 테스트 및 검증 방법

- `GET /api/report-writer/structures`로 유형 목록 확인
- POST `/generate`에 샘플 내용 전송 후 섹션 구조 확인

---

## 8. 향후 개선 과제

- 생성 보고서 HWPX 내보내기 기능
- 보고서 유형 추가 (현재 4카테고리)
