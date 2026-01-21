"""
주소-좌표 변환기 API (카카오 API 기반)
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd
import httpx
import io
import re
import os

from config import settings

router = APIRouter()

# 카카오 API 키 (config.py에 추가 필요)
#KAKAO_API_KEY = getattr(settings, 'KAKAO_API_KEY', '')
KAKAO_API_KEY = os.environ.get('KAKAO_API_KEY', '')

# 충주시 행정동 중심좌표 DB
DONG_COORDS = {
    "주덕읍": ("36.9756382529379", "127.795607766653"),
    "살미면": ("36.9053897150325", "127.964612737336"),
    "수안보면": ("36.8472710272136", "127.994785817453"),
    "대소원면": ("36.977810921957", "127.81798438609"),
    "신니면": ("36.995573390012", "127.736394413436"),
    "노은면": ("37.0481450135857", "127.754137176945"),
    "앙성면": ("37.1091674050492", "127.750768224757"),
    "중앙탑면": ("37.028931544342", "127.857035068528"),
    "금가면": ("37.0430221614579", "127.924478732073"),
    "동량면": ("37.0263327303528", "127.963254082287"),
    "산척면": ("37.0816686531557", "127.9559645917"),
    "엄정면": ("37.0866781306916", "127.914877536217"),
    "소태면": ("37.1097895873743", "127.847739119082"),
    "성내.충인동": ("36.9734381778844", "127.933869282965"),
    "교현.안림동": ("36.9747966497151", "127.935282939261"),
    "교현2동": ("36.9814769299978", "127.929102109455"),
    "용산동": ("36.9642270579558", "127.938737856086"),
    "지현동": ("36.9682108608662", "127.932188386436"),
    "문화동": ("36.9716759115419", "127.925560081272"),
    "호암.직동": ("36.9529358203833", "127.933609911294"),
    "달천동": ("36.9601080580716", "127.903345363646"),
    "봉방동": ("36.9736601560487", "127.919281720775"),
    "칠금.금릉동": ("36.9821246699753", "127.919046610961"),
    "연수동": ("36.9867248377519", "127.934130527889"),
    "목행.용탄동": ("37.0115867558614", "127.917010287047"),
}

DEFAULT_COORDS = ("36.991", "127.925")  # 충주시청 기준


# ===== Pydantic 모델 =====
class AddressToCoordRequest(BaseModel):
    address: str


class CoordToAddressRequest(BaseModel):
    lat: float
    lon: float


class CoordResult(BaseModel):
    address: str
    lat: Optional[str]
    lon: Optional[str]
    accuracy: str
    error: str


class AddressResult(BaseModel):
    lat: float
    lon: float
    jibun_address: Optional[str]
    road_address: Optional[str]
    error: str


# ===== 카카오 API 함수 =====
async def get_coords_from_kakao(address: str) -> Dict[str, Any]:
    """카카오 API로 주소 → 좌표 변환"""
    if not KAKAO_API_KEY:
        return {"lat": None, "lon": None, "accuracy": "", "error": "API 키 미설정"}
    
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": address}
    
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, headers=headers, params=params)
            if r.status_code == 200:
                docs = r.json().get("documents", [])
                if docs:
                    return {
                        "lat": docs[0]["y"],
                        "lon": docs[0]["x"],
                        "accuracy": "정좌표",
                        "error": ""
                    }
                return {"lat": None, "lon": None, "accuracy": "", "error": "주소 없음"}
            return {"lat": None, "lon": None, "accuracy": "", "error": f"API 오류({r.status_code})"}
        except Exception as e:
            return {"lat": None, "lon": None, "accuracy": "", "error": str(e)}


async def get_coords_with_fallback(address: str) -> Dict[str, Any]:
    """주소 → 좌표 변환 (fallback 포함)"""
    # 1차: 전체 주소로 시도
    result = await get_coords_from_kakao(address)
    if result["lat"]:
        return result
    
    # 2차: 인근번지 보정
    match = re.search(r"(\d+)-(\d+)", address)
    if match:
        base = int(match.group(1))
        sub = int(match.group(2))
        for i in range(1, 4):
            new_sub = sub - i
            if new_sub < 0:
                break
            new_addr = re.sub(r"\d+-\d+", f"{base}-{new_sub}", address)
            result = await get_coords_from_kakao(new_addr)
            if result["lat"]:
                result["accuracy"] = f"인근번지 보정({base}-{new_sub})"
                return result
        
        # 단일번지로 재시도
        result = await get_coords_from_kakao(address.replace(f"{base}-{sub}", str(base)))
        if result["lat"]:
            result["accuracy"] = f"인근번지 보정({base})"
            return result
    
    # 3차: 행정동 기반 좌표
    for dong, (lat, lon) in DONG_COORDS.items():
        if dong in address:
            return {"lat": lat, "lon": lon, "accuracy": "행정동 대표좌표", "error": ""}
    
    # 4차: 시군구 중심 좌표
    lat, lon = DEFAULT_COORDS
    return {"lat": lat, "lon": lon, "accuracy": "시군구 대표좌표", "error": ""}


async def get_address_from_kakao(lat: float, lon: float) -> Dict[str, Any]:
    """카카오 API로 좌표 → 주소 변환"""
    if not KAKAO_API_KEY:
        return {"jibun": None, "road": None, "error": "API 키 미설정"}
    
    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"x": lon, "y": lat}
    
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, headers=headers, params=params)
            if r.status_code == 200:
                docs = r.json().get("documents", [])
                if docs:
                    doc = docs[0]
                    jibun = doc.get("address", {}).get("address_name")
                    road_info = doc.get("road_address")
                    road = road_info.get("address_name") if road_info else None
                    return {"jibun": jibun, "road": road, "error": ""}
                return {"jibun": None, "road": None, "error": "주소정제 실패"}
            return {"jibun": None, "road": None, "error": f"API 오류({r.status_code})"}
        except Exception as e:
            return {"jibun": None, "road": None, "error": str(e)}


# ===== API 엔드포인트 =====
@router.post("/address-to-coord")
async def address_to_coord(request: AddressToCoordRequest):
    """단일 주소 → 좌표 변환"""
    result = await get_coords_with_fallback(request.address)
    return {
        "address": request.address,
        "lat": result["lat"],
        "lon": result["lon"],
        "accuracy": result["accuracy"],
        "error": result["error"]
    }


@router.post("/coord-to-address")
async def coord_to_address(request: CoordToAddressRequest):
    """단일 좌표 → 주소 변환"""
    result = await get_address_from_kakao(request.lat, request.lon)
    return {
        "lat": request.lat,
        "lon": request.lon,
        "jibun_address": result["jibun"],
        "road_address": result["road"],
        "error": result["error"]
    }


@router.post("/file/address-to-coord")
async def file_address_to_coord(file: UploadFile = File(...)):
    """파일 업로드 - 주소 → 좌표 일괄 변환"""
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="xlsx, xls, csv 파일만 지원합니다.")
    
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            for encoding in ['utf-8', 'cp949', 'euc-kr']:
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding=encoding)
                    break
                except:
                    continue
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        if "주소" not in df.columns:
            raise HTTPException(status_code=400, detail="'주소' 컬럼이 필요합니다.")
        
        results = []
        for addr in df["주소"]:
            r = await get_coords_with_fallback(str(addr))
            results.append({
                "주소": addr,
                "위도": r["lat"],
                "경도": r["lon"],
                "정확도": r["accuracy"],
                "오류": r["error"]
            })
        
        result_df = pd.DataFrame(results)
        
        # 엑셀 파일로 반환
        output = io.BytesIO()
        result_df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=result_address_to_coord.xlsx"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 실패: {str(e)}")


@router.post("/file/coord-to-address")
async def file_coord_to_address(file: UploadFile = File(...)):
    """파일 업로드 - 좌표 → 주소 일괄 변환"""
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="xlsx, xls, csv 파일만 지원합니다.")
    
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            for encoding in ['utf-8', 'cp949', 'euc-kr']:
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding=encoding)
                    break
                except:
                    continue
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        if not all(col in df.columns for col in ["위도", "경도"]):
            raise HTTPException(status_code=400, detail="'위도', '경도' 컬럼이 필요합니다.")
        
        results = []
        for _, row in df.iterrows():
            r = await get_address_from_kakao(float(row["위도"]), float(row["경도"]))
            results.append({
                "위도": row["위도"],
                "경도": row["경도"],
                "지번주소": r["jibun"],
                "도로명주소": r["road"],
                "오류": r["error"]
            })
        
        result_df = pd.DataFrame(results)
        
        output = io.BytesIO()
        result_df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=result_coord_to_address.xlsx"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 실패: {str(e)}")


@router.get("/template/{template_type}")
async def download_template(template_type: str):
    """템플릿 다운로드"""
    if template_type == "address":
        df = pd.DataFrame(columns=["주소"])
        filename = "template_주소_좌표.xlsx"
    elif template_type == "coord":
        df = pd.DataFrame(columns=["위도", "경도"])
        filename = "template_좌표_주소.xlsx"
    else:
        raise HTTPException(status_code=400, detail="잘못된 템플릿 타입")
    
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
@router.get("/debug-key")
async def debug_key():
    """API 키 확인용 (디버깅 후 삭제)"""
    key = getattr(settings, 'KAKAO_API_KEY', '')
    return {
        "key_exists": bool(key),
        "key_length": len(key) if key else 0,
        "key_prefix": key[:4] + "..." if key and len(key) > 4 else "없음"
    }