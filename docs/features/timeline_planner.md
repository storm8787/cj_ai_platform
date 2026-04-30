# 사업 타임라인 플래너

## 1. 기능 개요

- **목적**: 공공사업 계획 수립 시 AI가 타임라인·단계별 세부 업무를 자동 제안
- **사용 대상**: 충주시청 사업 담당 공무원
- **처리 내용**: 사업 정보 입력 → 법령 챗봇 연동으로 사전절차 확인 → GPT 타임라인 제안 → 이미지/Excel/PPTX 내보내기

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/timeline_planner.py` |
| 프롬프트 관리 | `backend/services/prompt_service.py` |
| 프론트엔드 페이지 | `frontend/src/pages/TimelinePlanner.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/timeline` (라우터 내부 선언)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/timeline/suggest` | 타임라인 자동 제안 |
| POST | `/api/timeline/detail-tasks` | 단계별 세부 업무 생성 |
| GET | `/api/timeline/project-types` | 사업 유형 목록 |
| GET | `/api/timeline/contract-types` | 계약 유형 목록 |
| GET | `/api/timeline/categories` | 카테고리 목록 |
| POST | `/api/timeline/export` | 타임라인 내보내기 (PNG/XLSX/PPTX) |
| GET | `/api/timeline/status` | 서비스 상태 |

---

## 4. 주요 데이터 흐름

```
사업 정보 입력 (유형, 예산, 기간 등)
    ↓
법령 챗봇 내부 API 호출 (httpx)
    → POST http://localhost:8000/api/law-chatbot/ask
    → 사전절차·법적 근거 자동 검색
    ↓
GPT-4o로 4단계 타임라인 생성
    (계획 → 계약 → 시행 → 완료)
    ↓
2차 실행단계 세부 업무 생성 (detail-tasks)
    ↓
내보내기: PNG (PIL) / XLSX (openpyxl) / PPTX (python-pptx)
```

---

## 5. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `OPENAI_API_KEY` | GPT-4o 타임라인 생성 |

**내부 의존성**:
- 법령 챗봇 API: `http://localhost:8000/api/law-chatbot/ask` (동일 컨테이너 내 호출)
- **PIL(Pillow)**: PNG 이미지 생성 (한글 폰트: fonts-noto-cjk Dockerfile 설치)
- **openpyxl**: XLSX 내보내기
- **python-pptx**: PPTX 내보내기

---

## 6. 수정 시 주의사항

- 법령 챗봇 API URL 하드코딩: `http://localhost:8000/api/law-chatbot/ask`
  - 배포 환경에서 동일 컨테이너 내 서비스이므로 `localhost` 동작
  - 서비스 분리 시 URL 환경변수화 필요
- 한글 PNG 출력 시 `fonts-noto-cjk` 필요 (Dockerfile에 포함)
- PPTX 생성 시 python-pptx 라이브러리 필요 (requirements.txt에 포함)

---

## 7. 테스트 및 검증 방법

- POST `/api/timeline/suggest`에 사업 정보 전송 후 TimelineData 구조 확인
- POST `/api/timeline/export`로 PNG/XLSX/PPTX 각각 생성 후 다운로드 확인
- 법령 챗봇 연동: 사전절차 정보가 타임라인에 반영되는지 확인

---

## 8. 향후 개선 과제

- 법령 챗봇 API URL 환경변수화
- 타임라인 저장·불러오기 기능
- 간트차트 SVG 내보내기
