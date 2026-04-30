# 재난상황 대시보드

## 1. 기능 개요

- **목적**: 카카오톡 재난상황 단톡방 TXT 파일을 업로드하면, 메시지를 파싱하여 사고별로 분류하고 현황 대시보드와 일일 보고서를 자동 생성
- **사용 대상**: 재난 대응 담당 공무원
- **처리 내용**: TXT 파싱 → 메시지 저장 → 사고 재구성 → 대시보드 통계 → 일일보고 생성

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/disaster_dashboard.py` |
| 사고 재구성 서비스 | `backend/services/disaster_incident_service.py` |
| 일일보고 생성 | `backend/services/disaster_report_service.py` |
| TXT 파싱 | `backend/services/disaster_parser_service.py` |
| 상수 정의 | `backend/services/disaster_constants.py` |
| 재난상황 훅 | `frontend/src/hooks/useDisasterSession.js` |
| 재난 상수 | `frontend/src/constants/disaster.js` |
| 업로드 페이지 | `frontend/src/pages/DisasterUpload.jsx` |
| 대시보드 페이지 | `frontend/src/pages/DisasterDashboard.jsx` |
| 사고 목록 | `frontend/src/pages/DisasterIncidents.jsx` |
| 일일보고 | `frontend/src/pages/DisasterDailyReport.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/disaster` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/disaster/upload` | 카카오톡 TXT 업로드 |
| GET | `/api/disaster/uploads` | 업로드 목록 |
| POST | `/api/disaster/analyze/{upload_id}` | 업로드 분석 (메시지 파싱 → 사고 재구성) |
| GET | `/api/disaster/upload/{upload_id}/summary` | 업로드 요약 |
| GET | `/api/disaster/incidents` | 사고 목록 (필터: upload_id/status/type/emd) |
| GET | `/api/disaster/incidents/{incident_id}` | 사고 상세 + 연결 메시지 |
| GET | `/api/disaster/dashboard/overview` | 통계 (유형별/상태별/읍면동별/시간별) |
| POST | `/api/disaster/reports/daily/generate` | 일일보고 생성 (GPT-4o) |
| GET | `/api/disaster/reports` | 일일보고 목록 |

---

## 4. 주요 데이터 흐름

```
카카오톡 TXT 업로드
    ↓
disaster_parser_service: 메시지 파싱 (4가지 날짜 형식 지원)
    → disaster_raw_messages 테이블 저장
    ↓
disaster_incident_service: 사고 재구성
    → 위치 유사도 매칭 (difflib, 80% threshold)
    → 상태 변경 추적 (reported → in_progress → completed/closed)
    → disaster_incidents 테이블 저장
    ↓
대시보드 통계 집계 (유형/상태/읍면동/시간대별)
    ↓
일일보고 생성 (gpt-4o, GPT-4o 자연어 보고서)
```

---

## 5. 핵심 구현 세부 사항

### 메시지 파싱 (4가지 날짜 형식)

- 한국어 형식: `2025년 7월 15일 오후 3:30`
- 점 형식: `2025. 7. 15. 오후 3:30`
- 구분선: `--------- 2025년 7월 15일 월요일 ---------`
- 대괄호 형식: `[홍길동] [오후 3:30] 메시지`

### 사고 상태 분류 (우선순위 순)

- `closed`: "해제|통행재개|개통"
- `completed`: "복구 완료|처리 완료|..."
- `in_progress`: "조치중|작업중|..."
- `reported`: "~예정"

### 동시 분석 방지

- `analysis_status` 필드: `uploaded` → `analyzing` → `analyzed`
- `analyzing` 중 중복 호출 시 **409 Conflict** 반환

### 위치 유사도 매칭

- `difflib.SequenceMatcher` 80% threshold
- 예: "용산동 천변산책로" ≈ "용산동 천변 산책로"
- 상수: `LOCATION_SIMILARITY_THRESHOLD = 0.80`

---

## 6. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `OPENAI_API_KEY` | 일일보고 GPT-4o 생성 |
| `SUPABASE_URL`, `SUPABASE_KEY` | 모든 데이터 저장 |

**Supabase 테이블**:
- `disaster_uploads`: 업로드 파일 정보 + 분석 상태
- `disaster_raw_messages`: 파싱된 메시지
- `disaster_incidents`: 재구성된 사고 목록
- `disaster_incident_messages`: 사고-메시지 연결 테이블
- `disaster_daily_reports`: 일일보고 저장

---

## 7. 수정 시 주의사항

- 일일보고 생성 모델: `gpt-4o` (다른 기능의 `gpt-4o-mini`와 다름)
- 프롬프트: `prompt_service.get("disaster", ...)` 패턴 (3단계 fallback)
- TXT 파일 인코딩: UTF-8 / CP949 자동 감지
- 빈 배열 insert 방지: `if incident_rows: insert(...)` 가드 필요 (없으면 crash)
- 개인정보: 일일보고 GPT 프롬프트에 보고자 이름 포함하지 않도록 주의
- 프론트엔드: `useDisasterSession()` 훅 사용 (sessionStorage 리액티브)

---

## 8. 테스트 및 검증 방법

- 카카오톡 TXT 파일 업로드 후 `/api/disaster/analyze/{id}` 호출
- `GET /api/disaster/incidents` 응답에서 사고 분류·상태 확인
- `GET /api/disaster/dashboard/overview` 통계 데이터 확인
- 일일보고 생성 후 `report_text` 내용 품질 확인

---

## 9. 향후 개선 과제

- 파싱 규칙 외 형식의 카카오톡 메시지 처리 (신규 버전 대응)
- 사고 유형 분류 정확도 개선 (현재 키워드 기반)
- 위치 정규화 개선 (행정동 코드 기반)
