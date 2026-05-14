"""
OpenAI 일일 사용량 조회 API

GET /api/openai-usage/status  - 본인 사용량 (로그인 필요)
GET /api/admin/openai-usage   - 전체 사용량 (관리자 전용)
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from config import settings
from services.api_quota_service import get_user_info_from_token, get_usage_status, get_kst_today
import httpx

router = APIRouter()

SUPABASE_URL = settings.SUPABASE_URL
_SVC_HEADERS = {
    "apikey": settings.SUPABASE_KEY,
    "Authorization": f"Bearer {settings.SUPABASE_KEY}",
    "Content-Type": "application/json",
}
KST = timezone(timedelta(hours=9))


async def _require_user(authorization: Optional[str]) -> dict:
    """Authorization 헤더에서 사용자 정보 추출. 실패 시 401."""
    if not authorization:
        raise HTTPException(status_code=401, detail="인증 필요")
    token = authorization.replace("Bearer ", "")
    info = await get_user_info_from_token(token)
    if not info:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰")
    return info


@router.get("/status")
async def get_my_usage(authorization: Optional[str] = Header(None)):
    """현재 사용자 오늘 OpenAI 사용량 조회"""
    info = await _require_user(authorization)
    status = await get_usage_status(info["user_id"], info["is_admin"])
    return status


@router.get("/admin/all")
async def get_all_usage(authorization: Optional[str] = Header(None)):
    """전체 사용자 오늘 사용량 조회 (관리자 전용)"""
    info = await _require_user(authorization)
    if not info["is_admin"]:
        raise HTTPException(status_code=403, detail="관리자만 접근할 수 있습니다.")

    today = get_kst_today()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/api_usage_daily",
                params={
                    "usage_date": f"eq.{today}",
                    "provider": "eq.openai",
                    "select": "user_id,feature,request_count,updated_at",
                    "order": "updated_at.desc",
                },
                headers=_SVC_HEADERS,
            )
            rows = resp.json() if resp.status_code == 200 else []

        # 사용자별 합산
        user_totals: dict = {}
        for row in rows:
            uid = row["user_id"]
            user_totals[uid] = user_totals.get(uid, 0) + row["request_count"]

        summary = [
            {"user_id": uid, "used_count": count, "daily_limit": 50}
            for uid, count in sorted(user_totals.items(), key=lambda x: -x[1])
        ]

        return {
            "today_kst": today,
            "total_users": len(summary),
            "users": summary,
            "raw_rows": rows,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"사용량 조회 오류: {str(e)}")
