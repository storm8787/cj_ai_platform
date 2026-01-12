"""헬스체크 엔드포인트"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "cj-ai-backend",
        "platform": "Azure Container Apps"
    }
