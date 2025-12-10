# Agents.md - CJ_AI_PLATFORM 개발 가이드

## 1. Overview

### 프로젝트 정의
**CJ_AI_PLATFORM**은 충주시 공무원의 실제 업무 자동화 및 데이터 분석을 위한 AI 기반 플랫폼입니다.

- **목적**: 행정업무 효율화 (보도자료 작성, 공적조서 생성, 데이터 분석, 회의록 요약 등)
- **대상 사용자**: 충주시청 내부 공무원 (실전 업무용)
- **개발 방향**: 데모/예제 프로젝트가 아닌 실제 운영 시스템

### 현재 상태 및 마이그레이션 목표

**현재 (AS-IS)**
- `cj_ai_app-main`: Streamlit 기반 웹 애플리케이션
- 모든 기능이 단일 앱 내에서 모듈 형태로 동작
- 로컬 실행 위주, 파일 기반 데이터 관리

**목표 (TO-BE)**
- **프론트엔드**: Vite + React + TypeScript + Tailwind CSS → Netlify 배포
- **백엔드**: FastAPI 기반 RESTful API → 클라우드 배포
- **구조**: 프론트/백엔드 완전 분리, API 기반 통신
- **방식**: 점진적 마이그레이션 (기존 Streamlit 앱을 참고하여 하나씩 포팅)

---

## 2. Tech Stack

### 프론트엔드 (계획)
- **프레임워크**: Vite 5.x
- **UI 라이브러리**: React 18.x + TypeScript
- **스타일링**: Tailwind CSS 3.x, shadcn/ui 컴포넌트
- **라우팅**: React Router v6
- **상태관리**: React Query (서버 상태), Context API (클라이언트 상태)
- **배포**: Netlify

### 백엔드 (계획)
- **프레임워크**: FastAPI (Python 3.10+)
- **라우터 구조**: 기능별 분리 (예: `press_release_router.py`, `geocoder_router.py`)
- **서비스 레이어**: `services/` 디렉터리 (비즈니스 로직)
- **유틸리티**: `utils/` 디렉터리 (공통 함수)
- **인증**: JWT 기반 (추후 도입 예정)
- **배포**: Docker 컨테이너화 → 클라우드 서버

### 공통 기술 스택
- **AI/ML**:
  - OpenAI API (GPT-4, GPT-3.5-turbo)
  - LangChain (RAG 구현, 벡터스토어 관리)
  - FAISS (벡터 검색)
  - Sentence Transformers (임베딩)

- **OCR/문서 처리**:
  - Google Cloud Vision API (이미지 텍스트 추출)
  - PyPDF2, pdfplumber (PDF 처리)
  - python-docx (Word 문서)
  - openpyxl, xlsxwriter (Excel 처리)

- **지리정보**:
  - geopy (주소-좌표 변환)
  - folium (지도 시각화)
  - Google Maps API (Geocoding)

- **한국어 처리**:
  - konlpy (형태소 분석)
  - py-hanspell (맞춤법 검사)

- **데이터 분석**:
  - pandas, numpy
  - scikit-learn
  - plotly (시각화)

---

## 3. Directory Structure

### 현재 구조 (cj_ai_app-main)

