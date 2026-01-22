# 충주시 AI 플랫폼 - 완전한 기술 명세서

> **목적**: 다른 AI 에이전트가 이 프로젝트를 완벽히 이해하고 작업할 수 있도록 작성된 상세 문서

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [아키텍처](#아키텍처)
3. [디렉토리 구조](#디렉토리-구조)
4. [기술 스택](#기술-스택)
5. [기능 명세](#기능-명세)
6. [API 엔드포인트](#api-엔드포인트)
7. [배포 환경](#배포-환경)
8. [개발 환경 설정](#개발-환경-설정)

---

## 프로젝트 개요

### 기본 정보
- **프로젝트명**: 충주시 AI 플랫폼 (Chungju City AI Platform)
- **GitHub 저장소**: https://github.com/storm8787/cj_ai_platform
- **담당자**: 충주시청 공무원 (leehojin)
- **목적**: 행정 업무 자동화를 위한 AI 통합 플랫폼
- **배포 플랫폼**: Azure (Static Web Apps + Container Apps)

### 핵심 가치
이 플랫폼은 **충주시청 직원들을 위한 AI 기반 행정 업무 자동화 도구**입니다.

주요 목표:
1. 반복적인 문서 작업 자동화 (보도자료, 공적조서, 회의록 등)
2. 데이터 분석 및 번역 작업 간소화
3. 주소/좌표 변환, 엑셀 취합 등 실무 유틸리티 제공
4. GPT-4 기반 챗봇으로 선거법, 뉴스 요약 등 정보 제공

---

## 아키텍처

### 전체 시스템 구성도

```
┌─────────────────────────────────────────────────────────────────┐
│                        Azure Cloud                               │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │          Azure Static Web Apps (Frontend)               │    │
│  │                                                           │    │
│  │  ┌───────────────────────────────────────────────────┐  │    │
│  │  │  React SPA (Vite + TailwindCSS + React Router)    │  │    │
│  │  │  • 11개 페이지 컴포넌트                            │  │    │
│  │  │  • Axios 기반 API 통신                            │  │    │
│  │  │  • Lucide Icons UI                                │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  │                      │                                   │    │
│  │                      │ /api/* 프록시                     │    │
│  └──────────────────────┼───────────────────────────────────┘    │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │       Azure Container Apps (Backend)                    │    │
│  │                                                           │    │
│  │  ┌───────────────────────────────────────────────────┐  │    │
│  │  │  FastAPI (Python 3.11)                            │  │    │
│  │  │  • 11개 라우터 모듈                                │  │    │
│  │  │  • OpenAI GPT-4o, GPT-4o-mini 통합               │  │    │
│  │  │  • FAISS 벡터스토어                               │  │    │
│  │  │  • Supabase 연동 (Storage + DB)                  │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  │                                                           │    │
│  │  Docker Image: ghcr.io/storm8787/cj-ai-backend:latest  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         │                                        │
└─────────────────────────┼────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐  ┌──────────────┐  ┌─────────────┐
│   Supabase    │  │  OpenAI API  │  │  Kakao API  │
│  • Storage    │  │  • GPT-4o    │  │  • 주소검색  │
│  • PostgreSQL │  │  • Embedding │  │  • 좌표변환  │
└───────────────┘  └──────────────┘  └─────────────┘
```

### 데이터 흐름

1. **프론트엔드 → 백엔드**
   - React 컴포넌트에서 Axios를 통해 API 호출
   - Azure Static Web Apps의 `/api/*` 경로가 Container Apps로 프록시
   - FastAPI 라우터가 요청 처리

2. **백엔드 처리**
   - 요청 검증 (Pydantic)
   - AI 모델 호출 (OpenAI GPT)
   - 벡터 검색 (FAISS)
   - 파일 저장 (Supabase Storage)
   - 로그 저장 (Supabase PostgreSQL)

3. **응답 반환**
   - JSON 또는 파일 스트림 (Excel, DOCX 등)
   - CORS 처리된 응답
   - 에러 핸들링

---

## 디렉토리 구조

### 전체 구조
```
cj_ai_platform/
├── .github/
│   └── workflows/
│       ├── azure-swa-deploy.yml      # 프론트엔드 CI/CD
│       └── azure-aca-deploy.yml      # 백엔드 CI/CD
│
├── backend/                          # FastAPI 백엔드
│   ├── routers/                      # API 라우터 (11개)
│   │   ├── __init__.py
│   │   ├── health.py                 # 헬스체크
│   │   ├── press_release.py          # 보도자료 생성
│   │   ├── election_law.py           # 선거법 챗봇
│   │   ├── news.py                   # 뉴스 조회/요약
│   │   ├── merit_report.py           # 공적조서 생성
│   │   ├── data_analysis.py          # AI 통계분석
│   │   ├── translator.py             # 다국어 번역
│   │   ├── address_geocoder.py       # 주소-좌표 변환
│   │   ├── kakao_promo.py            # 카카오 홍보문구
│   │   ├── excel_merger.py           # 엑셀 취합
│   │   ├── meeting_summarizer.py     # 회의록 요약
│   │   └── supabase_service.py       # Supabase 공통 로직
│   │
│   ├── services/                     # 공통 서비스
│   │   ├── __init__.py
│   │   ├── vectorstore.py            # FAISS 벡터스토어
│   │   ├── openai_service.py         # OpenAI 클라이언트
│   │   └── supabase_service.py       # Supabase 클라이언트
│   │
│   ├── models/                       # Pydantic 모델
│   │   └── __init__.py
│   │
│   ├── utils/                        # 유틸리티
│   │   ├── __init__.py
│   │   └── prompt_filter.py          # 프롬프트 필터링
│   │
│   ├── main.py                       # FastAPI 앱 진입점
│   ├── config.py                     # 환경변수 설정
│   ├── requirements.txt              # Python 의존성
│   ├── Dockerfile                    # 컨테이너 이미지
│   └── .env.example                  # 환경변수 템플릿
│
└── frontend/                         # React 프론트엔드
    ├── public/
    │   ├── index.html                # HTML 템플릿
    │   └── logo.png                  # 파비콘
    │
    ├── src/
    │   ├── pages/                    # 페이지 컴포넌트 (11개)
    │   │   ├── Dashboard.jsx         # 대시보드
    │   │   ├── NewsViewer.jsx        # 뉴스 조회
    │   │   ├── PressRelease.jsx      # 보도자료 생성
    │   │   ├── ElectionLaw.jsx       # 선거법 챗봇
    │   │   ├── MeritReport.jsx       # 공적조서 생성
    │   │   ├── DataAnalysis.jsx      # AI 통계분석
    │   │   ├── Translator.jsx        # 번역기
    │   │   ├── AddressGeocoder.jsx   # 주소-좌표 변환
    │   │   ├── KakaoPromo.jsx        # 카카오 홍보문구
    │   │   ├── ExcelMerger.jsx       # 엑셀 취합
    │   │   ├── MeetingSummarizer.jsx # 회의록 요약
    │   │   └── NotFound.jsx          # 404 페이지
    │   │
    │   ├── components/               # 공통 컴포넌트
    │   │   └── Layout.jsx            # 전체 레이아웃 (네비게이션)
    │   │
    │   ├── services/                 # API 서비스
    │   │   └── api.js                # Axios 인스턴스 + API 함수
    │   │
    │   ├── App.jsx                   # 라우터 설정
    │   ├── main.jsx                  # React 진입점
    │   └── index.css                 # TailwindCSS 설정
    │
    ├── staticwebapp.config.json      # Azure SWA 설정
    ├── vite.config.js                # Vite 빌드 설정
    ├── tailwind.config.js            # Tailwind 설정
    ├── postcss.config.js             # PostCSS 설정
    ├── package.json                  # npm 의존성
    └── .env.example                  # 환경변수 템플릿
```

---

## 기술 스택

### 프론트엔드 (Frontend)

| 카테고리 | 기술 | 버전 | 용도 |
|---------|------|------|------|
| **프레임워크** | React | 18.2.0 | UI 컴포넌트 |
| **빌드 도구** | Vite | 5.1.0 | 개발 서버 + 빌드 |
| **라우팅** | React Router | 6.22.0 | SPA 라우팅 |
| **HTTP 클라이언트** | Axios | 1.6.7 | API 통신 |
| **CSS 프레임워크** | TailwindCSS | 3.4.1 | 스타일링 |
| **아이콘** | Lucide React | 0.330.0 | 아이콘 |
| **배포** | Azure Static Web Apps | - | 정적 호스팅 |

#### 주요 설정 파일
- `vite.config.js`: Vite 개발 서버 설정
- `tailwind.config.js`: Tailwind 커스텀 설정
- `staticwebapp.config.json`: Azure SWA 라우팅 설정

### 백엔드 (Backend)

| 카테고리 | 기술 | 버전 | 용도 |
|---------|------|------|------|
| **프레임워크** | FastAPI | 0.109.2 | RESTful API |
| **서버** | Uvicorn | 0.27.1 | ASGI 서버 |
| **AI 모델** | OpenAI | 1.12.0 | GPT-4o, GPT-4o-mini |
| **벡터 검색** | FAISS | 1.7.4 | 임베딩 검색 |
| **임베딩** | Sentence Transformers | 2.3.1 | 텍스트 임베딩 |
| **데이터베이스** | Supabase | 2.3.4 | Storage + PostgreSQL |
| **문서 처리** | LangChain | 0.1.0+ | 문서 분할/처리 |
| **번역** | DeepL | 1.16.0+ | 번역 API |
| **Excel 처리** | OpenPyXL | 3.1.0+ | Excel 읽기/쓰기 |
| **컨테이너** | Docker | - | 이미지 빌드 |
| **배포** | Azure Container Apps | - | 컨테이너 호스팅 |

#### 주요 설정 파일
- `main.py`: FastAPI 앱 진입점
- `config.py`: 환경변수 관리 (Pydantic Settings)
- `Dockerfile`: 컨테이너 이미지 정의

---

## 기능 명세

### 1. 대시보드 (Dashboard)
**경로**: `/`  
**페이지**: `Dashboard.jsx`

**기능**:
- 전체 기능 카드 형태로 표시
- 각 기능별 바로가기 링크
- 서버 헬스체크 상태 표시

**API**:
- `GET /api/health` - 서버 상태 확인

---

### 2. 뉴스 조회 (NewsViewer)
**경로**: `/news`  
**페이지**: `NewsViewer.jsx`  
**라우터**: `routers/news.py`

**기능**:
1. Naver News API에서 충주 관련 뉴스 수집
2. OpenAI Embedding으로 중복 제거
3. 뉴스 목록 조회
4. GPT 기반 뉴스 요약

**API 엔드포인트**:
| 메서드 | 경로 | 설명 |
|-------|------|------|
| GET | `/api/news/list` | 뉴스 목록 조회 |
| POST | `/api/news/refresh` | 뉴스 수집 (최신 50개) |
| POST | `/api/news/summarize` | 뉴스 요약 생성 |

**데이터 흐름**:
1. Naver News API → 뉴스 수집
2. OpenAI Embedding → 벡터 변환
3. 코사인 유사도 계산 → 중복 제거
4. Supabase Storage → 저장
5. 프론트엔드 → 목록 표시

---

### 3. 보도자료 생성 (PressRelease)
**경로**: `/press-release`  
**페이지**: `PressRelease.jsx`  
**라우터**: `routers/press_release.py`

**기능**:
1. 8,000+ 과거 보도자료 벡터스토어 검색
2. 유사 보도자료 찾기 (FAISS)
3. GPT-4o로 보도자료 생성

**API 엔드포인트**:
| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/press-release/search-similar` | 유사 보도자료 검색 |
| POST | `/api/press-release/generate` | 보도자료 생성 |
| GET | `/api/press-release/status` | 벡터스토어 상태 |

**벡터스토어 정보**:
- 모델: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- 저장 위치: `/backend/vector_stores/press_release.faiss`
- 문서 수: 8,000+개
- 임베딩 차원: 384

**처리 프로세스**:
```
사용자 입력 (제목, 부서, 내용)
    ↓
임베딩 변환
    ↓
FAISS 벡터 검색 (top 5)
    ↓
GPT-4o 프롬프트 생성
    ↓
보도자료 생성 (구조화된 형식)
```

---

### 4. 선거법 챗봇 (ElectionLaw)
**경로**: `/election-law`  
**페이지**: `ElectionLaw.jsx`  
**라우터**: `routers/election_law.py`

**기능**:
1. 공직선거법 관련 질의응답
2. RAG(Retrieval-Augmented Generation) 기반
3. 법령 조항 인용

**API 엔드포인트**:
| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/election-law/ask` | 질문하기 |
| GET | `/api/election-law/targets` | 대상 후보 목록 |
| GET | `/api/election-law/status` | 벡터스토어 상태 |

**벡터스토어 정보**:
- 법령 데이터: 공직선거법 전문
- 검색 방식: 질문 임베딩 → 관련 조항 검색 → GPT 답변 생성

---

### 5. 공적조서 생성 (MeritReport)
**경로**: `/merit-report`  
**페이지**: `MeritReport.jsx`  
**라우터**: `routers/merit_report.py`

**기능**:
1. 표창 대상자 정보 입력
2. GPT-4o로 공적조서 생성
3. 정형화된 문서 포맷

**API 엔드포인트**:
| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/merit-report/generate` | 공적조서 생성 |

**입력 데이터**:
```json
{
  "name": "홍길동",
  "position": "○○과 주무관",
  "department": "자치행정과",
  "achievements": "업무 실적 내용...",
  "award_type": "표창장"
}
```

---

### 6. AI 통계분석 챗봇 (DataAnalysis)
**경로**: `/data-analysis`  
**페이지**: `DataAnalysis.jsx`  
**라우터**: `routers/data_analysis.py`

**기능**:
1. CSV/Excel 파일 업로드
2. Pandas 데이터프레임으로 변환
3. 자연어 질의 → Pandas 코드 생성 (GPT)
4. 코드 실행 → 결과 반환

**API 엔드포인트**:
| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/data-analysis/upload` | 파일 업로드 |
| POST | `/api/data-analysis/analyze` | 분석 실행 |
| DELETE | `/api/data-analysis/file/{id}` | 파일 삭제 |

**처리 흐름**:
```
Excel/CSV 업로드
    ↓
Pandas DataFrame 변환
    ↓
Supabase Storage 저장
    ↓
사용자 질문 입력
    ↓
GPT → Python 코드 생성
    ↓
코드 실행 (Pandas)
    ↓
결과 반환 (텍스트/차트)
```

**보안**:
- 코드 실행 샌드박스 적용
- 허용 라이브러리: `pandas`, `numpy`, `matplotlib`
- 위험 함수 차단: `eval`, `exec`, `os`, `sys`

---

### 7. 다국어 번역기 (Translator)
**경로**: `/translator`  
**페이지**: `Translator.jsx`  
**라우터**: `routers/translator.py`

**기능**:
1. HWPX/DOCX 문서 번역
2. DeepL API + GPT-4o 이중 번역
3. 충주시 고유명사 사전 적용

**지원 언어**:
- 영어 (EN)
- 일본어 (JA)
- 중국어 간체 (ZH)
- 베트남어 (VI)
- 스페인어 (ES)
- 프랑스어 (FR)
- 태국어 (TH)

**API 엔드포인트**:
| 메서드 | 경로 | 설명 |
|-------|------|------|
| GET | `/api/translator/languages` | 지원 언어 목록 |
| POST | `/api/translator/translate` | 문서 번역 (파일 다운로드) |

**번역 프로세스**:
```
HWPX/DOCX 업로드
    ↓
텍스트 추출 (lxml)
    ↓
DeepL API 번역
    ↓
GPT-4o 후처리 (고유명사, 어투 교정)
    ↓
번역 문서 생성 (원본 포맷 유지)
    ↓
파일 다운로드
```

---

### 8. 주소-좌표 변환기 (AddressGeocoder)
**경로**: `/address-geocoder`  
**페이지**: `AddressGeocoder.jsx`  
**라우터**: `routers/address_geocoder.py`

**기능**:
1. 주소 → 좌표 변환 (Kakao API)
2. 좌표 → 주소 변환 (Kakao API)
3. Excel 파일 일괄 변환

**API 엔드포인트**:
| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/geocoder/address-to-coord` | 주소 → 좌표 (단건) |
| POST | `/api/geocoder/coord-to-address` | 좌표 → 주소 (단건) |
| POST | `/api/geocoder/file/address-to-coord` | Excel 일괄 변환 (주소→좌표) |
| POST | `/api/geocoder/file/coord-to-address` | Excel 일괄 변환 (좌표→주소) |
| GET | `/api/geocoder/template/{type}` | 템플릿 다운로드 |

**Kakao API 연동**:
- REST API 키 사용
- 요청 제한: 1초당 10건 (Rate Limiting)
- 에러 처리: 타임아웃, 할당량 초과 등

---

### 9. 카카오 홍보문구 생성기 (KakaoPromo)
**경로**: `/kakao-promo`  
**페이지**: `KakaoPromo.jsx`  
**라우터**: `routers/kakao_promo.py`

**기능**:
1. 카카오톡 채널 홍보 문구 생성
2. 이미지 업로드 → GPT-4o Vision 분석
3. 카테고리별 맞춤 톤앤매너

**카테고리**:
- 🏛️ 행정/민원
- 🎉 문화/행사
- 🏥 보건/복지
- 🌳 환경/안전
- 💼 경제/일자리
- 📚 교육/평생학습

**API 엔드포인트**:
| 메서드 | 경로 | 설명 |
|-------|------|------|
| GET | `/api/kakao-promo/categories` | 카테고리 목록 |
| POST | `/api/kakao-promo/generate` | 홍보문구 생성 (텍스트) |
| POST | `/api/kakao-promo/generate-with-image` | 이미지 기반 생성 |

**생성 예시**:
```
[카테고리 이모지] 제목 (간결하게)

📍 핵심 내용 1-2줄
✨ 혜택/특징

📅 일시: YYYY.MM.DD
📍 장소: 위치
📞 문의: 000-000-0000

#충주시 #해시태그
```

---

### 10. 엑셀 취합기 (ExcelMerger)
**경로**: `/excel-merger`  
**페이지**: `ExcelMerger.jsx`  
**라우터**: `routers/excel_merger.py`

**기능**:
1. 여러 Excel 파일 업로드
2. 시트별 데이터 병합
3. 중복 제거 옵션
4. 통합 파일 다운로드

**API 엔드포인트**:
| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/excel-merger/merge` | 파일 병합 (다운로드) |
| POST | `/api/excel-merger/preview` | 병합 미리보기 |

**병합 옵션**:
```json
{
  "remove_duplicates": true,
  "sort_by_column": "날짜",
  "merge_mode": "vertical"  // vertical 또는 horizontal
}
```

**처리 과정**:
```
Excel 파일들 업로드
    ↓
OpenPyXL로 읽기
    ↓
Pandas DataFrame 변환
    ↓
병합 로직 적용
    ↓
중복 제거 (옵션)
    ↓
정렬 (옵션)
    ↓
Excel 파일 생성
    ↓
다운로드
```

---

### 11. 회의록 요약기 (MeetingSummarizer)
**경로**: `/meeting-summary`  
**페이지**: `MeetingSummarizer.jsx`  
**라우터**: `routers/meeting_summarizer.py`

**기능**:
1. 회의록 텍스트 입력 또는 파일 업로드
2. 3단계 상세도 선택 (최소/간략/표준)
3. GPT-4o 기반 구조화된 요약
4. 조치사항 자동 추출

**요약 모드**:

| 모드 | 주제당 문장수 | 문장당 길이 | 설명 |
|-----|-------------|-----------|------|
| 최소 | 1개 | 20-30자 | 핵심 키워드만 |
| 간략 | 1-2개 | 30-60자 | 요점 + 간단 배경 |
| 표준 | 4-6개 | 200-300자+ | 배경→현황→문제점→대응→계획 |

**API 엔드포인트**:
| 메서드 | 경로 | 설명 |
|-------|------|------|
| GET | `/api/meeting/modes` | 요약 모드 목록 |
| GET | `/api/meeting/system-info` | 시스템 정보 (부서/지역) |
| POST | `/api/meeting/summarize` | 텍스트 요약 |
| POST | `/api/meeting/summarize-file` | 파일 요약 |

**조치사항 추출**:
```json
{
  "summary": "회의 요약 내용...",
  "actions": [
    {
      "task": "예산 편성 검토",
      "assignee": "기획예산과 홍길동",
      "deadline": "2024-02-15",
      "details": "2024년도 예산안 재검토 필요"
    }
  ]
}
```

**충주시 맞춤 기능**:
- 부서명 자동 인식 (50개 부서)
- 읍면동 자동 인식 (25개 지역)
- 충주시 용어 사전 적용

---

## API 엔드포인트

### 전체 API 목록

#### Health Check
```
GET /api/health
→ {"status": "healthy"}
```

#### News (뉴스)
```
GET  /api/news/list
POST /api/news/refresh
POST /api/news/summarize
```

#### Press Release (보도자료)
```
POST /api/press-release/search-similar
POST /api/press-release/generate
GET  /api/press-release/status
```

#### Election Law (선거법)
```
POST /api/election-law/ask
GET  /api/election-law/targets
GET  /api/election-law/status
```

#### Merit Report (공적조서)
```
POST /api/merit-report/generate
```

#### Data Analysis (통계분석)
```
POST   /api/data-analysis/upload
POST   /api/data-analysis/analyze
DELETE /api/data-analysis/file/{id}
```

#### Translator (번역)
```
GET  /api/translator/languages
POST /api/translator/translate
```

#### Address Geocoder (주소변환)
```
POST /api/geocoder/address-to-coord
POST /api/geocoder/coord-to-address
POST /api/geocoder/file/address-to-coord
POST /api/geocoder/file/coord-to-address
GET  /api/geocoder/template/{type}
```

#### Kakao Promo (홍보문구)
```
GET  /api/kakao-promo/categories
POST /api/kakao-promo/generate
POST /api/kakao-promo/generate-with-image
```

#### Excel Merger (엑셀 취합)
```
POST /api/excel-merger/merge
POST /api/excel-merger/preview
```

#### Meeting Summarizer (회의 요약)
```
GET  /api/meeting/modes
GET  /api/meeting/system-info
POST /api/meeting/summarize
POST /api/meeting/summarize-file
```

---

## 배포 환경

### Azure 리소스

| 리소스 | 유형 | 이름 | 용도 |
|-------|------|------|------|
| Resource Group | 리소스 그룹 | `rg-cj-ai-platform` | 전체 리소스 묶음 |
| Static Web App | 정적 웹 앱 | `cj-ai-frontend` | React 프론트엔드 호스팅 |
| Container App | 컨테이너 앱 | `cj-ai-backend` | FastAPI 백엔드 |
| Container Apps Environment | 환경 | `cj-ai-env` | 컨테이너 런타임 환경 |
| Log Analytics Workspace | 모니터링 | `cj-ai-logs` | 로그 수집 |

### 환경변수

#### 프론트엔드 (Static Web App)
```bash
VITE_API_URL=https://cj-ai-backend.ashysky-xxx.koreacentral.azurecontainerapps.io
```

#### 백엔드 (Container App)
```bash
# OpenAI
OPENAI_API_KEY=sk-proj-xxx...

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Kakao
KAKAO_API_KEY=xxx...

# CORS
CORS_ORIGINS=https://cj-ai-frontend.azurestaticapps.net,http://localhost:5173

# 기타
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### GitHub Container Registry

**이미지 저장소**: `ghcr.io/storm8787/cj-ai-backend`

**빌드 프로세스**:
```bash
cd backend
docker build -t ghcr.io/storm8787/cj-ai-backend:latest .
docker push ghcr.io/storm8787/cj-ai-backend:latest
```

---

## 개발 환경 설정

### 로컬 개발

#### 1. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

**의존성**:
- Node.js 18.x 이상
- npm 9.x 이상

#### 2. 백엔드 실행

```bash
cd backend

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일 편집: API 키 입력

# 서버 실행
uvicorn main:app --reload --port 8000
# → http://localhost:8000
```

**의존성**:
- Python 3.11
- pip 23.x 이상

#### 3. API 문서 확인

```
http://localhost:8000/docs        # Swagger UI
http://localhost:8000/redoc       # ReDoc
```

---

## 데이터베이스 스키마 (Supabase)

### 주요 테이블

#### 1. `news_articles`
```sql
CREATE TABLE news_articles (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    published_at TIMESTAMP,
    summary TEXT,
    embedding VECTOR(384),  -- 임베딩 벡터
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 2. `press_releases`
```sql
CREATE TABLE press_releases (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    department TEXT,
    content TEXT,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 3. `usage_logs`
```sql
CREATE TABLE usage_logs (
    id SERIAL PRIMARY KEY,
    feature TEXT NOT NULL,  -- 기능명 (press_release, translator 등)
    user_ip TEXT,
    request_data JSONB,
    response_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Storage Buckets

| 버킷명 | 용도 |
|-------|------|
| `press-releases` | 보도자료 파일 |
| `translations` | 번역 결과 파일 |
| `data-analysis` | 업로드된 데이터 파일 |
| `meeting-summaries` | 회의록 파일 |

---

## 보안 설정

### CORS 설정
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cj-ai-frontend.azurestaticapps.net",  # 프로덕션
        "http://localhost:5173"  # 로컬 개발
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Processed-Count", "X-Total-Rows"]
)
```

### API 키 보호
- **환경변수 주입**: Azure Container Apps Secrets
- **GitHub Secrets**: CI/CD 파이프라인
- **코드 내 하드코딩 금지**: `.env` 파일 사용

### 프롬프트 인젝션 방지
```python
# backend/utils/prompt_filter.py
def filter_prompt(text: str) -> str:
    """위험한 프롬프트 패턴 필터링"""
    patterns = [
        r"ignore previous instructions",
        r"system prompt",
        r"<script>.*</script>",
        # ...
    ]
    # 필터링 로직
```

---

## 모니터링 & 로깅

### 로그 수준
```python
# 개발 환경
LOG_LEVEL=DEBUG

# 프로덕션 환경
LOG_LEVEL=INFO
```

### Azure Monitor
- Application Insights 연동
- 요청/응답 추적
- 에러 로그 수집
- 성능 메트릭

---

## 비용 최적화

### 예상 월간 비용

| 서비스 | 티어 | 예상 비용 |
|--------|------|----------|
| Static Web Apps | Free | ₩0 |
| Container Apps | Consumption | ~₩10,000-30,000 |
| Supabase | Free | ₩0 |
| OpenAI API | Pay-as-you-go | ~₩50,000-100,000 |
| Kakao API | Free (10,000건/일) | ₩0 |
| **총 예상** | | **~₩60,000-130,000/월** |

### 최적화 전략
1. Container Apps 자동 스케일링 (0→1)
2. OpenAI API 캐싱 활용
3. Supabase Free Tier 활용
4. 불필요한 벡터 검색 최소화

---

## 트러블슈팅

### 일반적인 문제

#### 1. CORS 오류
**증상**: 프론트엔드에서 API 호출 시 CORS 에러

**해결**:
```python
# backend/config.py
CORS_ORIGINS = "https://your-swa.azurestaticapps.net,http://localhost:5173"
```

#### 2. API 연결 실패
**증상**: 404 Not Found

**해결**:
```json
// frontend/staticwebapp.config.json
{
  "routes": [
    {
      "route": "/api/*",
      "rewrite": "https://your-backend.azurecontainerapps.io/api/*"
    }
  ]
}
```

#### 3. 벡터스토어 로드 실패
**증상**: `FileNotFoundError: vector_stores/press_release.faiss`

**해결**:
```bash
# 컨테이너 이미지에 벡터스토어 포함 확인
docker build -t backend .
docker run -it backend ls /app/vector_stores
```

#### 4. OpenAI API 타임아웃
**증상**: `openai.error.Timeout`

**해결**:
```python
# routers/*.py
client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=60.0)
```

---

## CI/CD 파이프라인

### GitHub Actions

#### 프론트엔드 배포 (.github/workflows/azure-swa-deploy.yml)
```yaml
name: Deploy Frontend to Azure Static Web Apps

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      
      - name: Build
        run: |
          cd frontend
          npm install
          npm run build
      
      - name: Deploy to Azure SWA
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_SWA_TOKEN }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: "upload"
          app_location: "/frontend"
          output_location: "dist"
```

#### 백엔드 배포 (.github/workflows/azure-aca-deploy.yml)
```yaml
name: Deploy Backend to Azure Container Apps

on:
  push:
    branches: [main]
    paths:
      - 'backend/**'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to GHCR
        run: echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
      
      - name: Build and Push
        run: |
          cd backend
          docker build -t ghcr.io/${{ github.repository_owner }}/cj-ai-backend:latest .
          docker push ghcr.io/${{ github.repository_owner }}/cj-ai-backend:latest
      
      - name: Deploy to Azure Container Apps
        uses: azure/container-apps-deploy-action@v1
        with:
          resource-group: rg-cj-ai-platform
          container-app-name: cj-ai-backend
          image: ghcr.io/${{ github.repository_owner }}/cj-ai-backend:latest
```

---

## 확장 가능성

### 추가 가능한 기능

1. **사용자 인증**
   - Azure AD B2C
   - JWT 토큰 기반 인증

2. **파일 버전 관리**
   - Git-like 버전 컨트롤
   - 변경 이력 추적

3. **협업 기능**
   - 실시간 공동 편집
   - 댓글/리뷰 시스템

4. **대시보드 강화**
   - 사용 통계 시각화
   - 인기 기능 분석

5. **모바일 앱**
   - React Native
   - PWA (Progressive Web App)

---

## 라이선스 & 크레딧

### 오픈소스 라이선스
- FastAPI: MIT License
- React: MIT License
- TailwindCSS: MIT License
- OpenAI Python SDK: MIT License

### 상업 라이선스
- OpenAI API: Pay-as-you-go
- DeepL API: Free Tier
- Kakao API: Free Tier

### 개발자
- **프로젝트 리드**: 이호진 (충주시청)
- **GitHub**: https://github.com/storm8787/cj_ai_platform

---

## 참고 자료

### 공식 문서
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [React 문서](https://react.dev/)
- [Azure Static Web Apps](https://learn.microsoft.com/azure/static-web-apps/)
- [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [OpenAI API](https://platform.openai.com/docs/)
- [Supabase 문서](https://supabase.com/docs)

### 관련 기술
- [FAISS (Facebook AI Similarity Search)](https://github.com/facebookresearch/faiss)
- [LangChain](https://python.langchain.com/)
- [Sentence Transformers](https://www.sbert.net/)

---

## 변경 이력

### v1.0.0 (2024-01-22)
- ✅ 11개 기능 모듈 완성
- ✅ Azure 배포 완료
- ✅ CI/CD 파이프라인 구축
- ✅ 프로덕션 운영 시작

---

**문서 작성일**: 2024-01-22  
**최종 수정**: 2024-01-22  
**문서 버전**: 1.0.0

---

## AI 에이전트를 위한 추가 노트

### 이 프로젝트를 이해하려면:

1. **핵심 아키텍처**
   - 프론트엔드: React SPA (Vite)
   - 백엔드: FastAPI (Python)
   - 배포: Azure (SWA + Container Apps)

2. **주요 파일**
   - `frontend/src/App.jsx`: 라우팅 설정
   - `frontend/src/services/api.js`: API 통신
   - `backend/main.py`: FastAPI 진입점
   - `backend/routers/*.py`: 각 기능별 라우터

3. **데이터 흐름**
   - 사용자 → React 페이지 → Axios → FastAPI 라우터 → OpenAI/Supabase → 응답

4. **코드 수정 시 주의사항**
   - 환경변수는 `.env`가 아닌 Azure Portal에서 설정
   - CORS 설정 필수 (프론트엔드 URL 추가)
   - API 엔드포인트 변경 시 `api.js`도 함께 수정
   - 새 라우터 추가 시 `main.py`에 등록 필요

5. **디버깅**
   - 프론트엔드: 브라우저 개발자 도구
   - 백엔드: Uvicorn 콘솔 로그
   - Azure: Log Analytics 또는 Container App 로그 스트림
