# 인증 시스템

## 1. 기능 개요

- **목적**: 충주시 AI 플랫폼 사용자 인증 및 역할(admin/user) 관리
- **사용 대상**: 충주시청 전 공무원 (로그인 필수)
- **처리 내용**: Supabase Auth 기반 이메일/OTP 인증 + 역할 관리

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/auth.py` |
| 프론트엔드 페이지 | `frontend/src/pages/Login.jsx` |
| 인증 컨텍스트 | `frontend/src/context/AuthContext.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/auth` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/auth/signup` | 회원가입 (OTP 이메일 발송) |
| POST | `/api/auth/verify-otp` | OTP 코드 검증 |
| POST | `/api/auth/resend-otp` | OTP 재발송 |
| POST | `/api/auth/login` | 이메일/비밀번호 로그인 |
| POST | `/api/auth/logout` | 로그아웃 |
| GET | `/api/auth/verify` | 토큰 검증 + 사용자·역할 정보 반환 |
| POST | `/api/auth/refresh` | 액세스 토큰 갱신 |
| GET | `/api/auth/me` | 현재 사용자 정보 + 역할/관리자 여부 |
| GET | `/api/auth/status` | 서비스 상태 |

---

## 4. 주요 데이터 흐름

```
회원가입 플로우:
POST /signup → Supabase Auth (OTP 이메일 발송)
POST /verify-otp → OTP 검증 → user_profiles 생성

로그인 플로우:
POST /login → Supabase Auth → JWT 토큰 반환
GET /verify → 토큰 검증 → user_profiles에서 역할 조회
```

---

## 5. 역할 구조

| 역할 | 설명 |
|-----|------|
| `user` | 일반 사용자. AI 기능 전체 사용. QnA 게시판 작성 가능 |
| `admin` | 관리자. 게시판 관리, 프롬프트 수정, QnA 답변 작성 가능 |

역할 저장 위치: Supabase `user_profiles.role` 컬럼

---

## 6. Supabase 테이블

```
user_profiles (
  id,
  email,
  name,
  department,
  role,         -- 'user' | 'admin'
  created_at
)
```

---

## 7. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | Supabase API 키 (anon 또는 service) |

---

## 8. 수정 시 주의사항

- JWT 토큰은 Authorization 헤더 Bearer 방식
- admin 역할 확인 로직: `user_profiles.role == 'admin'`
- OTP는 Supabase Auth 이메일 기능 사용
- Supabase RLS(Row Level Security): 현재 비활성화 상태일 수 있음 (프로덕션 활성화 권장)

---

## 9. 테스트 및 검증 방법

- 이메일로 회원가입 → OTP 확인 → 로그인 → JWT 토큰으로 API 호출
- `GET /api/auth/me`로 role 및 isAdmin 확인

---

## 10. 향후 개선 과제

- Supabase RLS 활성화 (프로덕션 보안 강화)
- 소셜 로그인 추가 (카카오, Google 등)
- 로그인 시도 횟수 제한
