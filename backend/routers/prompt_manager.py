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
# name/icon: 기능(feature) 표시용
# keys: prompt_key(영문) → 화면 표시용 한글 라벨
#   · DB·코드의 prompt_key 자체는 영문 그대로 유지(안정성) 하고, 화면에만 한글을 노출한다.
#   · 매핑에 없는 key(예: kakao_promo의 카테고리명)는 key 원문을 그대로 표시한다.
FEATURE_META = {
    "press_release": {
        "name": "보도자료 생성기", "icon": "📰",
        "keys": {
            "system_prompt": "시스템 프롬프트",
            "additional_instructions": "추가 지시사항",
            "user_query_template": "사용자 질의 템플릿",
            "full_prompt_template": "전체 프롬프트 템플릿",
        },
    },
    "election_law": {
        "name": "선거법 챗봇", "icon": "🗳️",
        "keys": {
            "classify_question_type": "질문 유형 분류",
            "multi_query_generation": "다중 검색어 생성",
            "answer_list_type": "목록형 답변 생성",
            "answer_general": "일반 답변 생성",
        },
    },
    "law_chatbot": {
        "name": "법령·자치법규 챗봇", "icon": "⚖️",
        "keys": {
            "answer_system_prompt": "답변 시스템 프롬프트",
            "legal_query_planner_prompt": "법령 검색계획 프롬프트",
        },
    },
    "trip_report": {
        "name": "출장보고 생성기", "icon": "✈️",
        "keys": {
            "classification_prompt": "이미지 분류 프롬프트",
            "extraction_prompt": "정보 추출 프롬프트",
            "report_system_prompt": "보고서 시스템 프롬프트",
            "report_prompt_template": "보고서 생성 템플릿",
            "rewrite_system_prompt": "재작성 시스템 프롬프트",
            "rewrite_prompt_template": "재작성 템플릿",
        },
    },
    "timeline_planner": {
        "name": "사업 타임라인", "icon": "📅",
        "keys": {
            "suggest_prompt": "타임라인 제안 프롬프트",
            "detail_with_law": "법령 연계 상세화",
            "detail_execute_phase1": "집행단계 상세화(1단계)",
            "detail_complete": "완료단계 상세화",
        },
    },
    "meeting_summarizer": {
        "name": "회의록 요약기", "icon": "📝",
        "keys": {
            "summary_prompt_focused": "핵심 요약 프롬프트",
            "summary_prompt_all": "전체 요약 프롬프트",
            "directive_prompt": "지시사항 반영 프롬프트",
        },
    },
    "report_writer": {
        "name": "업무보고 생성기", "icon": "📋",
        "keys": {
            "build_prompt_template": "보고서 작성 템플릿",
            "system_prompt": "시스템 프롬프트",
        },
    },
    "kakao_promo": {
        "name": "카카오 홍보문구", "icon": "💬",
        # prompt_key가 카테고리 한글명(행사/재난알림/기타 등)이라 별도 라벨 불필요
        "keys": {},
    },
    "merit_report": {
        "name": "공적조서 생성기", "icon": "🏆",
        "keys": {
            "generation_prompt": "공적조서 생성 프롬프트",
        },
    },
    "news": {
        "name": "뉴스 요약", "icon": "📰",
        "keys": {
            "summarize_system": "요약 시스템 프롬프트",
            "summarize_prompt": "요약 프롬프트",
        },
    },
    "translator": {
        "name": "다국어 번역기", "icon": "🌐",
        "keys": {
            "gpt_translate_system": "번역 시스템 프롬프트",
            "gpt_translate_prompt": "번역 프롬프트",
        },
    },
    "disaster_report": {
        "name": "재난 일일보고", "icon": "🚨",
        "keys": {
            "system_prompt": "시스템 프롬프트",
            "summary_prompt": "요약 프롬프트",
            "body_prompt": "본문 생성 프롬프트",
        },
    },
}


def _key_label(feature: str, prompt_key: str) -> str:
    """prompt_key(영문)를 화면 표시용 한글 라벨로 변환. 매핑 없으면 원문 반환."""
    meta = FEATURE_META.get(feature, {})
    return meta.get("keys", {}).get(prompt_key, prompt_key)


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
        p["prompt_key_label"] = _key_label(p["feature"], p["prompt_key"])

    return {"prompts": prompts}


@router.get("/by-feature/{feature}")
async def get_prompts_by_feature(feature: str, authorization: Optional[str] = Header(None)):
    """특정 기능의 프롬프트 목록"""
    await _verify_admin(authorization)
    
    prompts = await prompt_service.list_all()
    filtered = [p for p in prompts if p["feature"] == feature]

    meta = FEATURE_META.get(feature, {})
    for p in filtered:
        p["prompt_key_label"] = _key_label(feature, p["prompt_key"])

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