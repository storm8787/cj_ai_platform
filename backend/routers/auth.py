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
                return AuthResponse(
                    success=True,
                    message="이메일 인증이 완료되었습니다!",
                    access_token=data.get("access_token"),
                    refresh_token=data.get("refresh_token"),
                    user=data.get("user")
                )
            else:
                error_msg = data.get("error_description") or data.get("msg") or "인증 실패"
                
                if "invalid" in str(error_msg).lower() or "expired" in str(error_msg).lower():
                    error_msg = "인증 코드가 올바르지 않거나 만료되었습니다."
                
                return AuthResponse(success=False, message=error_msg)
                
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
                return AuthResponse(
                    success=True,
                    message="로그인 성공!",
                    access_token=data.get("access_token"),
                    refresh_token=data.get("refresh_token"),
                    user=data.get("user")
                )
            else:
                error_msg = data.get("error_description") or data.get("msg") or "로그인 실패"
                
                if "invalid" in str(error_msg).lower():
                    error_msg = "이메일 또는 비밀번호가 올바르지 않습니다."
                elif "email not confirmed" in str(error_msg).lower():
                    error_msg = "이메일 인증이 필요합니다. 메일함을 확인해주세요."
                
                return AuthResponse(success=False, message=error_msg)
                
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
    """토큰 검증"""
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
                return TokenVerifyResponse(
                    valid=True,
                    user={
                        "id": user.get("id"),
                        "email": user.get("email"),
                        "created_at": user.get("created_at")
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
                return AuthResponse(
                    success=True,
                    message="토큰 갱신 성공",
                    access_token=data.get("access_token"),
                    refresh_token=data.get("refresh_token"),
                    user=data.get("user")
                )
            else:
                return AuthResponse(success=False, message="토큰 갱신 실패")
                
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
        
        # 2. 프로필(권한, 이름, 부서) 가져오기
        profile_response = await client.get(
            f"{SUPABASE_URL}/rest/v1/user_profiles?id=eq.{user['id']}&select=role,name,department",
            headers={**HEADERS, "Authorization": f"Bearer {token}"}
        )
        
        role = 'user'
        name = None
        department = None
        
        if profile_response.status_code == 200:
            profile = profile_response.json()
            if profile and len(profile) > 0:
                role = profile[0].get('role', 'user')
                name = profile[0].get('name')
                department = profile[0].get('department')
        
        return {
            "id": user['id'],
            "email": user['email'],
            "name": name,
            "department": department,
            "role": role,
            "isAdmin": role == 'admin'
        }


@router.get("/status")
async def get_status():
    """서비스 상태 확인"""
    return {
        "status": "active",
        "service": "인증 서비스",
        "supabase_url": SUPABASE_URL[:30] + "..." if SUPABASE_URL else "Not configured"
    }