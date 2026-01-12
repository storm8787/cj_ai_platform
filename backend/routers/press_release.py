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
    paragraphs: str = "4개이상"
    length: str = "길게"
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
    """보도자료 생성 - 충주시 스타일"""
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
        
        # 유사 문서 텍스트 결합
        examples_combined = "\n\n---\n\n".join([
            doc.get('content', '')[:1000]  # 각 문서 1000자까지
            for doc in similar_docs
        ])
        
        # 내용 포인트 처리
        content_points = [line.strip() for line in request.content.strip().split("\n") if line.strip()]
        joined_points = "\n- ".join(content_points)
        
        # 길이 지시 (자 단위)
        length_chars = {
            "짧게": 600,
            "중간": 800,
            "길게": 1000
        }.get(request.length, 1000)
        
        # 문단 지시
        paragraph_instruction = {
            "4개이상": "전체 글은 4개 이상의 문단으로 구성해주세요.\n",
            "3개": "전체 글은 3개 문단으로 구성해주세요.\n",
            "2개": "전체 글은 2개 문단으로 구성해주세요.\n",
            "1개": "전체 글은 1개 문단으로 구성해주세요.\n"
        }.get(request.paragraphs, "")
        
        # 시스템 프롬프트
        system_prompt = (
            "너는 지방정부 보도자료 작성 전문가야. "
            "아래 유사 사례를 참고해, 행정기관 스타일로 공공 보도자료를 작성해줘."
        )
        
        # 추가 지시사항
        additional_instructions = (
            f"보도자료에는 상단의 보도일자, 담당자 정보, 연락처는 포함하지 말고 본문만 작성해주세요.\n"
            f"담당자 인용문이 나올 경우, 담당자 이름은 '{request.manager}'이고, "
            f"직책은 '{request.department}장'으로 표기해주세요.\n"
            f"담당자 인용문이 나올 경우, '{request.manager}' 한칸띄고 '{request.department}장'으로 표기해주세요. "
            f"예: 김태균 자치행정과장\n"
            f"전체 문체는 보도자료 스타일의 간접화법을 사용해주세요. 예: '~했다', '~라고 밝혔다' 등.\n"
            f"{paragraph_instruction}"
            f"보도자료는 반드시 '[제목] 본문제목'으로 시작한 후, 한 줄 아래에 부제목 형태의 요약 문장을 넣어주세요. "
            f"부제목은 '-' 기호로 시작하세요.\n"
            f"전체 보도자료 분량은 약 {length_chars}자 내외로 작성해주세요. 필요 시 최대 토큰 수를 늘려도 괜찮습니다.\n"
            f"전체 보도자료는 반드시 {length_chars}자 보다는 길게(+300자 가능) 작성해주세요."
        )
        
        # 사용자 쿼리 프롬프트
        user_query_prompt = (
            f"입력한 제목 후보: {request.title}\n\n"
            f"아래 내용 포인트를 반영하여 보도자료에 어울리는 제목을 새로 작성하고, "
            f"그 제목을 '[제목]'에 반영해줘. 입력한 제목은 참고만 하고 그대로 쓰지 않아도 돼.\n\n"
            f"내용 포인트:\n- {joined_points}\n\n"
            f"요청사항:\n- {request.additional if request.additional else '없음'}\n\n"
            f"{additional_instructions}"
        )
        
        # 최종 사용자 메시지
        user_message = f"""아래는 참고용 보도자료 예시입니다:

{examples_combined}

위 스타일을 참고하여 아래 요청사항에 맞는 새로운 보도자료를 작성해줘:

{user_query_prompt}
"""
        
        # GPT로 생성 (시스템 프롬프트 포함)
        full_prompt = f"{system_prompt}\n\n{user_message}"
        result = await openai_service.generate_text(
            prompt=full_prompt,
            max_tokens=2000,
            temperature=0.5  # 더 일관적인 결과를 위해 0.5로 조정
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