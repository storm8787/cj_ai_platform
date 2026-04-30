# 카카오 홍보문구 생성기

## 1. 기능 개요

- **목적**: 행정 공고·행사·정책을 카카오톡 채널에 맞는 홍보문구로 변환
- **사용 대상**: 충주시청 홍보·SNS 담당 공무원
- **처리 내용**: 텍스트 입력 또는 이미지 OCR → 카테고리별 홍보문구 생성

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/kakao_promo.py` |
| 프롬프트 관리 | `backend/services/prompt_service.py` |
| 프론트엔드 페이지 | `frontend/src/pages/KakaoPromo.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/kakao-promo` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| GET | `/api/kakao-promo/categories` | 홍보 카테고리 목록 |
| POST | `/api/kakao-promo/generate` | 텍스트 입력으로 홍보문구 생성 |
| POST | `/api/kakao-promo/generate-with-image` | 이미지 OCR 후 홍보문구 생성 |

---

## 4. 주요 데이터 흐름

1. 사용자: 텍스트 입력 또는 이미지 업로드
2. 이미지 입력 시: GPT-4o Vision으로 OCR
3. 카테고리 선택: 시정홍보/정책공지/문화행사/축제/이벤트/재난알림/기타 (7종)
4. GPT-4o-mini로 카테고리에 맞는 홍보문구 생성
5. 응답: 홍보문구 텍스트

---

## 5. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `OPENAI_API_KEY` | OCR(GPT-4o Vision) + 문구 생성(GPT-4o-mini) |

---

## 6. 수정 시 주의사항

- 카테고리별 프롬프트 템플릿이 라우터 내에 정의됨
- `prompt_service.get("kakao_promo", ...)` 패턴으로 Supabase 관리 가능
- 이미지 업로드는 base64로 인코딩하여 GPT Vision에 전달

---

## 7. 테스트 및 검증 방법

- POST `/api/kakao-promo/generate`에 텍스트와 카테고리 전송
- 생성된 문구가 카카오톡 형식(이모지, 줄바꿈 등)에 맞는지 확인

---

## 8. 향후 개선 과제

- 카테고리 목록 동적 관리 (현재 하드코딩 7종)
- 생성 이력 저장 기능
