# AI 작업지침서 (Claude Code용)

이 저장소에서 AI 에이전트(Claude Code)가 작업할 때 따라야 할 원칙과 패턴을 정리합니다.

---

## 시작 전 필수 확인 사항

1. `CLAUDE.md` 읽기 (루트 디렉토리)
2. 브랜치 확인: `git branch` → main이면 새 브랜치 생성
3. 작업 범위 파악: 기능 → 파일 대응은 `docs/FEATURE_MAP.md` 참고

---

## 브랜치 전략

```bash
# 새 작업 시작
git checkout main
git pull origin main
git checkout -b claude/작업내용-랜덤ID

# 작업 후
git add 변경파일들
git commit -m "feat: 설명"
git push -u origin claude/작업내용-랜덤ID
# → PR 생성 후 사용자 승인 → 머지
```

**절대 금지**: `git push origin main`

---

## 파일 수정 전 확인 패턴

### 라우터 수정 시

```
1. 해당 라우터 파일 전체 읽기
2. 의존 서비스 파일 확인
3. main.py에서 라우터 등록 방식 확인
4. 변경사항이 다른 엔드포인트에 영향을 미치는지 확인
```

### 법령 챗봇 수정 시 추가 확인

```
1. docs/LAW_CHATBOT_GUIDE.md 읽기
2. 키워드 사전 매핑이 아닌 방식인지 검토
3. GPT planner 결과에 의존하는 방식인지 확인
4. 수정 후: python tests/evaluate_law_chatbot.py --mode mock
   → 10/10 통과 확인 후 커밋
```

### 환경변수 추가 시

```
1. backend/config.py의 Settings 클래스에 필드 추가
2. docs/ENVIRONMENT_VARIABLES.md 업데이트
3. CLAUDE.md 업데이트 (필요 시)
4. 실제 값은 절대 커밋하지 않음
```

---

## 코드 작성 원칙

### 1. 단순성 우선

- 요청된 것만 구현 (over-engineering 금지)
- 추상화는 실제 필요할 때만
- 비슷한 코드 3곳 있어야 추출 고려

### 2. 에러 처리

- 시스템 경계(사용자 입력, 외부 API)에서만 검증
- 내부 함수 간 호출에서 불필요한 try-except 추가 금지
- 외부 API 실패는 graceful degradation (빈 리스트 반환 등)

### 3. 주석

- WHY가 명확하지 않을 때만 작성
- 코드가 하는 일을 설명하는 주석 금지
- 현재 태스크, 이슈번호 참조 주석 금지 (PR 설명에 넣기)

### 4. 보안

- API 키, 패스워드, 토큰을 코드에 절대 포함하지 않음
- 사용자 입력은 경계에서만 검증
- SQL injection, XSS 등 OWASP Top 10 주의

---

## 자주 하는 실수 방지

### 법령 챗봇 관련

| 실수 | 올바른 방법 |
|-----|-----------|
| "특정 키워드가 있으면 특정 법령을 검색" 코드 추가 | GPT planner 프롬프트에서 판단하도록 |
| 특정 법령/지역에 boost 점수 하드코딩 | planner의 plan.law_name 일치도만으로 점수 계산 |
| "충주시" prefix를 강제로 붙이는 코드 | planner 프롬프트에서 자치법규 시 "충주시" 명시 규칙 적용 |
| 시행령/시행규칙을 admrul로 분류 | law로 분류해야 함 (planner 프롬프트 규칙 참고) |

### 배포 관련

| 실수 | 올바른 방법 |
|-----|-----------|
| main 브랜치에 직접 push | PR → 승인 → 머지 |
| requirements.txt 업데이트 없이 새 패키지 import | requirements.txt에 먼저 추가 |
| Dockerfile 변경 후 로컬에서만 테스트 | Actions에서 전체 빌드 확인 |

---

## 작업별 체크리스트

### 새 라우터/기능 추가

- [ ] `backend/routers/` 에 새 파일 생성
- [ ] `backend/main.py` 에 라우터 등록
- [ ] `frontend/src/pages/` 에 페이지 컴포넌트 생성
- [ ] `frontend/src/App.jsx` 에 Route 추가
- [ ] `docs/FEATURE_MAP.md` 업데이트
- [ ] 필요한 환경변수가 있으면 `docs/ENVIRONMENT_VARIABLES.md` 업데이트

### 법령 챗봇 수정

- [ ] `docs/LAW_CHATBOT_GUIDE.md` 확인
- [ ] 키워드 사전 매핑 패턴 없는지 검토
- [ ] `python tests/evaluate_law_chatbot.py --mode mock` 10/10 통과
- [ ] `_rank_candidates()`, `_select_relevant_articles()` 수정 시 planner 결과만 신뢰하는지 확인

### PR 생성 전

- [ ] 불필요한 파일 변경 없는지 확인
- [ ] `.env` 파일, 실제 API 키 포함 없는지 확인
- [ ] 테스트/평가 통과 확인
- [ ] 커밋 메시지가 명확한지 확인

---

## 긴급 상황 대응

### 배포 후 서비스 장애

1. 최근 배포 Actions 확인 (빌드 실패 여부)
2. Azure Container Apps 로그 확인
3. 롤백이 필요하면 이전 SHA 태그로 `az containerapp update` 실행
4. 문제 분석 후 hotfix 브랜치에서 수정 → 빠른 PR 머지

### 법령 챗봇 응답 품질 저하

1. `/api/law-chatbot/status` 확인
2. `law_api.connected` false면 LAW_API_OC 환경변수 확인
3. planner 품질 문제면 `--mode planner` 평가 실행
4. 문제 케이스 식별 후 planner 프롬프트 개선

---

## 프로젝트 특이사항

### httpx 의존성

`backend/requirements.txt`에 `#httpx==0.27.0`으로 주석 처리됨.
httpx는 `openai>=1.12.0`의 transitive dependency로 설치됨.
직접 import는 가능하나 버전 고정이 안 되어 있으므로 openai 업그레이드 시 주의.

### BGE-M3 모델

Dockerfile에서 빌드 시 HuggingFace에서 다운로드.
로컬에서는 `/app/models/bge-m3`에 없으면 `FlagEmbedding`이 자동 다운로드 시도.
모델 크기가 크므로 첫 빌드는 시간이 오래 걸림.

### Korean Law MCP

`korean-law-mcp` npm 패키지는 JSON-RPC stdio MCP 서버로 설계됨.
현재 코드의 CLI 형태 호출(`korean-law search_law --query ...`)은 작동하지 않음.
실제 검색은 law.go.kr 직접 API가 담당.
MCP 관련 로그 `[korean-law-mcp] CLI 실패 rc=1`은 정상 동작의 일부임.

### Supabase 프롬프트 관리

`prompt_service.py`는 Supabase에서 프롬프트 템플릿을 가져옴.
`get(category, key, default=...)` 형태로 호출.
Supabase에 없으면 코드의 기본값(`_DEFAULT_...`) 사용.
배포 환경에서 프롬프트를 코드 변경 없이 조정하려면 Supabase에 저장.
