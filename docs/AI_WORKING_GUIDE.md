# AI 작업지침서 (Claude Code용)

이 저장소에서 AI 에이전트(Claude Code 등)가 작업할 때 따라야 할 원칙과 패턴입니다.

---

## 시작 전 필수 확인 순서

```
1. CLAUDE.md                    ← 핵심 규칙·금지사항
2. docs/INDEX.md                ← 전체 문서 진입점
3. docs/ARCHITECTURE.md         ← 시스템 구조
4. docs/features/해당기능.md    ← 수정할 기능 전용 문서
5. 실제 파일 열어 확인           ← 코드 작성 전 반드시 확인
```

---

## 브랜치 전략

```bash
# 새 작업 시작
git checkout main && git pull origin main
git checkout -b claude/작업내용-랜덤ID

# 완료 후
git add 변경파일들  # 특정 파일만 (git add -A 지양)
git commit -m "feat: 명확한 설명"
git push -u origin claude/작업내용-랜덤ID
# → PR 생성 → 사용자 승인 → 머지
```

**절대 금지**: `git push origin main` (직접 push)

---

## 파일 수정 전 확인 패턴

### 새 기능 추가 시

```
1. backend/routers/ 에 새 파일 생성
2. backend/main.py 에 라우터 등록 확인
3. frontend/src/pages/ 에 페이지 컴포넌트 생성
4. frontend/src/App.jsx 에 Route 추가
5. docs/features/새기능.md 작성
6. docs/INDEX.md 에 링크 추가
7. 환경변수 추가 시 docs/ENVIRONMENT_VARIABLES.md 업데이트
```

### 법령 챗봇 수정 시

```
1. docs/features/law_chatbot.md 읽기
2. 키워드 사전 매핑 방식이 아닌지 검토
3. GPT planner 결과에 의존하는 방식인지 확인
4. 수정 후: python tests/evaluate_law_chatbot.py --mode mock (10/10 확인)
```

### 환경변수 추가 시

```
1. backend/config.py Settings 클래스에 필드 추가
2. docs/ENVIRONMENT_VARIABLES.md 업데이트
3. 실제 값은 절대 커밋하지 않음
```

---

## 코드 작성 원칙

### 1. 단순성 우선

- 요청된 것만 구현 (과도한 추상화, 미래 확장 고려 금지)
- 비슷한 코드 3곳 이상일 때만 추출 고려
- 완성되지 않은 구현 금지

### 2. 에러 처리 최소화

- 시스템 경계(사용자 입력, 외부 API)에서만 검증
- 내부 함수 간 불필요한 try-except 추가 금지
- 외부 API 실패: graceful degradation (빈 리스트 반환 등)

### 3. 주석

- WHY가 비명백할 때만 작성 (숨겨진 제약, 버그 우회책 등)
- "이 코드는 X를 합니다" 형태의 설명 주석 금지
- 현재 작업·이슈번호 참조 주석 금지 (PR 설명에 넣기)

### 4. 보안

- API 키, 패스워드, 토큰 → 코드·문서에 절대 하드코딩 금지
- 사용자 입력 → 경계에서만 검증
- `data_analysis.py`의 `allow_dangerous_code=True` 참고: LangChain Agent가 임의 Python 실행 가능 → 사용자 입력 sanitize 주의

---

## 기능별 자주 하는 실수 방지

### 법령 챗봇

| 실수 | 올바른 방법 |
|-----|-----------|
| 특정 키워드로 특정 법령을 결정하는 if 분기 추가 | GPT planner 프롬프트에서 처리 |
| 지역/기관명 boost 점수 하드코딩 | planner의 plan.law_name 일치도만으로 점수 계산 |
| "충주시" prefix 코드에서 강제 추가 | planner 시스템 프롬프트의 자치법규 규칙 활용 |
| 시행령/시행규칙을 admrul로 분류 | law로 분류해야 함 |

### 배포

| 실수 | 올바른 방법 |
|-----|-----------|
| main 브랜치 직접 push | PR → 승인 → 머지 |
| requirements.txt 없이 새 패키지 import | requirements.txt 먼저 추가 |
| Dockerfile 수정 없이 시스템 패키지 의존 | Dockerfile RUN 단계에 추가 |

### 문서

| 실수 | 올바른 방법 |
|-----|-----------|
| 확인 안 된 기능·파일명 문서에 기재 | 직접 확인 후 "확인 필요" 표시 |
| 실제 API 키·토큰 문서에 기재 | 환경변수명만 기재 |
| PROJECT_DOCUMENTATION.md 수정 | docs/ 하위 관련 문서 수정 |

---

## 작업별 체크리스트

### 코드 변경 PR 생성 전

- [ ] 불필요한 파일 변경 없는지 확인
- [ ] `.env` 파일, 실제 API 키 커밋 없는지 확인
- [ ] `requirements.txt` 업데이트 확인 (새 패키지 추가 시)
- [ ] 법령 챗봇 변경 시 mock 평가 10/10 통과 확인
- [ ] 관련 docs/features/*.md 업데이트 확인

### 문서 작성 시

- [ ] 실제 파일 경로 확인 (추측 금지)
- [ ] 비밀값 포함 여부 확인
- [ ] "확인 필요" 표시 필요한 내용 확인
- [ ] docs/INDEX.md 링크 업데이트 확인

---

## 긴급 상황 대응

### 배포 후 서비스 장애

1. 최근 Actions 로그 확인 (빌드 실패 여부)
2. Azure Container Apps 로그 확인
3. `/api/health`, `/api/law-chatbot/status` 응답 확인
4. 롤백 필요 시 이전 SHA로 `az containerapp update`
5. hotfix 브랜치에서 수정 → 빠른 PR

### 법령 챗봇 응답 없음

1. `GET /api/law-chatbot/status` 확인
2. `law_api.connected: false` → `LAW_API_OC` 환경변수 확인
3. `[korean-law-mcp] CLI 실패 rc=1` 로그 → 정상 (직접 API fallback 동작)
4. `api.connected: false` → law.go.kr API 자체 문제 가능

---

## 프로젝트 특이사항

### httpx 의존성

`backend/requirements.txt`에 `#httpx==0.27.0` 주석 처리됨.
`openai>=1.12.0`의 transitive dependency로 설치됨. 버전 고정 안 됨 — openai 업그레이드 시 주의.

### BGE-M3 모델

Dockerfile에서 HuggingFace에서 다운로드(`BAAI/bge-m3`). 모델 크기로 인해 첫 빌드 시간 길어짐.
로컬에서는 `FlagEmbedding`이 자동 다운로드 시도.

### Korean Law MCP

CLI 형태 호출 작동 안 함. 로그 `[korean-law-mcp] CLI 실패 rc=1` → 정상. law.go.kr 직접 API가 실제 동작.

### Supabase 프롬프트 관리

`prompt_service.get(category, key, default=_DEFAULT_*)` 패턴.
Supabase 없으면 코드의 `_DEFAULT_*` 상수로 fallback. 3단계: 캐시 → DB → 기본값.

### LangChain Pandas Agent

`data_analysis.py`에서 `allow_dangerous_code=True`. 임의 Python 코드 실행 가능. 보안 유의.

### DeepL 버전 제약

`deepl>=1.16.0,<2.0.0`. 2.x `Translator` 클래스 deprecated → FastAPI 환경 오류.
