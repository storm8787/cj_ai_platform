"""
인증 API - Supabase Auth 연동
회원가입(OTP), 로그인, 로그아웃, 토큰 검증
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr
from typing import Optional
import httpx

from config import settings

router = APIRouter()


# ===========================================
# 📋 요청/응답 모델
# ===========================================
class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    department: str


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class ResendOTPRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[dict] = None


class TokenVerifyResponse(BaseModel):
    valid: bool
    user: Optional[dict] = None


# ===========================================
# 🔧 Supabase Auth 헬퍼
# ===========================================
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Content-Type": "application/json"
}


def _supabase_unreachable(action: str, err: Exception) -> HTTPException:
    """
    Supabase 호출 시 발생한 네트워크 오류(DNS 해석 실패·연결 거부·타임아웃 등)를
    사용자 친화적인 503 응답으로 변환한다.

    원인의 대부분은 코드가 아니라 인프라/설정 측에 있다:
      - SUPABASE_URL 환경변수 누락/오타
      - Supabase 프로젝트 일시정지(무료 플랜은 미사용 시 자동 정지)
      - 컨테이너 egress/DNS 차단
    raw errno("[Errno -2] Name or service not known")를 그대로 노출하지 않고,
    서버 로그에만 상세 원인을 남긴다.
    """
    print(f"[auth] ❌ Supabase 연결 실패({action}): {err!r}")
    return HTTPException(
        status_code=503,
        detail=(
            "인증 서버에 일시적으로 연결할 수 없습니다. 잠시 후 다시 시도해주세요. "
            "(문제가 계속되면 관리자에게 문의하세요)"
        ),
    )


async def _fetch_user_profile(client: httpx.AsyncClient, user_id: str, token: str) -> dict:
    """user_profiles 테이블에서 role/name/department 조회"""
    try:
        profile_response = await client.get(
            f"{SUPABASE_URL}/rest/v1/user_profiles?id=eq.{user_id}&select=role,name,department",
            headers={**HEADERS, "Authorization": f"Bearer {token}"}
        )
        if profile_response.status_code == 200:
            profile = profile_response.json()
            if profile and len(profile) > 0:
                return {
                    "role": profile[0].get("role", "user"),
                    "name": profile[0].get("name"),
                    "department": profile[0].get("department"),
                }
    except Exception as e:
        print(f"[auth] ⚠️ user_profiles 조회 실패: {e}")
    return {"role": "user", "name": None, "department": None}


async def _enrich_user_with_role(user: dict, token: str) -> dict:
    """Supabase auth user 객체에 role/name/department/isAdmin 추가"""
    if not user or not user.get("id"):
        return user
    async with httpx.AsyncClient() as client:
        profile = await _fetch_user_profile(client, user["id"], token)
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "created_at": user.get("created_at"),
        "name": profile["name"],
        "department": profile["department"],
        "role": profile["role"],
        "isAdmin": profile["role"] == "admin",
    }


# ===========================================
# 🌐 API 엔드포인트
# ===========================================
@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignUpRequest):
    """회원가입 - OTP 이메일 발송"""
    try:
        async with httpx.AsyncClient() as client:
            # 1. 회원가입 요청 (이메일 OTP 발송됨)
            response = await client.post(
                f"{SUPABASE_URL}/auth/v1/signup",
                headers=HEADERS,
                json={
                    "email": request.email,
                    "password": request.password,
                    "options": {
                        "data": {
                            "name": request.name,
                            "department": request.department
                        }
                    }
                }
            )
            
            data = response.json()
            
            if response.status_code == 200:
                user_id = data.get("id")
                
                # 2. user_profiles에 추가 정보 저장
                if user_id:
                    await client.post(
                        f"{SUPABASE_URL}/rest/v1/user_profiles",
                        headers={**HEADERS, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "resolution=merge-duplicates"},
                        json={
                            "id": user_id,
                            "email": request.email,
                            "name": request.name,
                            "department": request.department,
                            "role": "user"
                        }
                    )
                
                return AuthResponse(
                    success=True,
                    message="인증 코드가 이메일로 발송되었습니다. 이메일을 확인해주세요.",
                    user={"id": user_id, "email": request.email}
                )
            else:
                error_msg = data.get("error_description") or data.get("msg") or "회원가입 실패"
                
                if "already registered" in str(error_msg).lower():
                    error_msg = "이미 가입된 이메일입니다."
                
                return AuthResponse(success=False, message=error_msg)
                
    except (httpx.RequestError, OSError) as e:
        raise _supabase_unreachable("signup", e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원가입 오류: {str(e)}")


@router.post("/verify-otp", response_model=AuthResponse)
async def verify_otp(request: VerifyOTPRequest):
    """OTP 코드 검증"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/auth/v1/verify",
                headers=HEADERS,
                json={
                    "email": request.email,
                    "token": request.otp,
                    "type": "signup"
                }
            )
            
            data = response.json()
            
            if response.status_code == 200 and data.get("access_token"):
                access_token = data.get("access_token")
                user = data.get("user") or {}
                enriched_user = await _enrich_user_with_role(user, access_token)
                
                return AuthResponse(
                    success=True,
                    message="이메일 인증이 완료되었습니다!",
                    access_token=access_token,
                    refresh_token=data.get("refresh_token"),
                    user=enriched_user
                )
            else:
                error_msg = data.get("error_description") or data.get("msg") or "인증 실패"
                
                if "invalid" in str(error_msg).lower() or "expired" in str(error_msg).lower():
                    error_msg = "인증 코드가 올바르지 않거나 만료되었습니다."
                
                return AuthResponse(success=False, message=error_msg)
                
    except (httpx.RequestError, OSError) as e:
        raise _supabase_unreachable("verify-otp", e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"인증 오류: {str(e)}")


