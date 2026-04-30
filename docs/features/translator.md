# HWPX 번역기

## 1. 기능 개요

- **목적**: 한글(HWPX) 파일의 텍스트를 외국어로 번역하고, 번역된 HWPX 파일로 반환
- **사용 대상**: 충주시청 공무원 (외국어 문서 번역)
- **처리 내용**: HWPX 업로드 → DeepL 번역 → GPT 잔여 한국어 처리 → 번역된 HWPX 반환

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/translator.py` |
| 프론트엔드 페이지 | `frontend/src/pages/Translator.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/translator` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| GET | `/api/translator/languages` | 지원 언어 목록 (17개) |
| POST | `/api/translator/translate` | HWPX 파일 번역 |

---

## 4. 주요 데이터 흐름

```
HWPX 파일 업로드
    ↓
lxml으로 HWPX XML 파싱
→ <t> 텍스트 요소 추출
    ↓
1단계: DeepL API로 번역 (주력)
    ↓
2단계: 잔여 한국어 감지 → GPT-4o-mini로 추가 번역
    ↓
번역된 텍스트를 HWPX XML에 적용
→ linesegarray 제거 (레이아웃 재계산 트리거)
    ↓
번역된 HWPX 파일 반환 (binary 응답)
```

---

## 5. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `DEEPL_API_KEY` | DeepL 번역 API (필수) |
| `OPENAI_API_KEY` | GPT-4o-mini 잔여 한국어 처리 |

> ⚠️ **Critical**: `requirements.txt`에 `deepl>=1.16.0,<2.0.0` 버전 고정 필요
> DeepL 2.x는 `Translator` 클래스 deprecated → FastAPI 환경 오류 발생

---

## 6. 수정 시 주의사항

- DeepL 라이브러리 버전: 반드시 `<2.0.0` 유지 (`requirements.txt` 참고)
- HWPX 구조 변경 시 lxml 파싱 로직 조정 필요
- 응답은 binary HWPX 파일 (JSON 아님)
- linesegarray 제거: 한글의 줄 분절 정보를 제거하여 텍스트 교체 후 레이아웃 재계산 유도

---

## 7. 테스트 및 검증 방법

- `GET /api/translator/languages`로 지원 언어 확인
- 한국어 HWPX 파일로 POST `/translate` 호출 후 번역된 HWPX 다운로드
- 번역 결과 HWP 앱에서 열어 레이아웃·텍스트 확인

---

## 8. 향후 개선 과제

- 번역 언어 추가 (현재 17개)
- DeepL 2.x 버전 대응 (Translator → DeepLClient 클래스 변경)
- 일반 텍스트/DOC 파일 번역 지원
