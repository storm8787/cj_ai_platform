# 출장보고 생성기

## 1. 기능 개요

- **목적**: 출장 사진과 HWPX 파일을 분석하여 출장보고서 자동 생성
- **사용 대상**: 충주시청 공무원 (출장 후 보고서 작성)
- **처리 내용**: 출장 사진 업로드 → GPT Vision으로 이미지 분석 → 출장보고서 생성

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/trip_report.py` |
| 프론트엔드 페이지 | `frontend/src/pages/TripReport.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/trip-report` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/trip-report/analyze-images` | 출장 사진 분석 및 정보 추출 |
| POST | `/api/trip-report/generate-report` | 출장보고서 생성 |
| GET | `/api/trip-report/report-types` | 출장 유형 목록 |

---

## 4. 주요 데이터 흐름

```
1. 출장 사진 업로드 (복수 이미지)
    ↓
2. GPT Vision으로 이미지 분석
   → 출장 유형 분류 (8종)
   → 주요 내용 추출 (structured JSON)
    ↓
3. 선택적: HWPX 파일 업로드 (추가 컨텍스트)
    ↓
4. GPT로 출장보고서 생성
    ↓
5. 응답: 보고서 텍스트
```

---

## 5. 출장 유형 (8종)

회의참석 / 벤치마킹 / 교육연수 / 설명회참석 / 조사연구 / 시설점검 / 민원현장 / 환경점검

---

## 6. 환경변수 및 외부 의존성

| 환경변수 | 역할 | 기본값 |
|---------|------|--------|
| `OPENAI_API_KEY` | 이미지 분석 + 보고서 생성 | 필수 |
| `TRIP_ANALYSIS_MODEL` | 이미지 분석 모델명 | 확인 필요 |
| `TRIP_REPORT_MODEL` | 보고서 생성 모델명 | 확인 필요 |
| `TRIP_MAX_IMAGES` | 최대 이미지 수 | 확인 필요 |
| `TRIP_MAX_IMAGE_BYTES` | 최대 이미지 크기 (bytes) | 확인 필요 |
| `TRIP_MAX_HWPX_BYTES` | 최대 HWPX 크기 (bytes) | 확인 필요 |

- 이미지 분석: GPT-4o Vision (또는 TRIP_ANALYSIS_MODEL 환경변수)
- 보고서 생성: GPT (TRIP_REPORT_MODEL 환경변수)
- HWPX 파싱: lxml

> ⚠️ 라우터 코드에서 `gpt-5.1-chat-latest` 등 특정 모델 사용 확인됨. 환경변수로 오버라이드 가능.

---

## 7. 수정 시 주의사항

- 2단계 분석 구조: 1차(분류) → 2차(추출) — 순서 유지 필요
- 이미지 base64 인코딩 후 GPT Vision에 전달
- HWPX 파싱은 lxml 기반 (kordoc 미사용)
- 모델 선택 시 GPT Vision 지원 여부 확인

---

## 8. 테스트 및 검증 방법

- `GET /api/trip-report/report-types`로 유형 목록 확인
- 출장 사진 2~3장 업로드 후 `analyze-images` 응답의 `report_type` 및 `extracted_info` 확인
- `generate-report`로 최종 보고서 생성 확인

---

## 9. 향후 개선 과제

- 모델명 환경변수 표준화 (config.py Settings 클래스에 통합 여부 확인 필요)
- 생성 보고서 HWPX 형식 내보내기