```
cj_ai_app-main/
├── app.py                          # Streamlit 메인 엔트리포인트
├── main_dashboard.py               # 홈 대시보드
│
├── [기능별 앱 파일들]
├── press_release_app.py            # 보도자료 생성기
├── official_merit_report_app.py    # 공적조서 생성기
├── festival_analysis_app.py        # 축제 빅데이터 분석기
├── excel_merger.py                 # 엑셀 취합기
├── address_geocoder.py             # 주소-좌표 변환기
├── kakao_promo_app.py              # 카카오톡 홍보멘트 생성기
├── meeting_summarizer_app.py       # 회의 요약기
├── data_validator_app.py           # 공공데이터 검증기
├── report_writer_app.py            # 업무보고 생성기
├── policy_search_app.py            # 정책사례 검색기
├── openai_usage_dashboard.py       # OpenAI API 사용현황
├── hwpx_translator_perfect_format.py # 다국어 번역기
│
├── modules/                        # 보조 모듈
│   ├── gpt_corrector.py            # GPT 기반 텍스트 교정
│   └── name_correction.py          # 이름 교정 로직
│
├── utils/                          # 유틸리티 함수
│   ├── __init__.py
│   └── prompt_filter/              # 프롬프트 필터링 관련
│
├── data/                           # 데이터 및 리소스
│   ├── fonts/                      # 폰트 파일
│   ├── insights/                   # 분석 인사이트
│   ├── templates/                  # 문서 템플릿
│   └── vectorstores/               # FAISS 벡터스토어
│
├── festival/                       # 축제 분석 관련 데이터
├── policy_utils/                   # 정책검색 유틸리티
├── meta_dicts_final_clean/         # 메타 데이터 사전
│
├── .streamlit/                     # Streamlit 설정
├── .devcontainer/                  # 개발 컨테이너 설정
├── requirements.txt                # Python 의존성
└── logo.png                        # 로고 이미지
```

### 목표 구조 (마이그레이션 후)

```
CJ_AI_PLATFORM/
├── cj_ai_frontend/                 # Vite + React 프론트엔드
│   ├── src/
│   │   ├── components/             # 재사용 컴포넌트
│   │   │   ├── ToolCard.tsx        # 기능 카드 컴포넌트
│   │   │   ├── Layout.tsx          # 레이아웃 컴포넌트
│   │   │   └── ui/                 # shadcn/ui 컴포넌트
│   │   ├── pages/                  # 페이지 컴포넌트
│   │   │   ├── Index.tsx           # 메인 대시보드
│   │   │   ├── PressRelease.tsx    # 보도자료 생성기
│   │   │   ├── OfficialMerit.tsx   # 공적조서 생성기
│   │   │   ├── FestivalAnalysis.tsx # 축제 분석기
│   │   │   └── ...                 # 기타 기능 페이지
│   │   ├── services/               # API 호출 로직
│   │   │   ├── api.ts              # Axios 인스턴스
│   │   │   └── pressReleaseApi.ts  # 보도자료 API
│   │   ├── hooks/                  # Custom React Hooks
│   │   ├── types/                  # TypeScript 타입 정의
│   │   ├── utils/                  # 유틸리티 함수
│   │   ├── App.tsx                 # 앱 루트
│   │   └── main.tsx                # 엔트리포인트
│   ├── public/                     # 정적 파일
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── cj_ai_backend/                  # FastAPI 백엔드
│   ├── routers/                    # API 라우터
│   │   ├── press_release_router.py
│   │   ├── official_merit_router.py
│   │   ├── festival_router.py
│   │   ├── geocoder_router.py
│   │   └── ...
│   ├── services/                   # 비즈니스 로직
│   │   ├── press_release_service.py
│   │   ├── llm_service.py          # OpenAI 호출 관리
│   │   ├── ocr_service.py          # Google Vision OCR
│   │   └── rag_service.py          # RAG 관련
│   ├── utils/                      # 유틸리티
│   │   ├── prompt_templates.py     # 프롬프트 템플릿
│   │   ├── text_processor.py       # 텍스트 처리
│   │   └── validators.py           # 입력 검증
│   ├── models/                     # Pydantic 모델
│   ├── data/                       # 데이터 파일 (templates, vectorstores 등)
│   ├── main.py                     # FastAPI 앱 엔트리포인트
│   ├── config.py                   # 환경 변수 설정
│   └── requirements.txt
│
├── cj_ai_app/                      # 기존 Streamlit 앱 (참고용, 점진적 제거)
├── docs/                           # 문서
├── assets/                         # 공통 리소스
├── data/                           # 공통 데이터
└── Agents.md                       # 본 파일 (AI 개발 가이드)
```

---

## 4. Coding Conventions

### 파일 및 디렉터리 네이밍
- **파일명**: `snake_case` (예: `press_release_router.py`, `tool_card.tsx`)
- **컴포넌트 파일**: PascalCase (예: `ToolCard.tsx`, `PressRelease.tsx`)
- **디렉터리**: `snake_case` (예: `services/`, `utils/`)

