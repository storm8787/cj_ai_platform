"""
뉴스 API - GitHub Gist 연동 + AI 요약
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import html
from datetime import datetime

from config import settings
from services.openai_service import OpenAIService

router = APIRouter()
openai_service = OpenAIService()


class SummarizeRequest(BaseModel):
    title: str
    content: str


class NewsResponse(BaseModel):
    keyword: str
    total_count: int
    last_updated: str
    news: List[Dict[str, Any]]
    source: str


# ============================================
# 뉴스 목록 조회 (Gist에서)
# ============================================

@router.get("", response_model=NewsResponse)
@router.get("/", response_model=NewsResponse)
async def get_news_list():
    """
    GitHub Gist에서 뉴스 목록 조회
    """
    gist_id = settings.GIST_ID
    github_token = settings.GITHUB_TOKEN
    
    if not gist_id:
        # Gist 설정이 없으면 빈 데이터 반환
        return NewsResponse(
            keyword="충주시",
            total_count=0,
            last_updated="",
            news=[],
            source="not_configured"
        )
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Gist 메타데이터 가져오기
            headers = {"Accept": "application/vnd.github.v3+json"}
            if github_token:
                headers["Authorization"] = f"token {github_token}"
            
            response = await client.get(
                f"https://api.github.com/gists/{gist_id}",
                headers=headers
            )
            
            if response.status_code != 200:
                print(f"Gist API 오류: {response.status_code}")
                return NewsResponse(
                    keyword="충주시",
                    total_count=0,
                    last_updated="",
                    news=[],
                    source="gist_error"
                )
            
            gist_data = response.json()
            
            # news_data.json 파일 찾기
            files = gist_data.get("files", {})
            news_file = files.get("news_data.json")
            
            if not news_file:
                return NewsResponse(
                    keyword="충주시",
                    total_count=0,
                    last_updated="",
                    news=[],
                    source="file_not_found"
                )
            
            # raw_url에서 실제 데이터 가져오기
            raw_url = news_file.get("raw_url")
            raw_response = await client.get(raw_url, headers=headers)
            
            if raw_response.status_code != 200:
                return NewsResponse(
                    keyword="충주시",
                    total_count=0,
                    last_updated="",
                    news=[],
                    source="raw_error"
                )
            
            news_data = raw_response.json()
            
            return NewsResponse(
                keyword=news_data.get("keyword", "충주시"),
                total_count=news_data.get("total_count", 0),
                last_updated=news_data.get("last_updated", ""),
                news=news_data.get("news", []),
                source="gist"
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Gist 요청 타임아웃")
    except Exception as e:
        print(f"뉴스 로드 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# GitHub Actions 트리거 (뉴스 새로고침)
# ============================================

@router.post("/refresh")
async def refresh_news():
    """
    GitHub Actions 워크플로우 트리거하여 뉴스 새로고침
    """
    github_token = settings.GITHUB_TOKEN
    github_repo = settings.GITHUB_REPO
    
    if not github_token:
        raise HTTPException(status_code=400, detail="GITHUB_TOKEN이 설정되지 않았습니다")
    
    if not github_repo:
        raise HTTPException(status_code=400, detail="GITHUB_REPO가 설정되지 않았습니다")
    
    url = f"https://api.github.com/repos/{github_repo}/actions/workflows/scrape_news.yml/dispatches"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={"ref": "main"}
            )
            
            if response.status_code == 204:
                return {
                    "status": "triggered",
                    "message": "뉴스 업데이트가 시작되었습니다. 1-2분 후 새로고침 해주세요."
                }
            elif response.status_code == 401:
                raise HTTPException(status_code=401, detail="GitHub 토큰 권한이 없습니다. workflow 권한을 확인해주세요.")
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="저장소 또는 워크플로우를 찾을 수 없습니다.")
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"GitHub API 오류: {response.text}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="GitHub API 요청 타임아웃")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"요청 실패: {str(e)}")


# ============================================
# AI 뉴스 요약
# ============================================

@router.post("/summarize")
async def summarize_news(request: SummarizeRequest):
    """
    GPT로 뉴스 AI 요약 생성
    """
    # HTML 엔티티 디코딩
    clean_title = html.unescape(request.title)
    clean_content = html.unescape(request.content)
    
    prompt = f"""다음 충주시 관련 뉴스 기사를 정성껏 요약해주세요.

제목: {clean_title}

본문:
{clean_content[:3000]}

요약 작성 규칙:
1. 5-7문장으로 핵심 내용을 충실히 담아 작성
2. 육하원칙(누가, 언제, 어디서, 무엇을, 어떻게, 왜)을 최대한 반영
3. 주요 수치나 날짜가 있으면 포함
4. 시민에게 미치는 영향이나 의의가 있다면 언급
5. 객관적이고 명확한 문체 사용
6. 마지막에 한 줄로 핵심 의의나 전망 정리

형식:
[요약]
(본문 요약 5-7문장)

[핵심 포인트]
• (중요 포인트 2-3개)
"""
    
    try:
        summary = await openai_service.generate_text(
            prompt=prompt,
            system_prompt="당신은 지역 뉴스를 시민들이 이해하기 쉽게 요약하는 전문 기자입니다. 핵심 정보를 빠뜨리지 않으면서도 읽기 쉽게 정리합니다.",
            max_tokens=600,
            temperature=0.3
        )
        
        return {"summary": summary}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 요약 생성 실패: {str(e)}")
