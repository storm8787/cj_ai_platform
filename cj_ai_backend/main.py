from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import press_release_router
from routers import translator_router

app = FastAPI(
    title="충주시 AI 플랫폼 API",
    description="충주시 행정업무 지원 AI API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    #allow_origins=[
    #    "http://localhost:5173",  # Vite 개발서버
    #    "http://127.0.0.1:5173",
    #    "https://cj-ai.netlify.app",  # Netlify 배포 주소 (실제 주소로 변경 필요)
    #],
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(press_release_router.router)
app.include_router(translator_router.router)

@app.get("/")
async def root():
    return {
        "message": "충주시 AI 플랫폼 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)