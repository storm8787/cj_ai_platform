# 충주시 AI 플랫폼 - 완전한 기술 명세서 (Version 7.1)

> **목적**: 다른 AI 에이전트가 이 프로젝트를 완벽히 이해하고 작업할 수 있도록 작성된 상세 문서

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [아키텍처](#아키텍처)
3. [디렉토리 구조](#디렉토리-구조)
4. [기술 스택](#기술-스택)
5. [인증 시스템](#인증-시스템)
6. [기능 명세](#기능-명세)
7. [출장보고 생성기](#출장보고-생성기)
8. [공공데이터 검증기](#공공데이터-검증기)
9. [게시판 시스템](#게시판-시스템)
10. [프롬프트 중앙 관리 시스템](#프롬프트-중앙-관리-시스템)
11. [재난상황 단톡 대시보드 (Version 7.1)](#재난상황-단톡-대시보드-version-71)
12. [API 엔드포인트](#api-엔드포인트)
13. [데이터베이스 스키마](#데이터베이스-스키마)
14. [배포 환경](#배포-환경)
15. [개발 환경 설정](#개발-환경-설정)
16. [보안 설정](#보안-설정)
17. [CI/CD 파이프라인](#cicd-파이프라인)
18. [트러블슈팅](#트러블슈팅)
19. [비용 최적화](#비용-최적화)

---

## 프로젝트 개요

### 기본 정보
- **프로젝트명**: 충주시 AI 플랫폼 (Chungju City AI Platform)
- **GitHub 저장소**: https://github.com/storm8787/cj_ai_platform
- **프론트엔드 URL**: https://agreeable-smoke-0b02cf31e.2.azurestaticapps.net
- **백엔드 URL**: https://cj-ai-backend.ashysky-a846c5bf.koreacentral.azurecontainerapps.io
- **담당자**: 충주시청 공무원 (이호진)
- **목적**: 행정 업무 자동화를 위한 AI 통합 플랫폼
- **배포 플랫폼**: Azure (Static Web Apps + Container Apps)

### 핵심 가치
이 플랫폼은 **충주시청 직원들을 위한 AI 기반 행정 업무 자동화 도구**입니다.

주요 목표:
1. 반복적인 문서 작업 자동화 (보도자료, 공적조서, 회의록, 업무보고 등)
2. 데이터 분석 및 번역 작업 간소화
3. 주소/좌표 변환, 엑셀 취합 등 실무 유틸리티 제공
4. GPT-4 기반 챗봇으로 선거법, 법령·자치법규, 뉴스 요약 등 정보 제공
5. **사용자 인증 및 권한 관리** (관리자/일반 사용자)
6. **소통공간** (공지사항, 자료실, 묻고답하기 게시판)
7. **사업 타임라인 생성** (AI 일정 추천, 법령 기반 사전절차 자동 분석, 간트차트 시각화)
8. **프롬프트 중앙 관리** (Supabase DB 기반, 관리자 웹페이지에서 재배포 없이 AI 프롬프트 수정)
9. **재난상황 단톡 대시보드** (카카오톡 재난상황 txt 업로드 → 사건 분류 → 대시보드/일일보고 자동 생성, **GPT-4o 자연어 보고서**) 🆕 v7.1

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
│  │  │  • 28개 페이지 컴포넌트 (재난 대시보드 포함)         │  │    │
│  │  │  • Axios 기반 API 통신                            │  │    │
│  │  │  • Lucide Icons UI                                │  │    │
│  │  │  • AuthContext 인증 상태 관리                     │  │    │
│  │  │  • useDisasterSession (sessionStorage 리액티브)  │  │    │
│  │  │  • constants/disaster.js (라벨 단일 소스)        │  │    │
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
│  │  │  • 20개 라우터 모듈 (disaster_dashboard 포함)     │  │    │
│  │  │  • OpenAI GPT-4o, GPT-4o-mini 통합               │  │    │
│  │  │  • OpenAIService.generate_text(model=...) 🆕     │  │    │
│  │  │  • FAISS 벡터스토어 + BM25 Hybrid Search          │  │    │
│  │  │  • bge-m3 임베딩 모델 (1024차원)                  │  │    │
│  │  │  • Supabase 연동 (Auth + Storage + DB + Prompts)  │  │    │
│  │  │  • 프롬프트 중앙 관리 (DB → 캐시 → 코드 폴백)    │  │    │
│  │  │  • 재난 분석 락 (analysis_status 기반) 🆕        │  │    │
│  │  │  • logging 모듈 (PII 최소화) 🆕                  │  │    │
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
│  • Auth       │  │  • GPT-4o    │  │  • 주소검색  │
│  • Storage    │  │  • Embedding │  │  • 좌표변환  │
│  • PostgreSQL │  │              │  │             │
└───────────────┘  └──────────────┘  └─────────────┘
                                     ┌─────────────┐
                                     │ law.go.kr   │
                                     │ • 법령 검색  │
                                     │ • 조문 조회  │
                                     │ • 자치법규   │
                                     └─────────────┘
```

### 데이터 흐름

1. **인증 흐름**
   - 로그인 페이지 → Supabase Auth → JWT 토큰 발급
   - 토큰은 localStorage에 저장
   - 모든 API 요청 시 Authorization 헤더로 전송

2. **프론트엔드 → 백엔드**
   - React 컴포넌트에서 Axios를 통해 API 호출
   - Azure Static Web Apps의 `/api/*` 경로가 Container Apps로 프록시
   - FastAPI 라우터가 요청 처리

3. **백엔드 처리**
   - 요청 검증 (Pydantic)
   - 토큰 검증 (Supabase Auth)
   - AI 모델 호출 (OpenAI GPT)
   - 벡터 검색 (FAISS)
   - 파일 저장 (Supabase Storage)
   - 데이터 저장 (Supabase PostgreSQL)

4. **응답 반환**
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
│   ├── routers/                      # API 라우터 (20개)
│   │   ├── __init__.py
│   │   ├── health.py                 # 헬스체크
│   │   ├── auth.py                   # 인증 (회원가입/로그인/OTP)
│   │   ├── board.py                  # 게시판 (공지/자료실/QnA)
│   │   ├── press_release.py          # 보도자료 생성
│   │   ├── election_law.py           # 선거법 챗봇
│   │   ├── law_chatbot.py            # 법령·자치법규 챗봇 (v8, Hybrid Search)
│   │   ├── news.py                   # 뉴스 조회/요약
│   │   ├── merit_report.py           # 공적조서 생성
│   │   ├── data_analysis.py          # AI 통계분석
│   │   ├── translator.py             # 다국어 번역
│   │   ├── address_geocoder.py       # 주소-좌표 변환
│   │   ├── kakao_promo.py            # 카카오 홍보문구
│   │   ├── excel_merger.py           # 엑셀 취합
│   │   ├── meeting_summarizer.py     # 회의록 요약
│   │   ├── report_writer.py          # 업무보고 생성기
│   │   ├── trip_report.py            # 출장보고 생성기 (Vision AI)
│   │   ├── data_validator.py         # 공공데이터 검증기
│   │   ├── timeline_planner.py       # 사업 타임라인 생성기 (법령챗봇 연동)
│   │   ├── prompt_manager.py         # 프롬프트 관리 API (관리자 전용)
│   │   └── disaster_dashboard.py     # 🆕 재난상황 단톡 대시보드 (v7.1: async + 락)
│   │
│   ├── data/                         # 정적 데이터
│   │   ├── public_data_standards.json # 공공데이터 표준 300개
│   │   ├── eup_myeon_dong.txt        # 충주시 읍면동 목록
│   │   └── law_chatbot/              # 법령 챗봇 벡터스토어
│   │       └── vectorstores/
│   │           ├── index.faiss        # FAISS 인덱스 (bge-m3, 1024차원)
│   │           ├── index.pkl          # 텍스트 + 메타데이터
│   │           └── bm25_corpus.pkl    # BM25 토큰화 코퍼스
│   │
│   ├── scripts/                      # 유틸리티 스크립트
│   │   ├── build_law_vectorstore.py  # 법령 벡터스토어 구축 (v3)
│   │   ├── seed_all_prompts.sql      # 38개 프롬프트 시드
│   │   └── seed_disaster_prompts.sql # 🆕 재난 일일보고 프롬프트 시드 (3개)
│   │
│   ├── services/                     # 공통 서비스
│   │   ├── __init__.py
│   │   ├── vectorstore.py            # FAISS 벡터스토어
│   │   ├── openai_service.py         # 🆕 OpenAI 클라이언트 (model 오버라이드 추가)
│   │   ├── supabase_service.py       # Supabase 클라이언트 (싱글톤)
│   │   ├── prompt_service.py         # 프롬프트 중앙 관리 (싱글톤)
│   │   ├── disaster_constants.py     # 🆕 재난 라벨 상수 (단일 소스)
│   │   ├── disaster_parser_service.py # 🆕 카카오톡 txt 파서 (v7.1: 날짜 포맷 확장)
│   │   ├── disaster_incident_service.py # 🆕 사건 재구성 (v7.1: 상태 흐름 기반)
│   │   └── disaster_report_service.py # 🆕 일일보고 생성 (v7.1: GPT-4o + 폴백)
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
    │   ├── pages/                    # 페이지 컴포넌트 (28개)
    │   │   ├── Dashboard.jsx         # 🆕 대시보드 (재난 카드 경로 /disaster-upload)
    │   │   ├── Login.jsx             # 로그인/회원가입 (OTP 인증)
    │   │   ├── NewsViewer.jsx        # 뉴스 조회
    │   │   ├── PressRelease.jsx      # 보도자료 생성
    │   │   ├── ElectionLaw.jsx       # 선거법 챗봇
    │   │   ├── LawChatbot.jsx        # 법령·자치법규 챗봇
    │   │   ├── MeritReport.jsx       # 공적조서 생성
    │   │   ├── DataAnalysis.jsx      # AI 통계분석
    │   │   ├── Translator.jsx        # 번역기
    │   │   ├── AddressGeocoder.jsx   # 주소-좌표 변환
    │   │   ├── KakaoPromo.jsx        # 카카오 홍보문구
    │   │   ├── ExcelMerger.jsx       # 엑셀 취합
    │   │   ├── MeetingSummarizer.jsx # 회의록 요약
    │   │   ├── ReportWriter.jsx      # 업무보고 생성기
    │   │   ├── TripReport.jsx        # 출장보고 생성기
    │   │   ├── DataValidator.jsx     # 공공데이터 검증기
    │   │   ├── TimelinePlanner.jsx   # 사업 타임라인 생성기
    │   │   ├── PromptManager.jsx     # 프롬프트 관리 (관리자 전용)
    │   │   ├── About.jsx             # 시스템 소개
    │   │   ├── NoticeBoard.jsx       # 공지사항 게시판
    │   │   ├── ArchiveBoard.jsx      # 자료실 게시판
    │   │   ├── QnaBoard.jsx          # 묻고답하기 게시판
    │   │   ├── BoardDetail.jsx       # 게시글 상세
    │   │   ├── BoardWrite.jsx        # 게시글 작성
    │   │   ├── BoardEdit.jsx         # 게시글 수정
    │   │   ├── DisasterUpload.jsx    # 🆕 재난 카톡 업로드 (v7.1: 리액티브 세션)
    │   │   ├── DisasterDashboard.jsx # 🆕 재난 대시보드 (v7.1: 리액티브 세션)
    │   │   ├── DisasterIncidents.jsx # 🆕 사건 목록 (v7.1: 리액티브 세션)
    │   │   ├── DisasterDailyReport.jsx # 🆕 일일보고 (v7.1: 리액티브 세션)
    │   │   └── NotFound.jsx          # 404 페이지
    │   │
    │   ├── components/               # 공통 컴포넌트
    │   │   └── Layout.jsx            # 전체 레이아웃 (2단 드롭다운 메뉴)
    │   │
    │   ├── constants/                # 🆕 상수
    │   │   └── disaster.js           # 🆕 재난 라벨 + 세션 헬퍼 (단일 소스)
    │   │
    │   ├── hooks/                    # 🆕 커스텀 훅
    │   │   └── useDisasterSession.js # 🆕 sessionStorage 리액티브 훅
    │   │
    │   ├── context/                  # 상태 관리
    │   │   └── AuthContext.jsx       # 인증 상태 관리
    │   │
    │   ├── services/                 # API 서비스
    │   │   └── api.js                # Axios 인스턴스 + API 함수
    │   │
    │   ├── App.jsx                   # 라우터 설정 (ProtectedRoute 포함)
    │   ├── main.jsx                  # React 진입점
    │   └── index.css                 # TailwindCSS 설정 (커스텀 스타일)
    │
    ├── staticwebapp.config.json      # Azure SWA 설정
    ├── vite.config.js                # Vite 빌드 설정
    ├── tailwind.config.js            # Tailwind 설정 (Pretendard 폰트)
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
| **폰트** | Pretendard | - | 한글 폰트 |
| **배포** | Azure Static Web Apps | - | 정적 호스팅 |

#### 주요 설정 파일
- `vite.config.js`: Vite 개발 서버 설정
- `tailwind.config.js`: Tailwind 커스텀 설정 (Pretendard 폰트)
- `staticwebapp.config.json`: Azure SWA 라우팅 설정
- `index.css`: 커스텀 CSS (글래스모피즘, 애니메이션)

### 백엔드 (Backend)

| 카테고리 | 기술 | 버전 | 용도 |
|---------|------|------|------|
| **프레임워크** | FastAPI | 0.109.2 | RESTful API |
| **서버** | Uvicorn | 0.27.1 | ASGI 서버 |
| **AI 모델** | OpenAI | 1.12.0 | GPT-4o, GPT-4o-mini |
| **벡터 검색** | FAISS | 1.7.4 | 임베딩 검색 |
| **임베딩 (보도자료/선거법)** | Sentence Transformers (ko-sroberta) | 2.3.1 | 보도자료·선거법 전용 (`jhgan/ko-sroberta-multitask`, 768차원) |
| **임베딩 (법령)** | FlagEmbedding (bge-m3) | - | 법령 챗봇 전용 (`BAAI/bge-m3`, 1024차원, dense+sparse) |
| **BM25 검색** | rank-bm25 | - | 법령 챗봇 Hybrid Search용 키워드 매칭 |
| **인증** | Supabase Auth | - | 회원가입/로그인/OTP |
| **데이터베이스** | Supabase PostgreSQL | - | 사용자/게시판 데이터 |
| **파일 저장소** | Supabase Storage | - | 첨부파일 저장 |
| **HTTP 클라이언트** | httpx | - | 비동기 HTTP 요청 (법령챗봇 내부호출 포함) |
| **문서 처리** | LangChain | 0.1.0+ | 문서 분할/처리 |
| **번역** | DeepL | 1.16.0+,<2.0.0 | 번역 API (**반드시 2.x 미만으로 고정**) |
| **Excel 처리** | OpenPyXL | 3.1.0+ | Excel 읽기/쓰기 |
| **컨테이너** | Docker | - | 이미지 빌드 |
| **배포** | Azure Container Apps | - | 컨테이너 호스팅 |

---

## 인증 시스템

### 개요
Supabase Auth를 사용한 이메일 기반 인증 시스템

### 회원가입 흐름
```
1. 사용자 정보 입력 (이름, 부서, 이메일, 비밀번호)
        ↓
2. POST /api/auth/signup
        ↓
3. Supabase에서 6자리 OTP 이메일 발송
        ↓
4. 사용자가 OTP 입력
        ↓
5. POST /api/auth/verify-otp
        ↓
6. 인증 완료 → JWT 토큰 발급 → 자동 로그인
```

### 로그인 흐름
```
1. 이메일, 비밀번호 입력
        ↓
2. POST /api/auth/login
        ↓
3. Supabase Auth 검증
        ↓
4. JWT 토큰 발급 (access_token, refresh_token)
        ↓
5. localStorage에 토큰 저장
        ↓
6. 메인 페이지로 이동
```

### 인증 API
| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/auth/signup` | 회원가입 (이름, 부서, 이메일, 비밀번호) |
| POST | `/api/auth/verify-otp` | OTP 코드 검증 |
| POST | `/api/auth/resend-otp` | OTP 재발송 |
| POST | `/api/auth/login` | 로그인 |
| POST | `/api/auth/logout` | 로그아웃 |
| GET | `/api/auth/verify` | 토큰 검증 |
| GET | `/api/auth/me` | 현재 사용자 정보 + 권한 |
| POST | `/api/auth/refresh` | 토큰 갱신 |

### 권한 시스템
| 역할 | 설명 | 권한 |
|------|------|------|
| `user` | 일반 사용자 | 모든 AI 서비스 사용, QnA 질문 작성 |
| `admin` | 관리자 | 공지사항/자료실 작성, QnA 답변 작성, 모든 게시글 수정/삭제, 프롬프트 관리 |

### 관리자 지정 방법
```sql
-- Supabase SQL Editor에서 실행
UPDATE public.user_profiles
SET role = 'admin'
WHERE email = 'admin@example.com';
```

---

## 기능 명세

### 1. 대시보드 (Dashboard)
**경로**: `/`
**페이지**: `Dashboard.jsx`

**기능**:
- 전체 기능 카드 형태로 표시
- 각 기능별 바로가기 링크
- 서버 헬스체크 상태 표시

**v7.1 변경점** 🆕:
- 재난 대시보드 카드 경로: `/disaster-dashboard` → **`/disaster-upload`** (사용자가 먼저 업로드하도록 유도)
- description 명확화: "txt를 업로드하면 …생성합니다"
- `categoryOrder.data` 배열 경로도 동기화

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
```
Naver News API → 뉴스 수집
       ↓
OpenAI Embedding → 벡터 변환
       ↓
코사인 유사도 계산 → 중복 제거
       ↓
Supabase Storage → 저장
       ↓
프론트엔드 → 목록 표시
```

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
- 모델: `jhgan/ko-sroberta-multitask` (Docker 내 경로: `/app/models/ko-sroberta-multitask`)
- 저장 위치: `/app/data/vectorstores/press_release_faiss.index` + `documents_metadata.pkl`
- 문서 수: 8,037개
- 임베딩 차원: 768
- 메타데이터 구조: `{"documents": [...], "texts": [...], "model_info": {...}}`
- 각 문서 키: `page_content`, `metadata`

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

### 4-2. 법령·자치법규 챗봇 (LawChatbot)
**경로**: `/law-chatbot`
**페이지**: `LawChatbot.jsx`
**라우터**: `routers/law_chatbot.py` (v8)

**기능**:
1. 국가법령 + 충주시 자치법규 통합 질의응답
2. Hybrid Search (Dense + BM25) 기반 자치법규 검색
3. 국가법령정보센터 API 실시간 법령 검색
4. Agentic 재검색 루프 (검색 실패 시 자동 키워드 변경)
5. GPT-4o 자체 법률 지식 + 검색 결과 하이브리드 답변

**API 엔드포인트**:
| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/law-chatbot/ask` | 질문하기 |
| POST | `/api/law-chatbot/search` | 법령 직접 검색 |
| GET | `/api/law-chatbot/status` | 시스템 상태 (벡터스토어 + API) |
| GET | `/api/law-chatbot/categories` | 검색 범위 목록 |

**검색 범위**:
| 범위 | 설명 | 검색 소스 |
|------|------|----------|
| all | 전체 (법령+자치법규) | FAISS + BM25 + law.go.kr API |
| national | 국가법령 | law.go.kr API |
| local | 충주시 자치법규 | FAISS + BM25 벡터스토어 |

**벡터스토어 정보**:
- 임베딩 모델: `BAAI/bge-m3` (1024차원, dense+sparse)
- 문서 수: 12,002개 청크 (자치법규 716건, 별표/서식 252건)
- 검색 방식: Hybrid Search (Dense FAISS + BM25 RRF 합산)
- 청크 구조: 컨텍스트 보강 (법령명+조문제목 prefix)
- 저장 위치: `/backend/data/law_chatbot/vectorstores/`

**Hybrid Search 동작 원리**:
```
사용자 질문
    ↓
┌────────────────────┐    ┌────────────────────┐
│  Dense 검색 (FAISS) │    │  BM25 검색 (키워드) │
│  의미적 유사도 기반  │    │  정확한 단어 매칭    │
└────────┬───────────┘    └────────┬───────────┘
         │                         │
         └────────┬────────────────┘
                  ▼
         RRF (Reciprocal Rank Fusion)
         두 결과 순위를 합산하여 최종 순위 결정
                  ↓
         동적 threshold 필터링
         (절대 0.30 + 상대 85%)
```

**답변 전략 (3단계)**:
```
1단계: 검색 결과에 답이 있으면 → 조문 인용 답변
2단계: 검색 결과 없지만 GPT가 알면 → 답변 + 💡 AI 지식 기반 표시
3단계: 둘 다 모르면 → 법제팀 확인 권장
```

**Agentic 재검색 루프**:
```
키워드 추출 (GPT-4o)
    ↓
1차 검색 → 결과 충분? → Yes → 답변 생성
                        ↓ No
GPT에게 대안 키워드 요청 (gpt-4o-mini)
    ↓
2차 검색 → 결과 충분? → Yes → 답변 생성
                        ↓ No
GPT에게 대안 키워드 요청
    ↓
3차 검색 → 답변 생성 (결과 유무 관계없이)
```

**국가법령 API (law.go.kr)**:
- 인증: OC 코드 방식 (`LAW_API_OC` 환경변수)
- 인코딩: `resp.content.decode("utf-8")` (관공서 네트워크 인코딩 변조 대응)
- 법령 본문: 질문 관련 조문만 필터링 (최대 8,000자)
- 별표: XML `별표단위` 태그에서 제목 추출 (본문은 HWP 첨부파일로만 제공)

**GPT 모델 구성**:
| 용도 | 모델 | 이유 |
|------|------|------|
| 답변 생성 | gpt-4o | 법률 해석 정확도 |
| 키워드 추출 | gpt-4o | 실무→법령명 추론 |
| 대안 키워드 | gpt-4o-mini | 단순 변환, 비용 절약 |

**벡터스토어 구축 스크립트**:
```bash
cd backend
pip install FlagEmbedding
python scripts/build_law_vectorstore.py --oc YOUR_OC_CODE
```
- 출력: `C:\temp\law_vectorstore_v3\` (index.faiss, index.pkl, bm25_corpus.pkl)
- 소요시간: 약 30~40분 (711건 자치법규 수집 + bge-m3 임베딩)

**Docker 이미지 (bge-m3 + ko-sroberta 포함)**:
```dockerfile
ENV EMBEDDING_MODEL=/app/models/bge-m3
RUN mkdir -p /app/models && \
    python -c "from huggingface_hub import snapshot_download; \
    snapshot_download(repo_id='BAAI/bge-m3', local_dir='/app/models/bge-m3', local_dir_use_symlinks=False)" && \
    python -c "from huggingface_hub import snapshot_download; \
    snapshot_download(repo_id='jhgan/ko-sroberta-multitask', local_dir='/app/models/ko-sroberta-multitask', local_dir_use_symlinks=False)"
```
- `EMBEDDING_MODEL` 환경변수 → 법령 챗봇용 bge-m3 경로
- 보도자료/선거법은 `vectorstore.py` 내부의 `KOSROBERTA_MODEL` 상수로 별도 관리

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

**충주시 맞춤 기능**:
- 부서명 자동 인식 (50개 부서)
- 읍면동 자동 인식 (25개 지역)
- 충주시 용어 사전 적용

---

### 12. 업무보고 생성기 (ReportWriter)
**경로**: `/report-writer`
**페이지**: `ReportWriter.jsx`
**라우터**: `routers/report_writer.py`

**기능**:
1. 업무보고 섹션 자동 생성
2. 섹션별 스타일 차별화
3. 5가지 문체 스타일 자동 적용

**섹션별 스타일**:

| 스타일 | 대상 섹션 | 특징 |
|-------|---------|------|
| **서술형** | 추진배경, 현황, 문제점, 사업개요 | 2~3문장 상세 기술 |
| **나열형** | 추진일정, 소요예산, 협조사항, 참석자 | "항목: 내용" 형태 |
| **효과형** | 기대효과, 추진목표, 주요성과 | 정량+정성 효과 |
| **방안형** | 추진계획, 세부내용, 개선대책 | 구체적 실행방안 |
| **분석형** | 현상진단, 문제분석, 시사점 | 데이터 기반 분석 |

**API 엔드포인트**:
| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/report-writer/generate` | 업무보고 생성 |
| GET | `/api/report-writer/templates` | 템플릿 목록 |

---

### 13. 사업 타임라인 생성기 (TimelinePlanner)
**경로**: `/timeline`
**페이지**: `TimelinePlanner.jsx`
**라우터**: `routers/timeline_planner.py` (v5)

**기능**:
1. GPT 기반 자동 일정 추천 (4단계: 계획→계약→시행→완료)
2. 간트차트 시각화 (미리보기)
3. 단계별 세부 업무(TODO) 자동 생성 (바 클릭 시 펼쳐보기)
4. 법령 챗봇 연동으로 사전절차/법적 근거 자동 검색
5. 계약 방식별 절차 자동 반영
6. 예산 규모별 법정 의무사항 자동 판단
7. 시행 단계 2회 호출 세부 분해
8. 다중 포맷 내보내기 (PNG, XLSX+세부업무, PPTX)

**4단계 구조**:

| 단계 | 색상 | 법령 챗봇 | GPT | 주요 내용 |
|------|------|----------|-----|----------|
| 계획 | 보라 | ✅ | ✅ | 기본계획 수립, 사전 심의/검토, 일상감사, 투자심사 |
| 계약 | 파랑 | ✅ | ✅ | 계약방식별 절차, 입찰공고, 적격심사, 제안평가 |
| 시행 | 초록 | ❌ | ✅ | 사업 내용 기반 작업 분해 (공종, 개발단계 등) |
| 완료 | 주황 | ✅ | ✅ | 준공검사, 정산, 하자보증 + 사업유형별 마무리 |

**API 엔드포인트**:

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/timeline/suggest` | GPT 자동 일정 추천 |
| POST | `/api/timeline/detail-tasks` | 단계별 세부 업무 생성 (법령 연동) |
| POST | `/api/timeline/export` | 내보내기 (PNG/XLSX/PPTX) |
| GET | `/api/timeline/project-types` | 사업 유형 목록 (10개) |
| GET | `/api/timeline/contract-types` | 계약 방식 목록 (6개) |
| GET | `/api/timeline/categories` | 단계 카테고리 목록 |
| GET | `/api/timeline/status` | 기능 상태 확인 |

**입력 필드**:
- 사업명 (필수)
- 사업 설명 (선택) — GPT가 세부 업무에 반영
- 사업 유형 (선택) — 건설/토목, 정보화/시스템, 용역/연구, 행사/축제 등 10개
- 예산 규모 (선택) — 금액별 법정 의무사항 판단
- 계약 방식 (선택) — 수의계약, 소액수의, 제한경쟁(적격심사), 제한경쟁(협상), 일반경쟁, 긴급계약
- 완료 목표 (선택) — 지정 시 반드시 준수

**법령 챗봇 연동 방식**:
```
타임라인 생성기 → httpx로 /api/law-chatbot/ask 내부 호출
                 → 사업유형별 핀포인트 질의 (LAW_QUERIES_BY_TYPE 매핑)
                 → 법령 검색 결과를 GPT 프롬프트에 컨텍스트로 주입
                 → GPT가 법적 근거 포함한 세부 업무 생성
```

**사업유형별 법령 질의 매핑 (예시)**:
```python
# 정보화사업 + 계획 단계
"전자정부법 정보화사업 보안성 검토 대상 기준"
"소프트웨어산업진흥법 소프트웨어사업 과업심의 대상 금액"
"지방자치단체 정보화 사전협의 대상 및 절차"
"전자정부법 시행령 정보시스템 감리 의무 대상 금액"
"개인정보보호법 개인정보 영향평가 대상 기준"

# 건설공사 + 계획 단계
"건설기술진흥법 설계의 경제성 검토 대상 금액"
"환경영향평가법 소규모 환경영향평가 대상"
"건설기술진흥법 안전관리계획 수립 대상"
```

**시행 단계 2회 호출 프로세스**:
```
1차 호출: 사업 유형별 세부 공정 예시를 참고하여 큰 공정 분해
    ↓
결과가 5개 이하?
    → Yes → 2차 호출: 각 공정을 2~4개 세부 작업으로 재분해
    → No → 1차 결과 사용
```

**일정 산출 기간 기준 (지방계약법 기반)**:
- 입찰공고: 일반 7일, 협상 10~40일(금액별), 긴급 5일
- 적격심사: 서류제출 후 7일 이내
- 제안서 평가: 1~2주
- 계약 체결: 낙찰 후 7~10일
- 준공검수: 1~2주
- 대가 지급: 검수 후 14일 이내

**XLSX 내보내기 구조**:
- 시트1: 간트차트 (월별 색상 바)
- 시트2: 세부업무(TODO) — 단계, 구분, 순서, 업무명, 소요기간, 설명, 법적 근거, 필수, 참고사항

**Dockerfile 한글 폰트**:
```dockerfile
RUN apt-get update && apt-get install -y \
    gcc g++ fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
```
PNG 내보내기 시 Noto Sans CJK 한글 폰트 사용

**main.py 등록**:
```python
from routers import timeline_planner
app.include_router(timeline_planner.router)  # prefix 없이 (라우터 내부에 /api/timeline 포함)
```

**requirements.txt 추가 항목**:
```
Pillow>=10.0.0
python-pptx>=0.6.21
httpx
```

---

### 14. 재난상황 단톡 대시보드 (Disaster Dashboard) — v7.1 🆕

**경로**: `/disaster-upload`, `/disaster-dashboard`, `/disaster-incidents`, `/disaster-report`

**페이지**:
- `DisasterUpload.jsx` (시작점)
- `DisasterDashboard.jsx`
- `DisasterIncidents.jsx`
- `DisasterDailyReport.jsx`

**라우터**: `routers/disaster_dashboard.py`

상세 명세는 [재난상황 단톡 대시보드 (Version 7.1)](#재난상황-단톡-대시보드-version-71) 섹션 참조.

---

## 출장보고 생성기

### 개요
**GPT Vision API**를 활용하여 현장 사진(필수) + 출장 기본자료 HWPX(선택)를 업로드하면 AI가 자동으로 분석하여 **공문서 형식의 출장보고서**를 생성하는 기능

**경로**: `/trip-report`
**페이지**: `TripReport.jsx`
**라우터**: `routers/trip_report.py`

### 핵심 기능

| 기능 | 설명 |
|------|------|
| **2단계 분석** | 1차 분류(low detail, 비용절감) → 2차 추출(high detail, 정확도) |
| **8가지 보고서 유형** | 회의참석, 벤치마킹, 교육연수, 설명회참석, 조사연구, 시설점검, 민원현장, 환경점검 |
| **HWPX 기본자료 지원** | 설명회·벤치마킹 배포자료 첨부 → 행사명·일시·내용 정확도 향상 |
| **유형 변경 시 재분석** | `force_report_type` 파라미터로 Vision API 재호출 |
| **공문서 문체 자동 생성** | 경어체 금지, 단어형 종결 강제 |
| **문체 자동 교정** | 생성 후 경어체 감지 시 자동 재작성 |

### 보고서 유형별 필드 및 마지막 항목

| 유형 | 아이콘 | 필드 | 4번 항목명 |
|------|--------|------|-----------|
| 회의참석 | 🤝 | 회의명, 일시, 장소, 주최기관, 참석자 | 협의결과 |
| 벤치마킹 | 🏢 | 방문목적, 일시, 방문기관, 담당자 | 우리시 적용방안 |
| 교육연수 | 📚 | 교육명, 일시, 장소, 주관기관, 교육내용 | 적용방안 |
| 설명회참석 | 🎤 | 행사명, 일시, 장소, 주최, 참석인원 | 발표내용 요약 |
| 조사연구 | 🔍 | 조사목적, 일시, 조사지역, 조사항목 | 검토의견 및 우리시 반영사항 |
| 시설점검 | 🏗️ | 점검위치, 점검대상, 발견사항, 위험도 | 조치계획 |
| 민원현장 | 🚨 | 민원위치, 민원유형, 현장상황, 조치결과 | 재발방지 대책 |
| 환경점검 | 🌳 | 점검위치, 점검항목, 측정결과, 적합여부 | 조치계획 |

> ⚠️ 설명회참석의 4번 항목은 `"발표내용 요약"` — 보고서 구조 2번 `"주요 내용"`과 명칭 충돌 방지를 위해 의도적으로 다르게 설정

### 공문서 문체 규칙

```
[단어형 종결 - 핵심 규칙]
✅ 사용: "논의 예정", "검토 완료", "추진 계획", "수거 완료"
❌ 금지 (~임/~함/~됨): "논의할 예정임", "검토됨", "추진함"
❌ 금지 (경어체): ~합니다, ~입니다, ~했습니다, ~드립니다

[공문서 표현]
✅ 사용: "상기", "금번", "향후", "조속히", "~에 관한 사항"
❌ 피함: "~것 같습니다", "많이", "빨리"
```

### 예시 비교

| 항목 | ❌ 나쁜 예 | ✅ 좋은 예 |
|------|----------|----------|
| 종결 | "논의할 예정임" | "논의 예정" |
| 종결 | "검토됨" | "검토 완료" |
| 경어 | "앞으로 개선하겠습니다" | "3월 중 관련 부서 협의 후 결정" |
| 경어 | "쓰레기를 치웠습니다" | "방치쓰레기 120kg 수거 완료" |

### HWPX 기본자료 처리 흐름

```python
# _extract_hwpx_text() 함수
HWPX(ZIP) → zipfile 압축 해제 → lxml XML 파싱
    → <t> 태그 텍스트 추출 (fwSpace → 공백 처리 포함)
    → 6,000자 초과 시 자동 잘라내기 (토큰 절약)
    → 분류 프롬프트: [기본자료] 앞 1,000자 참고
    → 추출 프롬프트: [기본자료] 전체 참고 (행사명·일시 우선 매핑)
    → generate-report: [출장 기본자료] 섹션으로 전달
```

### API 엔드포인트

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/trip-report/analyze-images` | 사진+HWPX 분석 (Vision API) |
| POST | `/api/trip-report/generate-report` | 보고서 생성 (GPT-5-mini) |
| GET | `/api/trip-report/report-types` | 보고서 유형 목록 |

**analyze-images Form 파라미터**:

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `images` | List[UploadFile] | ✅ | 현장 사진 (최대 10장) |
| `hwpx_file` | UploadFile | ❌ | 출장 기본자료 HWPX (최대 20MB) |
| `reporter_name` | str | ❌ | 보고자 이름 |
| `reporter_dept` | str | ❌ | 보고자 부서 |
| `force_report_type` | str | ❌ | 유형 강제 지정 |

**generate-report 추가 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `hwpx_text` | str | analyze-images 응답에서 받은 HWPX 추출 텍스트 |

### 기술 구현

```python
# 모델 설정
ANALYSIS_MODEL = "gpt-5.1-chat-latest"  # Vision 분석 (temperature 제한 있음)
REPORT_MODEL   = "gpt-5-mini"           # 보고서 생성 (temperature=1.0)
MAX_HWPX_TEXT_CHARS = 6000              # 프롬프트 토큰 제한

# 2단계 분석 프로세스
1) 분류 (low detail): 유형 판단 → 비용 절감 + HWPX 앞 1,000자 참고
2) 추출 (high detail): 상세 정보 추출 → 정확도 + HWPX 전체 참고

# 안정화 3종 세트
1) response_format(json_schema) 시도 → 실패 시 일반 JSON 파싱
2) temperature 미지원 모델 자동 감지 → 파라미터 제거 후 재시도
3) main_content 타입 보정 → 문자열/글자쪼개짐 → 리스트로 변환
```

### 프론트엔드 흐름

```
Step 1: 자료 업로드
    - 현장 사진 (필수, 드래그앤드롭, 최대 10장)
    - HWPX 기본자료 (선택, 드래그앤드롭)
    ↓
Step 2: AI 분석 결과 확인/수정
    - 보고서 유형 변경 가능 (→ Vision 재분석, 경고 팝업)
    - 추출된 정보 편집 가능
    - 주요 내용 추가/삭제 가능
    - HWPX 첨부 시 "기본자료 반영" 뱃지 표시
    ↓
Step 3: 보고서 생성/복사/다운로드
    - 내용 없을 시 fallback UI 표시 (빈 화면 방지)
```

---

## 공공데이터 검증기

### 개요
CSV/Excel 파일을 업로드하면 **공공데이터 제공표준**에 따라 자동으로 검증하고 오류를 리포트하는 기능

**경로**: `/data-validator`
**페이지**: `DataValidator.jsx`
**라우터**: `routers/data_validator.py`

### 표준 데이터
- **300개 공공데이터 표준** (`backend/data/public_data_standards.json`)
- 각 표준별 필드명, 데이터타입, 허용값, 필수여부 정의

### 검증 항목

#### 1. 형식 검증

| 검증 항목 | 규칙 | 예시 |
|----------|------|------|
| 날짜 (YYYY-MM-DD) | 정확히 매치 | ✅ 2026-01-31 / ❌ 2026/01/31 |
| 년월 (YYYY-MM) | 정확히 매치 | ✅ 2026-01 / ❌ 202601 |
| 시간 (HH:MM) | 1~2자리:2자리 | ✅ 14:30, 9:00 |
| 전화번호 | 다양한 형식 허용 | ✅ 043-850-5963 |
| 휴대폰 번호 | **차단** (개인정보) | ❌ 010-1234-5678 |
| 좌표 (위도/경도) | 소수점 6~10자리 | ✅ 36.970619 / ❌ 36.97 |

#### 2. 내용 검증

| 검증 항목 | 규칙 | 예시 |
|----------|------|------|
| 허용값 체크 | 엄격 매칭 | "1" → "01"로 수정 필요 안내 |
| 조건부 필수 | 패턴 4가지 처리 | "도로종류가 '고속국도'인 경우 필수" |
| 중복 행 검사 | 전체 컬럼 기준 | 중복 행 개수 및 위치 표시 |
| Y/N 체크 | Y 또는 N만 허용 | ❌ "예", "Yes" |

#### 3. 특수 규칙

| 검증 항목 | 규칙 |
|----------|------|
| 줄바꿈 금지 | 셀 내 `\n`, `\r` 포함 시 오류 |
| 특수문자 제한 | `?!@#$%^&*` 등 포함 시 경고 |
| 천단위 콤마 금지 | 숫자 필드에 "20,000" → "20000" |
| N/단위 형식 | "889명" → 단위 제거 필요 (숫자만) |

#### 4. 주소 검증

| 검증 항목 | 규칙 |
|----------|------|
| 도로명 주소 | "~로" 또는 "~길" + 번호 포함 |
| 지번 주소 | "~동/면/리" + 번지 형식 |
| 주소 ↔ 좌표 | 주소 있으면 좌표 필수 (조건부) |

### 조건부 필수 패턴 (4가지)

```python
# 패턴 1: "A가 'X', 'Y'인 경우 필수"
"도로종류가 '고속국도', '일반국도'인 경우 필수"

# 패턴 2: "A가 'X'인 경우에만 필수"
"구분이 '유료'인 경우에만 필수"

# 패턴 3: "A값이 있는 경우 필수"
"도로명주소 값이 있는 경우 좌표 필수"

# 패턴 4: "A 입력 시 필수"
"상세주소 입력 시 우편번호 필수"
```

### API 엔드포인트

| 메서드 | 경로 | 설명 |
|-------|------|------|
| GET | `/api/data-validator/standards` | 표준 목록 조회 (검색/필터) |
| GET | `/api/data-validator/standards/{code}` | 표준 상세 조회 |
| POST | `/api/data-validator/validate` | 파일 검증 실행 |
| POST | `/api/data-validator/validate-custom` | 커스텀 규칙 검증 |

### 검증 결과 형식

```json
{
  "success": true,
  "summary": {
    "total_rows": 100,
    "error_count": 5,
    "warning_count": 12,
    "duplicate_count": 2
  },
  "errors": [
    {
      "type": "error",
      "field": "위도",
      "row": 15,
      "msg": "좌표 소수점 자릿수 부족",
      "detail": "15행: \"36.97\" (6자리 이상 필요)"
    }
  ],
  "warnings": [...]
}
```

### 프론트엔드 흐름

```
1. 표준 선택 (검색/카테고리 필터)
    ↓
2. 파일 업로드 (CSV/Excel, 드래그앤드롭)
    ↓
3. 검증 실행 → 결과 표시
    - 오류/경고 개수 요약
    - 필드별 오류 목록
    - 행 번호, 상세 메시지
    ↓
4. 결과 다운로드 (선택)
```

---

## 게시판 시스템

### 개요
소통공간으로 3개의 게시판 제공

### 게시판 종류
| 게시판 | 경로 | 글쓰기 권한 | 특징 |
|-------|------|------------|------|
| 공지사항 | `/board/notice` | 관리자만 | 중요 안내사항 |
| 자료실 | `/board/archive` | 관리자만 | 파일 첨부 지원 |
| 묻고답하기 | `/board/qna` | 모든 사용자 | 관리자 답변 기능 |

### 게시판 API
| 메서드 | 경로 | 설명 |
|-------|------|------|
| GET | `/api/board/list/{board_type}` | 게시글 목록 (페이지네이션) |
| GET | `/api/board/detail/{board_id}` | 게시글 상세 |
| POST | `/api/board/create` | 게시글 작성 |
| POST | `/api/board/create-with-file` | 파일 첨부 게시글 작성 |
| PUT | `/api/board/update/{board_id}` | 게시글 수정 |
| DELETE | `/api/board/delete/{board_id}` | 게시글 삭제 |
| POST | `/api/board/answer/{board_id}` | QnA 답변 작성 (관리자) |
| DELETE | `/api/board/answer/{answer_id}` | 답변 삭제 (관리자) |

### 파일 업로드
- **Storage 버킷**: `boards`
- **파일명 처리**: UUID로 변환 (한글 파일명 지원)
- **원본 파일명**: DB에 별도 저장

---

## 프롬프트 중앙 관리 시스템

### 개요 (v6.0.0~)

Supabase DB에 프롬프트를 저장하고, 관리자 페이지에서 재배포 없이 수정 가능한 시스템.

### 핵심 동작 원리

**3단계 폴백**:
```
1. prompt_service.get(feature, prompt_key, default=...)
        ↓
2. 메모리 캐시 hit?
   ├─ Yes → DB 값 반환 ([PROMPT] DB used)
   └─ No  → 캐시 TTL 5분 만료 시 DB 재로드 시도
        ↓
3. 재로드 후에도 없으면? → default 값 반환 ([PROMPT] FALLBACK used)
```

### 호출 시그니처

```python
from services.prompt_service import prompt_service

# 동기 메서드 (캐시 + 폴백)
prompt = prompt_service.get(feature: str, prompt_key: str, default: Optional[str]) -> Optional[str]

# 변수 치환은 호출측에서 .format() 적용
prompt = prompt_service.get("press_release", "system_prompt", default=_DEFAULT)
filled = prompt.format(department="자치행정과", manager="김태균")
```

### 관리자 API

| 메서드 | 경로 | 설명 |
|-------|------|------|
| GET | `/api/prompts/features` | 11개 기능 메타데이터 |
| GET | `/api/prompts/list` | 전체 프롬프트 목록 (관리자 전용) |
| GET | `/api/prompts/by-feature/{feature}` | 기능별 프롬프트 |
| PUT | `/api/prompts/update` | 프롬프트 수정 + 이력 저장 |
| POST | `/api/prompts/history` | 변경 이력 조회 |
| POST | `/api/prompts/refresh-cache` | 캐시 강제 갱신 |

### v7.1 추가 사항 🆕

**`disaster_report` feature 추가 (3개 프롬프트)**:
- `system_prompt` — 일일보고 시스템 프롬프트 (공문서 문체, 경어체 금지, PII 보호 원칙)
- `summary_prompt` — 상단 한 문장 요약 (100자 이내)
- `body_prompt` — 5개 섹션 본문 (총괄, 유형별, 조치상황, 주요사건, 향후계획)

**시드 SQL**: `backend/scripts/seed_disaster_prompts.sql`
- `ON CONFLICT DO UPDATE`로 재실행 안전
- 시드 안 돌려도 `_DEFAULT_*` 상수로 폴백 작동

---

## 재난상황 단톡 대시보드 (Version 7.1)

### v7.0 → v7.1 변경 요약

| 영역 | v7.0 | v7.1 |
|------|------|------|
| 사건 그룹핑 | `(emd, location, type)` 정적 키 | **상태 흐름 기반** (`closed` 만나면 종결) |
| 위치 매칭 | 문자열 80자 prefix 일치 | **유사도 80% 이상** (`SequenceMatcher`) |
| incident_type | 첫 메시지 기준 고정 | **다수결 재계산** (inspection 우선순위 낮춤) |
| status 분류 | `~예정`이 `in_progress`에 섞임 | **`~예정`은 `reported`로 분리** |
| 날짜 포맷 | 한글형/점형만 | + **구분선형**, **대괄호형** |
| 위치 정리 | 대괄호 `[]`만 제거 | **다양한 괄호** 일괄 제거 |
| 응답 메시지 필터 | 정확 일치 | **정규식 기반** (`네~`, `넵`, `확인했습니다` 등) |
| analyze 동시성 | 락 없음 | **`analysis_status` 기반 락** (409 Conflict) |
| 빈 배열 처리 | `.insert([])` 호출 시 에러 | **빈 배열 가드** |
| 로깅 | `print()` (PII dict 통째 출력) | **`logging` 모듈** (id/count만) |
| 일일보고 | 템플릿 기반 고정 문장 | **GPT-4o 자연어** + 템플릿 폴백 |
| 라벨 상수 | 4곳 중복 정의 | **단일 소스** (백엔드/프론트 각각) |
| sessionStorage | 렌더 중 직접 호출 | **`useDisasterSession` 훅** |

### 기능

1. 카카오톡 재난상황 단체대화 txt 업로드
2. 원본 메시지 파싱 및 저장
3. 메시지 단위 → 사건 단위 재구성 (상태 흐름 기반)
4. 유형/상태/읍면동/위치 자동 분류
5. 사건 목록 시각화
6. 읍면동별/유형별/상태별 대시보드 제공
7. **GPT-4o 자연어 일일보고서 자동 생성** 🆕
8. 기존 업로드 목록은 사용자 화면에 미노출 (sessionStorage 기반)

### 백엔드 서비스 분리

| 서비스 파일 | 역할 |
|------------|------|
| `services/disaster_constants.py` 🆕 | 라벨 상수 (`INCIDENT_TYPE_LABELS`, `STATUS_LABELS`), `incident_label()`, `status_label()` |
| `services/disaster_parser_service.py` | 카카오톡 txt 파싱, 메시지 분류, 위치/유형/상태 추론 |
| `services/disaster_incident_service.py` | 메시지 → 사건 재구성 (상태 흐름 기반 그룹핑) |
| `services/disaster_report_service.py` | 일일보고서 생성 (GPT-4o + 폴백) |

### 사건 그룹핑 로직 (v7.1 핵심)

#### 상태 흐름 기반 그룹핑

```text
[타임라인 예시]
7/15 용산동 천변산책로 출입통제       → 사건 A 시작 (in_progress)
7/16 용산동 천변산책로 통제 유지       → 사건 A에 병합
7/22 용산동 천변산책로 통제 해제       → 사건 A 종결 (status=closed, _closed=True)
─────────────────────────────────────
8/10 용산동 천변산책로 출입통제       → 사건 B 시작 (closed 이후 새 사건)
8/12 용산동 천변산책로 통제 해제       → 사건 B 종결
```

**규칙**:
1. 활성 사건 리스트 (`active_incidents`)에 `_closed` 플래그로 종결 여부 추적
2. 새 메시지가 오면 활성 사건 중 `(emd 동일, type 호환, location 유사도 ≥ 0.80)` 매칭 시도
3. 매칭되면 병합, 없으면 신규 사건
4. 메시지 status가 `closed`면 해당 사건 `_closed=True` (이후 매칭 대상에서 제외)
5. 사진 메시지는 직전 활성 사건에 부착

#### 위치 유사도 매칭

```python
from difflib import SequenceMatcher

def _location_similarity(a, b):
    # 정규화 (괄호/공백/특수문자 제거)
    na = _normalize_location(a)
    nb = _normalize_location(b)
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()

LOCATION_SIMILARITY_THRESHOLD = 0.80
```

→ "용산동 천변산책로" ≈ "용산동 천변 산책로" (유사도 0.95) → 동일 위치로 병합

#### incident_type 다수결 재계산

첫 메시지가 `inspection`(분류 불가)이어도 후속 메시지의 실제 유형으로 다수결 재계산.

```python
def _recalculate_incident_type(msgs):
    types = [m.incident_type for m in msgs if m.message_type == "normal"]
    non_inspection = [t for t in types if t != "inspection"]
    if non_inspection:
        return Counter(non_inspection).most_common(1)[0][0]
    return "inspection"
```

### 파서 정교화 (v7.1)

#### 날짜 포맷 커버리지

| 포맷 | 예시 | 처리 방식 |
|------|------|----------|
| 한글형 (연도 포함) | `2025년 7월 15일 오후 3:30,홍길동 : 메시지` | `MESSAGE_RE_KOR` |
| 점형 (연도 포함) | `2025. 7. 15. 오후 3:30,홍길동 : 메시지` | `MESSAGE_RE_DOT` |
| 구분선형 🆕 | `--------- 2025년 7월 15일 월요일 ---------` | `current_date` 추출 후 보관 |
| 대괄호형 (연도 없음) 🆕 | `[홍길동] [오후 3:30] 메시지` | `current_date` + `MESSAGE_RE_BRACKET` |
| 단독 시각줄 | `2025년 7월 15일 오후 3:30` | 스킵 (`TIME_HEADER_RE`) |
| 단독 날짜줄 | `2025년 7월 15일` | `current_date` 추출 후 스킵 |
| 시스템 메시지 | `홍길동님이 들어왔습니다` | 경계만 인식, content 무시 |

#### 상태 분류 정교화

```python
STATUS_RULES = [
    (re.compile(r"해제|통행재개|개통"), "closed"),
    (re.compile(r"복구 완료|처리 완료|...|완료했습니다"), "completed"),
    (re.compile(r"조치중|작업중|진행중|...|처리 중"), "in_progress"),
    (re.compile(r"이상없음|이상 없습니다"), "no_issue"),
    (re.compile(r"모니터링|상황관리|예찰강화"), "monitoring"),
    (re.compile(r"예정"), "reported"),  # 🆕 예정 계열은 reported로 분리
]
```

**v7.0 → v7.1 차이**:
- v7.0: `보수예정`, `정비예정`이 `in_progress`로 잡힘 → 과대계상
- v7.1: `~예정` 명시적 패턴으로 `reported`에 분리

#### 응답 문구 필터 (정규식)

```python
# v7.0: 정확 일치만 필터링
if text in ["네", "감사합니다", "고맙습니다", "확인"]:
    return False

# v7.1: 정규식으로 변형 흡수
if len(text) <= 8 and re.match(
    r"^(네\.?|넵\.?|확인\.?|확인했습니다\.?|감사|고맙|수고|굿|ㅇㅋ|ok)",
    text, re.IGNORECASE
):
    return False
```

### analyze 락 (v7.1)

#### 동시성 제어

```python
# 1. 락 획득
upload_res = supabase.table("disaster_uploads").select("id, analysis_status")...
if upload_res.data["analysis_status"] == "analyzing":
    raise HTTPException(409, "이미 분석 중입니다.")

supabase.table("disaster_uploads").update({"analysis_status": "analyzing"})...

# 2. 분석 수행 (try/except로 감쌈)
try:
    return _run_analysis(...)
except HTTPException:
    # 명시적 예외는 이전 상태로 복원
    supabase.update({"analysis_status": prev_status})...
    raise
except Exception:
    # 일반 예외는 failed 마킹
    supabase.update({"analysis_status": "failed"})...
    raise HTTPException(500, ...)

# 3. 성공 시 analyzed로 변경
supabase.update({"analysis_status": "analyzed"})...
```

#### `analysis_status` 값 목록

| 값 | 의미 |
|---|---|
| `uploaded` | 파일 업로드 후, 분석 전 |
| `analyzing` | 분석 진행 중 (락) |
| `analyzed` | 분석 완료 |
| `parse_failed` | 파일 파싱 단계 실패 |
| `failed` | 분석 단계 실패 |

#### 빈 배열 가드

```python
inserted_incidents = []
if incident_rows:  # 🆕 빈 배열일 때 .insert([]) 호출 방지
    res = supabase.table("disaster_incidents").insert(incident_rows).execute()
    inserted_incidents = res.data or []
```

### 일일보고서 GPT 자연어화 (v7.1)

#### 호출 흐름

```
사용자가 "보고서 생성" 클릭
  ↓
POST /api/disaster/reports/daily/generate (async)
  ↓
await generate_daily_report(report_date, incidents)  ← 비동기
  ↓
[1] prompt_service.get() × 3 (system_prompt, summary_prompt, body_prompt)
  ↓ (DB 미연결 시 _DEFAULT_* 폴백)
[2] OpenAIService().generate_text(model="gpt-4o", ...) × 2 (요약 + 본문)
  ↓ (실패 시 None 반환)
[3] None이면 _generate_fallback_summary / _generate_fallback_body 사용
  ↓
DB insert (disaster_daily_reports)
  ↓
응답 반환
```

#### `OpenAIService` 변경 (v7.1)

```python
async def generate_text(
    self,
    prompt: str,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    system_prompt: str = "...",
    model: Optional[str] = None,  # 🆕 v7.1 추가
) -> str:
    response = await self.client.chat.completions.create(
        model=model or self.model,  # override 가능
        ...
    )
```

→ 기존 호출부는 영향 없음. 재난보고만 `model="gpt-4o"` 명시 override.

#### 폴백 체인 (3중 안전망)

```
1차: prompt_service (DB) + GPT-4o
2차: prompt_service 실패 시 → _DEFAULT_* 상수 + GPT-4o
3차: GPT 호출 실패 시 → 템플릿 기반 폴백 (기존 v7.0 방식)
```

→ 어떤 컴포넌트가 실패해도 보고서는 생성됨 (서비스 중단 없음)

#### PII 보호

GPT 프롬프트와 폴백 템플릿 모두에서 **보고자 이름(`reporter_name`) 미포함**. 시스템 프롬프트에도 "개인정보(보고자 이름) 노출 금지" 명시.

### 프론트엔드 리액티브 세션 (v7.1)

#### 문제 (v7.0)

```jsx
// ❌ 렌더 중 sessionStorage 직접 호출 → React가 재평가 안 함
const activeUploadId = sessionStorage.getItem("disaster_active_upload_id");
```

→ 업로드 페이지에서 새 파일 올린 후 대시보드로 이동해도 stale 값 유지 (SPA 라우팅이라 컴포넌트 unmount 안 되면 발생)

#### 해결 (v7.1)

**`constants/disaster.js`**:
```js
export const DISASTER_SESSION_EVENT = "disaster-session-changed";

export function setDisasterSession(uploadId, fileName) {
  sessionStorage.setItem(...);
  window.dispatchEvent(new Event(DISASTER_SESSION_EVENT));  // 🆕 커스텀 이벤트
}
```

**`hooks/useDisasterSession.js`**:
```js
export function useDisasterSession() {
  const [session, setSession] = useState(getDisasterSession());

  useEffect(() => {
    const refresh = () => setSession(getDisasterSession());

    window.addEventListener(DISASTER_SESSION_EVENT, refresh);  // 같은 탭 내
    window.addEventListener("focus", refresh);                  // 탭 전환 복귀
    window.addEventListener("storage", refresh);                // 다른 탭

    return () => { /* cleanup */ };
  }, []);

  return { uploadId: session.uploadId, fileName: session.fileName };
}
```

**페이지에서 사용**:
```jsx
// ✅ 리액티브
const { uploadId: activeUploadId, fileName: activeFileName } = useDisasterSession();

useEffect(() => {
  loadOverview();
}, [activeUploadId]);  // 🆕 의존성 배열로 자동 재조회
```

#### 라벨 상수 단일 소스

**`frontend/src/constants/disaster.js`**:
```js
export const INCIDENT_TYPE_LABELS = { road_control: "도로통제", ... };
export const STATUS_LABELS = { reported: "발생", ... };
export const incidentLabel = (code) => INCIDENT_TYPE_LABELS[code] || code || "미분류";
export const statusLabel = (code) => STATUS_LABELS[code] || code || "미분류";
```

→ 각 페이지에서 `import { incidentLabel, statusLabel } from "../constants/disaster"`
→ 라벨 변경 시 한 곳만 수정 (백엔드 `disaster_constants.py`와 함께 양쪽 업데이트 필요)

### 핵심 구현 포인트 (v7.1)

- 한글 날짜형 / 점(.) 날짜형 / 구분선형 / 대괄호형 카카오톡 txt 동시 지원
- `저장한 날짜`, 날짜 헤더, 단독 시각줄 스킵 처리
- 시스템 메시지(초대/입장/퇴장) 경계 인식
- `backend/data/eup_myeon_dong.txt` 기반 읍면동 분류 강화
- `읍면동 + 장소명` 조합 방식으로 위치 추출 보강
- 내부 분류 코드는 영어 유지, 사용자 화면은 한글 라벨로 표시
- `inspection`은 화면상 `기타/미분류`로 표기
- 사진 메시지는 **직전 사건**에 부착
- 현재 세션에서 업로드한 파일만 `sessionStorage` + 커스텀 이벤트로 관리 (v7.1 리액티브)

### 유형 분류 코드 / 화면 라벨

| 내부 코드 | 화면 표시 |
|----------|----------|
| `road_control` | 도로통제 |
| `landslide` | 산사태·토사유출 |
| `tree_fall` | 나무전도 |
| `flood` | 침수·범람 |
| `sinkhole` | 싱크홀·노면파손 |
| `drainage` | 배수·맨홀·양수 |
| `facility` | 시설물 이상 |
| `inspection` | 기타/미분류 |

### 상태 코드 / 화면 라벨

| 내부 코드 | 화면 표시 |
|----------|----------|
| `reported` | 발생 |
| `in_progress` | 조치중 |
| `completed` | 조치완료 |
| `monitoring` | 모니터링 |
| `no_issue` | 이상없음 |
| `closed` | 해제·종결 |

> 일일보고서의 `completed_count`는 내부적으로는 `completed`와 `closed`를 분리 저장하되, **합산 표시** (`completed + closed`).

### 데이터 흐름

```text
카카오톡 txt 업로드
    ↓
disaster_uploads 저장 (analysis_status='uploaded')
    ↓
parse_kakao_txt() → disaster_raw_messages 저장
    ↓
[POST /analyze/{upload_id}]
    ↓
analysis_status = 'analyzing' (락 획득) 🆕
    ↓
build_incidents() — 상태 흐름 기반 그룹핑 + 80% 위치 유사도 🆕
    ↓
disaster_incidents / disaster_incident_messages 저장
    ↓
analysis_status = 'analyzed' (락 해제) 🆕
    ↓
[POST /reports/daily/generate]
    ↓
generate_daily_report() — GPT-4o + prompt_service (폴백 3중) 🆕
    ↓
disaster_daily_reports 저장
```

---

## API 엔드포인트

### 전체 API 목록

#### Health Check
```
GET /api/health
→ {"status": "healthy"}
```

#### Auth (인증)
```
POST /api/auth/signup          # 회원가입
POST /api/auth/verify-otp      # OTP 검증
POST /api/auth/resend-otp      # OTP 재발송
POST /api/auth/login           # 로그인
POST /api/auth/logout          # 로그아웃
GET  /api/auth/verify          # 토큰 검증
GET  /api/auth/me              # 현재 사용자 정보
POST /api/auth/refresh         # 토큰 갱신
```

#### Board (게시판)
```
GET    /api/board/list/{type}        # 게시글 목록
GET    /api/board/detail/{id}        # 게시글 상세
POST   /api/board/create             # 게시글 작성
POST   /api/board/create-with-file   # 파일 첨부 작성
PUT    /api/board/update/{id}        # 게시글 수정
DELETE /api/board/delete/{id}        # 게시글 삭제
POST   /api/board/answer/{id}        # 답변 작성
DELETE /api/board/answer/{id}        # 답변 삭제
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

#### Law Chatbot (법령·자치법규)
```
POST /api/law-chatbot/ask
POST /api/law-chatbot/search
GET  /api/law-chatbot/status
GET  /api/law-chatbot/categories
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

#### Report Writer (업무보고)
```
POST /api/report-writer/generate
GET  /api/report-writer/templates
```

#### Trip Report (출장보고)
```
POST /api/trip-report/analyze-images
POST /api/trip-report/generate-report
GET  /api/trip-report/report-types
```

#### Data Validator (공공데이터 검증)
```
GET  /api/data-validator/standards
GET  /api/data-validator/standards/{code}
POST /api/data-validator/validate
POST /api/data-validator/validate-custom
```

#### Timeline Planner (사업 타임라인)
```
POST /api/timeline/suggest           # AI 자동 일정 추천
POST /api/timeline/detail-tasks      # 세부 업무 생성 (법령 연동)
POST /api/timeline/export            # 내보내기 (PNG/XLSX/PPTX)
GET  /api/timeline/project-types     # 사업 유형 목록
GET  /api/timeline/contract-types    # 계약 방식 목록
GET  /api/timeline/categories        # 단계 카테고리 목록
GET  /api/timeline/status            # 기능 상태
```

#### Prompt Manager (프롬프트 관리)
```
GET  /api/prompts/features           # 기능 메타데이터
GET  /api/prompts/list               # 전체 목록 (관리자)
GET  /api/prompts/by-feature/{f}     # 기능별 프롬프트
PUT  /api/prompts/update             # 프롬프트 수정
POST /api/prompts/history            # 변경 이력
POST /api/prompts/refresh-cache      # 캐시 강제 갱신
```

#### Disaster Dashboard (재난상황 대시보드) v7.1 🆕
```
POST /api/disaster/upload
GET  /api/disaster/uploads
POST /api/disaster/analyze/{upload_id}              # 🆕 async + 409 Conflict (락)
GET  /api/disaster/upload/{upload_id}/summary
GET  /api/disaster/incidents
GET  /api/disaster/incidents/{incident_id}
GET  /api/disaster/dashboard/overview
POST /api/disaster/reports/daily/generate           # 🆕 async (GPT-4o)
GET  /api/disaster/reports
```

**`/analyze/{upload_id}` 응답 코드 (v7.1)**:
- `200 OK` — 분석 성공
- `404 Not Found` — 업로드 정보 없음 또는 메시지 없음
- `409 Conflict` — 이미 분석 중 (락)
- `500 Internal Server Error` — 분석 실패 (`analysis_status='failed'`로 마킹)

---

## 데이터베이스 스키마

### Supabase 테이블

#### user_profiles (사용자 프로필)
```sql
CREATE TABLE public.user_profiles (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  email TEXT,
  name TEXT,
  department TEXT,
  role TEXT DEFAULT 'user',  -- 'user' 또는 'admin'
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### boards (게시판)
```sql
CREATE TABLE public.boards (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  board_type TEXT NOT NULL,  -- 'notice', 'qna', 'archive'
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  author_id UUID REFERENCES auth.users(id),
  author_email TEXT,
  file_url TEXT,
  file_name TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  view_count INTEGER DEFAULT 0
);
```

#### board_answers (QnA 답변)
```sql
CREATE TABLE public.board_answers (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  board_id UUID REFERENCES public.boards(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  author_id UUID REFERENCES auth.users(id),
  author_email TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### news_articles
```sql
CREATE TABLE news_articles (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  url TEXT UNIQUE NOT NULL,
  published_at TIMESTAMP,
  summary TEXT,
  embedding VECTOR(384),
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### usage_logs
```sql
CREATE TABLE usage_logs (
  id SERIAL PRIMARY KEY,
  feature TEXT NOT NULL,
  user_ip TEXT,
  request_data JSONB,
  response_data JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### prompts (v6.0~)
```sql
CREATE TABLE public.prompts (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  feature TEXT NOT NULL,
  prompt_key TEXT NOT NULL,
  content TEXT NOT NULL,
  description TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(feature, prompt_key)
);
```

#### prompt_history (v6.0~)
```sql
CREATE TABLE public.prompt_history (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  prompt_id UUID REFERENCES public.prompts(id),
  feature TEXT,
  prompt_key TEXT,
  old_content TEXT,
  new_content TEXT,
  changed_by TEXT,
  changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### disaster_uploads
```sql
CREATE TABLE public.disaster_uploads (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  file_name TEXT NOT NULL,
  source_type TEXT DEFAULT 'kakao_txt',
  message_count INTEGER DEFAULT 0,
  valid_message_count INTEGER DEFAULT 0,
  incident_count INTEGER DEFAULT 0,
  analysis_status TEXT DEFAULT 'uploaded',
  -- v7.1: analysis_status 가능 값
  -- 'uploaded', 'analyzing', 'analyzed', 'parse_failed', 'failed'
  uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### disaster_raw_messages
```sql
CREATE TABLE public.disaster_raw_messages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  upload_id UUID REFERENCES public.disaster_uploads(id) ON DELETE CASCADE,
  message_time TIMESTAMP WITH TIME ZONE,
  sender_name TEXT,
  raw_text TEXT,
  message_type TEXT,
  photo_count INTEGER DEFAULT 0,
  is_system BOOLEAN DEFAULT FALSE,
  parsed_success BOOLEAN DEFAULT TRUE
);
```

#### disaster_incidents
```sql
CREATE TABLE public.disaster_incidents (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  upload_id UUID REFERENCES public.disaster_uploads(id) ON DELETE CASCADE,
  incident_time TIMESTAMP WITH TIME ZONE,
  first_report_time TIMESTAMP WITH TIME ZONE,
  last_update_time TIMESTAMP WITH TIME ZONE,
  emd TEXT,
  location_raw TEXT,
  location_normalized TEXT,
  incident_type TEXT,
  severity TEXT,
  status TEXT,
  summary TEXT,
  damage_text TEXT,
  action_text TEXT,
  related_agency TEXT,
  reporter_name TEXT,
  photo_count INTEGER DEFAULT 0,
  message_count INTEGER DEFAULT 0,
  is_reportable BOOLEAN DEFAULT TRUE
);
```

#### disaster_incident_messages
```sql
CREATE TABLE public.disaster_incident_messages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  incident_id UUID REFERENCES public.disaster_incidents(id) ON DELETE CASCADE,
  raw_message_id UUID REFERENCES public.disaster_raw_messages(id) ON DELETE CASCADE,
  relation_type TEXT
);
```

#### disaster_daily_reports
```sql
CREATE TABLE public.disaster_daily_reports (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  report_date DATE NOT NULL,
  upload_id UUID REFERENCES public.disaster_uploads(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  summary_text TEXT,
  report_text TEXT,
  total_incident_count INTEGER DEFAULT 0,
  completed_count INTEGER DEFAULT 0,
  in_progress_count INTEGER DEFAULT 0,
  created_by TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Storage Buckets
| 버킷명 | 용도 | 공개 |
|-------|------|------|
| `boards` | 게시판 첨부파일 | ✅ Public |
| `press-releases` | 보도자료 파일 | ❌ |
| `translations` | 번역 결과 파일 | ❌ |
| `data-analysis` | 업로드된 데이터 파일 | ❌ |
| `meeting-summaries` | 회의록 파일 | ❌ |

### RLS (Row Level Security)
현재 테스트 환경으로 비활성화 상태:
```sql
ALTER TABLE public.user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.boards DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.board_answers DISABLE ROW LEVEL SECURITY;
```

> ⚠️ 프로덕션 환경에서는 RLS 활성화 권장

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

#### 백엔드 (Container App)
```bash
# OpenAI
OPENAI_API_KEY=sk-proj-xxx...
OPENAI_MODEL=gpt-4o-mini  # 기본 모델 (재난보고는 gpt-4o로 override)

# Supabase
SUPABASE_URL=https://hhlelnlvprymnymvdnsn.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIs...

# Kakao
KAKAO_API_KEY=xxx...

# DeepL
DEEPL_API_KEY=xxx...

# Naver
NAVER_CLIENT_ID=xxx...
NAVER_CLIENT_SECRET=xxx...

# 법령 API (법령·자치법규 챗봇)
LAW_API_OC=storm8787
EMBEDDING_MODEL=/app/models/bge-m3

# CORS
CORS_ORIGINS=https://agreeable-smoke-0b02cf31e.2.azurestaticapps.net,http://localhost:5173

# 기타
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Azure Container Apps CORS 설정
- **허용된 원본**: `https://agreeable-smoke-0b02cf31e.2.azurestaticapps.net`
- **허용된 메서드**: `GET, POST, PUT, DELETE, OPTIONS, PATCH`
- **허용된 헤더**: `*`

### GitHub Container Registry
**이미지 저장소**: `ghcr.io/storm8787/cj-ai-backend`

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

#### 3. API 문서 확인
```
http://localhost:8000/docs        # Swagger UI
http://localhost:8000/redoc       # ReDoc
```

### 재난상황 대시보드 추가 설정 (v7.1)

#### 1. 읍면동 파일

```text
backend/data/eup_myeon_dong.txt
```

파일 형식은 한 줄에 하나씩 충주시 읍면동 명칭을 기재하는 방식.

예:
```text
교현안림동
호암직동
칠금금릉동
용산동
문화동
지현동
봉방동
달천동
목행용탄동
중앙탑면
살미면
수안보면
대소원면
주덕읍
신니면
동량면
산척면
앙성면
엄정면
소태면
노은면
```

#### 2. 프롬프트 시드 (선택, v7.1) 🆕

```bash
# Supabase SQL Editor에서 실행
backend/scripts/seed_disaster_prompts.sql
```

→ 안 돌려도 `_DEFAULT_*` 상수로 작동. 관리자 페이지에서 프롬프트 수정하려면 필수.

#### 3. 프론트엔드 디렉토리 생성 (v7.1) 🆕

```bash
mkdir -p frontend/src/constants
mkdir -p frontend/src/hooks
```

(기존에 있으면 생략)

#### 4. v7.1 적용 후 검증 🆕

```bash
# 백엔드 import 체크
cd backend
python -c "
from services.disaster_constants import incident_label, status_label
from services.disaster_parser_service import parse_kakao_txt
from services.disaster_incident_service import build_incidents
from services.disaster_report_service import generate_daily_report
print('OK: all imports')
"
```

---

## 보안 설정

### CORS 설정
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Processed-Count", "X-Total-Rows", "X-Total-Cols", "X-Errors"],
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
    ]
    # 필터링 로직
```

### PII 보호 (v7.1) 🆕

**재난 대시보드 일일보고**:
- GPT 프롬프트에 보고자 이름(`reporter_name`) 미포함
- 시스템 프롬프트에 "개인정보 노출 금지" 명시
- 폴백 템플릿에서도 보고자 이름 제거

**로깅**:
- `print()` → `logger.info()` 전환
- `id`, `count`, 단계명만 로깅 (dict 통째 출력 금지)
- `first_incident_sample` 같은 PII 포함 dict 출력 제거

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

## 트러블슈팅

### 1. CORS DELETE 오류
**증상**: DELETE 요청 시 CORS 에러

**해결**:
1. `backend/main.py`에서 `allow_methods`에 DELETE 명시
2. Azure Portal → Container Apps → CORS 설정에서 DELETE 추가

### 2. 파일 업로드 실패 (한글 파일명)
**증상**: `Invalid key` 에러

**해결**: 파일명을 UUID로 변환
```python
import uuid
safe_filename = f"{uuid.uuid4().hex}.{file_ext}"
```

### 3. Storage RLS 오류
**증상**: `new row violates row-level security policy`

**해결**:
```sql
CREATE POLICY "Allow all for boards"
ON storage.objects
FOR ALL
TO public
USING (bucket_id = 'boards')
WITH CHECK (bucket_id = 'boards');
```

### 4. isAdmin이 항상 false
**증상**: 관리자로 설정했는데 권한 인식 안 됨

**해결**: user_profiles 테이블 RLS 비활성화
```sql
ALTER TABLE public.user_profiles DISABLE ROW LEVEL SECURITY;
```

### 5. 벡터스토어 로드 실패
**증상**: `FileNotFoundError: vector_stores/press_release.faiss`

**해결**:
```bash
# 컨테이너 이미지에 벡터스토어 포함 확인
docker build -t backend .
docker run -it backend ls /app/vector_stores
```

### 6. OpenAI API 타임아웃
**증상**: `openai.error.Timeout`

**해결**:
```python
client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=60.0)
```

### 7. temperature 미지원 오류 (GPT-5.1)
**증상**: `"temperature" does not support 0.2 with this model. Only the default (1) value is supported.`

**해결**:
```python
# temperature=None 또는 1.0 사용
# _chat_create_compat() 함수로 자동 폴백 처리
```

### 8. 출장보고 main_content 글자 쪼개짐
**증상**: `["표", "나", "내", "용"]` 형태로 반환

**해결**: `_coerce_main_content()` 함수로 타입 보정
```python
if all(len(x) <= 1 for x in v):
    joined = "".join(v).strip()
    return _split_lines_like_bullets(joined)
```

### 9. 조건부 필수 유니코드 따옴표
**증상**: JSON에 `'`(U+2018), `'`(U+2019) 사용으로 파싱 실패

**해결**: `normalize_quotes()` 함수로 변환
```python
text = text.replace("'", "'").replace("'", "'")
```

### 10. 출장보고 Step3 보고서 화면 미표시
**증상**: 보고서 생성 후 Step3으로 이동하지만 내용이 비어있거나 화면 자체가 안 나옴

**원인**: `{step === 3 && generatedReport && (...)}` 조건에서 `generatedReport`가 빈 문자열이면 렌더링 차단

**해결**:
```jsx
// 수정 전
{step === 3 && generatedReport && (...)}

// 수정 후: step === 3이면 항상 렌더링, 내용 없으면 fallback UI
{step === 3 && (
  generatedReport ? (
    <textarea value={generatedReport} ... />
  ) : (
    <p>보고서 내용을 불러오지 못했습니다. 이전 단계로 돌아가 다시 생성해주세요.</p>
  )
)}
```

### 11. 출장보고 `_has_required_structure` 검증 실패
**증상**: 보고서가 정상 생성되었으나 구조 미인식으로 불필요한 재작성 발생

**원인**: 기존 코드가 `"1."`, `"2."`, `"3."`, `"4."` 형식만 인정 → `"1)"` 등 다른 표기 미인식

**해결**: 정규식으로 다양한 번호 표기 허용
```python
patterns = [r"1[.\)]", r"2[.\)]", r"3[.\)]", r"4[.\)]"]
return all(re.search(p, text) for p in patterns)
```

### 12. DeepL 번역기 500 에러 (라이브러리 버전 충돌)
**증상**: `/api/translator/translate` 500 Internal Server Error, Streamlit 환경에서는 정상 동작

**원인**: `deepl>=1.16.0` 조건으로 최신 2.x 버전 설치됨. 2.x에서 `Translator` 클래스 deprecated → 동작 불안정

**해결**: `requirements.txt`에서 버전 상한 고정
```txt
# 수정 전
deepl>=1.16.0

# 수정 후
deepl>=1.16.0,<2.0.0
```
> ⚠️ Streamlit과 FastAPI 환경의 라이브러리 버전이 다를 수 있으므로 반드시 버전 고정 필요

### 13. law.go.kr API 인코딩 깨짐
**증상**: XML 태그명이 `?먯튂踰뺢퇋?쇰젴踰덊샇` 형태로 깨짐

**원인**: 관공서 네트워크 프록시가 응답 인코딩을 변조

**해결**: `resp.text` 대신 `resp.content.decode("utf-8")` 사용
```python
# 수정 전
text = resp.text  # 깨짐

# 수정 후
text = resp.content.decode("utf-8")  # 정상
```

### 14. 법령 본문 3,000자 잘림
**증상**: 국가공무원 복무규정에서 연가일수 조문이 GPT에 전달 안 됨

**원인**: 본문 전체(25,336자)를 앞에서 3,000자만 잘라서 전달 → 연가 관련 조문(6,520자 위치)이 누락

**해결**: 질문 관련 조문만 키워드 매칭으로 필터링 (최대 8,000자)

### 15. bge-m3 모델 메모리 부족 (Azure 503)
**증상**: `/api/law-chatbot/ask` 호출 시 503 Service Unavailable, 로그 갑자기 끊김

**원인**: BGEM3FlagModel(fp16)이 약 1.2GB 메모리 필요, 기존 Azure 사양(0.5CPU/1Gi)으로 부족

**해결**: Azure Container Apps 리소스 증설
```
기존: 0.5 CPU / 1.0 Gi
변경: 1.0 CPU / 2.0 Gi
```

### 16. 법령 벡터스토어 별표 누락
**증상**: "장기재직휴가 일수표" 같은 별표 내용을 검색 못 함

**원인**: law.go.kr API의 자치법규 별표는 `별표내용` 태그가 비어있고 HWP 첨부파일로만 제공

**해결**: 별표 제목은 벡터스토어에 포함 (`(첨부파일로 제공 - [별표 3] 특별휴가일수표)`), 핵심 별표 내용은 수동 JSON 파일로 보강 예정

### 17. Azure Container Apps 활성화 실패 (재난 대시보드 추가 직후)
**증상**
- `Activation failed`
- `1/1 Container crashing`

**원인 후보**
- `disaster_dashboard.py` import 실패
- `get_supabase_client()` 미정의
- 신규 서비스 파일 누락
- Supabase 전역 초기화 시 앱 시작 실패

**조치**
- `supabase = get_supabase_client()` 전역 호출 제거
- 각 라우터 함수 내부에서 Supabase 클라이언트 호출
- `supabase_service.py`에 싱글톤 인스턴스와 `get_supabase_client()` 추가

### 18. incident_count = 0 / disaster_incidents 비어 있음
**증상**
- 업로드는 되었으나 `disaster_incidents` 테이블이 비어 있음
- `incident_count = 0`

**원인 확인**
- `disaster_raw_messages`에는 normal 메시지가 충분히 존재
- 따라서 파싱 자체보다 사건 재구성 또는 저장 단계 문제로 판단

**조치**
- `analyze_disaster_chat()`에 디버깅 print 추가
  - `raw_messages_count`
  - `parsed_messages_count`
  - `normal_messages_count`
  - `incidents_count`
  - `inserted_incidents_count`

> v7.1에서 `print` 디버깅은 `logging.info`로 전환됨 (트러블슈팅 26번 참조)

### 19. 사진 메시지가 다음 사건에 붙는 문제
**증상**
- 사진 수가 다음 사람 사건에 부착됨
- 보고자/사진 수/읍면동/위치/요약이 서로 밀려서 표시됨

**원인**
- 초기 로직에서 사진 메시지를 `photo_buffer`에 담아 다음 사건에 붙이는 구조 사용

**조치**
- `disaster_incident_service.py` 수정
- 사진 메시지는 **직전 사건**에 부착하도록 변경

### 20. 첫 번째 txt는 안 되고 두 번째 txt는 되는 문제
**증상**
- 특정 카카오톡 txt 파일은 분석 실패
- 다른 txt 파일은 정상 분석

**원인**
- 파일별 날짜/시간 헤더 형식 차이
- 단독 시각줄 / 날짜 헤더 / 한글 날짜형 / 점 날짜형 혼재

**조치**
- 단독 시각줄 스킵
- 한글 날짜형 / 점 날짜형 모두 지원
- 시스템 메시지 경계 인식 강화

> v7.1에서 추가로 구분선형, 대괄호형 카톡 포맷도 지원 (트러블슈팅은 신규 형식 발견 시 추가)

### 21. 읍면동/위치 누락 문제
**증상**
- `용산동 천변산책로 출입 통제 완료했습니다`
  같은 메시지에서 위치 누락 발생

**조치**
- 읍면동 목록 파일 기반 매칭 우선 적용
- 장소 키워드 사전 확장
- `읍면동 + 장소명` 조합 방식 추가
- 대괄호 제거 및 문장 후미 불필요 표현 정리

### 22. analyze 중복 호출로 데이터 꼬임 🆕 v7.1
**증상**: 사용자가 "분석 실행" 버튼을 빠르게 더블클릭하거나 새로고침 후 재요청 시 incident가 중복 생성되거나 일부 누락

**원인**: v7.0에서는 동시성 제어 없음. 두 요청이 동시에 진입하면 둘 다 기존 데이터 삭제 후 insert → race condition

**해결**: `analysis_status='analyzing'` 락 도입
- 진입 시 현재 상태 확인
- `analyzing`이면 **409 Conflict** 반환
- 성공 시 `analyzed`, 실패 시 `failed` 또는 이전 상태로 롤백

**프론트엔드 처리**:
```jsx
catch (err) {
  if (err?.response?.status === 409) {
    setError("이미 분석 중입니다. 잠시 후 다시 시도해주세요.");
  }
}
```

### 23. 같은 위치 사건이 한 사건으로 영구 병합되는 문제 🆕 v7.1
**증상**: 7월 통제 사건과 8월 통제 사건이 같은 사건으로 묶여서 사건 카운트가 절반으로 줄어듦

**원인**: v7.0의 `make_incident_key()`는 `(emd, location, type)`만 사용 → 시간 개념 없음

**해결**: 상태 흐름 기반 그룹핑 도입
- 활성 사건 리스트로 추적
- `closed` 상태 도달 시 `_closed=True` 마킹
- 이후 같은 키 메시지는 새 사건으로 인식

### 24. 위치 표기 차이로 사건이 분리되는 문제 🆕 v7.1
**증상**: "용산동 천변산책로"와 "용산동 천변 산책로"가 다른 사건으로 잡힘

**원인**: v7.0은 정확 일치 또는 prefix 80자 비교

**해결**: `difflib.SequenceMatcher` 기반 80% 유사도 매칭
```python
LOCATION_SIMILARITY_THRESHOLD = 0.80
similarity = SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()
```

### 25. "~예정" 메시지가 조치중으로 잡혀 과대계상 🆕 v7.1
**증상**: "보수예정", "정비예정" 메시지가 `in_progress` 상태로 분류 → 일일보고 "조치중 N건"이 실제보다 많음

**원인**: v7.0의 `STATUS_RULES`에서 "예정" 패턴이 `in_progress` 정규식에 포함됨

**해결**: `~예정`을 명시적으로 `reported`에 분리
```python
(re.compile(r"예정"), "reported"),  # 마지막에 배치
```

### 26. PII가 Azure 로그에 남는 문제 🆕 v7.1
**증상**: `print(f"[ANALYZE] first_incident_sample={incidents[0]}")`로 보고자 이름/위치 등 dict 통째 출력

**해결**: `logging` 모듈 전환 + 출력 항목 제한
```python
logger.info("analyze start: upload_id=%s, raw_messages=%d", upload_id, raw_count)
# id와 count만, dict 통째 출력 금지
```

### 27. 일일보고서가 너무 기계적으로 보이는 문제 🆕 v7.1
**증상**: v7.0 템플릿 기반 보고서는 "총 N건 분석, 완료 X건, 조치중 Y건" 같이 딱딱한 문장만 반복

**해결**: GPT-4o 자연어화
- `OpenAIService`에 `model` 오버라이드 파라미터 추가
- `disaster_report_service`에서 `model="gpt-4o"` 명시 override
- prompt_service 연동 → 관리자가 톤 조정 가능
- GPT 실패 시 템플릿 폴백 (서비스 중단 방지)

### 28. SPA 라우팅에서 sessionStorage stale 데이터 🆕 v7.1
**증상**: DisasterUpload에서 새 파일 업로드 후 DisasterDashboard로 이동했는데 이전 파일 정보가 표시됨

**원인**: 컴포넌트가 unmount 안 되면 `const x = sessionStorage.getItem(...)`이 재평가 안 됨

**해결**: 커스텀 이벤트 + 훅 도입
```jsx
// constants/disaster.js
export function setDisasterSession(uploadId, fileName) {
  sessionStorage.setItem(...);
  window.dispatchEvent(new Event(DISASTER_SESSION_EVENT));
}

// hooks/useDisasterSession.js
window.addEventListener(DISASTER_SESSION_EVENT, refresh);
window.addEventListener("focus", refresh);
window.addEventListener("storage", refresh);
```

### 29. Dashboard 재난 카드가 "데이터 없음" 화면으로 진입 🆕 v7.1
**증상**: 사용자가 대시보드에서 "재난상황 대시보드" 카드 클릭 → "현재 세션에 선택된 파일이 없습니다" 화면 → 당황

**원인**: v7.0 카드 경로가 `/disaster-dashboard`로 바로 이동 → 업로드 안 한 사용자는 빈 화면

**해결**: 카드 경로를 `/disaster-upload`로 변경 + description 명확화
```jsx
{
  title: '재난상황 대시보드',
  description: '카카오톡 상황보고 txt를 업로드하면 사건 목록·대시보드·일일보고서를 생성합니다',
  path: '/disaster-upload',  // ← v7.0: '/disaster-dashboard'
  category: 'data',
}
```

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
1. Container Apps 자동 스케일링 (0→1, 최소 복제본 0)
2. OpenAI API 캐싱 활용
3. Supabase Free Tier 활용
4. 불필요한 벡터 검색 최소화

### v7.1 추가 비용 영향 🆕

**일일보고서 GPT-4o 호출**:
- 1회 보고서당 약 2,000~4,000 토큰 (요약 + 본문)
- gpt-4o 기준 약 $0.02~$0.04 / 보고서
- 하루 5회 생성 시 월간 약 $3~$6 추가 (한화 약 4천~8천원)

→ 비용 매우 미미. 폴백 작동 시 비용 0.

---

## 변경 이력

### v7.1.0 (2026-04-26) 🆕

#### 백엔드 코어 로직 개선 (1단계)

- ✅ **사건 그룹핑 알고리즘 전면 재작성** (`disaster_incident_service.py`)
  - v7.0: `(emd, location, type)` 정적 키 기반 → 같은 위치 여러 사건이 한 사건으로 영구 병합
  - v7.1: **상태 흐름 기반 그룹핑** — `closed` 상태 도달 시 사건 종결, 이후 같은 키 메시지는 새 사건
  - `_closed` 플래그로 활성 사건만 매칭 대상에 포함

- ✅ **위치 유사도 매칭 도입**
  - `difflib.SequenceMatcher` 기반 80% 유사도 임계값
  - "용산동 천변산책로" ≈ "용산동 천변 산책로" 같은 표기 차이 흡수
  - `_normalize_location()`: 괄호/공백/특수문자 제거 후 비교

- ✅ **incident_type 다수결 재계산**
  - 첫 메시지가 `inspection`(분류 불가)이어도 후속 메시지의 실제 유형으로 재산정
  - `_recalculate_incident_type()`: `inspection`을 우선순위 낮춤

- ✅ **status 분류 정교화** (`disaster_parser_service.py`)
  - `~예정` 계열을 `reported`로 명시적 분리 (v7.0: `in_progress`에 섞임)
  - `completed` 패턴을 구체화 ("복구 완료", "처리 완료" 등만 매칭)

- ✅ **날짜 포맷 커버리지 확장**
  - 구분선형 (`--------- 2025년 7월 15일 월요일 ---------`) 지원
  - 대괄호형 (`[이름] [오후 3:30] 메시지`) 지원 — `current_date`로 연도 보완

- ✅ **위치 정리 강화**
  - `_clean_location_text()`: 다양한 괄호 (`【】()『』〔〕「」《》`) 일괄 제거

- ✅ **응답 문구 필터 개선**
  - 정확 일치 → 정규식 기반 (`네~`, `넵`, `확인했습니다` 등 변형 흡수)

#### 백엔드 안정성 개선 (2단계)

- ✅ **analyze 동시성 제어** (`routers/disaster_dashboard.py`)
  - `analysis_status='analyzing'` 기반 락
  - 중복 호출 시 **409 Conflict** 반환
  - 분석 실패 시 `analysis_status='failed'`로 롤백
  - 명시적 예외(404)는 이전 상태로 복원

- ✅ **빈 배열 가드**
  - `incident_rows`가 비어 있을 때 `.insert([])` 호출 방지

- ✅ **logging 모듈 전환**
  - `print()` → `logger.info()` / `logger.exception()`
  - PII 최소화: `id`, `count`, 단계명만 로깅 (dict 통째 출력 제거)
  - Azure Container Apps 로그 grep 필터링 용이

- ✅ **`get_dashboard_overview` 날짜 파싱 방어**
  - `datetime.fromisoformat()` 실패 시 해당 시각 스킵 (`try/except`)

#### GPT 일일보고서 (3단계)

- ✅ **`backend/services/disaster_constants.py`** 신규 생성
  - `INCIDENT_TYPE_LABELS`, `STATUS_LABELS` 단일 소스
  - `incident_label()`, `status_label()` 헬퍼 함수
  - `COMPLETED_STATUSES`, `IN_PROGRESS_STATUSES` 상태 그룹 상수

- ✅ **`backend/services/disaster_report_service.py`** 전면 재작성
  - 동기 → **비동기**(`async def generate_daily_report`)
  - GPT-4o로 요약(summary_text) + 본문(report_text) 자연어화
  - `prompt_service` 연동 (3개 프롬프트: `system_prompt`, `summary_prompt`, `body_prompt`)
  - **3중 폴백**: prompt_service → `_DEFAULT_*` 상수 → 템플릿 기반 폴백
  - PII 보호: 보고자 이름 프롬프트에 미포함

- ✅ **`backend/services/openai_service.py`** 수정
  - `generate_text()`에 `model: Optional[str] = None` 파라미터 추가
  - 기존 호출부 영향 없음 (None이면 `settings.OPENAI_MODEL` 사용)
  - 재난보고만 `model="gpt-4o"` 명시 override

- ✅ **`backend/routers/disaster_dashboard.py`** 일부 수정
  - `create_daily_report`를 `async def`로 변경
  - `await generate_daily_report(...)` 호출

- ✅ **`backend/scripts/seed_disaster_prompts.sql`** 신규
  - 3개 프롬프트 INSERT (`ON CONFLICT DO UPDATE`로 재실행 안전)
  - `prompts` 테이블에 `disaster_report` feature 추가

#### 프론트엔드 전체 (4단계)

- ✅ **`frontend/src/constants/disaster.js`** 신규
  - `INCIDENT_TYPE_LABELS`, `STATUS_LABELS` 단일 소스
  - `incidentLabel()`, `statusLabel()` 헬퍼 함수
  - `setDisasterSession()`, `getDisasterSession()` 세션 헬퍼
  - `DISASTER_SESSION_EVENT` 커스텀 이벤트명

- ✅ **`frontend/src/hooks/useDisasterSession.js`** 신규
  - `useState` + 이벤트 구독으로 sessionStorage 리액티브 처리
  - `DISASTER_SESSION_EVENT` (같은 탭 내), `focus`, `storage` 이벤트 모두 구독
  - 컴포넌트 언마운트 시 cleanup

- ✅ **`DisasterUpload.jsx`** 전면 재작성
  - 렌더 중 `sessionStorage.getItem()` 직접 호출 제거 → 훅 사용
  - 409 Conflict 특별 처리 ("이미 분석 중입니다" 메시지)
  - 업로드 성공 시 `setDisasterSession()` 호출 → 다른 페이지에 자동 전파

- ✅ **`DisasterDashboard.jsx`, `DisasterIncidents.jsx`, `DisasterDailyReport.jsx`** 전면 재작성
  - `useDisasterSession` 훅 사용
  - `useEffect` 의존성 배열에 `[activeUploadId]` 추가 → 세션 변경 시 자동 재조회
  - `INCIDENT_TYPE_LABELS`, `STATUS_LABELS` 상수 import
  - `incidentLabel()`, `statusLabel()` 헬퍼 사용

- ✅ **`Dashboard.jsx`** 수정
  - 재난 대시보드 카드 경로: `/disaster-dashboard` → **`/disaster-upload`**
  - description 명확화: "txt를 업로드하면 …생성합니다"
  - `categoryOrder.data` 배열 경로 동기화

### v7.0.0 (2026-04-23)
- 🆕 재난상황 단톡 대시보드 기능 추가
- 카카오톡 txt 업로드 → 사건 분류 → 대시보드/일일보고 자동 생성
- `disaster_dashboard.py` 라우터 추가
- `disaster_parser_service.py`, `disaster_incident_service.py`, `disaster_report_service.py` 추가
- `backend/data/eup_myeon_dong.txt` 기반 읍면동 분류 강화
- 유형/상태는 내부 영어 코드 유지, 화면은 한글 라벨 표기
- `inspection` 화면 표시를 `기타/미분류`로 통일
- 사진 메시지를 직전 사건에 붙이도록 사건 재구성 로직 수정
- 업로드 목록을 사용자 화면에서 숨기고 `sessionStorage` 기반 현재 세션 파일만 사용하도록 변경

### v6.0.0 (2026-04-07)
- ✅ **프롬프트 중앙 관리 시스템** 신규 구축
  - Supabase `prompts` 테이블 + `prompt_history` 이력 테이블 생성
  - 38개 프롬프트 DB 시딩 완료 (`seed_all_prompts.sql`)
  - 3단계 폴백: DB 캐시 → DB 재로드 → 코드 내 default 하드코딩
  - 관리자가 웹에서 프롬프트 수정 시 즉시 반영 (재배포 불필요)
  - 캐시 TTL 5분, 수동 캐시 갱신 API 제공

- ✅ **`prompt_service.py`** 신규 (싱글톤 서비스)
  - `prompt_service.get(feature, key, default=...)` 패턴
  - Supabase 지연 초기화 (서버 시작 시 즉시 연결 시도 안 함)
  - `update()`: DB 업데이트 + `prompt_history` 이력 자동 기록
  - `list_all()`, `get_history()`, `refresh()` 관리자 API용 메서드
  - 로그: `[prompt-service] [PROMPT] DB used / FALLBACK used` 구분

- ✅ **`prompt_manager.py`** 신규 (관리자 API 라우터)
  - `GET /api/prompts/features` — 11개 기능 메타데이터
  - `GET /api/prompts/list` — 전체 프롬프트 목록 (관리자 전용)
  - `GET /api/prompts/by-feature/{feature}` — 기능별 프롬프트
  - `PUT /api/prompts/update` — 프롬프트 수정 + 이력 저장
  - `POST /api/prompts/history` — 변경 이력 조회
  - `POST /api/prompts/refresh-cache` — 캐시 강제 갱신
  - `_verify_admin()` 헬퍼: Supabase `user_profiles.role='admin'` 체크

- ✅ **`PromptManager.jsx`** 신규 (관리자 웹 페이지)
  - 좌측 패널: 기능별 프롬프트 목록 (검색, 카테고리 필터)
  - 우측 패널: 텍스트 에디터, 글자 수 표시, 변경 이력, 버전 복원
  - 다크모드 테마 (플랫폼 slate-950 + cyan 포인트 컬러 일치)
  - 토스트 알림, 캐시 갱신 버튼

- ✅ **11개 라우터 전부 `prompt_service` 적용**
  - `press_release.py` — 4개 프롬프트
  - `kakao_promo.py` — 7개 카테고리별 프롬프트
  - `news.py` — 2개
  - `merit_report.py` — 1개
  - `election_law.py` — 4개
  - `law_chatbot.py` — 3개
  - `translator.py` — 2개
  - `trip_report.py` — 5개
  - `report_writer.py` — 2개
  - `timeline_planner.py` — 4개
  - `meeting_summarizer.py` — 3개
  - 모든 라우터에 `_DEFAULT_*` 상수로 기존 하드코딩 보존 → DB 장애 시 자동 폴백

- ✅ **`auth.py` 관리자 권한 지원 강화**
- ✅ **`AuthContext.jsx`** 수정 — `isAdmin` 추가
- ✅ **`Layout.jsx`** 수정 — 관리자 메뉴 조건부 렌더링
- ✅ **`requirements.txt`** 변경 — `supabase==2.9.1` 업그레이드
- ✅ **Supabase 테이블** — `prompts`, `prompt_history`

### v5.1.0 (2026-04-03)
- ✅ **임베딩 모델 분리**: 보도자료/선거법 검색이 bge-m3 로드로 인해 차원 불일치(768 vs 1024) 에러 발생 → 모델별 분리
  - `vectorstore.py`에 `get_kosroberta_model()` 함수 신규 추가 (보도자료 + 선거법 전용, 768차원)
  - `get_embedding_model()` → 법령 챗봇 전용 (bge-m3, 1024차원) 유지
- ✅ **Dockerfile**: `ko-sroberta-multitask` 모델 다운로드 추가
- ✅ **법령 챗봇 컨텍스트 초과 수정**: `MAX_CONTEXT_CHARS = 60000` 제한 추가

### v5.0.0 (2026-03-18)
- ✅ **사업 타임라인 생성기** 신규 추가
  - 4단계 구조: 계획 → 계약 → 시행 → 완료
  - GPT 자동 일정 추천 (지방계약법 기반 현실적 기간 산출)
  - 간트차트 시각화
  - **법령 챗봇 내부 연동**
  - 사업유형별 법령 질의 매핑
  - 예산 규모별 법정 의무사항 자동 판단
  - 계약 방식 6종 지원
  - 단계별 세부 업무(TODO) 자동 생성
  - XLSX 시트2에 세부업무 포함
- ✅ **Dockerfile** 한글 폰트 추가 (`fonts-noto-cjk`)
- ✅ **requirements.txt** 추가: `Pillow>=10.0.0`, `python-pptx>=0.6.21`, `httpx`

### v4.0.0 (2026-03-13)
- ✅ **법령·자치법규 챗봇** 신규 추가 및 고도화
  - 충주시 자치법규 716건 + 별표/서식 252건 FAISS 벡터스토어 구축
  - 임베딩 모델: `BAAI/bge-m3` (1024차원, dense+sparse 동시 지원)
  - **Hybrid Search**: Dense(FAISS) + BM25 키워드 매칭을 RRF로 합산
  - **Agentic 재검색 루프**
  - 국가법령정보센터 API (`law.go.kr`) 실시간 검색 연동
  - GPT-4o 하이브리드 답변 전략

### v3.1.0 (2026-02-24)
- ✅ **출장보고 생성기** 대폭 업그레이드
  - 보고서 유형 5개 → **8개**
  - **HWPX 기본자료 업로드** 지원
  - 공문서 문체 규칙 강화
- ✅ **번역기 500 에러 수정**: `deepl>=1.16.0,<2.0.0` 버전 고정

### v3.0.0 (2026-02-20)
- ✅ **출장보고 생성기** 추가 (GPT Vision 기반)
- ✅ **공공데이터 검증기** 추가
- ✅ **카테고리 기반 대시보드** 개편 (4개 카테고리)
- ✅ GPT-5.1-chat-latest, GPT-5-mini 모델 적용

### v2.0.0 (2026-01-29)
- ✅ Supabase Auth 기반 인증 시스템 추가
- ✅ 회원가입 OTP 이메일 인증 방식
- ✅ 사용자 프로필 (이름, 부서) 추가
- ✅ 관리자/일반사용자 권한 시스템
- ✅ 소통공간 게시판 3종
- ✅ 업무보고 생성기

### v1.0.0 (2024-01-22)
- ✅ 11개 AI 기능 모듈 완성
- ✅ Azure 배포 완료
- ✅ CI/CD 파이프라인 구축

---

**문서 작성일**: 2024-01-22
**최종 수정**: 2026-04-26
**문서 버전**: 7.1.0

---

## AI 에이전트를 위한 추가 노트

### 이 프로젝트를 이해하려면:

1. **핵심 아키텍처**
   - 프론트엔드: React SPA (Vite)
   - 백엔드: FastAPI (Python)
   - 인증: Supabase Auth
   - DB: Supabase PostgreSQL
   - AI: OpenAI GPT-5.1 (Vision), GPT-5-mini, GPT-4o (재난보고)
   - 배포: Azure (SWA + Container Apps)

2. **주요 파일**
   - `frontend/src/App.jsx`: 라우팅 설정 (ProtectedRoute)
   - `frontend/src/context/AuthContext.jsx`: 인증 상태 관리 (isAdmin 포함)
   - `frontend/src/components/Layout.jsx`: 헤더/네비게이션 (2단 드롭다운 + 관리자 메뉴)
   - `frontend/src/pages/Dashboard.jsx`: 카테고리 탭 대시보드
   - `frontend/src/pages/TimelinePlanner.jsx`: 사업 타임라인 생성기
   - `frontend/src/pages/PromptManager.jsx`: 프롬프트 관리 페이지 (관리자 전용)
   - `frontend/src/constants/disaster.js`: 🆕 v7.1 재난 라벨 단일 소스
   - `frontend/src/hooks/useDisasterSession.js`: 🆕 v7.1 sessionStorage 리액티브 훅
   - `frontend/src/services/api.js`: API 통신
   - `backend/main.py`: FastAPI 진입점
   - `backend/routers/auth.py`: 인증 API
   - `backend/routers/board.py`: 게시판 API
   - `backend/routers/prompt_manager.py`: 프롬프트 관리 API (관리자 전용)
   - `backend/services/prompt_service.py`: 프롬프트 중앙 관리 서비스 (싱글톤)
   - `backend/services/openai_service.py`: 🆕 v7.1 model 오버라이드 추가
   - `backend/services/disaster_constants.py`: 🆕 v7.1 재난 라벨 백엔드 단일 소스
   - `backend/services/disaster_report_service.py`: 🆕 v7.1 GPT-4o 일일보고
   - `backend/routers/trip_report.py`: 출장보고 생성기
   - `backend/routers/timeline_planner.py`: 사업 타임라인 생성기 (법령챗봇 연동)
   - `backend/routers/data_validator.py`: 공공데이터 검증기
   - `backend/routers/disaster_dashboard.py`: 🆕 v7.1 재난 대시보드 (async + 락)
   - `backend/data/public_data_standards.json`: 300개 표준 데이터

3. **인증 흐름**
   - 로그인 안 됨 → `/login`으로 리다이렉트
   - JWT 토큰은 localStorage에 저장
   - 모든 API 요청에 `Authorization: Bearer {token}` 헤더 포함

4. **권한 체크**
   - `GET /api/auth/me` 호출 → `isAdmin` 값 확인
   - 관리자: 공지사항/자료실 글쓰기, QnA 답변, 프롬프트 관리

5. **출장보고 생성기 핵심**
   - Vision API 2단계 분석 (분류 → 추출)
   - 사진 필수 + HWPX 기본자료 선택 업로드
   - 보고서 유형 8개, 유형별 `closing_section` 다름
   - 설명회참석 closing_section = `"발표내용 요약"`
   - `force_report_type` 파라미터로 유형 강제 재분석
   - 공문서 문체: ~임/~함/~됨 금지 → 단어형 종결
   - `gpt-5.1-chat-latest`: temperature 제한 (1.0만 지원)
   - `gpt-5-mini`: temperature 자유롭게 사용 가능

6. **공공데이터 검증기 핵심**
   - 조건부 필수 패턴 4가지 자동 파싱
   - 허용값 엄격 체크 (01 vs 1 구분)
   - 좌표 소수점 6~10자리 검증

7. **코드 수정 시 주의사항**
   - 환경변수는 Azure Portal에서 설정
   - CORS 설정 필수 (Azure Container Apps + FastAPI 둘 다)
   - 새 라우터 추가 시 `main.py`에 등록 필요
   - Supabase 테이블/정책 변경 시 SQL Editor 사용
   - GPT-5.1은 temperature 파라미터에 제한 있음 (1.0만 지원)

8. **법령·자치법규 챗봇 핵심**
   - 라우터(`law_chatbot.py`)가 직접 FAISS + BM25 검색을 수행
   - 임베딩: `BGEM3FlagModel` (FlagEmbedding 라이브러리)
   - 벡터스토어 구축: `scripts/build_law_vectorstore.py --oc OC코드`
   - law.go.kr API: `resp.content.decode("utf-8")` 필수
   - GPT 컨텍스트 제한: `MAX_CONTEXT_CHARS = 60000`
   - Azure 최소 사양: 1.0 CPU / 2.0 Gi (bge-m3 모델 메모리)

⚠️ **임베딩 모델 분리 구조 (v5.1.0~)**:
   - `get_embedding_model()` → bge-m3 (1024차원) → **법령 챗봇만**
   - `get_kosroberta_model()` → ko-sroberta-multitask (768차원) → **보도자료 + 선거법**
   - 새 벡터스토어를 빌드할 때 반드시 해당 모델과 차원을 맞출 것

9. **디버깅**
   - 프론트엔드: 브라우저 개발자 도구 (F12)
   - 백엔드: Azure Container Apps 로그 스트림
   - Supabase: Table Editor / SQL Editor

10. **사업 타임라인 생성기 핵심**
    - 라우터(`timeline_planner.py`)가 법령 챗봇 API를 httpx로 내부 호출
    - 4단계 구조: 계획/계약은 법령 연동, 시행은 GPT만, 완료는 혼합
    - `LAW_QUERIES_BY_TYPE` 딕셔너리에 사업유형별 핀포인트 법령 질의 매핑
    - `_clean_json()` 함수로 GPT의 ```json 래핑 자동 제거
    - 프론트엔드에서 세부 업무 캐싱 (`detailTasks` state)
    - Dockerfile에 `fonts-noto-cjk` 필요

11. **프롬프트 중앙 관리 시스템 핵심**
    - **작동 흐름**: 서버 시작 → `prompt_service`가 Supabase에서 전체 프롬프트 로드 → 메모리 캐시 → 라우터에서 `prompt_service.get()` 호출 → 캐시 hit면 DB 값, miss면 default(코드 하드코딩) 반환
    - **3단계 폴백**: ① DB 캐시 → ② DB 재로드 → ③ 코드 내 `_DEFAULT_*` 상수
    - **Supabase 연결 실패 시**: 모든 프롬프트가 default 값으로 동작
    - **변수 치환 패턴**: DB에 `{manager}` 같은 플레이스홀더 저장 → 라우터에서 `.format()` 호출
    - **관리자 페이지 접근**: `user_profiles.role = 'admin'`인 사용자만
    - **이력 관리**: 프롬프트 수정 시 `prompt_history`에 자동 기록

### 재난 대시보드 핵심 (v7.1) 🆕

12. **사건 그룹핑 = 상태 흐름 기반**
    - `disaster_incident_service.build_incidents()`는 시간순으로 메시지를 순회하며 활성 사건에 병합 또는 신규 생성
    - `closed` 상태 메시지를 만나면 해당 사건 `_closed=True` 마킹 → 이후 매칭 대상 제외
    - 같은 위치 통제→해제→통제 시퀀스가 자연스럽게 2개 사건으로 분리

13. **위치 유사도 80%**
    - `difflib.SequenceMatcher`의 `ratio()` 사용
    - 정규화 후 비교 (괄호/공백/특수문자 제거)
    - `LOCATION_SIMILARITY_THRESHOLD = 0.80` 상수로 조절 가능

14. **OpenAIService 모델 오버라이드**
    - 기존 호출은 그대로 → `settings.OPENAI_MODEL` 사용
    - 새 호출에서 `model="gpt-4o"` 명시 가능
    - 재난보고만 gpt-4o, 다른 기능은 settings 따름

15. **3중 폴백 체인 (서비스 중단 방지)**
    - prompt_service DB 실패 → `_DEFAULT_*` 상수 사용
    - GPT 호출 실패 → 템플릿 기반 폴백 사용
    - 어떤 단계가 실패해도 응답은 항상 생성됨

16. **analyze 락**
    - `analysis_status` 컬럼이 락 역할
    - 중복 호출은 409 Conflict
    - 실패 시 `failed`로 마킹 → 추후 재시도 가능

17. **프론트엔드 sessionStorage 리액티브**
    - `useDisasterSession()` 훅 사용 필수
    - 직접 `sessionStorage.getItem()` 금지 (렌더 중 stale 데이터)
    - 변경 시 `setDisasterSession()` 호출 → 자동 전파

18. **라벨 단일 소스**
    - 백엔드: `services/disaster_constants.py`
    - 프론트: `constants/disaster.js`
    - 둘이 일치해야 함 (수동 동기화 필요)

19. **`disaster_report_service.generate_daily_report()`는 비동기 함수**
    - 호출측은 `async def` + `await` 사용 필수
    - `routers/disaster_dashboard.py`의 `create_daily_report` 참고

20. **새 프롬프트 추가 시**
    - `seed_disaster_prompts.sql`에 INSERT 추가 (또는 `seed_all_prompts.sql`에 통합)
    - `_DEFAULT_*` 상수도 함께 추가 (DB 미연결 폴백용)

21. **라벨 변경 시**
    - 백엔드 `disaster_constants.py` + 프론트 `constants/disaster.js` 양쪽 수정
    - 한쪽만 수정하면 화면과 보고서 텍스트 불일치 발생

22. **사건 그룹핑 임계값 조정**
    - 위치 유사도 너무 엄격하면 같은 사건이 분리됨
    - 너무 느슨하면 다른 사건이 병합됨
    - `LOCATION_SIMILARITY_THRESHOLD`를 0.75~0.85 범위에서 조정

23. **logging 레벨 통일**
    - 다른 라우터에 `print()`가 많으면 일관성 떨어짐
    - 점진적으로 `logging` 전환 권장
    - `main.py`에 `logging.basicConfig(level=logging.INFO, ...)` 추가 가능

### 디버깅 (v7.1) 🆕

24. **재난 분석 실패 시 추적**
    ```bash
    # Azure 로그에서 실패 추적
    grep "analyze failed: upload_id=" logs.txt
    grep "analysis_status='failed'" supabase.txt

    # 특정 upload_id 전체 흐름 추적
    grep "upload_id=ABC123" logs.txt
    ```

25. **프롬프트 동작 확인**
    ```bash
    # DB used인지 FALLBACK used인지 확인
    grep "\[PROMPT\]" logs.txt
    ```

26. **GPT 호출 여부 확인**
    ```bash
    grep "used_gpt=" logs.txt
    # used_gpt=True → GPT 사용
    # used_gpt=False → 폴백 사용
    ```