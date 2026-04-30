# 엑셀 취합기

## 1. 기능 개요

- **목적**: 여러 Excel/CSV 파일을 하나의 파일로 취합·병합
- **사용 대상**: 데이터 취합 업무를 하는 충주시청 공무원
- **처리 내용**: 복수 파일 업로드 → 시트별 읽기 → 하나의 Excel로 병합

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/excel_merger.py` |
| 프론트엔드 페이지 | `frontend/src/pages/ExcelMerger.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/excel-merger` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/excel-merger/merge` | 복수 파일 병합 |
| POST | `/api/excel-merger/preview` | 첫 10행 미리보기 |
| GET | `/api/excel-merger/sheet-count` | 시트 수 조회 |

---

## 4. 주요 데이터 흐름

1. 복수 Excel/CSV/XLS 파일 업로드
2. pandas로 각 파일 읽기 (인코딩 자동 감지: utf-8/cp949/euc-kr)
3. 다중 시트 지원
4. DataFrame 병합 → Excel 파일로 반환
5. 응답 헤더: 처리 건수, 행/열 수, 오류 정보 (`X-Processed-Count`, `X-Total-Rows`, `X-Total-Cols`, `X-Errors`)

---

## 5. 환경변수 및 외부 의존성

환경변수: 없음

- **pandas**: 데이터 읽기·병합
- **openpyxl**: Excel 쓰기 (xlsx)
- **xlrd**: 구형 xls 읽기

---

## 6. 수정 시 주의사항

- 파일 크기 제한 설정 확인 필요 (FastAPI `python-multipart` 기본 한도)
- 인코딩 감지 순서: utf-8 → cp949 → euc-kr

---

## 7. 테스트 및 검증 방법

- 2~3개 Excel 파일로 POST `/merge` 호출
- 응답 Excel 파일의 행 수와 원본 합계 비교
- 응답 헤더의 `X-Total-Rows` 값 확인

---

## 8. 향후 개선 과제

- 열 매핑 기능 (서로 다른 컬럼명 파일 병합)
- 중복 행 제거 옵션
