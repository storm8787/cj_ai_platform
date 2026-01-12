"""뉴스 관리 API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import httpx
import json

from config import settings
from services.openai_service import OpenAIService

router = APIRouter()
openai_service = OpenAIService()


class SummarizeRequest(BaseModel):
    title: str
    content: str
    link: str = ""


@router.get("/list")
async def get_news_list():
    """뉴스 목록 조회 (GitHub Gist에서)"""
    if not settings.GIST_ID or not settings.GITHUB_TOKEN:
        return {"news": [], "source": "not_configured"}
    
    try:
        async with httpx.AsyncClient() as client:
            # Gist 메타데이터 가져오기
            response = await client.get(
                f"https://api.github.com/gists/{settings.GIST_ID}",
                headers={
                    "Authorization": f"token {settings.GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return {"news": [], "source": "gist_error", "error": response.text}
            
            gist_data = response.json()
            
            # news_data.json 파일 찾기
            files = gist_data.get("files", {})
            news_file = files.get("news_data.json")
            
            if not news_file:
                return {"news": [], "source": "file_not_found"}
            
            # raw_url에서 데이터 가져오기
            raw_url = news_file.get("raw_url")
            news_response = await client.get(raw_url, timeout=10.0)
            
            if news_response.status_code != 200:
                return {"news": [], "source": "raw_error"}
            
            news_data = news_response.json()
            
            return {
                "news": news_data if isinstance(news_data, list) else news_data.get("articles", []),
                "source": "gist",
                "updated_at": gist_data.get("updated_at")
            }
            
    except Exception as e:
        return {"news": [], "source": "error", "error": str(e)}


@router.post("/refresh")
async def refresh_news():
    """GitHub Actions 워크플로우 트리거"""
    if not settings.GITHUB_REPO or not settings.GITHUB_TOKEN:
        raise HTTPException(
            status_code=400,
            detail="GitHub 설정이 필요합니다."
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/repos/{settings.GITHUB_REPO}/actions/workflows/scrape_news.yml/dispatches",
                headers={
                    "Authorization": f"token {settings.GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={"ref": "main"},
                timeout=10.0
            )
            
            if response.status_code == 204:
                return {"status": "triggered", "message": "뉴스 새로고침이 시작되었습니다."}
            elif response.status_code == 401:
                raise HTTPException(status_code=401, detail="GitHub 토큰 권한이 없습니다.")
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="워크플로우를 찾을 수 없습니다.")
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"GitHub API 오류: {response.text}"
                )
                
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"요청 오류: {str(e)}")


@router.post("/summarize")
async def summarize_news(request: SummarizeRequest):
    """뉴스 AI 요약"""
    try:
        prompt = f"""다음 뉴스 기사를 요약해주세요.

제목: {request.title}

내용:
{request.content}

요약 지침:
1. 5-7문장으로 핵심 내용을 요약
2. 주요 포인트를 불릿으로 정리
3. 객관적인 톤 유지
4. 충주시 관련 내용이 있으면 강조"""

        summary = await openai_service.generate_text(
            prompt=prompt,
            max_tokens=600,
            temperature=0.3
        )
        
        return {"summary": summary}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
