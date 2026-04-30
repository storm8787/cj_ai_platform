# 환경변수 목록

모든 환경변수는 `backend/config.py`의 `Settings` 클래스에 선언됩니다.

**실제 값은 절대 이 파일에 기록하지 마세요.**
- 로컬: `backend/.env`
- 배포: Azure Container Apps 환경변수 설정

---

## 필수 환경변수

### OpenAI

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `OPENAI_API_KEY` | `""` (필수) | OpenAI API 키. 법령 챗봇, 보도자료 등 대부분의 AI 기능에 사용 |
| `OPENAI_MODEL` | `gpt-4o-mini` | 기본 모델. 법령 챗봇 답변은 코드 내에서 `gpt-4o` 고정 사용 |

### 국가법령정보센터 API

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `LAW_API_OC` | `""` (필수) | 법령정보센터 Open API 인증키(OC). law.go.kr 직접 API 호출에 사용. 없으면 법령 챗봇 검색 불가 |

### Supabase

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `SUPABASE_URL` | `""` (필수) | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | `""` (필수) | Supabase anon/service key |

---

## 기능별 선택 환경변수

### 번역기 (DeepL)

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `DEEPL_API_KEY` | `""` | DeepL API 키. translator 기능에 사용 |

### 주소-좌표 변환 (Kakao)

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `KAKAO_API_KEY` | `""` | Kakao REST API 키. address_geocoder 기능에 사용 |

### 뉴스 관련 (GitHub Gist)

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `GITHUB_TOKEN` | `""` | GitHub Personal Access Token |
| `GIST_ID` | `""` | 뉴스 데이터 저장용 Gist ID |
| `GITHUB_REPO` | `""` | 연동 GitHub 저장소명 |

---

## 시스템/경로 설정

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `CORS_ORIGINS` | `http://localhost:5173` | CORS 허용 도메인 (콤마 구분). 배포 시 프론트엔드 URL 추가 필요 |
| `VECTORSTORE_PATH` | `/app/data/vectorstores` | 보도자료 FAISS 인덱스 경로 |
| `ELECTION_VECTORSTORE_PATH` | `/app/data/election_law/vectorstores` | 선거법 FAISS 인덱스 경로 |
| `LAW_CHATBOT_VECTORSTORE_PATH` | `/app/data/law_chatbot/vectorstores` | 법령 챗봇 충주시 자치법규 FAISS 인덱스 경로 |
| `EMBEDDING_MODEL` | `jhgan/ko-sroberta-multitask` | 선거법 임베딩 모델명. 법령 챗봇은 `EMBEDDING_MODEL` env를 Dockerfile에서 `/app/models/bge-m3`로 오버라이드 |

---

## Korean Law MCP 설정

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `KOREAN_LAW_MCP_ENABLED` | `true` | MCP CLI 활성화 여부. false로 설정하면 MCP 시도 없이 바로 직접 API 사용 |
| `KOREAN_LAW_MCP_COMMAND` | `korean-law` | MCP CLI 실행 명령어 |
| `KOREAN_LAW_MCP_TIMEOUT` | `15` | CLI 실행 timeout (초) |

**참고**: `korean-law-mcp` npm 패키지는 JSON-RPC stdio MCP 서버이므로 CLI 형태 호출은 현재 작동하지 않음.
MCP 실패 시 자동으로 law.go.kr 직접 API를 사용함.

---

## 로컬 .env 파일 예시

```env
# backend/.env

OPENAI_API_KEY=sk-...
LAW_API_OC=your_oc_key_here
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJ...
DEEPL_API_KEY=xxx
KAKAO_API_KEY=xxx
CORS_ORIGINS=http://localhost:5173
KOREAN_LAW_MCP_ENABLED=false
```

---

## 배포 환경 환경변수 예시

Azure Container Apps에 설정해야 할 최소 변수 목록:

```
OPENAI_API_KEY         ← 법령 챗봇, 보도자료 등 필수
LAW_API_OC             ← 법령 챗봇 필수
SUPABASE_URL           ← 게시판, 인증 필수
SUPABASE_KEY           ← 게시판, 인증 필수
CORS_ORIGINS           ← 프론트엔드 도메인 명시 필요
DEEPL_API_KEY          ← 번역기 사용 시
KAKAO_API_KEY          ← 주소변환 사용 시
KOREAN_LAW_MCP_ENABLED ← false 권장 (MCP CLI 미작동)
```