### 변수 및 함수 네이밍
- **Python**:
  - 함수/변수: `snake_case` (예: `generate_press_release()`)
  - 클래스: `PascalCase` (예: `PressReleaseService`)
  - 상수: `UPPER_SNAKE_CASE` (예: `MAX_TOKEN_LIMIT`)
- **TypeScript**:
  - 함수/변수: `camelCase` (예: `fetchPressRelease()`)
  - 컴포넌트: `PascalCase` (예: `ToolCard`)
  - 타입/인터페이스: `PascalCase` (예: `PressReleaseRequest`)

### 코드 스타일
- **실전용 코드 원칙**: 예제 코드, 튜토리얼 코드, 장난용 코드 절대 금지
- **주석**:
  - 한글 주석 허용 (업무 컨텍스트 설명 시)
  - 함수명, 변수명은 반드시 영어
- **에러 처리**:
  - 백엔드: FastAPI HTTPException 사용
  - 프론트엔드: try-catch + 사용자 친화적 에러 메시지
- **타입 안정성**:
  - TypeScript strict 모드 사용
  - Python Type Hints 적극 활용 (Pydantic 모델)

### Tailwind CSS 사용 원칙
- **shadcn/ui 우선**: 기본 UI 컴포넌트는 shadcn/ui 사용
- **커스텀 스타일**: Tailwind 유틸리티 클래스 조합
- **반응형**: `sm:`, `md:`, `lg:` 브레이크포인트 적극 활용
- **다크모드**: 추후 지원 예정 (`dark:` 접두사 대비)

### API 호출 패턴
- **프론트엔드**:
  - React Query 사용 (`useQuery`, `useMutation`)
  - Axios 인스턴스 통해 중앙 관리
  - 로딩/에러 상태 UI 필수 제공
- **백엔드**:
  - RESTful 원칙 준수 (GET, POST, PUT, DELETE)
  - Request/Response Pydantic 모델 명시
  - CORS 설정 (프론트엔드 도메인 허용)

### 환경 변수 관리
- **로컬 경로 하드코딩 금지**: `E:\...`, `C:\Users\...` 등
- **환경 변수 사용**:
  - 백엔드: `.env` 파일 + `python-dotenv`
  - 프론트엔드: `.env.local` 파일 + Vite 환경 변수 (`VITE_API_URL`)
- **민감 정보**: OpenAI API Key, Google API Key 등은 반드시 환경 변수로 관리

---

## 5. Current Migration Plan

### 마이그레이션 목표
기존 Streamlit 앱(`cj_ai_app-main`)의 기능들을 **점진적으로** Vite+React 프론트엔드와 FastAPI 백엔드로 이전합니다.

### 우선순위 작업

#### Phase 1: 기본 인프라 구축
1. **프론트엔드 초기 설정**
   - Vite + React + TypeScript 프로젝트 생성
   - Tailwind CSS + shadcn/ui 설치
   - React Router 설정
   - 메인 대시보드 페이지 (`Index.tsx`) 구현
   - ToolCard 컴포넌트로 기능 목록 표시

2. **백엔드 초기 설정**
   - FastAPI 프로젝트 구조 생성
   - CORS 설정
   - Health Check 엔드포인트 (`/api/health`)
   - 환경 변수 설정 (`.env`)

3. **프론트-백엔드 연동 테스트**
   - Axios 인스턴스 설정
   - 간단한 API 호출 테스트 (예: ping/pong)

#### Phase 2: 핵심 기능 포팅 (우선순위 순)
각 기능마다 아래 단계를 반복:

1. **보도자료 생성기 (1순위)**
   - 백엔드:
     - `press_release_app.py` 로직 분석
     - `routers/press_release_router.py` 생성
     - `services/press_release_service.py` 생성 (OpenAI 호출)
     - API 엔드포인트: `POST /api/press-release/generate`
   - 프론트엔드:
     - `pages/PressRelease.tsx` 생성
     - 입력 폼 (제목, 내용, 스타일 옵션 등)
     - API 호출 + 결과 표시

