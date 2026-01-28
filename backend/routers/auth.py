"""
인증 API - Supabase Auth 연동
회원가입, 로그인, 로그아웃, 토큰 검증
"""
from fastapi import APIRouter, HTTPException, Depends, Header
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
    """회원가입"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/auth/v1/signup",
                headers=HEADERS,
                json={
                    "email": request.email,
                    "password": request.password
                }
            )
            
            data = response.json()
            
            if response.status_code == 200:
                # 이메일 확인이 필요한 경우
                if data.get("id") and not data.get("access_token"):
                    return AuthResponse(
                        success=True,
                        message="회원가입 완료! 이메일을 확인해주세요.",
                        user={"id": data.get("id"), "email": data.get("email")}
                    )
                # 이메일 확인 없이 바로 로그인
                return AuthResponse(
                    success=True,
                    message="회원가입 성공!",
                    access_token=data.get("access_token"),
                    refresh_token=data.get("refresh_token"),
                    user=data.get("user")
                )
            else:
                error_msg = data.get("error_description") or data.get("msg") or "회원가입 실패"
                
                # 이미 존재하는 이메일
                if "already registered" in str(error_msg).lower():
                    error_msg = "이미 가입된 이메일입니다."
                
                return AuthResponse(success=False, message=error_msg)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원가입 오류: {str(e)}")


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
                
                # 에러 메시지 한글화
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
            response = await client.post(
                f"{SUPABASE_URL}/auth/v1/logout",
                headers={
                    **HEADERS,
                    "Authorization": f"Bearer {token}"
                }
            )
            
            return AuthResponse(success=True, message="로그아웃 완료")
            
    except Exception as e:
        # 로그아웃은 실패해도 클라이언트에서 토큰 삭제하면 됨
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


@router.get("/status")
async def get_status():
    """서비스 상태 확인"""
    return {
        "status": "active",
        "service": "인증 서비스",
        "supabase_url": SUPABASE_URL[:30] + "..." if SUPABASE_URL else "Not configured"
    }
@router.get("/me", response_model=dict)
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
        
        # 2. 프로필(권한) 가져오기
        profile_response = await client.get(
            f"{SUPABASE_URL}/rest/v1/user_profiles?id=eq.{user['id']}&select=*",
            headers={**HEADERS, "Authorization": f"Bearer {token}"}
        )
        
        profile = profile_response.json()
        role = profile[0]['role'] if profile else 'user'
        
        return {
            "id": user['id'],
            "email": user['email'],
            "role": role,
            "isAdmin": role == 'admin'
        }