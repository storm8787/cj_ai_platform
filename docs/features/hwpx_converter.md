# HWPX 변환기

## 1. 기능 개요

- **목적**: 한글(HWP) 파일의 최신 형식인 HWPX를 Markdown으로 변환
- **사용 대상**: 충주시청 공무원 (HWP 문서 → 텍스트 추출·변환)
- **처리 내용**: HWPX 업로드 → kordoc 또는 Python 파서로 Markdown 변환 → 결과 반환

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/hwpx_converter.py` |
| kordoc 서비스 | `backend/services/kordoc_service.py` |
| 프론트엔드 페이지 | `frontend/src/pages/HwpxConverter.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/hwpx-converter` (라우터 내부 선언)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/hwpx-converter/convert` | HWPX → Markdown (JSON 응답) |
| POST | `/api/hwpx-converter/convert-download` | HWPX → Markdown 파일 다운로드 |
| GET | `/api/hwpx-converter/status` | 서비스 상태 |

---

## 4. 주요 데이터 흐름

1. HWPX 파일 업로드 (최대 50MB)
2. **이중 엔진 처리**:
   - 1순위: kordoc (`backend/services/kordoc_service.py`) — 정확도 높음
   - 2순위: Python lxml 파서 (kordoc 실패 시 fallback)
3. 응답: `markdown` 텍스트, `images` (base64 인코딩), `stats` (단락/표/이미지 수)

---

## 5. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| (kordoc 설정 — 확인 필요) | kordoc 서비스 연동 |

- **kordoc**: npm 패키지. Dockerfile에서 `npm install -g kordoc`으로 설치
  - `kordoc --help || true` (설치 실패 시 무시)
- **lxml**: Python XML 파서 (requirements.txt에 포함)
- 내장 이미지 처리: inline/separate 모드 지원

---

## 6. 수정 시 주의사항

- kordoc npm 패키지 설치 여부에 따라 첫 번째 엔진 동작 결정
- kordoc 실패 시 Python lxml fallback 자동 적용
- 대용량 파일(50MB 초과) 거부 처리 확인 필요
- HWPX 내부 이미지는 base64로 응답에 포함 (응답 크기 주의)

---

## 7. 테스트 및 검증 방법

- `GET /api/hwpx-converter/status`로 kordoc 설치 여부 확인
- HWPX 파일 업로드 후 `markdown` 필드 내용 및 `stats` 확인

---

## 8. 향후 개선 과제

- kordoc vs Python 파서 품질 비교 테스트 자동화
- PDF → Markdown 변환 지원 검토
