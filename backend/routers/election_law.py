"""선거법 챗봇 API"""
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

# 검색 대상 목록
SEARCH_TARGETS = {
    "all": "전체",
    "law": "법령",
    "panli": "판례",
    "written": "서면질의",
    "internet": "인터넷질의",
    "guidance": "지도기준"
}


class QuestionRequest(BaseModel):
    question: str
    target: str = "all"


class Reference(BaseModel):
    content: str
    similarity: float
    type: str


@router.post("/ask")
async def ask_question(request: QuestionRequest):
    """선거법 질문 답변"""
    # 입력값 검증
    is_safe, message = check_text_security(request.question)
    if not is_safe:
        raise HTTPException(status_code=400, detail=message)
    
    if request.target not in SEARCH_TARGETS:
        raise HTTPException(status_code=400, detail="잘못된 검색 대상입니다.")
    
    try:
        # 1. 질문 유형 분류
        question_type = await classify_question_type(request.question)
        
        # 2. 관련 문서 검색
        if question_type == "list_type":
            # 목록형 질문: 멀티쿼리 검색
            references = await search_multi_query(request.question, request.target)
        else:
            # 일반 질문: 단일 검색
            references = await vectorstore.search_election_law(
                query=request.question,
                target=request.target,
                top_k=5
            )
        
        # 3. 답변 생성
        answer = await generate_answer(
            question=request.question,
            references=references,
            question_type=question_type
        )
        
        return {
            "answer": answer,
            "references": references[:3],  # 상위 3개만 반환
            "question_type": question_type
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def classify_question_type(question: str) -> str:
    """질문 유형 분류"""
    prompt = f"""다음 질문의 유형을 분류해주세요.

질문: {question}

유형:
- list_type: "어떤 것들이 있나요?", "종류는?", "사례를 알려주세요" 등 여러 항목을 나열해야 하는 질문
- single_case: 특정 사례나 상황에 대한 질문
- definition: 정의나 개념을 묻는 질문
- period: 기간이나 시기를 묻는 질문
- general: 기타 일반 질문

답변은 유형 이름만 출력하세요 (예: list_type)"""
    
    try:
        result = await openai_service.generate_text(
            prompt=prompt,
            max_tokens=20,
            temperature=0
        )
        
        result = result.strip().lower()
        valid_types = ["list_type", "single_case", "definition", "period", "general"]
        return result if result in valid_types else "general"
    except:
        return "general"


async def search_multi_query(question: str, target: str) -> List[dict]:
    """멀티쿼리 검색 (목록형 질문용)"""
    # 서브쿼리 생성
    prompt = f"""다음 질문에 답하기 위해 검색해야 할 키워드나 하위 질문 3개를 생성하세요.

질문: {question}

JSON 형식으로 출력:
["키워드1", "키워드2", "키워드3"]"""
    
    try:
        result = await openai_service.generate_text(
            prompt=prompt,
            max_tokens=100,
            temperature=0.3
        )
        
        import json
        sub_queries = json.loads(result)
        
        # 각 서브쿼리로 검색
        all_results = []
        seen_contents = set()
        
        for sub_query in sub_queries:
            docs = await vectorstore.search_election_law(
                query=sub_query,
                target=target,
                top_k=3
            )
            for doc in docs:
                content_hash = hash(doc.get("content", "")[:100])
                if content_hash not in seen_contents:
                    seen_contents.add(content_hash)
                    all_results.append(doc)
        
        # 유사도 기준 정렬
        all_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return all_results[:10]
        
    except Exception as e:
        # 폴백: 원본 질문으로 검색
        return await vectorstore.search_election_law(
            query=question,
            target=target,
            top_k=5
        )


async def generate_answer(question: str, references: List[dict], question_type: str) -> str:
    """답변 생성"""
    if not references:
        return "죄송합니다. 관련 정보를 찾을 수 없습니다. 질문을 다시 확인해주세요."
    
    # 참고 문서 텍스트 구성
    ref_text = "\n\n".join([
        f"[참고 {i+1}] (유사도: {doc.get('similarity', 0):.2f})\n{doc.get('content', '')[:800]}"
        for i, doc in enumerate(references[:5])
    ])
    
    if question_type == "list_type":
        prompt = f"""다음 참고 자료를 바탕으로 질문에 답변하세요.

질문: {question}

참고 자료:
{ref_text}

답변 지침:
1. 참고 자료에서 관련 내용을 최대한 많이 찾아 나열하세요
2. 각 항목에 대해 간략한 설명을 포함하세요
3. 번호나 불릿 포인트로 정리하세요
4. 참고 자료에 없는 내용은 추측하지 마세요"""
    else:
        prompt = f"""다음 참고 자료를 바탕으로 질문에 답변하세요.

질문: {question}

참고 자료:
{ref_text}

답변 지침:
1. 참고 자료의 내용을 기반으로 정확하게 답변하세요
2. 법령이나 판례가 있으면 구체적으로 인용하세요
3. 참고 자료에 없는 내용은 추측하지 마세요
4. 명확하고 이해하기 쉽게 설명하세요"""
    
    result = await openai_service.generate_text(
        prompt=prompt,
        max_tokens=1500,
        temperature=0
    )
    
    return result


@router.get("/targets")
async def get_search_targets():
    """검색 대상 목록 반환"""
    return {
        "targets": [
            {"value": k, "label": v}
            for k, v in SEARCH_TARGETS.items()
        ]
    }


@router.get("/status")
async def get_vectorstore_status():
    """벡터스토어 상태 확인"""
    try:
        status = vectorstore.get_election_law_status()
        return status
    except Exception as e:
        return {"status": "error", "message": str(e)}
