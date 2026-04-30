# 환경변수 목록

모든 환경변수는 `backend/config.py`의 `Settings` 클래스에 선언됩니다.

**실제 값은 절대 이 파일에 기재하지 마세요.**
- 로컬 개발: `backend/.env` (`.gitignore`에 포함됨)
- 배포: Azure Container Apps → 설정 → 환경 변수
- GitHub Actions: Repository Secrets / Variables

---

## 필수 환경변수

### OpenAI API

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `OPENAI_API_KEY` | `""` **(필수)** | OpenAI API 키. 대부분의 AI 기능에 사용 |
| `OPENAI_MODEL` | `gpt-4o-mini` | 기본 모델. 법령 챗봇 답변은 코드 내에서 `gpt-4o` 고정 |

### 법령정보센터 API

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `LAW_API_OC` | `""` **(필수)** | law.go.kr Open API 인증키(OC). 없으면 법령 챗봇 검색 불가 |

### Supabase

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `SUPABASE_URL` | `""` **(필수)** | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | `""` **(필수)** | Supabase anon/service key |

---

## 기능별 선택 환경변수

### HWPX 번역기 (DeepL)

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `DEEPL_API_KEY` | `""` | DeepL API 키. 번역기 기능에 사용 |

> ⚠️ `deepl` 패키지 버전: `>=1.16.0,<2.0.0` (2.x 호환 불가)

### 주소-좌표 변환기 (Kakao)

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `KAKAO_API_KEY` | `""` | Kakao REST API 키. 주소↔좌표 변환에 사용 |

### 뉴스 기능 (GitHub)

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `GITHUB_TOKEN` | `""` | GitHub Personal Access Token |
| `GIST_ID` | `""` | 뉴스 데이터 저장 Gist ID |
| `GITHUB_REPO` | `""` | Actions 트리거용 저장소명 |

### 출장보고 생성기 (선택)

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `TRIP_ANALYSIS_MODEL` | (확인 필요) | 이미지 분석 모델명 |
| `TRIP_REPORT_MODEL` | (확인 필요) | 보고서 생성 모델명 |
| `TRIP_MAX_IMAGES` | (확인 필요) | 최대 이미지 수 |
| `TRIP_MAX_IMAGE_BYTES` | (확인 필요) | 최대 이미지 크기 |
| `TRIP_MAX_HWPX_BYTES` | (확인 필요) | 최대 HWPX 크기 |

---

## 시스템/경로 설정

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `CORS_ORIGINS` | `http://localhost:5173` | CORS 허용 도메인 (콤마 구분). 배포 시 프론트엔드 URL 추가 |
| `VECTORSTORE_PATH` | `/app/data/vectorstores` | 보도자료 FAISS 인덱스 경로 |
| `ELECTION_VECTORSTORE_PATH` | `/app/data/election_law/vectorstores` | 선거법 FAISS 인덱스 경로 |
| `LAW_CHATBOT_VECTORSTORE_PATH` | `/app/data/law_chatbot/vectorstores` | 법령 챗봇 자치법규 FAISS 인덱스 경로 |
| `EMBEDDING_MODEL` | `jhgan/ko-sroberta-multitask` | 기본 임베딩 모델명. Dockerfile에서 법령챗봇용 bge-m3 경로로 오버라이드 |

---

## Korean Law MCP 설정

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `KOREAN_LAW_MCP_ENABLED` | `true` | MCP CLI 활성화. `false`면 바로 직접 API 사용 |
| `KOREAN_LAW_MCP_COMMAND` | `korean-law` | MCP CLI 실행 명령어 |
| `KOREAN_LAW_MCP_TIMEOUT` | `15` | CLI timeout (초) |

> `korean-law-mcp` npm 패키지는 JSON-RPC stdio MCP 서버이므로 CLI 호출은 항상 실패.
> 실질 검색 경로: law.go.kr 직접 API. `KOREAN_LAW_MCP_ENABLED=false` 권장.

---

## GitHub Actions Secrets / Variables

### Repository Secrets

| Secret 이름 | 용도 |
|------------|------|
| `GHCR_TOKEN` | GitHub Container Registry push |
| `AZURE_CREDENTIALS` | Azure 서비스 주체 JSON |
| `OPENAI_API_KEY` | law-chatbot-eval.yml 평가용 |
| `LAW_API_OC` | law-chatbot-eval.yml 평가용 |

### Repository Variables (일반)

| Variable 이름 | 용도 |
|-------------|------|
| `LAW_CHATBOT_URL` | live 모드 평가 시 서버 URL |

---

## 로컬 개발 .env 예시

```env
# backend/.env (절대 Git에 커밋하지 마세요)

OPENAI_API_KEY=sk-...
LAW_API_OC=your_oc_key_here
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJ...
DEEPL_API_KEY=...
KAKAO_API_KEY=...
CORS_ORIGINS=http://localhost:5173
KOREAN_LAW_MCP_ENABLED=false
```

---

## 배포 환경 최소 설정

Azure Container Apps에 반드시 설정해야 할 환경변수:

```
OPENAI_API_KEY         ← AI 기능 전반 필수
LAW_API_OC             ← 법령 챗봇 필수
SUPABASE_URL           ← DB, 인증, 게시판 필수
SUPABASE_KEY           ← DB, 인증, 게시판 필수
CORS_ORIGINS           ← 프론트엔드 도메인 포함 필요
DEEPL_API_KEY          ← 번역기 사용 시
KAKAO_API_KEY          ← 주소변환 사용 시
GITHUB_TOKEN           ← 뉴스 기능 사용 시
GIST_ID                ← 뉴스 기능 사용 시
KOREAN_LAW_MCP_ENABLED ← false 권장
```

---

## 임베딩 모델 분리 (중요)

| 기능 | 모델 | 차원 | 비고 |
|------|------|------|------|
| 법령 챗봇 | `BAAI/bge-m3` (bge-m3) | 1024 | Dockerfile에서 `/app/models/bge-m3`로 설치 |
| 선거법 챗봇 | `jhgan/ko-sroberta-multitask` | 768 | Dockerfile에서 설치 |
| 보도자료 | `jhgan/ko-sroberta-multitask` | 768 | 동일 |

> ⚠️ 모델 차원이 다르므로 벡터스토어를 교차 사용하면 crash 발생.
