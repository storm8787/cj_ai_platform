# 공공데이터 검증기

## 1. 기능 개요

- **목적**: CSV/Excel 파일을 공공데이터 개방 표준에 맞게 검증
- **사용 대상**: 공공데이터 담당 공무원 (데이터 개방 전 품질 검사)
- **처리 내용**: 표준 선택 → 파일 업로드 → 필드/형식/값 검증 → 오류·경고 리포트

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/data_validator.py` |
| 표준 정의 파일 | `backend/data/public_data_standards.json` |
| 프론트엔드 페이지 | `frontend/src/pages/DataValidator.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/data-validator` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| GET | `/api/data-validator/standards` | 공공데이터 표준 목록 |
| GET | `/api/data-validator/standards/{standard_id}` | 표준 상세 |
| POST | `/api/data-validator/validate/{standard_id}` | CSV/Excel 검증 |
| GET | `/api/data-validator/status` | 서비스 상태 |

---

## 4. 주요 데이터 흐름

1. 사용자: 표준 선택 (카테고리 필터)
2. CSV 또는 Excel 파일 업로드
3. `pandas`로 데이터 읽기 (최대 ~1000행 샘플 검증)
4. 검증 항목:
   - 필수 필드 존재 여부
   - 날짜 형식 (YYYY-MM-DD)
   - 좌표 소수점 자릿수
   - 허용값 범위 (Y/N, 코드값 등)
   - 주소 형식 (도로명/지번)
   - 중복 행
5. 응답: `score`, `errors`, `warnings`, `field_matches`

---

## 5. 환경변수 및 외부 의존성

환경변수: 없음 (외부 API 미사용)

- **pandas**: 데이터 파일 읽기
- **표준 정의**: `backend/data/public_data_standards.json` (파일 기반)

---

## 6. 수정 시 주의사항

- 새 공공데이터 표준 추가 시 `public_data_standards.json` 파일 수정
- 검증 규칙 추가 시 라우터 내 검증 로직 수정
- Supabase 연동은 선택적 (현재 사용 여부 확인 필요)

---

## 7. 테스트 및 검증 방법

- `GET /api/data-validator/standards`로 표준 목록 확인
- 샘플 CSV 파일로 `POST /validate/{id}` 호출 후 오류 리포트 확인

---

## 8. 향후 개선 과제

- 표준 목록 동적 관리 (현재 JSON 파일 기반)
- 검증 결과 Excel 내보내기 기능
- 표준 버전 관리