2. **공적조서 생성기 (2순위)**
   - 백엔드: `routers/official_merit_router.py`
   - 프론트: `pages/OfficialMerit.tsx`

3. **축제 빅데이터 분석기 (3순위)**
   - 백엔드: `routers/festival_router.py` + 데이터 시각화 로직
   - 프론트: `pages/FestivalAnalysis.tsx` + Plotly/Chart.js

4. **엑셀 취합기 (4순위)**
   - 파일 업로드 처리 (`FastAPI UploadFile`)
   - 프론트: Dropzone 또는 파일 입력

5. **주소-좌표 변환기 (5순위)**
   - Google Maps API 연동
   - 지도 표시 (Leaflet 또는 Google Maps React)

6. **기타 기능들 (6-10순위)**
   - 홍보멘트 생성기
   - 회의 요약기
   - 데이터 검증기
   - 업무보고 생성기
   - 정책사례 검색기

#### Phase 3: 고도화
- 사용자 인증 (JWT)
- 사용량 모니터링 (OpenAI API 사용량)
- 파일 스토리지 (S3 또는 클라우드 스토리지)
- 로깅 및 에러 추적 (Sentry)
- 성능 최적화 (캐싱, 벡터스토어 최적화)

### AI 에이전트가 도와줄 작업 (우선순위)

#### 최우선
1. **메인 대시보드 라우팅 구조 정리**
   - `Index.tsx`에서 각 기능 페이지로 라우팅
   - ToolCard 클릭 시 해당 페이지 이동
   - 페이지별 URL 설계 (예: `/press-release`, `/official-merit`)

2. **Streamlit → FastAPI 로직 분리**
   - 기존 `press_release_app.py` 등의 핵심 로직 추출
   - OpenAI API 호출 부분을 `services/llm_service.py`로 분리
   - 프롬프트 템플릿을 `utils/prompt_templates.py`로 분리

3. **프론트엔드 API 연동 패턴 구축**
   - `services/api.ts`: Axios 인스턴스 + 인터셉터
   - `services/pressReleaseApi.ts`: 보도자료 API 호출 함수
   - React Query 훅: `usePressRelease`, `useGeneratePressRelease`

#### 부차적
- UI 컴포넌트 라이브러리 확장 (shadcn/ui 커스터마이징)
- 반응형 디자인 개선
- 다크모드 지원
- 접근성(a11y) 개선

---

## 6. Non-goals (현재 단계에서 하지 않을 것)

### 기능적 제외 사항
- **HWP(한글) 포맷 직접 지원**: Word(docx) 변환 후 처리로 대체
- **실시간 협업 기능**: 현재는 단일 사용자 위주
- **모바일 네이티브 앱**: 반응형 웹으로 대응
- **오프라인 모드**: 온라인 전용

### 기술적 제외 사항
- **GraphQL**: RESTful API로 충분
- **Server-Side Rendering (SSR)**: CSR(Client-Side Rendering)로 진행
- **Microservices 아키텍처**: 모놀리식 백엔드로 시작
- **Kubernetes**: 단일 서버 배포로 시작

### 디자인적 제외 사항
- **과도한 애니메이션**: 심플하고 빠른 UI 우선
- **복잡한 인터랙션**: 직관적인 폼 중심
- **브랜딩 실험**: 충주시 공식 색상/로고 기준 고수

### 보안적 제외 사항 (초기 단계)
- **OAuth 소셜 로그인**: 추후 도입 (현재는 사내 전용)
- **2FA(이중 인증)**: 추후 고려
- **RBAC(역할 기반 권한)**: 현재는 단순 인증만

---

## 7. 주요 기능 목록 (Feature List)