@router.post("/resend-otp", response_model=AuthResponse)
async def resend_otp(request: ResendOTPRequest):
    """OTP 재발송"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/auth/v1/resend",
                headers=HEADERS,
                json={
                    "email": request.email,
                    "type": "signup"
                }
            )
            
            if response.status_code == 200:
                return AuthResponse(
                    success=True,
                    message="인증 코드가 재발송되었습니다."
                )
            else:
                return AuthResponse(
                    success=False,
                    message="인증 코드 재발송에 실패했습니다."
                )
                
    except (httpx.RequestError, OSError) as e:
        raise _supabase_unreachable("resend-otp", e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"재발송 오류: {str(e)}")


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """로그인"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                headers=HEADERS,
                json={
                    "email": request.email,
                    "password": request.password
                }
            )
            
            data = response.json()
            
            if response.status_code == 200:
                access_token = data.get("access_token")
                user = data.get("user") or {}
                enriched_user = await _enrich_user_with_role(user, access_token)
                
                return AuthResponse(
                    success=True,
                    message="로그인 성공!",
                    access_token=access_token,
                    refresh_token=data.get("refresh_token"),
                    user=enriched_user
                )
            else:
                error_msg = data.get("error_description") or data.get("msg") or "로그인 실패"
                
                if "invalid" in str(error_msg).lower():
                    error_msg = "이메일 또는 비밀번호가 올바르지 않습니다."
                elif "email not confirmed" in str(error_msg).lower():
                    error_msg = "이메일 인증이 필요합니다. 메일함을 확인해주세요."
                
                return AuthResponse(success=False, message=error_msg)
                
    except (httpx.RequestError, OSError) as e:
        raise _supabase_unreachable("login", e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 오류: {str(e)}")


@router.post("/logout", response_model=AuthResponse)
async def logout(authorization: Optional[str] = Header(None)):
    """로그아웃"""
    try:
        if not authorization:
            return AuthResponse(success=True, message="로그아웃 완료")
        
        token = authorization.replace("Bearer ", "")
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{SUPABASE_URL}/auth/v1/logout",
                headers={
                    **HEADERS,
                    "Authorization": f"Bearer {token}"
                }
            )
            
            return AuthResponse(success=True, message="로그아웃 완료")
            
    except Exception as e:
        return AuthResponse(success=True, message="로그아웃 완료")


