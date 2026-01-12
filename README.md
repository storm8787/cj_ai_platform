# 충주시 AI 플랫폼 - Azure 배포 버전

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Azure Cloud                                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Azure Static Web Apps                          │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │   React SPA (Vite + TailwindCSS)                           │  │  │
│  │  │   • 대시보드                                                │  │  │
│  │  │   • 보도자료 생성기                                         │  │  │
│  │  │   • 선거법 챗봇                                             │  │  │
│  │  │   • 뉴스 뷰어                                               │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │                           │                                       │  │
│  │                  API Proxy (/api/*)                               │  │
│  └───────────────────────────┼──────────────────────────────────────┘  │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                  Azure Container Apps                             │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │   FastAPI Backend (Python 3.11)                            │  │  │
│  │  │   • /api/press-release/* - 보도자료 생성 API               │  │  │
│  │  │   • /api/election-law/*  - 선거법 챗봇 API                 │  │  │
│  │  │   • /api/news/*          - 뉴스 관리 API                   │  │  │
│  │  │   • /api/health          - 헬스체크                        │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │                              │                                    │  │
│  │                    (이미지: ghcr.io)                              │  │
│  └──────────────────────────────┼───────────────────────────────────┘  │
│                                 │                                       │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Supabase      │     │   OpenAI API    │     │  GitHub (ghcr)  │
│  • Storage      │     │  • GPT-4o-mini  │     │  • Container    │
│  • PostgreSQL   │     │  • Embeddings   │     │    Registry     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 📁 프로젝트 구조

```
cj_ai_azure/
├── frontend/                          # Azure Static Web Apps
│   ├── src/
│   │   ├── pages/                     # 페이지 컴포넌트
│   │   │   ├── Dashboard.jsx
│   │   │   ├── PressRelease.jsx
│   │   │   ├── ElectionLaw.jsx
│   │   │   └── NewsViewer.jsx
│   │   ├── components/
│   │   │   └── Layout.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── staticwebapp.config.json       # ⭐ Azure SWA 설정
│   └── .env.example
│
├── backend/                           # Azure Container Apps
│   ├── routers/
│   │   ├── press_release.py
│   │   ├── election_law.py
│   │   ├── news.py
│   │   └── health.py
│   ├── services/
│   │   ├── vectorstore.py
│   │   ├── openai_service.py
│   │   └── supabase_service.py
│   ├── utils/
│   │   └── prompt_filter.py
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   ├── Dockerfile                     # ⭐ Container Apps용
│   └── .env.example
│
├── .github/workflows/
│   ├── azure-swa-deploy.yml           # ⭐ 프론트엔드 배포
│   └── azure-aca-deploy.yml           # ⭐ 백엔드 배포
│
└── README.md
```

## 🚀 배포 가이드

### 사전 준비사항

1. **Azure 계정** 및 구독
2. **GitHub 저장소** (코드 업로드 완료)
3. **GitHub Personal Access Token** (ghcr.io용, `read:packages`, `write:packages` 권한)

---

## 🖥️ Azure Portal 배포 (GUI 방식)

### Step 1: 리소스 그룹 생성

1. [Azure Portal](https://portal.azure.com) 접속 → 로그인
2. 상단 검색창에 **"리소스 그룹"** 검색 → 클릭
3. **➕ 만들기** 클릭
4. 설정 입력:
   - **구독**: 사용할 구독 선택
   - **리소스 그룹**: `rg-cj-ai-platform`
   - **지역**: `Korea Central`
5. **검토 + 만들기** → **만들기**

---

### Step 2: Container Apps 환경 생성

1. 상단 검색창에 **"Container Apps 환경"** 검색 → 클릭
2. **➕ 만들기** 클릭
3. **기본 사항** 탭:
   - **구독**: 선택
   - **리소스 그룹**: `rg-cj-ai-platform`
   - **환경 이름**: `cj-ai-env`
   - **지역**: `Korea Central`
   - **영역 중복**: 사용 안 함
4. **모니터링** 탭:
   - **Log Analytics 작업 영역**: 새로 만들기 또는 기존 선택
5. **검토 + 만들기** → **만들기**

---

### Step 3: Container App 생성 (백엔드)

#### 3-1. 먼저 GitHub에 Docker 이미지 푸시

로컬에서 한 번만 실행 (또는 GitHub Actions가 자동 처리):
```bash
# 로컬 터미널에서
cd backend
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
docker build -t ghcr.io/YOUR_USERNAME/cj-ai-backend:latest .
docker push ghcr.io/YOUR_USERNAME/cj-ai-backend:latest
```

#### 3-2. GitHub Package를 Public으로 설정

1. GitHub 저장소 → **Packages** 탭
2. `cj-ai-backend` 패키지 클릭
3. 우측 **Package settings**
4. 하단 **Danger Zone** → **Change visibility** → **Public**

#### 3-3. Azure Portal에서 Container App 생성

1. 상단 검색창에 **"Container Apps"** 검색 → 클릭
2. **➕ 만들기** 클릭

3. **기본 사항** 탭:
   | 항목 | 값 |
   |------|-----|
   | 구독 | 선택 |
   | 리소스 그룹 | `rg-cj-ai-platform` |
   | 컨테이너 앱 이름 | `cj-ai-backend` |
   | 지역 | `Korea Central` |
   | Container Apps 환경 | `cj-ai-env` 선택 |

4. **컨테이너** 탭:
   | 항목 | 값 |
   |------|-----|
   | 빠른 시작 이미지 사용 | ❌ 체크 해제 |
   | 이미지 원본 | `Docker Hub 또는 기타 레지스트리` |
   | 이미지 형식 | `Public` |
   | 레지스트리 로그인 서버 | `ghcr.io` |
   | 이미지 및 태그 | `YOUR_USERNAME/cj-ai-backend:latest` |
   | CPU 및 메모리 | `0.5 vCPU, 1 GiB` (또는 필요에 따라) |

5. **컨테이너** 탭 → **환경 변수** 섹션에서 **➕ 추가**:
   | 이름 | 소스 | 값 |
   |------|------|-----|
   | `OPENAI_API_KEY` | 수동 항목 | `sk-your-key` |
   | `SUPABASE_URL` | 수동 항목 | `https://xxx.supabase.co` |
   | `SUPABASE_KEY` | 수동 항목 | `your-key` |
   | `CORS_ORIGINS` | 수동 항목 | `http://localhost:5173` (나중에 SWA URL 추가) |

6. **수신** 탭:
   | 항목 | 값 |
   |------|-----|
   | 수신 | ✅ 사용 |
   | 수신 트래픽 | `어디서나 트래픽 허용` |
   | 수신 형식 | `HTTP` |
   | 대상 포트 | `8000` |

7. **검토 + 만들기** → **만들기**

8. 배포 완료 후 **리소스로 이동** → **애플리케이션 URL** 복사
   - 예: `https://cj-ai-backend.koreacentral.azurecontainerapps.io`

---

### Step 4: Static Web App 생성 (프론트엔드)

1. 상단 검색창에 **"Static Web Apps"** 검색 → 클릭
2. **➕ 만들기** 클릭

3. **기본 사항** 탭:
   | 항목 | 값 |
   |------|-----|
   | 구독 | 선택 |
   | 리소스 그룹 | `rg-cj-ai-platform` |
   | 이름 | `cj-ai-frontend` |
   | 호스팅 계획 | `무료` |
   | 지역 | `East Asia` (한국 가까운 곳) |
   | 원본 | `GitHub` |

4. **GitHub 계정 연결** 버튼 클릭 → 로그인 → 권한 부여

5. **GitHub 설정**:
   | 항목 | 값 |
   |------|-----|
   | 조직 | 본인 계정 |
   | 리포지토리 | 프로젝트 저장소 선택 |
   | 분기 | `main` |

6. **빌드 세부 정보**:
   | 항목 | 값 |
   |------|-----|
   | 빌드 사전 설정 | `Custom` |
   | 앱 위치 | `/frontend` |
   | API 위치 | (비워두기) |
   | 출력 위치 | `dist` |

7. **검토 + 만들기** → **만들기**

8. 배포 완료 후:
   - **리소스로 이동** → **URL** 복사
   - 예: `https://cj-ai-frontend.azurestaticapps.net`

---

### Step 5: 프론트엔드 ↔ 백엔드 연결

#### 5-1. 프론트엔드 환경변수 설정

1. Static Web App 리소스 → 좌측 메뉴 **구성**
2. **➕ 추가** 클릭:
   | 이름 | 값 |
   |------|-----|
   | `VITE_API_URL` | `https://cj-ai-backend.koreacentral.azurecontainerapps.io` |
3. **저장**

#### 5-2. 백엔드 CORS 업데이트

1. Container App 리소스 → 좌측 메뉴 **컨테이너**
2. **편집 및 배포** 클릭
3. 컨테이너 이미지 옆 **편집** 클릭
4. 환경 변수에서 `CORS_ORIGINS` 수정:
   ```
   https://cj-ai-frontend.azurestaticapps.net,http://localhost:5173
   ```
5. **저장** → **만들기**

#### 5-3. staticwebapp.config.json 수정

GitHub 저장소의 `frontend/staticwebapp.config.json` 파일 수정:
```json
{
  "routes": [
    {
      "route": "/api/*",
      "allowedRoles": ["anonymous"],
      "rewrite": "https://cj-ai-backend.koreacentral.azurecontainerapps.io/api/*"
    }
  ]
}
```

커밋 & 푸시하면 자동 재배포됨.

---

### Step 6: 배포 확인

1. **백엔드 헬스체크**:
   - 브라우저에서 `https://cj-ai-backend.xxx.azurecontainerapps.io/api/health` 접속
   - `{"status": "healthy"}` 응답 확인

2. **프론트엔드 접속**:
   - `https://cj-ai-frontend.azurestaticapps.net` 접속
   - 대시보드에서 "서버 정상" 표시 확인

---

## ⌨️ CLI 배포 (명령어 방식)

<details>
<summary>CLI 명령어로 배포하기 (클릭해서 펼치기)</summary>

### Step 1: Azure 리소스 생성

```bash
# Azure 로그인
az login

# 리소스 그룹 생성
az group create --name rg-cj-ai-platform --location koreacentral

# Container Apps 환경 생성
az containerapp env create --name cj-ai-env \
    --resource-group rg-cj-ai-platform \
    --location koreacentral
```

### Step 2: 백엔드 배포

```bash
# GitHub Container Registry 로그인
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Docker 이미지 빌드 및 푸시
cd backend
docker build -t ghcr.io/YOUR_USERNAME/cj-ai-backend:latest .
docker push ghcr.io/YOUR_USERNAME/cj-ai-backend:latest

# Container App 생성
az containerapp create --name cj-ai-backend \
    --resource-group rg-cj-ai-platform \
    --environment cj-ai-env \
    --image ghcr.io/YOUR_USERNAME/cj-ai-backend:latest \
    --target-port 8000 \
    --ingress external \
    --env-vars \
        OPENAI_API_KEY=sk-xxx \
        SUPABASE_URL=https://xxx.supabase.co \
        SUPABASE_KEY=xxx \
        CORS_ORIGINS=http://localhost:5173
```

### Step 3: GitHub Actions 자동 배포 설정

GitHub 저장소 Settings → Secrets에 추가:

| Secret 이름 | 값 |
|------------|---|
| `AZURE_CREDENTIALS` | Azure Service Principal JSON |

```bash
# Service Principal 생성
az ad sp create-for-rbac --name "cj-ai-github-actions" \
    --role contributor \
    --scopes /subscriptions/{subscription-id}/resourceGroups/rg-cj-ai-platform \
    --sdk-auth
```

</details>

---

## 🔧 로컬 개발

### 프론트엔드
```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

### 백엔드
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## 📝 GitHub Actions (CI/CD 자동화)

GitHub에 푸시하면 자동 배포되도록 설정할 수 있습니다.

### 필요한 GitHub Secrets 설정

GitHub 저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret 이름 | 설명 | 얻는 방법 |
|------------|------|----------|
| `AZURE_CREDENTIALS` | Azure 인증 정보 | 아래 참조 |

### Azure Credentials 생성 방법

<details>
<summary>Azure Portal에서 생성하기 (클릭)</summary>

1. Azure Portal → **Microsoft Entra ID** (구 Azure AD)
2. 좌측 **앱 등록** → **➕ 새 등록**
3. 이름: `cj-ai-github-actions` → **등록**
4. 생성된 앱에서:
   - **개요** → `애플리케이션(클라이언트) ID` 복사
   - **개요** → `디렉터리(테넌트) ID` 복사
5. **인증서 및 비밀** → **➕ 새 클라이언트 비밀**
   - 설명: `github-actions`
   - 만료: 24개월
   - **추가** → 값 복사 (한 번만 표시됨!)
6. **구독** → 사용 중인 구독 → **액세스 제어(IAM)**
   - **➕ 추가** → **역할 할당 추가**
   - 역할: `Contributor`
   - 멤버: `cj-ai-github-actions` 앱 선택
   - **검토 + 할당**

7. 아래 JSON 형식으로 `AZURE_CREDENTIALS` 생성:
```json
{
  "clientId": "애플리케이션-ID",
  "clientSecret": "클라이언트-비밀-값",
  "subscriptionId": "구독-ID",
  "tenantId": "테넌트-ID"
}
```
</details>

<details>
<summary>Azure CLI로 생성하기 (클릭)</summary>

```bash
az ad sp create-for-rbac --name "cj-ai-github-actions" \
    --role contributor \
    --scopes /subscriptions/{구독ID}/resourceGroups/rg-cj-ai-platform \
    --sdk-auth
```
출력된 JSON 전체를 `AZURE_CREDENTIALS`에 저장

</details>

## 🔐 보안 설정

### CORS 설정 (backend/main.py)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-swa-name.azurestaticapps.net",  # 프로덕션
        "http://localhost:5173"  # 로컬 개발
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API 키 보호
- Azure Key Vault 또는 Container Apps Secrets 사용
- GitHub Secrets로 CI/CD 파이프라인에서 주입

## 💰 예상 비용 (월간)

| 서비스 | 티어 | 예상 비용 |
|--------|------|----------|
| Static Web Apps | Free | ₩0 |
| Container Apps | Consumption | ~₩10,000~30,000 |
| GitHub Container Registry | Free (Public) | ₩0 |
| **총 예상** | | **~₩10,000~30,000/월** |

*트래픽이 적은 경우 Container Apps도 무료 티어 내에서 운영 가능
*ghcr.io Private 저장소도 GitHub Free 플랜에서 500MB 무료

## 🆘 트러블슈팅

### CORS 오류
- Container Apps의 환경변수 `CORS_ORIGINS`에 SWA 도메인 추가
- `https://` 포함 전체 URL 입력

### API 연결 실패
- staticwebapp.config.json의 rewrite URL 확인
- Container Apps의 ingress 설정 확인 (external)

### 빌드 실패
- Node.js 버전 확인 (18.x 권장)
- Python 버전 확인 (3.11 권장)
