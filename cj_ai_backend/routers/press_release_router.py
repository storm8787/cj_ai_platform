from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import io

from services.press_release_service import PressReleaseService
from utils.prompt_filter import check_text_security, scan_dataframe_for_security

router = APIRouter(prefix="/api/press-release", tags=["press-release"])
service = PressReleaseService()


class PressReleaseRequest(BaseModel):
    title: str  # 제목
    department: str  # 담당부서
    manager: str  # 담당자
    paragraph_count: str = "4개이상"  # 문단수
    length: str = "중간"  # 길이
    key_points: str  # 내용포인트 (여러 줄)
    additional_request: Optional[str] = ""  # 기타요청


class ReferenceDocument(BaseModel):
    순번: int
    유사도점수: str
    문서ID: str
    내용미리보기: str
    전체내용: str


class PressReleaseResponse(BaseModel):
    success: bool
    content: Optional[str] = None
    references: Optional[list[ReferenceDocument]] = None
    error: Optional[str] = None


@router.post("/generate", response_model=PressReleaseResponse)
async def generate_press_release(request: PressReleaseRequest):
    """보도자료 생성 API"""
    
    # 1. 입력값 보안 검사
    fields_to_check = {
        "제목": request.title,
        "담당부서": request.department,
        "담당자": request.manager,
        "내용포인트": request.key_points,
        "기타요청": request.additional_request
    }
    
    for field_name, field_value in fields_to_check.items():
        if field_value:
            is_malicious, reason = check_text_security(field_value, field_name)
            if is_malicious:
                raise HTTPException(status_code=400, detail=f"부적절한 입력 ({field_name}): {reason}")
    
    try:
        # 2. 보도자료 생성 (참조 문서 정보도 함께 받음)
        content, references = await service.generate_press_release_with_references(
            title=request.title,
            department=request.department,
            manager=request.manager,
            paragraph_count=request.paragraph_count,
            length=request.length,
            key_points=request.key_points,
            additional_request=request.additional_request
        )
        
        # 3. 참조 문서를 Pydantic 모델로 변환
        reference_models = [
            ReferenceDocument(
                순번=ref["순번"],
                유사도점수=ref["유사도점수"],
                문서ID=ref["문서ID"],
                내용미리보기=ref["내용미리보기"],
                전체내용=ref["전체내용"]
            )
            for ref in references
        ]
        
        return PressReleaseResponse(
            success=True, 
            content=content,
            references=reference_models
        )
    
    except Exception as e:
        return PressReleaseResponse(success=False, error=str(e))


@router.post("/analyze-reference", response_model=PressReleaseResponse)
async def analyze_reference_file(file: UploadFile = File(...)):
    """참고자료 분석 API (엑셀 업로드)"""
    
    try:
        # 1. 엑셀 파일 읽기
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # 2. 보안 검사
        alerts = scan_dataframe_for_security(df, "참고자료")
        if alerts:
            raise HTTPException(status_code=400, detail=f"부적절한 내용 발견: {', '.join(alerts[:3])}")
        
        # 3. 데이터 분석 및 요약
        summary = await service.analyze_reference_data(df)
        
        return PressReleaseResponse(success=True, content=summary)
    
    except Exception as e:
        return PressReleaseResponse(success=False, error=str(e))


@router.get("/health")
async def health_check():
    """헬스체크"""
    return {"status": "healthy", "service": "press-release"}