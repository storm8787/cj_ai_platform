# 배포 가이드

## 배포 환경 구성

| 컴포넌트 | 플랫폼 | 자동화 |
|---------|--------|--------|
| 백엔드 | Azure Container Apps (`cj-ai-backend`, RG: `rg-cj-ai-platform`) | GitHub Actions 자동 배포 |
| 프론트엔드 | Azure Static Web Apps | GitHub Actions 자동 배포 |
| 컨테이너 레지스트리 | GHCR (`ghcr.io/storm8787/cj-ai-backend`) | Actions에서 push |

---

## 백엔드 배포 흐름

### 트리거 조건

```yaml
on:
  push:
    branches: [main]
    paths:
      - 'backend/**'
```

`backend/` 하위 파일 변경 후 main 브랜치에 머지되면 자동 실행.

### 배포 단계 (`.github/workflows/backend-deploy.yml`)

```
1. Checkout (actions/checkout@v4)
2. GHCR 로그인 (GHCR_TOKEN 시크릿 사용)
3. Docker 빌드 & push
   - 태그: latest, {github.sha}
   - Context: ./backend
4. Azure 로그인 (AZURE_CREDENTIALS 시크릿)
5. Azure Container Apps update
   - az containerapp update
   - --name cj-ai-backend
   - --resource-group rg-cj-ai-platform
   - --image ghcr.io/storm8787/cj-ai-backend:{SHA}
```

### 예상 소요 시간

- Docker 빌드: 15~25분 (HuggingFace 모델 2개 다운로드 포함)
- Azure 배포: 2~5분
- 총계: 약 20~30분

---

## Dockerfile 구조 (`backend/Dockerfile`)

```dockerfile
FROM python:3.11-slim

# 1. 시스템 패키지 + Node 20 설치
#    - gcc, g++, curl, ca-certificates, gnupg
#    - fonts-noto-cjk (한글 폰트)
#    - Node 20 (nodesource 공식 저장소)
#    - npm install -g kordoc korean-law-mcp
#      (MCP CLI 설치. 현재 CLI 호출은 작동하지 않으나
#       미래 정상화 대비 및 법령 챗봇 기능 확장 목적으로 유지)

# 2. Python 의존성 설치
#    COPY requirements.txt → pip install

# 3. HuggingFace 모델 다운로드
#    - BAAI/bge-m3→ /app/models/bge-m3
#    - jhgan/ko-sroberta-multitask → /app/models/ko-sroberta-multitask

# 4. 애플리케이션 코드 복사
#    COPY . .

# 5. 포트 8000 노출, 헬스체크, 실행
#    CMD uvicorn main:app --host 0.0.0.0 --port 8000
```

**주의**: Dockerfile 마지막 줄 `# Force rebuild: 날짜-태그` 는 빌드 캐시 무효화용 주석.
의존성 변경 없이 재빌드가 필요할 때 이 날짜 텍스트를 변경.

---

## 환경변수 설정

### 로컬 개발

```bash
# backend/.env 파일 생성 (Git 추적 제외됨)
cp backend/.env.example backend/.env  # 예시 파일이 있다면
# 없으면 직접 작성 (ENVIRONMENT_VARIABLES.md 참고)
```

### Azure Container Apps 배포 환경

Azure Portal → Container Apps → `cj-ai-backend` → 설정 → 환경 변수

또는 Azure CLI:
```bash
az containerapp update \
  --name cj-ai-backend \
  --resource-group rg-cj-ai-platform \
  --set-env-vars "OPENAI_API_KEY=secretref:openai-key"
```

전체 환경변수 목록 → `docs/ENVIRONMENT_VARIABLES.md`

---

## GitHub Secrets 설정 (필수)

| Secret 이름 | 용도 |
|------------|------|
| `GHCR_TOKEN` | GitHub Container Registry push 권한 |
| `AZURE_CREDENTIALS` | Azure 서비스 주체 JSON |
| `OPENAI_API_KEY` | law-chatbot-eval.yml 평가 실행용 |
| `LAW_API_OC` | law-chatbot-eval.yml 평가 실행용 |

GitHub Actions Variables (secrets 아닌 일반 변수):

| Variable 이름 | 용도 |
|-------------|------|
| `LAW_CHATBOT_URL` | live 모드 평가 시 서버 URL |

---

## 프론트엔드 배포 흐름

파일: `.github/workflows/azure-static-web-apps-agreeable-smoke-0b02cf31e.yml`

Azure Static Web Apps 전용 Action이 자동으로 빌드·배포.
`frontend/` 변경 후 main 머지 시 자동 실행 (확인 필요).

---

## 수동 배포 (긴급 시)

```bash
# 1. Docker 빌드
cd backend
docker build -t ghcr.io/storm8787/cj-ai-backend:manual .

# 2. GHCR push
docker push ghcr.io/storm8787/cj-ai-backend:manual

# 3. Azure Container Apps update
az containerapp update \
  --name cj-ai-backend \
  --resource-group rg-cj-ai-platform \
  --image ghcr.io/storm8787/cj-ai-backend:manual
```

---

## 배포 후 검증

헬스체크 엔드포인트:
```
GET /api/health
```

법령 챗봇 상태 확인:
```
GET /api/law-chatbot/status
```

응답에 `vectorstore.loaded`, `api.connected` 상태 포함.

---

## 트러블슈팅

### 빌드 실패 — HuggingFace 다운로드 timeout

Dockerfile의 모델 다운로드 단계는 네트워크 상태에 따라 실패할 수 있음.
재시도하거나 Actions에서 수동 재실행.

### 법령 챗봇 응답 없음

1. `/api/law-chatbot/status` 확인
2. `law_api.connected: false`면 `LAW_API_OC` 환경변수 확인
3. MCP CLI 실패 로그는 정상 (직접 API fallback이 실제 동작)
   → `[korean-law-mcp] CLI 실패 rc=1` 로그는 무시해도 됨

### 컨테이너 시작 후 첫 요청 느림

FAISS 인덱스와 임베딩 모델 지연 로딩 때문. 첫 요청에서 로드 후 이후는 정상 속도.
