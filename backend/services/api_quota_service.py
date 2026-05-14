"""
OpenAI API 일일 사용량 제한 서비스

- 일반 사용자: KST 기준 하루 50회
- 관리자: 무제한 (기록은 남김)
- api_usage_daily 테이블 사용
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import logging
import httpx

from config import settings

logger = logging.getLogger(__name__)

DAILY_LIMIT = 50
PROVIDER = "openai"
KST = timezone(timedelta(hours=9))

SUPABASE_URL = settings.SUPABASE_URL
_SVC_HEADERS = {
    "apikey": settings.SUPABASE_KEY,
    "Authorization": f"Bearer {settings.SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# ── 간단한 인메모리 role 캐시 (5분 TTL) ──────────────────────────────
_role_cache: dict = {}  # {user_id: (is_admin, expires_at)}
_ROLE_CACHE_TTL = 300


def _get_cached_role(user_id: str) -> Optional[bool]:
    entry = _role_cache.get(user_id)
    if entry and datetime.now() > entry[1]:
        del _role_cache[user_id]
        return None
    return entry[0] if entry else None


def _set_cached_role(user_id: str, is_admin: bool) -> None:
    _role_cache[user_id] = (is_admin, datetime.now() + timedelta(seconds=_ROLE_CACHE_TTL))


# ── KST 오늘 날짜 ────────────────────────────────────────────────────
def get_kst_today() -> str:
    return datetime.now(KST).date().isoformat()


# ── 사용자 정보 추출 ─────────────────────────────────────────────────
async def get_user_info_from_token(token: str) -> Optional[dict]:
    """
    Authorization 헤더 토큰으로 user_id / is_admin 조회.
    1) Supabase Auth /auth/v1/user  →  user_id
    2) user_profiles 테이블          →  role (캐시 5분)
    실패 시 None 반환 (quota 처리 건너뜀).
    """
    if not token or not SUPABASE_URL:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 1. 사용자 id 확인
            auth_resp = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "apikey": settings.SUPABASE_KEY,
                    "Authorization": f"Bearer {token}",
                },
            )
            if auth_resp.status_code != 200:
                return None
            user_id: str = auth_resp.json().get("id")
            if not user_id:
                return None

            # 2. role 확인 (캐시 우선)
            cached = _get_cached_role(user_id)
            if cached is not None:
                return {"user_id": user_id, "is_admin": cached}

            profile_resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/user_profiles",
                params={"id": f"eq.{user_id}", "select": "role"},
                headers=_SVC_HEADERS,
            )
            role = "user"
            if profile_resp.status_code == 200 and profile_resp.json():
                role = profile_resp.json()[0].get("role", "user")
            is_admin = role == "admin"
            _set_cached_role(user_id, is_admin)
            return {"user_id": user_id, "is_admin": is_admin}
    except Exception as e:
        logger.warning(f"[quota] 사용자 정보 조회 실패: {e}")
        return None


# ── 오늘 사용량 조회 ─────────────────────────────────────────────────
async def get_usage_today(user_id: str) -> int:
    """오늘(KST) 해당 사용자의 OpenAI 총 호출 횟수"""
    today = get_kst_today()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/api_usage_daily",
                params={
                    "usage_date": f"eq.{today}",
                    "provider": f"eq.{PROVIDER}",
                    "user_id": f"eq.{user_id}",
                    "select": "request_count",
                },
                headers=_SVC_HEADERS,
            )
            if resp.status_code == 200:
                return sum(row["request_count"] for row in resp.json())
        return 0
    except Exception as e:
        logger.warning(f"[quota] 사용량 조회 실패 (user={user_id}): {e}")
        return 0


# ── 사용량 증가 ──────────────────────────────────────────────────────
async def increment_usage(user_id: str, feature: str) -> None:
    """오늘 사용량 1 증가 (feature row 단위 upsert)"""
    today = get_kst_today()
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 기존 row 확인
            find_resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/api_usage_daily",
                params={
                    "usage_date": f"eq.{today}",
                    "provider": f"eq.{PROVIDER}",
                    "user_id": f"eq.{user_id}",
                    "feature": f"eq.{feature}",
                    "select": "id,request_count",
                },
                headers=_SVC_HEADERS,
            )
            rows = find_resp.json() if find_resp.status_code == 200 else []

            if rows:
                row = rows[0]
                await client.patch(
                    f"{SUPABASE_URL}/rest/v1/api_usage_daily",
                    params={"id": f"eq.{row['id']}"},
                    json={"request_count": row["request_count"] + 1, "updated_at": now_iso},
                    headers=_SVC_HEADERS,
                )
            else:
                await client.post(
                    f"{SUPABASE_URL}/rest/v1/api_usage_daily",
                    json={
                        "usage_date": today,
                        "provider": PROVIDER,
                        "user_id": user_id,
                        "feature": feature,
                        "request_count": 1,
                        "updated_at": now_iso,
                    },
                    headers=_SVC_HEADERS,
                )
    except Exception as e:
        logger.warning(f"[quota] 사용량 증가 실패 (user={user_id}, feature={feature}): {e}")


# ── 확인 + 증가 ──────────────────────────────────────────────────────
async def check_and_increment(
    user_id: str,
    feature: str,
    is_admin: bool,
) -> Tuple[bool, int, int]:
    """
    사용량 확인 후 허용되면 1 증가.
    Returns: (allowed, used_count, remaining_count)
      - admin: allowed=True, remaining=-1 (무제한)
      - user: allowed=(used < DAILY_LIMIT)
    """
    current = await get_usage_today(user_id)

    if not is_admin and current >= DAILY_LIMIT:
        return False, current, 0

    await increment_usage(user_id, feature)
    new_count = current + 1
    remaining = -1 if is_admin else max(0, DAILY_LIMIT - new_count)
    return True, new_count, remaining


# ── 상태 조회 (API 응답용) ────────────────────────────────────────────
async def get_usage_status(user_id: str, is_admin: bool) -> dict:
    today = get_kst_today()
    used = await get_usage_today(user_id)
    kst_tomorrow = (datetime.now(KST).date() + timedelta(days=1)).isoformat()
    return {
        "today_kst": today,
        "user_id": user_id,
        "is_admin": is_admin,
        "daily_limit": None if is_admin else DAILY_LIMIT,
        "used_count": used,
        "remaining_count": -1 if is_admin else max(0, DAILY_LIMIT - used),
        "limit_exceeded": False if is_admin else used >= DAILY_LIMIT,
        "reset_at": f"{kst_tomorrow}T00:00:00+09:00",
        "message": (
            "관리자는 사용량 제한이 없습니다."
            if is_admin
            else f"오늘 {used}/{DAILY_LIMIT}회 사용하셨습니다."
        ),
    }