@router.get("/verify", response_model=TokenVerifyResponse)
async def verify_token(authorization: Optional[str] = Header(None)):
    """토큰 검증 - role/isAdmin 포함"""
    try:
        if not authorization:
            return TokenVerifyResponse(valid=False)
        
        token = authorization.replace("Bearer ", "")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    **HEADERS,
                    "Authorization": f"Bearer {token}"
                }
            )
            
            if response.status_code == 200:
                user = response.json()
                # user_profiles에서 role 조회
                profile = await _fetch_user_profile(client, user.get("id"), token)
                
                return TokenVerifyResponse(
                    valid=True,
                    user={
                        "id": user.get("id"),
                        "email": user.get("email"),
                        "created_at": user.get("created_at"),
                        "name": profile["name"],
                        "department": profile["department"],
                        "role": profile["role"],
                        "isAdmin": profile["role"] == "admin",
                    }
                )
            else:
                return TokenVerifyResponse(valid=False)
                
    except Exception as e:
        return TokenVerifyResponse(valid=False)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(refresh_token: str):
    """토큰 갱신"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
                headers=HEADERS,
                json={"refresh_token": refresh_token}
            )
            
            data = response.json()
            
            if response.status_code == 200:
                access_token = data.get("access_token")
                user = data.get("user") or {}
                enriched_user = await _enrich_user_with_role(user, access_token)
                
                return AuthResponse(
                    success=True,
                    message="토큰 갱신 성공",
                    access_token=access_token,
                    refresh_token=data.get("refresh_token"),
                    user=enriched_user
                )
            else:
                return AuthResponse(success=False, message="토큰 갱신 실패")
                
    except (httpx.RequestError, OSError) as e:
        raise _supabase_unreachable("refresh", e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"토큰 갱신 오류: {str(e)}")


@router.get("/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """현재 사용자 정보 + 권한 조회"""
    if not authorization:
        raise HTTPException(status_code=401, detail="인증 필요")
    
    token = authorization.replace("Bearer ", "")
    
    async with httpx.AsyncClient() as client:
        # 1. 사용자 정보 가져오기
        user_response = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={**HEADERS, "Authorization": f"Bearer {token}"}
        )
        
        if user_response.status_code != 200:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰")
        
        user = user_response.json()
        profile = await _fetch_user_profile(client, user["id"], token)
        
        return {
            "id": user['id'],
            "email": user['email'],
            "name": profile["name"],
            "department": profile["department"],
            "role": profile["role"],
            "isAdmin": profile["role"] == 'admin'
        }


@router.get("/status")
async def get_status():
    """
    서비스 상태 + Supabase 연결 진단.

    로그인 시 '[Errno -2] Name or service not known' 같은 DNS/네트워크 오류가
    났을 때, 이 엔드포인트로 백엔드 → Supabase 연결 가능 여부를 즉시 확인한다.
    시크릿(전체 URL·키)은 노출하지 않는다.
    """
    result = {
        "status": "active",
        "service": "인증 서비스",
        "supabase_url_configured": bool(SUPABASE_URL),
        "supabase_url": (SUPABASE_URL[:30] + "...") if SUPABASE_URL else "Not configured",
        "supabase_reachable": None,
        "supabase_detail": None,
    }

    if not SUPABASE_URL:
        result["supabase_detail"] = "SUPABASE_URL 환경변수가 설정되지 않았습니다."
        return result

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 인증 불필요한 health 엔드포인트로 연결성만 확인
            resp = await client.get(f"{SUPABASE_URL}/auth/v1/health", headers=HEADERS)
        result["supabase_reachable"] = True
        result["supabase_detail"] = f"HTTP {resp.status_code}"
    except httpx.RequestError as e:
        # DNS 해석 실패·연결 거부·타임아웃 등 → 인프라/설정 문제
        result["supabase_reachable"] = False
        result["supabase_detail"] = f"{type(e).__name__}: {e}"

    return result