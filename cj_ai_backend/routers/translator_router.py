from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
import io

from services.translator_service import TranslatorService
from utils.prompt_filter import check_text_security

router = APIRouter(prefix="/api/translator", tags=["translator"])
service = TranslatorService()


class TranslationResponse(BaseModel):
    success: bool
    filename: Optional[str] = None
    error: Optional[str] = None


@router.post("/translate-hwpx")
async def translate_hwpx(
    file: UploadFile = File(...),
    target_lang: str = Form(...),
    font_mode: str = Form("all")
):
    """HWPX 파일 번역"""
    
    # 파일 형식 확인
    if not file.filename.endswith('.hwpx'):
        raise HTTPException(status_code=400, detail="HWPX 파일만 업로드 가능합니다")
    
    try:
        # 파일 읽기
        file_bytes = await file.read()
        original_name = file.filename.rsplit('.', 1)[0]
        
        print(f"📥 번역 시작: {file.filename}, 언어: {target_lang}, 폰트: {font_mode}")
        
        # 번역 처리 (sync 함수로 호출)
        translated_bytes = service.translate_hwpx_sync(
            file_bytes=file_bytes,
            target_lang=target_lang,
            font_mode=font_mode
        )
        
        print(f"✅ 번역 완료: {file.filename}")
        
        # 파일명 생성
        download_filename = f"{original_name}_translated_{target_lang}.hwpx"
        
        # 파일 반환을 위한 응답
        from fastapi.responses import Response
        return Response(
            content=translated_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={download_filename}"
            }
        )
    
    except Exception as e:
        print(f"❌ 번역 에러: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/languages")
async def get_supported_languages():
    """지원 언어 목록"""
    return {
        "languages": {
            "한국어": "KO",
            "영어 (미국)": "EN-US",
            "영어 (영국)": "EN-GB",
            "일본어": "JA",
            "중국어 (간체)": "ZH-HANS",
            "중국어 (번체)": "ZH-HANT",
            "베트남어": "VI",
            "태국어": "TH",
            "러시아어": "RU",
            "아랍어": "AR",
            "히브리어": "HE",
            "스페인어": "ES",
            "독일어": "DE",
            "프랑스어": "FR",
            "인도네시아어": "ID",
            "이탈리아어": "IT",
            "포르투갈어": "PT",
            "포르투갈어 (브라질)": "PT-BR",
            "폴란드어": "PL",
            "네덜란드어": "NL",
            "터키어": "TR",
            "우크라이나어": "UK"
        }
    }


@router.get("/health")
async def health_check():
    """헬스체크"""
    return {"status": "healthy", "service": "translator"}