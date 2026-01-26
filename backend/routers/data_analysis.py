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


# ===========================================
# 🎯 AI Agent 사전 지시사항 (핵심!)
# ===========================================
AGENT_PREFIX = """You are a helpful data analysis assistant that analyzes pandas DataFrames.

## 중요 규칙 (MUST FOLLOW):

### 1. NaN/빈 값 처리
- 컬럼에 데이터가 있는지 확인할 때 반드시 dropna()를 사용하여 NaN을 제외하고 확인
- 단 하나라도 실제 값이 있으면 "데이터가 있다"고 답변
- 예: df["컬럼명"].dropna() 로 실제 값 확인

### 2. 데이터 존재 여부 확인 방법
```python
# 올바른 방법
non_null_values = df["컬럼명"].dropna()
if len(non_null_values) > 0:
    print("데이터가 있습니다:", non_null_values.tolist())
```

### 3. 답변 언어
- 모든 답변은 한국어로 작성
- 친절하고 상세하게 답변

### 4. 관련 데이터 찾기
- "법령", "근거", "관련법" 등의 질문이 오면 관련 컬럼들을 모두 확인
- 부분 일치도 확인 (컬럼명에 해당 키워드가 포함되어 있는지)

### 5. 결과 보여주기
- 데이터가 있으면 실제 값을 보여줌
- 어떤 행에 있는지 구체적으로 알려줌

Remember: NaN이 많아도 실제 값이 하나라도 있으면 "있다"고 답해야 합니다!
"""


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
    print(f"[DEBUG] analyze 시작 - file_id: {request.file_id}")
    
    # 파일 확인
    if request.file_id not in temp_files:
        print(f"[DEBUG] 파일 없음! 요청된 ID: {request.file_id}")
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다. 다시 업로드해주세요.")
    
    temp_path = temp_files[request.file_id]
    if not os.path.exists(temp_path):
        del temp_files[request.file_id]
        raise HTTPException(status_code=404, detail="파일이 만료되었습니다. 다시 업로드해주세요.")
    
    try:
        print("[DEBUG] try 블록 진입")

        # LangChain imports
        print("[DEBUG] LangChain import 시작")
        from langchain_experimental.agents.agent_toolkits.pandas.base import create_pandas_dataframe_agent
        from langchain_openai import ChatOpenAI
        print("[DEBUG] LangChain import 성공")
        
        # 데이터프레임 로드
        df = pd.read_parquet(temp_path)
        print(f"[DEBUG] DataFrame 로드 완료 - shape: {df.shape}")

        # LLM 설정
        print("[DEBUG] LLM 생성 시작")
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.OPENAI_API_KEY,
        )
        print("[DEBUG] LLM 생성 완료")

        try:
            from langchain.agents.agent_types import AgentType
        except ImportError:
            from langchain.agents import AgentType
        
        # Pandas Agent 생성 (prefix 추가!)
        print("[DEBUG] Agent 생성 시작")
        agent = create_pandas_dataframe_agent(
            llm,
            df,
            verbose=True,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            allow_dangerous_code=True,
            handle_parsing_errors=True,
            prefix=AGENT_PREFIX,  # 🎯 핵심: 사전 지시사항 추가!
        )
        print("[DEBUG] Agent 생성 완료")
        
        # 질문 실행
        print(f"[DEBUG] 질문 실행: {request.question}")
        result = agent.invoke({"input": request.question})
        print(f"[DEBUG] 결과 받음")

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
        
    except ImportError as e:
        print(f"[DEBUG] ImportError: {e}")
        raise HTTPException(
            status_code=500, 
            detail="LangChain 패키지가 설치되지 않았습니다. pip install langchain langchain-openai langchain-experimental"
        )
    except Exception as e:
        import traceback
        print("[DEBUG] Exception 발생!")
        traceback.print_exc()
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