| 기능명 | Streamlit 파일 | 설명 | API 엔드포인트 (계획) |
|--------|---------------|------|----------------------|
| 보도자료 생성기 | `press_release_app.py` | OpenAI 기반 보도자료 초안 작성 | `POST /api/press-release/generate` |
| 공적조서 생성기 | `official_merit_report_app.py` | 공무원 공적조서 자동 생성 | `POST /api/official-merit/generate` |
| 축제 빅데이터 분석기 | `festival_analysis_app.py` | 축제 관련 데이터 시각화 분석 | `GET /api/festival/analysis` |
| 엑셀 취합기 | `excel_merger.py` | 여러 엑셀 파일 병합 | `POST /api/excel/merge` |
| 주소-좌표 변환기 | `address_geocoder.py` | 주소 → 위경도 변환 (Google Maps) | `POST /api/geocode` |
| 홍보멘트 생성기 | `kakao_promo_app.py` | 카카오톡 홍보 문구 생성 | `POST /api/promo/kakao` |
| 회의 요약기 | `meeting_summarizer_app.py` | 회의록 요약 (OCR + GPT) | `POST /api/meeting/summarize` |
| 데이터 검증기 | `data_validator_app.py` | 공공데이터 품질 검증 | `POST /api/data/validate` |
| 업무보고 생성기 | `report_writer_app.py` | 업무보고서 자동 작성 | `POST /api/report/generate` |
| 정책사례 검색기 | `policy_search_app.py` | RAG 기반 정책 사례 검색 | `GET /api/policy/search` |
| OpenAI 사용현황 | `openai_usage_dashboard.py` | API 사용량 모니터링 (관리자용) | `GET /api/admin/usage` |
| 다국어 번역기 | `hwpx_translator_perfect_format.py` | 문서 다국어 번역 | `POST /api/translate` |

---

## 8. 개발 워크플로우

### 로컬 개발 환경
1. **백엔드 실행**:
   ```bash
   cd cj_ai_backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```

2. **프론트엔드 실행**:
   ```bash
   cd cj_ai_frontend
   npm install
   npm run dev  # Vite dev server (default: http://localhost:5173)
   ```

3. **환경 변수 설정**:
   - 백엔드: `cj_ai_backend/.env`
     ```
     OPENAI_API_KEY=sk-...
     GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
     ALLOWED_ORIGINS=http://localhost:5173
     ```
   - 프론트엔드: `cj_ai_frontend/.env.local`
     ```
     VITE_API_URL=http://localhost:8000
     ```

### Git 브랜치 전략
- `main`: 운영 브랜치 (Netlify 자동 배포)
- `develop`: 개발 통합 브랜치
- `feature/기능명`: 기능 개발 브랜치 (예: `feature/press-release`)
- `fix/버그명`: 버그 수정 브랜치

### 커밋 메시지 규칙
```
feat: 새 기능 추가
fix: 버그 수정
refactor: 리팩토링
docs: 문서 수정
style: 코드 포맷팅
test: 테스트 추가
chore: 빌드/설정 변경
```

예시:
```
feat: 보도자료 생성 API 엔드포인트 구현
fix: 주소 변환 시 한글 인코딩 오류 수정
refactor: LLM 서비스 레이어 분리
```

---

## 9. 참고 사항

### 기존 Streamlit 앱 참고 시 주의사항
- **세션 상태**: Streamlit의 `st.session_state`는 React의 `useState` 또는 Context API로 대체
- **파일 업로더**: `st.file_uploader`는 HTML `<input type="file">` 또는 react-dropzone으로 대체
- **컬럼 레이아웃**: `st.columns`는 Tailwind Grid/Flex로 대체
- **프로그레스바**: `st.progress`는 shadcn/ui Progress 컴포넌트로 대체

### OpenAI API 사용 시 주의사항
- **토큰 제한**: GPT-4는 최대 8K/32K 토큰, 입력 길이 검증 필수
- **비용 관리**: API 호출 로깅, 사용량 모니터링
- **에러 핸들링**: Rate limit, Timeout 등 예외 처리
- **프롬프트 버전 관리**: `utils/prompt_templates.py`에서 중앙 관리

### RAG (Retrieval-Augmented Generation) 관련
- **벡터스토어**: FAISS 기반, `data/vectorstores/` 디렉터리에 저장
- **임베딩 모델**: Sentence Transformers (예: `all-MiniLM-L6-v2`)
- **검색 최적화**: Top-K 결과 조정, 유사도 임계값 설정
- **벡터스토어 갱신**: 정책 문서 업데이트 시 재임베딩 필요

