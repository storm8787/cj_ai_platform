# 백엔드 이미지 슬림화 설계 (근본책)

> 상태: **설계(제안)** — 구현 전. 2026-07 반복된 배포-다운 장애의 근본 원인 해소용.
> 관련: `docs/DEPLOYMENT.md`(블루-그린 배포), `.github/workflows/backend-deploy.yml`

---

## 1. 배경 / 문제

`cj-ai-backend` 컨테이너 이미지가 **약 9.6GB**라, cold start 시 이미지 pull에 **~13분**이 걸린다.
Azure Container Apps의 프로비저닝 데드라인은 **10분**이라, 새 리비전이 뜨기 전에 실패로 마킹 →
running replica 없음 → ingress 404/000 → **사이트 다운**.

- 블루-그린 배포(PR #24)로 "배포가 사이트를 죽이는" 것은 막았지만, **cold pull 13분 자체**는 그대로다.
  replica 재생성(플랫폼 유지보수·스케일 이벤트 등) 시 여전히 느리다.
- 근본 해결 = **이미지 크기 축소 → pull 시간을 데드라인 아래로.**

앱 코드 자체는 정상이다(로그상 `Application startup complete`, `GET / 200` 확인). 순수 인프라 문제다.

---

## 2. 조사 결과 — 9.6GB의 구성

| 구성 요소 | 추정 크기 | 필요성 | 근거 |
|-----------|-----------|--------|------|
| **torch (CUDA 빌드)** | **~5~6GB** | ❌ 낭비 | `requirements.txt`의 `torch>=2.6.0`이 CPU 인덱스 지정 없이 설치돼 nvidia CUDA 라이브러리가 딸려옴. 앱은 GPU 없음(`cpu:1`, `faiss-cpu`) |
| HF 모델 (이미지에 구움) | ~2.7GB | ⚠️ 필요하나 이미지에 있을 필요 없음 | `Dockerfile`의 `snapshot_download`로 bge-m3(~2.3GB) + ko-sroberta(~0.44GB)를 `/app/models`에 다운로드 |
| Python 의존성 | ~1~1.5GB | ✅ 필요 | transformers, sentence-transformers, FlagEmbedding, langchain 등 |
| fonts-noto-cjk | ~300MB | △ 과함 | CJK 폰트 전체 |
| Node 20 + npm(kordoc, korean-law-mcp) | ~200~400MB | ❌ 미사용 | Dockerfile 주석: "현재 CLI 호출 작동 안 함, 미래 대비 유지" |
| `data/` 벡터스토어 | 274MB | ✅ 유지 | `data/election_law`(110M), `data/vectorstores`(85M), `data/law_chatbot`(77M) |

**핵심**: 최대 덩어리는 모델(2.7GB)이 아니라 **불필요한 CUDA torch(~5~6GB)** 다. 인덱스 한 줄로 제거 가능.

### 모델 로딩 구조 (Phase 2에서 중요)

| 모델 | 로더 | 경로 지정 방식 | 용도 |
|------|------|----------------|------|
| bge-m3 | `BGEM3FlagModel` (`law_chatbot.py:181`) | `ENV EMBEDDING_MODEL=/app/models/bge-m3` (로컬 경로) ✓ | 법령 챗봇 (1024차원 dense+sparse) |
| ko-sroberta | `SentenceTransformer` (`vectorstore.py:38`) | 하드코딩 repo-id `"jhgan/ko-sroberta-multitask"` → HF 캐시 | 보도자료·선거법 (768차원) |

- 모델은 모두 **지연 로딩**(첫 요청 시 싱글톤). uvicorn은 모델과 무관하게 즉시 8000 바인딩.
- ⚠️ ko-sroberta는 이미지에 `/app/models/ko-sroberta-multitask`로 구워지지만, 코드는 **repo-id로 로드**해 HF 캐시를 봄
  → 구워진 사본이 실제로 안 쓰이고 런타임 재다운로드될 가능성. Phase 2에서 경로 통일 시 함께 정리.

---

## 3. 설계 — 2단계

### 🥇 Phase 1 — CPU torch + 정리 (저위험 · 최대 효과)

- **CPU 전용 torch 설치**: `torch`를 CPU 인덱스로 분리 설치하여 CUDA 라이브러리 제거.
  ```dockerfile
  # requirements.txt 에서 torch 줄 제거 후, 별도 설치
  RUN pip install --no-cache-dir torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
  RUN pip install --no-cache-dir -r requirements.txt
  ```
- (선택) **미사용 Node/MCP CLI 제거** — 빌드 시간·용량 절감. *docs상 "미래 대비 유지"라 유지/제거는 결정 필요.*
- (선택) **multi-stage 빌드** — gcc/g++ 등 빌드 도구를 최종 이미지에서 제외.
- **예상 결과: 9.6GB → ~4GB, pull ~13분 → ~5분** (데드라인 아래로 내려갈 공산 큼)
- **위험: 낮음.** torch는 어차피 CPU로만 구동. 앱 코드 변경 없음. `use_fp16=True`는 CPU에서 무시/폴백되므로 동작 동일.

### 🥈 Phase 2 — 모델을 런타임 볼륨으로 분리 (근본책)

- **Azure Files 볼륨**을 ACA에 마운트(예: `/app/models`), 모델은 볼륨에 **1회 사전 적재**.
  `Dockerfile`의 모델 `snapshot_download` `RUN` 제거 → 이미지에서 2.7GB 제거.
- 볼륨은 영속되므로 replica/revision이 바뀌어도 재다운로드 없음. 지연 로딩이라 부팅도 계속 빠름.
- **로딩 경로 통일**: bge-m3는 이미 ENV 경로 사용 ✓ / ko-sroberta는 repo-id → 볼륨 내 고정 경로로 변경.
- **예상 결과: ~4GB → ~1.5GB, pull ~2분.**
- **위험: 중간.** ACA 볼륨 설정(managed environment storage) + **법령 챗봇(CLAUDE.md 최우선 보호 영역)** 로딩
  동작을 정확히 보존해야 함. 반드시 `python backend/tests/evaluate_law_chatbot.py --mode mock` **10/10 재확인**.

#### Phase 2 대안(비권장) — 모델을 별도 base 이미지 레이어로 분리
`FROM cj-ai-backend-base:models` 방식은 레이어 캐시로 **빌드**는 빨라지지만, ACA는 새 노드/replica에서
**전체 이미지를 새로 pull**하므로 **cold pull 시간은 줄지 않는다.** 근본 해결은 볼륨 분리다.

---

## 4. 권장 순서

```
Phase 1 (CPU torch)  → 저위험으로 데드라인 문제 사실상 해소   ← 먼저
Phase 2 (볼륨 분리)  → 이미지 최소화 + cold pull ~2분         ← 그다음, 신중히
```

Phase 1만으로도 pull이 데드라인 아래로 내려갈 가능성이 크고, 블루-그린(PR #24)이 이미 안전망을
깔았으므로, **Phase 1 우선 구현**을 권장한다.

---

## 5. 검증 기준

- 배포 빌드 로그에서 이미지 크기 / Azure SYSTEM 로그의 `Successfully pulled image ... in <초>` 확인
- `python backend/tests/evaluate_law_chatbot.py --mode mock` → 10/10 통과 (법령 챗봇 회귀 없음)
- 보도자료·선거법(ko-sroberta 사용 기능) 정상 동작 확인
- 블루-그린 배포가 새 리비전 Running 확인 후 트래픽 전환하는지(무중단) 확인
