"""
충주시 AI 플랫폼 - FastAPI 백엔드
Azure Container Apps 배포용
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import logging

from config import settings
from routers import press_release, election_law, news, health
from routers import merit_report, data_analysis, translator
from routers import address_geocoder, kakao_promo, excel_merger, meeting_summarizer
from routers import report_writer
from routers import auth
from routers import data_validator
from routers import board
from routers import trip_report
from routers import law_chatbot
from routers import timeline_planner
from routers.prompt_manager import router as prompt_manager_router
from routers import hwpx_converter
from routers import disaster_dashboard
from routers import openai_usage
from services.api_quota_service import get_user_info_from_token, check_and_increment, DAILY_LIMIT

logger = logging.getLogger(__name__)

# ── OpenAI quota 적용 대상 엔드포인트 ─────────────────────────────────
# (method, exact_path 또는 prefix) → feature 이름
_QUOTA_EXACT: dict[str, str] = {
    "/api/press-release/generate":          "보도자료",
    "/api/election-law/ask":               "선거법챗봇",
    "/api/news/summarize":                 "뉴스요약",
    "/api/timeline/suggest":              "타임라인",
    "/api/timeline/detail-tasks":         "타임라인",
    "/api/meeting/summarize":             "회의요약",
    "/api/meeting/summarize-file":        "회의요약",
    "/api/trip-report/analyze-images":    "출장보고",
    "/api/trip-report/generate-report":   "출장보고",
    "/api/report-writer/generate":        "업무보고",
    "/api/law-chatbot/ask":               "법령챗봇",
    "/api/kakao-promo/generate":          "카카오홍보",
    "/api/kakao-promo/generate-with-image": "카카오홍보",
    "/api/merit-report/generate":         "공적조서",
    "/api/translator/translate":          "번역기",
    "/api/data-analysis/analyze":         "통계분석",
    "/api/disaster/reports/daily/generate": "재난일일보고",
}

# prefix 매칭 (동적 경로 대응)
_QUOTA_PREFIX: dict[str, str] = {
    "/api/disaster/analyze/": "재난대시보드",
}


def _get_feature(path: str) -> str | None:
    """경로가 quota 대상이면 feature명 반환, 아니면 None."""
    if path in _QUOTA_EXACT:
        return _QUOTA_EXACT[path]
    for prefix, feature in _QUOTA_PREFIX.items():
        if path.startswith(prefix):
            return feature
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행"""
    print("🚀 충주시 AI 플랫폼 백엔드 시작")
    print(f"📍 CORS Origins: {settings.cors_origins_list}")
    yield
    print("👋 백엔드 종료")


app = FastAPI(
    title="충주시 AI 플랫폼 API",
    description="보도자료 생성, 선거법 챗봇, 뉴스 관리 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Processed-Count", "X-Total-Rows", "X-Total-Cols", "X-Errors"],
)


# ── OpenAI 일일 사용량 제한 미들웨어 ────────────────────────────────────
@app.middleware("http")
async def openai_quota_middleware(request: Request, call_next):
    """
    POST 요청이 AI 엔드포인트에 해당하면:
    1. Authorization 헤더에서 사용자 추출
    2. 관리자: 기록만 하고 통과
    3. 일반 사용자: 오늘 사용량 >= 50이면 429 반환
    토큰 없거나 Supabase 연결 실패 시: 통과 (실패 개방 원칙)
    """
    if request.method == "POST":
        feature = _get_feature(request.url.path)
        if feature:
            authorization = request.headers.get("Authorization", "")
            token = authorization.replace("Bearer ", "").strip() if authorization else ""

            if token and settings.SUPABASE_URL:
                try:
                    user_info = await get_user_info_from_token(token)
                    if user_info:
                        allowed, used, remaining = await check_and_increment(
                            user_info["user_id"],
                            feature,
                            user_info["is_admin"],
                        )
                        if not allowed:
                            kst_tomorrow = (
                                datetime.now().date() + timedelta(days=1)
                            ).isoformat()
                            return JSONResponse(
                                status_code=429,
                                content={
                                    "detail": (
                                        "일일 AI 사용 한도에 도달했습니다. "
                                        "일반 사용자는 하루 최대 50회까지 AI 기능을 사용할 수 있습니다. "
                                        "내일 다시 이용해 주세요."
                                    ),
                                    "daily_limit": DAILY_LIMIT,
                                    "used_count": used,
                                    "remaining_count": 0,
                                    "reset_at": f"{kst_tomorrow}T00:00:00+09:00",
                                },
                            )
                except Exception as e:
                    # quota 오류는 non-blocking — 요청은 통과
                    logger.warning(f"[quota middleware] 오류 (non-fatal): {e}")

    return await call_next(request)


# ── 라우터 등록 ──────────────────────────────────────────────────────
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(press_release.router, prefix="/api/press-release", tags=["Press Release"])
app.include_router(election_law.router, prefix="/api/election-law", tags=["Election Law"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(merit_report.router, prefix="/api/merit-report", tags=["공적조서"])
app.include_router(data_analysis.router, prefix="/api/data-analysis", tags=["통계분석"])
app.include_router(translator.router, prefix="/api/translator", tags=["번역기"])

# 기능 라우터
app.include_router(address_geocoder.router, prefix="/api/geocoder", tags=["주소-좌표 변환"])
app.include_router(kakao_promo.router, prefix="/api/kakao-promo", tags=["카카오 홍보문구"])
app.include_router(excel_merger.router, prefix="/api/excel-merger", tags=["엑셀 취합기"])
app.include_router(meeting_summarizer.router, prefix="/api/meeting", tags=["회의요약기"])
app.include_router(report_writer.router, prefix="/api/report-writer", tags=["업무보고"])
app.include_router(data_validator.router, prefix="/api/data-validator", tags=["공공데이터 검증기"])
app.include_router(trip_report.router, prefix="/api/trip-report", tags=["출장보고"])

# 법령 챗봇 / 타임라인 / 프롬프트
app.include_router(law_chatbot.router)
app.include_router(timeline_planner.router)
app.include_router(prompt_manager_router)

# HWPX 변환기
app.include_router(hwpx_converter.router)

# 재난상황 대시보드
app.include_router(disaster_dashboard.router, prefix="/api/disaster", tags=["재난상황 대시보드"])

# 인증 / 게시판
app.include_router(auth.router, prefix="/api/auth", tags=["인증"])
app.include_router(board.router, prefix="/api/board", tags=["게시판"])

# OpenAI 사용량 조회
app.include_router(openai_usage.router, prefix="/api/openai-usage", tags=["OpenAI 사용량"])


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "충주시 AI 플랫폼 API",
        "version": "1.0.0",
        "platform": "Azure Container Apps",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