### 한국어 처리 특수 사항
- **맞춤법 검사**: `py-hanspell` (Naver API 기반, 속도 느림)
- **형태소 분석**: `konlpy` (Okt, Mecab 등)
- **띄어쓰기**: GPT API에 맡기는 것도 고려
- **존댓말 변환**: 프롬프트 엔지니어링으로 처리

---

## 10. 트러블슈팅 가이드

### 자주 발생하는 문제

#### 1. OpenAI API Key 오류
- **증상**: `InvalidRequestError: Incorrect API key`
- **해결**: `.env` 파일 확인, 환경 변수 재로드

#### 2. Google Vision OCR 권한 오류
- **증상**: `PermissionDenied: 403`
- **해결**: `GOOGLE_APPLICATION_CREDENTIALS` 경로 확인, 서비스 계정 권한 검증

#### 3. CORS 에러
- **증상**: 프론트엔드에서 `Access-Control-Allow-Origin` 에러
- **해결**: FastAPI `CORSMiddleware` 설정 확인
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:5173"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

#### 4. 파일 업로드 크기 제한
- **증상**: 큰 파일 업로드 시 413 에러
- **해결**: FastAPI `max_upload_size` 설정 조정

#### 5. 한글 인코딩 문제
- **증상**: 파일 읽기 시 깨진 문자
- **해결**: `encoding='utf-8-sig'` 또는 `chardet` 라이브러리로 자동 감지

---

## 11. AI 에이전트 협업 가이드

### AI에게 작업 요청 시 권장 패턴

#### 좋은 요청 예시 ✅
```
"보도자료 생성 기능을 FastAPI 라우터로 분리해줘.
기존 press_release_app.py의 OpenAI 호출 로직을 services/press_release_service.py로 옮기고,
routers/press_release_router.py에 POST /api/press-release/generate 엔드포인트를 만들어줘."
```

#### 나쁜 요청 예시 ❌
```
"AI 기능 만들어줘"  (너무 모호함)
"예쁘게 디자인해줘"  (주관적, 구체적 지침 없음)
```

### AI가 코드 생성 시 체크리스트
- [ ] 파일명이 `snake_case`인가?
- [ ] 타입 힌트(Python) 또는 타입 정의(TypeScript)가 있는가?
- [ ] 에러 핸들링이 포함되어 있는가?
- [ ] 환경 변수 하드코딩이 없는가?
- [ ] 한글 주석이 적절히 사용되었는가?
- [ ] 실전 코드 기준을 충족하는가? (예제/튜토리얼 코드 아님)

### AI가 참고해야 할 우선순위
1. **본 Agents.md 문서** (최우선)
2. **기존 Streamlit 코드** (`cj_ai_app-main/`)
3. **공식 문서** (FastAPI, React, Tailwind)
4. **일반적인 베스트 프랙티스** (최하위)

---

## 12. 용어 사전

| 한국어 | 영어 | 설명 |
|--------|------|------|
| 보도자료 | Press Release | 언론 배포용 공식 문서 |
| 공적조서 | Official Merit Report | 공무원 표창/승진 시 작성하는 공적 문서 |
| 축제 | Festival | 지역 축제 (예: 충주 세계무술축제) |
| 취합 | Merge/Consolidate | 여러 파일을 하나로 병합 |
| 좌표 | Coordinates | 위도/경도 (Latitude/Longitude) |
| 홍보멘트 | Promotional Message | 카카오톡 등 SNS 홍보 문구 |
| 회의록 | Meeting Minutes | 회의 내용 기록 |
| 업무보고 | Work Report | 상급자에게 제출하는 업무 진행 보고서 |
| 정책사례 | Policy Case | 타 지자체 정책 참고 사례 |

---

## 13. 버전 히스토리

| 버전 | 날짜 | 변경 사항 |
|------|------|----------|
| 1.0 | 2025-12-09 | 초안 작성 (Agents.md 최초 생성) |

---

**Last Updated**: 2025-12-09
**Maintained by**: CJ AI Platform Development Team
**Contact**: 충주시청 AI 플랫폼 담당자
