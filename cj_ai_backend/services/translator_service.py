import os
import tempfile
import zipfile
import shutil
import re
from io import BytesIO
from lxml import etree
from typing import Optional
import deepl
from openai import OpenAI

from utils.openai_client import get_openai_client


class TranslatorService:
    def __init__(self):
        self.openai_client = get_openai_client()
        
        # SSL 인증서 검증 비활성화 (회사/공공기관 네트워크용)
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        
        # DeepL API 키
        deepl_key = os.getenv("DEEPL_API_KEY")
        if not deepl_key:
            raise ValueError("DEEPL_API_KEY 환경변수가 설정되지 않았습니다")
        self.deepl_translator = deepl.Translator(deepl_key)
        
        # 상수
        self.FWSPACE_LOCALNAME = 'fwSpace'
        self.WS_PATTERN = re.compile(r'[\u00A0\u1680\u180E\u2000-\u200D\u202F\u205F\u2060\u3000\uFEFF]')
        self.ZW_PATTERN = re.compile(r'[\u200B-\u200D\u2060\uFEFF]')
    
    def has_korean(self, text: str) -> bool:
        """한글 포함 여부 확인"""
        return bool(re.search(r'[가-힣]', text))
    
    def normalize_spaces_strict(self, s: str) -> str:
        """공백 정규화"""
        if not s:
            return s
        s = self.WS_PATTERN.sub(' ', s)
        s = self.ZW_PATTERN.sub('', s)
        s = re.sub(r'[\t]+', ' ', s)
        s = re.sub(r' {2,}', ' ', s)
        return s.strip()
    
    def extract_full_text(self, t_elem):
        """텍스트 요소에서 전체 텍스트 추출"""
        parts = []
        if t_elem.text:
            parts.append(t_elem.text)
        for child in t_elem:
            if child.tag.split('}')[-1] == self.FWSPACE_LOCALNAME:
                parts.append(' ')
            if child.tail:
                parts.append(child.tail)
        return ''.join(parts)
    
    def remove_only_fwspace_children(self, t_elem):
        """fwSpace 자식 요소 제거"""
        to_remove = []
        for child in t_elem:
            if child.tag.split('}')[-1] == self.FWSPACE_LOCALNAME:
                to_remove.append(child)
        for child in to_remove:
            if child.tail:
                t_elem.text = (t_elem.text or '') + child.tail
            t_elem.remove(child)
    
    def set_clean_text(self, t_elem, translated_text):
        """번역된 텍스트를 깨끗하게 설정"""
        self.remove_only_fwspace_children(t_elem)
        translated_text = self.normalize_spaces_strict(translated_text)
        t_elem.text = translated_text
        for child in t_elem:
            child.tail = None
    
    def gpt_translate_full(self, original: str, target_lang: str) -> Optional[str]:
        """GPT로 2차 번역"""
        lang_name_map = {
            "KO": "Korean",
            "EN-US": "American English",
            "EN-GB": "British English",
            "JA": "Japanese",
            "ZH-HANS": "Simplified Chinese",
            "ZH-HANT": "Traditional Chinese",
            "VI": "Vietnamese",
            "TH": "Thai",
            "RU": "Russian",
            "AR": "Arabic",
            "HE": "Hebrew",
            "ES": "Spanish",
            "DE": "German",
            "FR": "French",
            "ID": "Indonesian",
            "IT": "Italian",
            "PT": "Portuguese",
            "PT-BR": "Brazilian Portuguese",
            "PL": "Polish",
            "NL": "Dutch",
            "TR": "Turkish",
            "UK": "Ukrainian"
        }

        target_lang_name = lang_name_map.get(target_lang, "English")
        prompt = f"""Translate this Korean text to {target_lang_name}.

Korean text:
{original}

Return ONLY the translation, no explanations.

Translation:"""
        try:
            resp = self.openai_client.chat.completions.create(
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
    
    def fix_spacing_in_header(self, header_path: str, font_mode: str = "all") -> tuple:
        """header.xml 보정"""
        ns = {'hh': 'http://www.hancom.co.kr/hwpml/2011/head'}
        with open(header_path, 'rb') as f:
            xml_content = f.read()

        try:
            parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False)
            tree = etree.fromstring(xml_content, parser)
            fixed_count = 0

            # spacing 자간 0
            spacing_elements = tree.xpath('.//hh:spacing', namespaces=ns)
            for spacing in spacing_elements:
                for attr in ['hangul', 'latin', 'hanja', 'japanese', 'other', 'symbol', 'user']:
                    if spacing.get(attr, '0') != '0':
                        spacing.set(attr, '0')
                        fixed_count += 1

            # JUSTIFY -> LEFT
            align_elements = tree.xpath('.//hh:align[@horizontal="JUSTIFY"]', namespaces=ns)
            for align in align_elements:
                align.set('horizontal', 'LEFT')
                fixed_count += 1

            # charSpacing 0
            charpr_elements = tree.xpath('.//hh:charPr', namespaces=ns)
            for charpr in charpr_elements:
                if charpr.get('charSpacing') and charpr.get('charSpacing') != '0':
                    charpr.set('charSpacing', '0')
                    fixed_count += 1

            # 폰트 보정
            font_changed = 0
            if font_mode != "none":
                fontfaces = tree.xpath('.//hh:fontface', namespaces=ns)
                malgun_ids = {}
                for fontface in fontfaces:
                    lang = fontface.get('lang', '').upper()
                    fonts = fontface.xpath('.//hh:font', namespaces=ns)
                    for font in fonts:
                        face = font.get('face', '')
                        if '맑은 고딕' in face or 'Malgun Gothic' in face:
                            lang_map = {
                                'HANGUL': 'hangul', 'LATIN': 'latin', 'HANJA': 'hanja',
                                'JAPANESE': 'japanese', 'OTHER': 'other',
                                'SYMBOL': 'symbol', 'USER': 'user'
                            }
                            attr_name = lang_map.get(lang)
                            if attr_name:
                                font_id = font.get('id')
                                if font_id:
                                    malgun_ids[attr_name] = font_id

                if malgun_ids:
                    charshapes = tree.xpath('.//hh:charshape', namespaces=ns)
                    for charshape in charshapes:
                        fontRefs = charshape.xpath('.//hh:fontRef', namespaces=ns)
                        for fontRef in fontRefs:
                            if font_mode == "all":
                                for attr_name, font_id in malgun_ids.items():
                                    old_val = fontRef.get(attr_name)
                                    if old_val and old_val != font_id:
                                        fontRef.set(attr_name, font_id)
                                        font_changed += 1
                            elif font_mode == "hangul_only" and 'hangul' in malgun_ids:
                                old_val = fontRef.get('hangul')
                                new_val = malgun_ids['hangul']
                                if old_val != new_val:
                                    fontRef.set('hangul', new_val)
                                    font_changed += 1

            with open(header_path, 'wb') as f:
                f.write(etree.tostring(
                    tree, encoding='UTF-8', xml_declaration=True, pretty_print=False
                ))
            return (fixed_count, font_changed)

        except Exception as e:
            return (0, 0)
    
    def sweep_body_charspacing_zero(self, tree):
        """본문 charSpacing 0으로 스윕"""
        charprs = tree.xpath(".//*[local-name()='charPr']")
        changed = 0
        for c in charprs:
            v = c.get('charSpacing')
            if v and v != '0':
                c.set('charSpacing', '0')
                changed += 1
        return changed
    
    def translate_hwpx_sync(
        self,
        file_bytes: bytes,
        target_lang: str,
        font_mode: str = "all"
    ) -> bytes:
        """HWPX 파일 번역 메인 로직 (동기)"""
        
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix=".hwpx") as tmp_input:
            tmp_input.write(file_bytes)
            tmp_input_path = tmp_input.name

        extract_dir = tempfile.mkdtemp()
        
        try:
            # HWPX 압축 해제
            with zipfile.ZipFile(tmp_input_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # header.xml 보정
            header_path = os.path.join(extract_dir, 'Contents', 'header.xml')
            if os.path.exists(header_path):
                self.fix_spacing_in_header(header_path, font_mode=font_mode)

            # 본문 XML 파일 찾기
            xml_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.xml') and file != 'header.xml':
                        xml_files.append(os.path.join(root, file))

            total_translations = 0
            gpt_translations = 0

            # 각 XML 파일 번역
            for xml_file in xml_files:
                with open(xml_file, 'rb') as f:
                    xml_content = f.read()

                try:
                    parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False)
                    tree = etree.fromstring(xml_content, parser)

                    # 텍스트 요소 찾기
                    t_elements = tree.xpath(".//*[local-name()='t']")
                    for t_elem in t_elements:
                        original_text = self.extract_full_text(t_elem)
                        if not original_text or not original_text.strip():
                            continue

                        # 1차: DeepL 번역
                        try:
                            deepl_result = self.deepl_translator.translate_text(
                                original_text, target_lang=target_lang
                            ).text
                        except Exception:
                            deepl_result = original_text

                        final_translation = deepl_result

                        # 2차: GPT 번역 (한글 남아있으면)
                        if self.has_korean(deepl_result):
                            gpt_result = self.gpt_translate_full(original_text, target_lang)
                            if gpt_result and not self.has_korean(gpt_result):
                                final_translation = gpt_result
                                gpt_translations += 1

                        # 번역된 텍스트 설정
                        try:
                            self.set_clean_text(t_elem, final_translation)
                            total_translations += 1
                        except Exception:
                            t_elem.text = self.normalize_spaces_strict(final_translation)
                            for child in list(t_elem):
                                if child.tag.split('}')[-1] == self.FWSPACE_LOCALNAME:
                                    t_elem.remove(child)

                    # charSpacing 스윕
                    self.sweep_body_charspacing_zero(tree)

                    # linesegarray 삭제
                    linesegarray_elements = tree.xpath(".//*[local-name()='linesegarray']")
                    for lsa in linesegarray_elements:
                        parent = lsa.getparent()
                        if parent is not None:
                            parent.remove(lsa)

                    # 파일 저장
                    with open(xml_file, 'wb') as f:
                        f.write(etree.tostring(
                            tree, encoding='UTF-8', xml_declaration=True, pretty_print=False
                        ))

                except etree.XMLSyntaxError:
                    pass

            print(f"✅ 번역 완료: 총 {total_translations}개, GPT 2차 {gpt_translations}개")

            # 재압축
            output_buffer = BytesIO()
            with zipfile.ZipFile(output_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, extract_dir)
                        zip_out.write(file_path, arcname)

            return output_buffer.getvalue()

        finally:
            # 임시 파일 정리
            os.remove(tmp_input_path)
            shutil.rmtree(extract_dir)