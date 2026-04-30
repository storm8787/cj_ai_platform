# 뉴스 뷰어

## 1. 기능 개요

- **목적**: 충주시 관련 뉴스를 모아보고 AI로 요약하는 기능
- **사용 대상**: 충주시청 공무원
- **처리 내용**: GitHub Gist에서 뉴스 목록 가져오기 → 뷰어 표시 → AI 요약

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/news.py` |
| 프롬프트 관리 | `backend/services/prompt_service.py` |
| 프론트엔드 페이지 | `frontend/src/pages/NewsViewer.jsx` |
| 뉴스 스크래퍼 스크립트 | `news_scraper_api.py` (루트) |
| 스크래핑 워크플로우 | `.github/workflows/scrape_news.yml` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/news` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| GET | `/api/news/list` | GitHub Gist에서 뉴스 목록 가져오기 |
| POST | `/api/news/refresh` | GitHub Actions 스크래퍼 수동 트리거 |
| POST | `/api/news/summarize` | 뉴스 기사 AI 요약 |

---

## 4. 주요 데이터 흐름

```
[자동 수집]
GitHub Actions (scrape_news.yml)
    → news_scraper_api.py 실행
    → 뉴스 스크래핑
    → GitHub Gist에 JSON 저장

[뷰어]
GET /api/news/list
    → GitHub API로 Gist 내용 읽기
    → HTML entity 디코딩
    → 뉴스 목록 반환

[AI 요약]
POST /api/news/summarize
    → GPT-4o-mini로 기사 요약
    → 구조화된 형식으로 반환
```

---

## 5. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `GIST_ID` | 뉴스 데이터 저장 GitHub Gist ID |
| `GITHUB_TOKEN` | GitHub API 인증 |
| `GITHUB_REPO` | 스크래퍼 Actions 트리거용 저장소명 |
| `OPENAI_API_KEY` | GPT-4o-mini 뉴스 요약 |

---

## 6. 수정 시 주의사항

- 뉴스 데이터 저장소: GitHub Gist (DB 아님)
- 스크래핑 주기: `.github/workflows/scrape_news.yml` 스케줄 설정 확인 필요
- `news_scraper_api.py`: 루트 디렉토리에 위치 (backend/ 외부)
- 프롬프트: `prompt_service.get("news", ...)` 패턴으로 Supabase 관리 가능

---

## 7. 테스트 및 검증 방법

- `GET /api/news/list`로 뉴스 목록 확인 (GIST_ID 설정 필요)
- POST `/api/news/summarize`에 기사 URL 전송 후 요약 확인

---

## 8. 향후 개선 과제

- Gist 대신 Supabase DB로 뉴스 저장 전환
- 뉴스 카테고리 분류 기능
- 뉴스 알림 기능
