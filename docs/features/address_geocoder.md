# 주소-좌표 변환기

## 1. 기능 개요

- **목적**: 주소를 좌표로, 좌표를 주소로 변환. 대량 Excel 일괄 처리 지원
- **사용 대상**: GIS·공공데이터 담당 공무원
- **처리 내용**: Kakao Maps API로 주소 ↔ 좌표 변환, 실패 시 충주시 내 fallback

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/address_geocoder.py` |
| 읍면동 참조 데이터 | `backend/data/eup_myeon_dong.txt` |
| 프론트엔드 페이지 | `frontend/src/pages/AddressGeocoder.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/geocoder` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/geocoder/address-to-coord` | 주소 → 좌표 |
| POST | `/api/geocoder/coord-to-address` | 좌표 → 주소 |
| POST | `/api/geocoder/file/address-to-coord` | Excel 일괄 주소→좌표 |
| POST | `/api/geocoder/file/coord-to-address` | Excel 일괄 좌표→주소 |
| GET | `/api/geocoder/template/{template_type}` | 업로드용 Excel 템플릿 다운로드 |
| GET | `/api/geocoder/debug-key` | API 키 확인 (개발용) |

---

## 4. 주요 데이터 흐름

1. 주소 입력 → Kakao Maps API 호출
2. Kakao API 실패 시 fallback (우선순위 순):
   - 인접 주소 범위 검색 (±1~3)
   - 행정동 중심 좌표
   - 충주시 기본 좌표
3. Excel 일괄 처리: pandas로 읽기 → 행별 변환 → Excel 반환

---

## 5. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `KAKAO_API_KEY` | Kakao Maps REST API 인증 |

- **Kakao Maps API**: 주소↔좌표 변환
- **httpx**: async HTTP 클라이언트
- **pandas, openpyxl**: Excel 파일 처리

---

## 6. 수정 시 주의사항

- `debug-key` 엔드포인트는 개발 환경 전용 (프로덕션에서 API 키 노출 주의)
- fallback 좌표 데이터가 라우터에 하드코딩됨 (충주시 읍면동 중심 좌표)
- `backend/data/eup_myeon_dong.txt` 파일이 fallback에 사용될 수 있음 (확인 필요)

---

## 7. 테스트 및 검증 방법

- POST `/api/geocoder/address-to-coord`에 충주시 주소 전송 후 좌표 확인
- Excel 파일로 일괄 변환 테스트

---

## 8. 향후 개선 과제

- Kakao API 외 백업 변환 서비스 연동 (Naver Maps 등)
- 변환 실패 주소 목록 별도 반환
