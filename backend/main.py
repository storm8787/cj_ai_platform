"""
충주시 AI 플랫폼 - FastAPI 백엔드
Azure Container Apps 배포용
"""
import langchain_experimental
print(f"🔍 langchain_experimental version: {langchain_experimental.__version__}")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from routers import press_release, election_law, news, health
from routers import merit_report, data_analysis, translator
from routers import address_geocoder, kakao_promo, excel_merger, meeting_summarizer

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행"""
    # 시작 시
    print("🚀 충주시 AI 플랫폼 백엔드 시작")
    print(f"📍 CORS Origins: {settings.cors_origins_list}")
    yield
    # 종료 시
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
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Processed-Count", "X-Total-Rows", "X-Total-Cols", "X-Errors"],
)

# 라우터 등록
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(press_release.router, prefix="/api/press-release", tags=["Press Release"])
app.include_router(election_law.router, prefix="/api/election-law", tags=["Election Law"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(merit_report.router, prefix="/api/merit-report", tags=["공적조서"])
app.include_router(data_analysis.router, prefix="/api/data-analysis", tags=["통계분석"])
app.include_router(translator.router, prefix="/api/translator", tags=["번역기"])

# 새로 추가된 라우터
app.include_router(address_geocoder.router, prefix="/api/geocoder", tags=["주소-좌표 변환"])
app.include_router(kakao_promo.router, prefix="/api/kakao-promo", tags=["카카오 홍보문구"])
app.include_router(excel_merger.router, prefix="/api/excel-merger", tags=["엑셀 취합기"])
app.include_router(meeting_summarizer.router, prefix="/api/meeting", tags=["회의요약기"])


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
