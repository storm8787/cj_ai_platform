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
| POST | `/api/prompts/reset-default` | DB 프롬프트를 코드 기본값으로 재설정 | admin |
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

## 6-1. 기능 메타데이터 (`FEATURE_META`)

`backend/routers/prompt_manager.py`의 `FEATURE_META`가 관리 화면 표시를 담당한다.

- `name` / `icon`: 기능(feature) 탭·그룹 표시
- `keys`: **`prompt_key`(영문) → 화면 표시용 한글 라벨** 매핑
  - DB·코드의 `prompt_key` 자체는 영문 그대로 유지(안정성)하고 **화면에만 한글**을 노출한다.
  - API(`/list`, `/by-feature`)가 각 프롬프트에 `prompt_key_label`을 붙여 반환.
  - 매핑에 없는 key(예: `kakao_promo`의 카테고리명은 이미 한글)는 key 원문을 그대로 표시.
  - 편집 패널에서는 한글 라벨과 함께 원문 영문 key도 작게 병기(관리자 식별용).

현재 등록된 기능: 보도자료·선거법·법령챗봇·출장보고·타임라인·회의요약·업무보고·카카오홍보·공적조서·뉴스요약·번역기·**재난 일일보고(`disaster_report`)**.

> `disaster_report`는 `services/disaster_report_service.py`가 `prompt_service.get("disaster_report", ...)`로
> 사용하고 있어 관리 대상이지만 이전에는 `FEATURE_META`에 누락되어 있었다(원문 key로만 표시). 이제 등록됨.

---

## 6-2. 코드 기본값 노출 (DB 미저장 프롬프트도 관리 화면에 표시)

관리자 목록(`/list`, `/by-feature`)은 원래 **DB `prompts`에 저장된 row만** 반환했다.
따라서 아직 DB에 seed되지 않은 프롬프트(코드 `_DEFAULT_*`만 존재)는 관리 화면에 **아예 보이지 않아 관리자가 조회·수정할 수 없었다.**

이를 해소하기 위해 `backend/services/prompt_defaults.py` 레지스트리를 두고,
`FEATURE_META`에 등록된 키 중 **DB에 없는 것은 코드 기본값을 합성 항목으로 함께 반환**한다.

- 합성 항목 필드: `is_default=True`, `id="default:{feature}:{key}"`, `updated_at=null`, `content=코드 기본값`
- 화면에서는 **"미저장" 배지**와 안내 문구를 표시하며, 관리자가 **저장하면 그때 DB로 insert**되어 이후 요청부터 DB 값이 우선 적용된다.
- 단일 소스 유지: 레지스트리는 기본값을 복사하지 않고 실제 기능 모듈의 상수를 **지연 참조**한다.
- 현재 레지스트리 등록: `report_writer`의 `system_prompt`, `build_prompt_template`. (다른 기능도 필요 시 `_REGISTRY`에 추가)

> ⚠️ 이미 DB에 **구버전** row가 저장돼 있으면 합성 항목이 추가되지 않고 DB 값이 그대로 표시된다.
> (DB가 소스이므로 정상) — 코드 기본값이 갱신됐다면 관리자가 화면에서 내용을 확인·갱신해야 한다.

### 6-3. 코드 기본값으로 재설정 (`/reset-default`)

**문제**: 코드의 `_DEFAULT_*` 프롬프트를 개선·배포해도, DB에 옛 row가 저장돼 있으면
`prompt_service.get()`이 DB 값을 우선 반환해 **코드 개선이 반영되지 않는다**(silent override).

**해결**: 관리 화면에서 DB row가 사용 중인 프롬프트(코드 기본값 존재 시)에 대해
**"코드 기본값으로 재설정"** 버튼을 제공 → `/reset-default`가 현재 코드 기본값(`prompt_defaults`)으로
DB row를 덮어쓰고 이력을 남긴다. 재설정 후 즉시 최신 코드 프롬프트가 적용된다.

- 응답의 `has_code_default`로 재설정 가능 여부를 표시(레지스트리에 등록된 키만)
- `is_default=false && has_code_default=true`(=DB값이 코드보다 우선인 상태)일 때 안내 문구 노출

---

## 7. 수정 시 주의사항

- admin 역할 확인: Supabase `user_profiles.role = 'admin'`
- 새 기능의 프롬프트 추가 시: 코드에 `_DEFAULT_*` 상수 먼저 추가 → DB는 선택
- **새 기능/새 prompt_key 추가 시 `FEATURE_META`의 `name`·`keys`에도 한글 라벨을 등록**할 것 (안 하면 화면에 영문 key 노출)
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
