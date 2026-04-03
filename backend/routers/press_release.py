"""보도자료 생성 API - 완벽 구현"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import datetime

from services.vectorstore import VectorStoreService
from services.openai_service import OpenAIService
from services.supabase_service import SupabaseService
from utils.prompt_filter import check_text_security

from services.prompt_service import prompt_service

router = APIRouter()

# 서비스 인스턴스
vectorstore = VectorStoreService()
openai_service = OpenAIService()
supabase_service = SupabaseService()


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


class DocumentReference(BaseModel):
    """참조 문서 정보"""
    index: int
    similarity: float
    doc_id: str
    preview: str
    full_content: str


class GenerateResponse(BaseModel):
    """보도자료 생성 응답"""
    result: str
    references: List[DocumentReference]
    search_method: str
    vectorstore_status: Dict
    generation_time: float
    supabase_log_id: Optional[int] = None


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


@router.post("/generate", response_model=GenerateResponse)
async def generate_press_release(request: GenerateRequest):
    """보도자료 생성 - 완벽 구현"""
    import time
    start_time = time.time()
    
    # 입력값 검증
    for text in [request.title, request.content, request.additional]:
        if text:
            is_safe, message = check_text_security(text)
            if not is_safe:
                raise HTTPException(status_code=400, detail=message)
    
    try:
        # 1. 벡터스토어 상태 확인
        vectorstore_status = vectorstore.get_press_release_status()
        search_method = "🤖 AI 벡터 검색" if vectorstore_status.get("loaded") else "📊 기본 검색"
        
        # 2. 유사 문서 검색
        similar_docs = await vectorstore.search_press_release(
            query=request.title,
            top_k=3
        )
        
        # 3. 참조 문서 정보 구성
        references = []
        examples_for_prompt = []
        
        for i, doc in enumerate(similar_docs):
            content = doc.get('content', '')
            similarity = doc.get('similarity', 0.0)
            
            # 참조 문서 정보
            references.append({
                "index": i + 1,
                "similarity": round(similarity, 4),
                "doc_id": doc.get('metadata', {}).get('id', f'doc_{i+1}'),
                "preview": content[:200] + "..." if len(content) > 200 else content,
                "full_content": content
            })
            
            # 프롬프트용 예시 (전체 내용, 최대 1000자)
            examples_for_prompt.append(content[:1000])
        
        # 4. 프롬프트 생성 (기존 개선된 버전)
        examples_combined = "\n\n---\n\n".join(examples_for_prompt)
        content_points = [line.strip() for line in request.content.strip().split("\n") if line.strip()]
        joined_points = "\n- ".join(content_points)
        
        # 길이 지시
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
        
        # 변경 후
        system_prompt = prompt_service.get(
            "press_release", "system_prompt",
            default="너는 지방정부 보도자료 작성 전문가야. 아래 유사 사례를 참고해, 행정기관 스타일로 공공 보도자료를 작성해줘."
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
        
        # 최종 프롬프트
        full_prompt = f"""{system_prompt}

아래는 참고용 보도자료 예시입니다:

{examples_combined}

위 스타일을 참고하여 아래 요청사항에 맞는 새로운 보도자료를 작성해줘:

{user_query_prompt}
"""
        
        # 5. GPT로 생성
        result = await openai_service.generate_text(
            prompt=full_prompt,
            max_tokens=2000,
            temperature=0.5
        )
        
        # 6. 생성 시간 계산
        generation_time = round(time.time() - start_time, 2)
        
        # 7. Supabase 로깅
        supabase_log_id = None
        try:
            # 파일 저장
            safe_title = request.title[:20].replace(" ", "_").replace("/", "_") if request.title else "보도자료"
            file_name = f"{safe_title}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            file_bytes = result.encode('utf-8')
            
            log_result = await supabase_service.log_press_release(
                file_bytes=file_bytes,
                file_name=file_name,
                metadata={
                    "title": request.title,
                    "department": request.department,
                    "manager": request.manager,
                    "paragraphs": request.paragraphs,
                    "length": request.length,
                    "search_method": search_method,
                    "references_count": len(references),
                    "generation_time": generation_time
                }
            )
            supabase_log_id = log_result.get("id") if log_result else None
        except Exception as e:
            print(f"⚠️ Supabase 로깅 실패: {e}")
        
        # 8. 응답 반환
        return GenerateResponse(
            result=result,
            references=references,
            search_method=search_method,
            vectorstore_status=vectorstore_status,
            generation_time=generation_time,
            supabase_log_id=supabase_log_id
        )
        
    except Exception as e:
        # 에러 로깅
        try:
            await supabase_service.log_error(
                feature_name="보도자료 생성기",
                error_message=str(e)
            )
        except:
            pass
        
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_vectorstore_status():
    """벡터스토어 상태 확인"""
    try:
        status = vectorstore.get_press_release_status()
        return status
    except Exception as e:
        return {"status": "error", "message": str(e)}