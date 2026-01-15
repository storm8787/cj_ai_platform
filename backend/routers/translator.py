"""
다국어 번역기 API - HWPX 파일 번역 (DeepL + GPT)
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import zipfile
import tempfile
import os
import shutil
import re
from io import BytesIO
from lxml import etree
from openai import OpenAI

from config import settings

router = APIRouter()


# 지원 언어 목록
SUPPORTED_LANGUAGES = {
    "KO": "한국어",
    "EN-US": "영어 (미국)",
    "EN-GB": "영어 (영국)",
    "JA": "일본어",
    "ZH-HANS": "중국어 (간체)",
    "ZH-HANT": "중국어 (번체)",
    "VI": "베트남어",
    "TH": "태국어",
    "RU": "러시아어",
    "AR": "아랍어",
    "ES": "스페인어",
    "DE": "독일어",
    "FR": "프랑스어",
    "ID": "인도네시아어",
    "IT": "이탈리아어",
    "PT": "포르투갈어",
    "PT-BR": "포르투갈어 (브라질)",
}


class LanguagesResponse(BaseModel):
    languages: dict


@router.get("/languages", response_model=LanguagesResponse)
async def get_languages():
    """
    지원 언어 목록 반환
    """
    return LanguagesResponse(languages=SUPPORTED_LANGUAGES)


@router.post("/translate")
async def translate_hwpx(
    file: UploadFile = File(...),
    target_lang: str = Form(default="EN-US"),
    font_mode: str = Form(default="all")  # all, hangul_only, none
):
    """
    HWPX 파일 번역
    """
    if not file.filename.endswith('.hwpx'):
        raise HTTPException(status_code=400, detail="HWPX 파일만 지원합니다.")
    
    if target_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 언어입니다: {target_lang}")
    
    try:
        import deepl
        deepl_translator = deepl.Translator(settings.DEEPL_API_KEY)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DeepL 초기화 실패: {str(e)}")
    
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    try:
        file_bytes = await file.read()
        original_name = file.filename.rsplit('.', 1)[0]
        
        # 번역 수행
        translated_bytes = translate_hwpx_preserve_format(
            file_bytes, target_lang, font_mode,
            deepl_translator, openai_client
        )
        
        download_filename = f"{original_name}_translated_{target_lang}.hwpx"
        
        return Response(
            content=translated_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{download_filename}"'
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"번역 실패: {str(e)}")


def has_korean(text: str) -> bool:
    """한글 포함 여부 확인"""
    return bool(re.search(r'[가-힣]', text))


def translate_hwpx_preserve_format(
    file_bytes: bytes,
    target_lang: str,
    font_mode: str,
    deepl_translator,
    openai_client
) -> bytes:
    """
    HWPX 파일 번역 (구조 보존)
    """
    
    def extract_full_text(t_elem) -> str:
        """t 요소에서 전체 텍스트 추출"""
        texts = []
        if t_elem.text:
            texts.append(t_elem.text)
        for child in t_elem:
            local = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if local == 'fwSpace':
                texts.append(' ')
            if child.tail:
                texts.append(child.tail)
        return ''.join(texts)
    
    def set_clean_text(t_elem, new_text: str):
        """t 요소에 새 텍스트 설정"""
        for child in list(t_elem):
            t_elem.remove(child)
        t_elem.text = new_text
    
    def gpt_translate_full(original: str, target_lang: str) -> Optional[str]:
        """GPT 2차 번역"""
        lang_names = {
            "EN-US": "English", "EN-GB": "British English",
            "JA": "Japanese", "ZH-HANS": "Simplified Chinese",
            "ZH-HANT": "Traditional Chinese", "VI": "Vietnamese",
            "TH": "Thai", "RU": "Russian", "AR": "Arabic",
            "ES": "Spanish", "DE": "German", "FR": "French"
        }
        target_lang_name = lang_names.get(target_lang, "English")
        
        prompt = f"""Translate the following Korean text to {target_lang_name}.
Preserve all formatting, numbers, and special characters.

Korean text:
{original}

Return ONLY the translation, no explanations.

Translation:"""
        
        try:
            resp = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"You are a professional translator. Translate Korean to {target_lang_name}."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return None
    
    # 임시 파일로 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".hwpx") as tmp_input:
        tmp_input.write(file_bytes)
        tmp_input_path = tmp_input.name
    
    extract_dir = tempfile.mkdtemp()
    
    try:
        # HWPX 압축 해제
        with zipfile.ZipFile(tmp_input_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # XML 파일 찾기
        xml_files = []
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                if f.endswith('.xml') and f != 'header.xml':
                    xml_files.append(os.path.join(root, f))
        
        total_translations = 0
        gpt_translations = 0
        
        # 각 XML 파일 번역
        for xml_file in xml_files:
            with open(xml_file, 'rb') as f:
                xml_content = f.read()
            
            try:
                parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False)
                tree = etree.fromstring(xml_content, parser)
                
                t_elements = tree.xpath(".//*[local-name()='t']")
                for t_elem in t_elements:
                    original_text = extract_full_text(t_elem)
                    if not original_text or not original_text.strip():
                        continue
                    
                    # DeepL 1차 번역
                    try:
                        deepl_result = deepl_translator.translate_text(
                            original_text, target_lang=target_lang
                        ).text
                    except Exception:
                        deepl_result = original_text
                    
                    final_translation = deepl_result
                    
                    # 한글 잔존 시 GPT 2차 번역
                    if has_korean(deepl_result):
                        gpt_result = gpt_translate_full(original_text, target_lang)
                        if gpt_result and not has_korean(gpt_result):
                            final_translation = gpt_result
                            gpt_translations += 1
                    
                    set_clean_text(t_elem, final_translation)
                    total_translations += 1
                
                # linesegarray 삭제 (레이아웃 재계산용)
                linesegarray_elements = tree.xpath(".//*[local-name()='linesegarray']")
                for lsa in linesegarray_elements:
                    parent = lsa.getparent()
                    if parent is not None:
                        parent.remove(lsa)
                
                with open(xml_file, 'wb') as f:
                    f.write(etree.tostring(
                        tree, encoding='UTF-8', xml_declaration=True, pretty_print=False
                    ))
                    
            except etree.XMLSyntaxError:
                pass
        
        # 재압축
        output_buffer = BytesIO()
        with zipfile.ZipFile(output_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    file_path = os.path.join(root, f)
                    arcname = os.path.relpath(file_path, extract_dir)
                    zip_out.write(file_path, arcname)
        
        return output_buffer.getvalue()
        
    finally:
        os.remove(tmp_input_path)
        shutil.rmtree(extract_dir)
