"""
엑셀 취합기 API
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import List
import pandas as pd
import io

router = APIRouter()


def read_excel_file(contents: bytes, filename: str, sheet_index: int = 0, header_row: int = 0, all_sheets: bool = False):
    """
    엑셀 파일 읽기
    - sheet_index: 읽을 시트 인덱스 (0부터 시작)
    - header_row: 헤더 행 인덱스 (0부터 시작)
    - all_sheets: True면 모든 시트 읽기
    """
    try:
        if filename.endswith('.csv'):
            for encoding in ['utf-8', 'cp949', 'euc-kr', 'utf-8-sig']:
                try:
                    return [pd.read_csv(io.BytesIO(contents), encoding=encoding, header=header_row)]
                except UnicodeDecodeError:
                    continue
            raise ValueError("CSV 파일 인코딩을 인식할 수 없습니다.")
        
        if all_sheets:
            xls = pd.read_excel(io.BytesIO(contents), sheet_name=None, header=header_row, engine='openpyxl')
            return list(xls.values())
        else:
            df = pd.read_excel(io.BytesIO(contents), sheet_name=sheet_index, header=header_row, engine='openpyxl')
            return [df]
            
    except Exception as e:
        raise ValueError(f"파일 읽기 실패: {str(e)}")


@router.post("/merge")
async def merge_excel_files(
    files: List[UploadFile] = File(...),
    header_row: int = Form(default=1),
    sheet_option: str = Form(default="1")
):
    """
    여러 엑셀 파일 병합
    - files: 업로드된 파일들
    - header_row: 제목행 번호 (1부터 시작)
    - sheet_option: "1", "2", ... 또는 "all" (모든 시트)
    """
    if not files:
        raise HTTPException(status_code=400, detail="파일을 업로드해주세요.")
    
    combined_df = pd.DataFrame()
    header_index = header_row - 1  # 0-based index로 변환
    all_sheets = sheet_option.lower() == "all"
    sheet_index = 0 if all_sheets else int(sheet_option) - 1
    
    processed_count = 0
    errors = []
    
    for file in files:
        if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
            errors.append(f"{file.filename}: 지원하지 않는 형식")
            continue
        
        try:
            contents = await file.read()
            dfs = read_excel_file(
                contents, 
                file.filename, 
                sheet_index=sheet_index, 
                header_row=header_index,
                all_sheets=all_sheets
            )
            
            for df in dfs:
                # 컬럼명 문자열로 변환
                df.columns = df.columns.astype(str)
                combined_df = pd.concat([combined_df, df], ignore_index=True)
            
            processed_count += 1
            
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
    
    if combined_df.empty:
        raise HTTPException(
            status_code=400, 
            detail=f"병합할 데이터가 없습니다. 오류: {', '.join(errors)}"
        )
    
    # 결과 엑셀 파일 생성
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        combined_df.to_excel(writer, index=False, sheet_name='통합결과')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=merged_result.xlsx",
            "X-Processed-Count": str(processed_count),
            "X-Total-Rows": str(len(combined_df)),
            "X-Total-Cols": str(len(combined_df.columns)),
            "X-Errors": ",".join(errors) if errors else ""
        }
    )


@router.post("/preview")
async def preview_excel_file(
    file: UploadFile = File(...),
    header_row: int = Form(default=1),
    sheet_option: str = Form(default="1")
):
    """
    엑셀 파일 미리보기 (첫 10행)
    """
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="xlsx, xls, csv 파일만 지원합니다.")
    
    try:
        contents = await file.read()
        header_index = header_row - 1
        all_sheets = sheet_option.lower() == "all"
        sheet_index = 0 if all_sheets else int(sheet_option) - 1
        
        dfs = read_excel_file(
            contents,
            file.filename,
            sheet_index=sheet_index,
            header_row=header_index,
            all_sheets=all_sheets
        )
        
        # 첫 번째 시트의 미리보기
        df = dfs[0] if dfs else pd.DataFrame()
        df.columns = df.columns.astype(str)
        
        # 모든 값을 문자열로 변환
        preview = []
        for _, row in df.head(10).iterrows():
            row_dict = {}
            for col in df.columns:
                val = row[col]
                if pd.isna(val):
                    row_dict[str(col)] = ""
                else:
                    row_dict[str(col)] = str(val)
            preview.append(row_dict)
        
        return {
            "file_name": file.filename,
            "row_count": len(df),
            "col_count": len(df.columns),
            "columns": [str(col) for col in df.columns],
            "preview": preview,
            "sheet_count": len(dfs) if all_sheets else 1
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"미리보기 실패: {str(e)}")


@router.get("/sheet-count")
async def get_sheet_count(file: UploadFile = File(...)):
    """
    엑셀 파일의 시트 개수 조회
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        return {"sheet_count": 1, "sheet_names": ["Sheet1"]}
    
    try:
        contents = await file.read()
        xls = pd.ExcelFile(io.BytesIO(contents), engine='openpyxl')
        return {
            "sheet_count": len(xls.sheet_names),
            "sheet_names": xls.sheet_names
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시트 정보 조회 실패: {str(e)}")
