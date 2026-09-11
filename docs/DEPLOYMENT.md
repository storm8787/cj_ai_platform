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

### 배포 단계 (`.github/workflows/backend-deploy.yml`) — 블루-그린 (무중단)

```
1. Checkout (actions/checkout@v4)
2. GHCR 로그인 (GHCR_TOKEN 시크릿 사용)
3. Docker 빌드 & push
   - 태그: latest, {github.sha}
   - Context: ./backend
4. Azure 로그인 (AZURE_CREDENTIALS 시크릿)
5. 블루-그린 배포 (단일 az update → 아래 순서로 대체)
   ① 다중 리비전 모드 전환
   ② 현재 서빙 리비전(OLD) 확인 → 트래픽 100% OLD 고정
   ③ GHCR pull 자격증명 재등록(방어)
   ④ 새 리비전(NEW)을 0% 트래픽 + min-replicas 1 로 생성
      (revision-suffix = sha7-runNumber)
   ⑤ NEW 의 runningState=Running 될 때까지 폴링 (최대 25분)
   ⑥ 성공 → 트래픽 100% NEW 전환 → OLD 비활성화
      실패 → NEW 비활성화, 트래픽은 OLD 유지(사이트 정상), 잡 실패 처리
   ⑦ 같은 이미지로 min-replicas 0 리비전(suffix: …-idle) 생성 → 트래픽 100% 전환
   ⑧ /api/health 폴링(콜드스타트 포함 최대 10분)
      성공 → warm 리비전(NEW) 비활성화 → 유휴 요금 0
      실패 → 트래픽을 NEW(min 1)로 롤백 + idle 리비전 비활성화 + 잡 실패 처리
```

> **왜 블루-그린인가**: 기존 방식(`az containerapp update` + 단일 모드)은 새 리비전으로 트래픽을
> **즉시** 넘겨서, 새 리비전이 큰 이미지(약 9.6GB) pull(~13분)로 ACA 프로비저닝 데드라인(10분)을
> 넘기면 사이트가 다운됐다(2026-07 반복 장애의 직접 원인). 이제 새 리비전이 실제로 Running 된
> 뒤에만 트래픽을 전환하므로, 배포가 실패해도 기존 리비전이 계속 서비스한다.
>
> **근본책(별도 과제)**: 이미지 슬림화 — 이미지에 구워진 HuggingFace 모델(bge-m3, ko-sroberta)을
> 런타임 볼륨으로 분리하고 CPU 전용 torch로 교체하여 pull 시간을 단축하면 데드라인 문제 자체가 사라진다.
> 상세 설계: **`docs/design/image_slimming.md`**

### 왜 min-replicas 를 2단계로 바꾸는가

ACA 는 `scale` 설정을 **리비전 템플릿의 일부**로 취급한다. 즉 `--min-replicas` 를 바꾸면
무조건 새 리비전이 만들어진다. 그래서 "검증"과 "요금"을 한 리비전으로 동시에 만족시킬 수 없다.

- 검증 단계에서는 `min-replicas 1` 이 필요하다. 0% 트래픽 리비전은 min 0 이면 replica 가
  아예 뜨지 않아 `runningState=Running` 검증 자체가 불가능하다.
- 서빙 단계에서는 `min-replicas 0` 이어야 한다. 1 이면 요청이 없어도 replica 가 계속 떠 있어
  **24시간 과금**된다.

→ 검증은 min 1 리비전으로, 서빙은 같은 이미지의 min 0 리비전으로 넘긴다.

### 예상 소요 시간

- Docker 빌드: 15~25분 (HuggingFace 모델 2개 다운로드 포함)
- 블루-그린 배포: 새 리비전 이미지 pull(~13분) + Running 확인 + 트래픽 전환 → 약 15~25분
- 총계: 약 30~50분 (무중단. 배포 중에도 기존 리비전이 서비스)

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
#    - torch 를 CPU 전용(torch==2.6.0+cpu, pytorch cpu 인덱스)으로 먼저 설치
#      → nvidia CUDA 라이브러리(~5~6GB) 제거. 앱은 GPU 미사용(cpu:1, faiss-cpu).
#    - COPY requirements.txt → pip install (torch 는 이미 충족되어 재설치 안 됨)

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

