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


def safe_preview(df: pd.DataFrame, rows: int = 10) -> List[Dict[str, Any]]:
    """
    미리보기 데이터 생성 - 모든 키와 값을 문자열로 변환
    """
    # 컬럼명을 문자열로 변환
    df_copy = df.head(rows).copy()
    df_copy.columns = df_copy.columns.astype(str)
    
    # 모든 값을 문자열로 변환 (None, NaN 처리)
    preview = []
    for _, row in df_copy.iterrows():
        row_dict = {}
        for col in df_copy.columns:
            val = row[col]
            if pd.isna(val):
                row_dict[str(col)] = ""
            else:
                row_dict[str(col)] = str(val)
        preview.append(row_dict)
    
    return preview


def read_excel_file(contents: bytes, filename: str) -> pd.DataFrame:
    """
    엑셀 파일 읽기 - xls/xlsx/csv 지원
    """
    try:
        if filename.endswith('.csv'):
            # CSV 파일 - 여러 인코딩 시도
            for encoding in ['utf-8', 'cp949', 'euc-kr', 'utf-8-sig']:
                try:
                    return pd.read_csv(io.BytesIO(contents), encoding=encoding)
                except UnicodeDecodeError:
                    continue
            raise ValueError("CSV 파일 인코딩을 인식할 수 없습니다.")
        
        elif filename.endswith('.xls'):
            # .xls 파일 - xlrd 대신 openpyxl 엔진 시도, 실패시 xlrd
            try:
                # 먼저 openpyxl로 시도 (일부 .xls도 읽을 수 있음)
                return pd.read_excel(io.BytesIO(contents), engine='openpyxl')
            except Exception:
                try:
                    # xlrd로 시도
                    return pd.read_excel(io.BytesIO(contents), engine='xlrd')
                except ImportError:
                    raise ValueError(
                        ".xls 파일은 지원이 제한됩니다. "
                        ".xlsx 또는 .csv로 변환 후 업로드해주세요."
                    )
        else:
            # .xlsx 파일 - openpyxl 사용
            return pd.read_excel(io.BytesIO(contents), engine='openpyxl')
            
    except Exception as e:
        raise ValueError(f"파일 읽기 실패: {str(e)}")


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
        
        # 엑셀/CSV 파일 읽기
        df = read_excel_file(contents, file.filename)
        
        # 컬럼명이 숫자인 경우 문자열로 변환 (Pydantic 호환)
        df.columns = df.columns.astype(str)
        
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
                "name": str(col),  # 문자열로 변환
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isnull().sum()),
                "unique_count": int(df[col].nunique())
            })
        
        # 미리보기 (첫 10행) - 안전한 변환 사용
        preview = safe_preview(df, 10)
        
        return FileInfoResponse(
            file_id=file_id,
            file_name=file.filename,
            row_count=len(df),
            col_count=len(df.columns),
            columns=columns,
            preview=preview
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 처리 실패: {str(e)}")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_data(request: AnalyzeRequest):
    """
    LangChain Pandas Agent로 데이터 분석
    """
    print(f"[DEBUG] analyze 시작 - file_id: {request.file_id}")  # 추가
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
        
        # 데이터프레임 로드
        df = pd.read_parquet(temp_path)
        
        # LLM 설정 (langchain_openai 최신 스타일)
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.OPENAI_API_KEY,
        )
        
        # Pandas Agent 생성
        # - agent_type / allow_dangerous_code / handle_parsing_errors 제거
        agent = create_pandas_dataframe_agent(
            llm,
            df,
            verbose=False,            
        )
        
        # 질문 실행 (run → invoke)
        result = agent.invoke({"input": request.question})
        
        # 결과에서 텍스트만 추출
        if isinstance(result, dict):
            answer = (
                result.get("output")
                or result.get("output_text")
                or str(result)
            )
        else:
            answer = str(result)
        
        return AnalyzeResponse(
            answer=answer,
            success=True
        )
        
    except ImportError:
        raise HTTPException(
            status_code=500, 
            detail="LangChain 패키지가 설치되지 않았습니다. pip install langchain langchain-openai langchain-experimental"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()  # 이 줄 추가 - 터미널에 전체 에러 출력
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
