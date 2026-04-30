# 프롬프트 중앙 관리

## 1. 기능 개요

- **목적**: AI 기능의 프롬프트를 코드 재배포 없이 Supabase DB에서 관리
- **사용 대상**: 관리자 (admin 역할)
- **처리 내용**: Supabase `prompts` 테이블에 기능별 프롬프트 저장 → API로 조회/수정

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/prompt_manager.py` |
| 프롬프트 서비스 | `backend/services/prompt_service.py` |
| 프론트엔드 페이지 | `frontend/src/pages/PromptManager.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/prompts` (라우터 내부 선언)

| 메서드 | 경로 | 설명 | 권한 |
|-------|------|------|------|
| GET | `/api/prompts/features` | 기능 목록 | 인증 |
| GET | `/api/prompts/list` | 전체 프롬프트 목록 | admin |
| GET | `/api/prompts/by-feature/{feature}` | 기능별 프롬프트 | admin |
| PUT | `/api/prompts/update` | 프롬프트 수정 | admin |
| POST | `/api/prompts/history` | 변경 이력 조회 | admin |
| POST | `/api/prompts/refresh-cache` | 캐시 강제 갱신 | admin |

---

## 4. 주요 데이터 흐름

### 프롬프트 조회 (3단계 fallback)

```
prompt_service.get(feature, prompt_key, default=_DEFAULT_*)
    ↓
1단계: 메모리 캐시 (TTL 5분)
    ↓ 캐시 miss
2단계: Supabase DB 재로드
    ↓ DB 없음
3단계: 코드 하드코딩 기본값 (_DEFAULT_* 상수)
```

### 프롬프트 수정

```
관리자 → PUT /api/prompts/update
    → Supabase prompts 테이블 업데이트
    → prompt_history 이력 저장
    → 캐시 갱신
```

---

## 5. Supabase 테이블 구조

```sql
-- 프롬프트 저장
prompts (
  id,
  feature,        -- 기능명 (press_release, law_chatbot 등)
  prompt_key,     -- 프롬프트 키 (system_prompt 등)
  content,        -- 프롬프트 내용
  is_active,
  updated_at,
  UNIQUE(feature, prompt_key)
)

-- 변경 이력
prompt_history (
  id,
  prompt_id,
  old_content,
  new_content,
  changed_by,
  changed_at
)
```

---

## 6. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | Supabase API 키 |

---

## 7. 수정 시 주의사항

- admin 역할 확인: Supabase `user_profiles.role = 'admin'`
- 새 기능의 프롬프트 추가 시: 코드에 `_DEFAULT_*` 상수 먼저 추가 → DB는 선택
- 변수 치환은 호출측에서 `.format()` 처리 (예: `prompt.format(department="자치행정과")`)
- Supabase 연결 실패 시 하드코딩 기본값으로 자동 fallback

---

## 8. 테스트 및 검증 방법

- admin 계정으로 `GET /api/prompts/list` 호출 후 기능별 프롬프트 확인
- `PUT /api/prompts/update`로 수정 후 `POST /api/prompts/refresh-cache` 호출
- 해당 기능 API 재호출 후 수정된 프롬프트가 적용되는지 확인

---

## 9. 향후 개선 과제

- 프롬프트 A/B 테스트 기능
- 변경 이력 롤백 기능
- 기능별 프롬프트 템플릿 변수 목록 자동 추출
