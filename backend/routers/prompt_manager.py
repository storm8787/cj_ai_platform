"""
프롬프트 관리 API - 관리자 전용

엔드포인트:
  GET  /api/prompts/list          - 전체 프롬프트 목록
  GET  /api/prompts/features      - 기능 목록 (카테고리)
  GET  /api/prompts/{feature}     - 특정 기능의 프롬프트 목록
  PUT  /api/prompts/update        - 프롬프트 수정
  GET  /api/prompts/history       - 변경 이력 조회
  POST /api/prompts/refresh-cache - 캐시 강제 갱신
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
import httpx

from config import settings
from services.prompt_service import prompt_service

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


# ─── 기능 메타데이터 ───
FEATURE_META = {
    "press_release": {"name": "보도자료 생성기", "icon": "📰"},
    "election_law": {"name": "선거법 챗봇", "icon": "🗳️"},
    "law_chatbot": {"name": "법령·자치법규 챗봇", "icon": "⚖️"},
    "trip_report": {"name": "출장보고 생성기", "icon": "✈️"},
    "timeline_planner": {"name": "사업 타임라인", "icon": "📅"},
    "meeting_summarizer": {"name": "회의록 요약기", "icon": "📝"},
    "report_writer": {"name": "업무보고 생성기", "icon": "📋"},
    "kakao_promo": {"name": "카카오 홍보문구", "icon": "💬"},
    "merit_report": {"name": "공적조서 생성기", "icon": "🏆"},
    "news": {"name": "뉴스 요약", "icon": "📰"},
    "translator": {"name": "다국어 번역기", "icon": "🌐"},
}


# ─── Pydantic 모델 ───
class PromptUpdateRequest(BaseModel):
    feature: str
    prompt_key: str
    content: str


class PromptHistoryRequest(BaseModel):
    feature: str
    prompt_key: str
    limit: int = 10


# ─── 권한 확인 헬퍼 ───
async def _verify_admin(authorization: Optional[str]) -> str:
    """관리자 권한 확인, 이메일 반환"""
    if not authorization:
        raise HTTPException(status_code=401, detail="인증 필요")
    
    token = authorization.replace("Bearer ", "")
    
    async with httpx.AsyncClient() as client:
        # 1. 유저 정보
        user_resp = await client.get(
            f"{settings.SUPABASE_URL}/auth/v1/user",
            headers={
                "apikey": settings.SUPABASE_KEY,
                "Authorization": f"Bearer {token}",
            },
        )
        if user_resp.status_code != 200:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰")
        
        user = user_resp.json()
        user_id = user.get("id")
        email = user.get("email", "")
        
        # 2. 관리자 여부 확인
        profile_resp = await client.get(
            f"{settings.SUPABASE_URL}/rest/v1/user_profiles?id=eq.{user_id}&select=role",
            headers={
                "apikey": settings.SUPABASE_KEY,
                "Authorization": f"Bearer {token}",
            },
        )
        
        if profile_resp.status_code == 200:
            profiles = profile_resp.json()
            if profiles and profiles[0].get("role") == "admin":
                return email
        
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")


# ─── API 엔드포인트 ───
@router.get("/features")
async def get_features():
    """기능 목록 반환"""
    return {
        "features": [
            {"id": k, "name": v["name"], "icon": v["icon"]}
            for k, v in FEATURE_META.items()
        ]
    }


@router.get("/list")
async def list_prompts(authorization: Optional[str] = Header(None)):
    """전체 프롬프트 목록 (관리자 전용)"""
    await _verify_admin(authorization)
    
    prompts = await prompt_service.list_all()
    
    # 기능 메타데이터 병합
    for p in prompts:
        meta = FEATURE_META.get(p["feature"], {})
        p["feature_name"] = meta.get("name", p["feature"])
        p["feature_icon"] = meta.get("icon", "📄")
    
    return {"prompts": prompts}


@router.get("/by-feature/{feature}")
async def get_prompts_by_feature(feature: str, authorization: Optional[str] = Header(None)):
    """특정 기능의 프롬프트 목록"""
    await _verify_admin(authorization)
    
    prompts = await prompt_service.list_all()
    filtered = [p for p in prompts if p["feature"] == feature]
    
    meta = FEATURE_META.get(feature, {})
    
    return {
        "feature": feature,
        "feature_name": meta.get("name", feature),
        "feature_icon": meta.get("icon", "📄"),
        "prompts": filtered,
    }


@router.put("/update")
async def update_prompt(
    request: PromptUpdateRequest,
    authorization: Optional[str] = Header(None),
):
    """프롬프트 수정 (관리자 전용)"""
    email = await _verify_admin(authorization)
    
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="프롬프트 내용이 비어있습니다")
    
    success = await prompt_service.update(
        feature=request.feature,
        prompt_key=request.prompt_key,
        content=request.content,
        changed_by=email,
    )
    
    if success:
        return {"success": True, "message": "프롬프트가 업데이트되었습니다"}
    else:
        raise HTTPException(status_code=500, detail="프롬프트 업데이트 실패")


@router.post("/history")
async def get_history(
    request: PromptHistoryRequest,
    authorization: Optional[str] = Header(None),
):
    """프롬프트 변경 이력 조회"""
    await _verify_admin(authorization)
    
    history = await prompt_service.get_history(
        feature=request.feature,
        prompt_key=request.prompt_key,
        limit=request.limit,
    )
    
    return {"history": history}


@router.post("/refresh-cache")
async def refresh_cache(authorization: Optional[str] = Header(None)):
    """캐시 강제 갱신"""
    await _verify_admin(authorization)
    prompt_service.refresh()
    return {"success": True, "message": "캐시가 갱신되었습니다"}