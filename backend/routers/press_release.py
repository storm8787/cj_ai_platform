"""보도자료 생성 API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from services.vectorstore import VectorStoreService
from services.openai_service import OpenAIService
from utils.prompt_filter import check_text_security

router = APIRouter()

# 서비스 인스턴스
vectorstore = VectorStoreService()
openai_service = OpenAIService()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 3


class GenerateRequest(BaseModel):
    title: str
    department: str = ""
    manager: str = ""
    paragraphs: str = "2개"
    length: str = "중간"
    content: str
    additional: str = ""


class DocumentResult(BaseModel):
    title: str
    content: str
    similarity: float


@router.post("/search-similar")
async def search_similar_documents(request: SearchRequest):
    """유사 문서 검색"""
    # 입력값 검증
    is_safe, message = check_text_security(request.query)
    if not is_safe:
        raise HTTPException(status_code=400, detail=message)
    
    try:
        documents = await vectorstore.search_press_release(
            query=request.query,
            top_k=request.top_k
        )
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_press_release(request: GenerateRequest):
    """보도자료 생성"""
    # 입력값 검증
    for text in [request.title, request.content, request.additional]:
        if text:
            is_safe, message = check_text_security(text)
            if not is_safe:
                raise HTTPException(status_code=400, detail=message)
    
    try:
        # 유사 문서 검색
        similar_docs = await vectorstore.search_press_release(
            query=request.title,
            top_k=3
        )
        
        # 프롬프트 생성
        reference_text = "\n\n".join([
            f"[참고 {i+1}]\n{doc.get('content', '')[:500]}"
            for i, doc in enumerate(similar_docs)
        ])
        
        # 길이 가이드
        length_guide = {
            "짧게": "400-600자",
            "중간": "700-1000자",
            "길게": "1200-1500자"
        }.get(request.length, "700-1000자")
        
        prompt = f"""다음 정보를 바탕으로 충주시청 보도자료를 작성해주세요.

[기본 정보]
- 제목: {request.title}
- 담당부서: {request.department}
- 담당자: {request.manager}
- 문단 수: {request.paragraphs}
- 분량: {length_guide}

[내용 포인트]
{request.content}

[추가 요청]
{request.additional if request.additional else "없음"}

[유사 보도자료 참고]
{reference_text}

위 내용을 참고하여 다음 형식으로 보도자료를 작성해주세요:
1. 제목
2. 부제목 (선택)
3. 본문 ({request.paragraphs})
4. 문의처 (담당부서, 담당자)

작성 시 주의사항:
- 공공기관 보도자료 형식을 따를 것
- 객관적이고 명확한 문체 사용
- 핵심 내용을 앞에 배치 (역피라미드 구조)
"""
        
        # GPT로 생성
        result = await openai_service.generate_text(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.7
        )
        
        return {"result": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_vectorstore_status():
    """벡터스토어 상태 확인"""
    try:
        status = vectorstore.get_press_release_status()
        return status
    except Exception as e:
        return {"status": "error", "message": str(e)}
