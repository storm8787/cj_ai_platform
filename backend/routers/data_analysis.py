"""
AI 통계분석 챗봇 API - LangChain Pandas Agent
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd
import io
import tempfile
import os
import uuid

from config import settings

router = APIRouter()

# 임시 파일 저장소 (실제 운영에서는 Redis 등 사용 권장)
temp_files: Dict[str, str] = {}


class AnalyzeRequest(BaseModel):
    file_id: str
    question: str


class FileInfoResponse(BaseModel):
    file_id: str
    file_name: str
    row_count: int
    col_count: int
    columns: List[Dict[str, Any]]
    preview: List[Dict[str, Any]]


class AnalyzeResponse(BaseModel):
    answer: str
    success: bool


@router.post("/upload", response_model=FileInfoResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    엑셀 파일 업로드 및 분석 준비
    """
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="xlsx, xls, csv 파일만 지원합니다.")
    
    try:
        # 파일 읽기
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        # 임시 파일로 저장
        file_id = str(uuid.uuid4())[:8]
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix='.parquet').name
        df.to_parquet(temp_path)
        temp_files[file_id] = temp_path
        
        # 컬럼 정보
        columns = []
        for i, col in enumerate(df.columns, 1):
            columns.append({
                "index": i,
                "name": col,
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isnull().sum()),
                "unique_count": int(df[col].nunique())
            })
        
        # 미리보기 (첫 10행)
        preview = df.head(10).fillna("").to_dict(orient='records')
        
        return FileInfoResponse(
            file_id=file_id,
            file_name=file.filename,
            row_count=len(df),
            col_count=len(df.columns),
            columns=columns,
            preview=preview
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 처리 실패: {str(e)}")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_data(request: AnalyzeRequest):
    """
    LangChain Pandas Agent로 데이터 분석
    """
    # 파일 확인
    if request.file_id not in temp_files:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다. 다시 업로드해주세요.")
    
    temp_path = temp_files[request.file_id]
    if not os.path.exists(temp_path):
        del temp_files[request.file_id]
        raise HTTPException(status_code=404, detail="파일이 만료되었습니다. 다시 업로드해주세요.")
    
    try:
        # LangChain imports
        from langchain_experimental.agents.agent_toolkits.pandas.base import create_pandas_dataframe_agent
        from langchain_openai import ChatOpenAI
        from langchain.agents.agent_types import AgentType
        
        # 데이터프레임 로드
        df = pd.read_parquet(temp_path)
        
        # Agent 생성
        agent = create_pandas_dataframe_agent(
            ChatOpenAI(
                temperature=0,
                model="gpt-4o-mini",
                openai_api_key=settings.OPENAI_API_KEY
            ),
            df,
            verbose=False,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            allow_dangerous_code=True,
            handle_parsing_errors=True
        )
        
        # 질문 실행
        response = agent.run(request.question)
        
        return AnalyzeResponse(
            answer=response,
            success=True
        )
        
    except ImportError:
        raise HTTPException(
            status_code=500, 
            detail="LangChain 패키지가 설치되지 않았습니다. pip install langchain langchain-openai langchain-experimental"
        )
    except Exception as e:
        return AnalyzeResponse(
            answer=f"분석 중 오류가 발생했습니다: {str(e)}",
            success=False
        )


@router.delete("/file/{file_id}")
async def delete_file(file_id: str):
    """
    임시 파일 삭제
    """
    if file_id in temp_files:
        temp_path = temp_files[file_id]
        if os.path.exists(temp_path):
            os.remove(temp_path)
        del temp_files[file_id]
        return {"message": "파일이 삭제되었습니다."}
    
    return {"message": "파일을 찾을 수 없습니다."}