## 비용 / 스케일 정책 (Azure 요금)

### 기본 원칙

| 설정 | 동작 | 요금 |
|------|------|------|
| `min-replicas 0` (기본·권장) | 무요청 상태가 이어지면 replica 0 으로 축소 | 유휴 시 vCPU/메모리 요금 **없음** |
| `min-replicas 1` | replica 가 항상 기동 | 24시간 과금 |

`min-replicas 1` 은 **배포 롤아웃 검증**과 **장애 진단(`fix-registry-auth.yml`)** 에서만 임시로 쓴다.
두 워크플로 모두 끝날 때 0 으로 되돌리거나, 되돌리라는 경고를 출력한다.

### 지금 당장 스케일을 바꾸는 법 (재빌드 불필요)

**방법 1 — GitHub Actions (권장, 로컬 az CLI 불필요)**

Actions → **Ops - Container App 스케일 전환** → Run workflow → `min_replicas` = `0`
(`.github/workflows/scale-control.yml`)

새 리비전 생성 → 트래픽 전환 → health check → 옛 리비전 비활성화까지 자동 수행한다.
실패하면 이전 리비전으로 자동 롤백한다.

**방법 2 — Azure CLI**

```bash
az containerapp update \
  --name cj-ai-backend \
  --resource-group rg-cj-ai-platform \
  --min-replicas 0 --max-replicas 3

# 다중 리비전 모드라면 새 리비전으로 트래픽을 직접 넘겨야 한다
az containerapp revision list -n cj-ai-backend -g rg-cj-ai-platform -o table
az containerapp ingress traffic set -n cj-ai-backend -g rg-cj-ai-platform \
  --revision-weight <새-리비전-이름>=100
# 옛(min 1) 리비전은 비활성화해야 replica 가 내려간다
az containerapp revision deactivate -n cj-ai-backend -g rg-cj-ai-platform \
  --revision <옛-리비전-이름>
```

**방법 3 — Azure Portal**

Container Apps → `cj-ai-backend` → 애플리케이션 → 크기 조정(Scale) → 최소 복제본 수 = 0 → 저장.
포털도 새 리비전을 만드므로, **리비전 관리에서 트래픽이 새 리비전으로 갔는지 / 옛 리비전이
비활성화됐는지 반드시 확인**해야 실제로 요금이 멈춘다.

### 확인해야 할 함정

1. **워크로드 프로필이 Dedicated 면 scale-to-zero 해도 요금이 멈추지 않는다.**
   Dedicated 프로필은 replica 수와 무관하게 노드 자체가 과금된다. 확인:
   ```bash
   az containerapp env show -n <환경이름> -g rg-cj-ai-platform \
     --query "properties.workloadProfiles" -o json
   ```
   `Consumption` 이어야 유휴 요금이 0 이 된다. Dedicated 면 프로필을 Consumption 으로 바꾸거나
   최소 인스턴스 수를 0 으로 내려야 한다.
2. **활성 리비전이 2개 이상이면 둘 다 과금된다.** `az containerapp revision list` 로
   `active=true` 인 리비전이 1개인지 확인.
3. **Log Analytics 작업 영역**은 Container Apps 와 별도로 수집량만큼 과금된다.
   요금 청구서에 남아 있다면 보존 기간·수집량을 조정한다.
4. **scale-to-zero 의 대가는 콜드스타트다.** 이미지가 아직 크기 때문에(→ `docs/design/image_slimming.md`)
   유휴 후 첫 요청이 수십 초~수 분 걸릴 수 있다. 프론트엔드는
   `frontend/src/hooks/useBackendWakeup.js` 에서 최대 약 6분간 재시도하며 기동을 기다린다.

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
