"""
업무보고 결과(report dict) → HWPX(OWPML) 바이너리 생성기

- 새로운 pip 의존성 없이 표준 라이브러리 zipfile + lxml(기존 설치)만 사용
- HWPX는 OWPML 규격의 zip 컨테이너 (mimetype + version.xml + Contents/* + META-INF/*)
- 이 모듈은 '구조적으로 유효한' HWPX를 생성한다. 실제 한글(HWP) 프로그램에서의
  렌더링/열림 검증은 배포 환경에서만 가능하므로, 열리지 않을 경우 HEADER_XML /
  _sec_pr() 템플릿을 실제 한글에서 저장한 빈 문서로 교체하면 된다.

참고 단위:
- HWPUNIT = 1/7200 inch → 1pt = 100 HWPUNIT, 1mm ≈ 283.465 HWPUNIT
- A4: 가로 210mm=59528, 세로 297mm=84188
"""
from typing import Dict, Any, List
from io import BytesIO
import zipfile
import re

from lxml import etree


# ===========================================
# XML 이스케이프
# ===========================================
def _esc(text: str) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ===========================================
# 개조식 마커 판별 (프론트 parseItem과 동일 규칙)
# ===========================================
_MARKER_RE = re.compile(r"^((?:[가-힣][.)])|(?:\d{1,2}[.)])|[①-⑳])\s+")


def _item_indent_level(text: str) -> int:
    """0: 마커 없음/숫자 최상위, 1: 한글 소분류(가./나.) 들여쓰기"""
    m = _MARKER_RE.match(text or "")
    if not m:
        return 0
    marker = m.group(1)
    # 한글 소분류(가. 나.)와 원문자(①)는 하위 레벨로 들여쓰기
    if re.match(r"^[가-힣]", marker) or re.match(r"^[①-⑳]", marker):
        return 1
    return 0


# ===========================================
# 고정 파트 (컨테이너/버전/설정)
# ===========================================
_MIMETYPE = b"application/hwp+zip"

_VERSION_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<hv:HCFVersion xmlns:hv="http://www.hancom.co.kr/hwpml/2011/version" '
    'tagetApplication="WORDPROCESSOR" major="5" minor="0" micro="5" buildNumber="0" '
    'os="1" xmlVersion="1.4" application="cj-ai-platform" appVersion="1.0.0.0"/>'
)

_CONTAINER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<ocf:container xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container" '
    'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf">'
    '<ocf:rootfiles>'
    '<ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/>'
    '</ocf:rootfiles>'
    '</ocf:container>'
)

_SETTINGS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<ha:HWPApplicationSetting xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app">'
    '<ha:CaretPosition listIDRef="0" paraIDRef="0" pos="0"/>'
    '</ha:HWPApplicationSetting>'
)


def _content_hpf(title: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<opf:package xmlns:opf="http://www.idpf.org/2007/opf/" '
        'version="" unique-identifier="" id="">'
        '<opf:metadata>'
        f'<opf:title>{_esc(title)}</opf:title>'
        '<opf:language>ko</opf:language>'
        '</opf:metadata>'
        '<opf:manifest>'
        '<opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>'
        '<opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>'
        '<opf:item id="settings" href="settings.xml" media-type="application/xml"/>'
        '</opf:manifest>'
        '<opf:spine>'
        '<opf:itemref idref="header"/>'
        '<opf:itemref idref="section0"/>'
        '</opf:spine>'
        '</opf:package>'
    )


# ===========================================
# header.xml (글꼴/글자모양/문단모양/스타일 정의)
# ===========================================
_LANGS = ("HANGUL", "LATIN", "HANJA", "JAPANESE", "OTHER", "SYMBOL", "USER")
_FONT_ATTRS = 'hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"'
_RATIO_ATTRS = 'hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"'
_ZERO_ATTRS = 'hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"'


def _fontfaces() -> str:
    faces = []
    for lang in _LANGS:
        faces.append(
            f'<hh:fontface lang="{lang}" fontCnt="1">'
            '<hh:font id="0" face="함초롬바탕" type="TTF" isEmbedded="0">'
            '<hh:typeInfo familyType="FCAP_TYPE_UNKNOWN" weight="0" proportion="0" '
            'contrast="0" strokeVariation="0" armStyle="0" letterform="0" midline="0" xHeight="0"/>'
            '</hh:font></hh:fontface>'
        )
    return f'<hh:fontfaces itemCnt="{len(_LANGS)}">' + "".join(faces) + "</hh:fontfaces>"


def _char_pr(cid: int, height: int, bold: bool, color: str = "#000000") -> str:
    bold_el = "<hh:bold/>" if bold else ""
    return (
        f'<hh:charPr id="{cid}" height="{height}" textColor="{color}" shadeColor="none" '
        'useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="1">'
        f'<hh:fontRef {_FONT_ATTRS}/>'
        f'<hh:ratio {_RATIO_ATTRS}/>'
        f'<hh:spacing {_ZERO_ATTRS}/>'
        f'<hh:relSz {_RATIO_ATTRS}/>'
        f'<hh:offset {_ZERO_ATTRS}/>'
        f'{bold_el}'
        '<hh:underline type="NONE" shape="SOLID" color="#000000"/>'
        '<hh:strikeout shape="NONE" color="#000000"/>'
        '<hh:outline type="NONE"/>'
        '<hh:shadow type="NONE" color="#C0C0C0" offsetX="10" offsetY="10"/>'
        '</hh:charPr>'
    )


def _para_pr(pid: int, align: str, left_margin: int = 0) -> str:
    return (
        f'<hh:paraPr id="{pid}" tabPrIDRef="0" condense="0" fontLineHeight="0" '
        'snapToGrid="1" suppressLineNumbers="0" checked="0">'
        f'<hh:align horizontal="{align}" vertical="BASELINE"/>'
        '<hh:heading type="NONE" idRef="0" level="0"/>'
        '<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="KEEP_WORD" '
        'widowOrphan="0" keepWithNext="0" keepLines="0" pageBreakBefore="0" lineWrap="BREAK"/>'
        '<hh:margin>'
        '<hc:intent value="0" unit="HWPUNIT"/>'
        f'<hc:left value="{left_margin}" unit="HWPUNIT"/>'
        '<hc:right value="0" unit="HWPUNIT"/>'
        '<hc:prev value="0" unit="HWPUNIT"/>'
        '<hc:next value="0" unit="HWPUNIT"/>'
        '</hh:margin>'
        '<hh:lineSpacing type="PERCENT" value="160" unit="HWPUNIT"/>'
        '</hh:paraPr>'
    )


# charPr: 0 본문(10pt), 1 소제목(12pt bold), 2 제목(16pt bold), 3 머리말(10pt 회색)
_CHAR_PRS = [
    _char_pr(0, 1000, False),
    _char_pr(1, 1200, True),
    _char_pr(2, 1600, True),
    _char_pr(3, 1000, False, color="#666666"),
]

# paraPr: 0 양쪽정렬 본문, 1 가운데정렬, 2 들여쓰기 본문(소분류)
_PARA_PRS = [
    _para_pr(0, "JUSTIFY", 0),
    _para_pr(1, "CENTER", 0),
    _para_pr(2, "JUSTIFY", 1400),
]

_HEADER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" '
    'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
    'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" version="1.4" secCnt="1">'
    '<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/>'
    '<hh:refList>'
    + _fontfaces()
    + '<hh:borderFills itemCnt="1">'
    '<hh:borderFill id="1" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
    '<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
    '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
    '<hh:leftBorder type="NONE" width="0.1 mm" color="#000000"/>'
    '<hh:rightBorder type="NONE" width="0.1 mm" color="#000000"/>'
    '<hh:topBorder type="NONE" width="0.1 mm" color="#000000"/>'
    '<hh:bottomBorder type="NONE" width="0.1 mm" color="#000000"/>'
    '<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>'
    '</hh:borderFill>'
    '</hh:borderFills>'
    + f'<hh:charProperties itemCnt="{len(_CHAR_PRS)}">' + "".join(_CHAR_PRS) + '</hh:charProperties>'
    + f'<hh:paraProperties itemCnt="{len(_PARA_PRS)}">' + "".join(_PARA_PRS) + '</hh:paraProperties>'
    + '<hh:styles itemCnt="1">'
    '<hh:style id="0" type="PARA" name="바탕글" engName="Normal" paraPrIDRef="0" '
    'charPrIDRef="0" nextStyleIDRef="0" langID="1042" lockForm="0"/>'
    '</hh:styles>'
    '</hh:refList>'
    '</hh:head>'
)


# ===========================================
# section0.xml (본문)
# ===========================================
def _sec_pr() -> str:
    """첫 문단 첫 run에 들어가는 구역 속성 (A4 세로)"""
    return (
        '<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" tabStop="8000" '
        'tabStopVal="4000" tabStopUnit="HWPUNIT" memoShapeIDRef="0" '
        'textVerticalWidthHead="0" masterPageCnt="0">'
        '<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0" strtnum="0"/>'
        '<hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0"/>'
        '<hp:visibility hideFirstHeader="0" hideFirstFooter="0" hideFirstMasterPage="0" '
        'border="SHOW_ALL" fill="SHOW_ALL" hideFirstPageNum="0" hideFirstEmptyLine="0" showLineNumber="0"/>'
        '<hp:lineNumberShape restartType="0" countBy="0" distance="0" startNumber="0"/>'
        '<hp:pagePr landscape="WIDELY" width="59528" height="84188" gutterType="LEFT_ONLY">'
        '<hp:margin header="4252" footer="4252" gutter="0" left="8504" right="8504" top="5668" bottom="4252"/>'
        '</hp:pagePr>'
        '</hp:secPr>'
    )


_LINESEG = (
    '<hp:linesegarray>'
    '<hp:lineseg textpos="0" vertpos="0" vertsize="1000" textheight="1000" baseline="850" '
    'spacing="600" horzpos="0" horzsize="42520" flags="393216"/>'
    '</hp:linesegarray>'
)


def _paragraph(pid: int, para_pr: int, char_pr: int, text: str, first: bool = False) -> str:
    secpr = _sec_pr() if first else ""
    t = f"<hp:t>{_esc(text)}</hp:t>" if text else "<hp:t></hp:t>"
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para_pr}" styleIDRef="0" pageBreak="0" '
        'columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{char_pr}">{secpr}{t}</hp:run>'
        f'{_LINESEG}'
        '</hp:p>'
    )


def _build_section(report: Dict[str, Any]) -> str:
    paras: List[str] = []
    pid = 0

    def add(para_pr: int, char_pr: int, text: str):
        nonlocal pid
        paras.append(_paragraph(pid, para_pr, char_pr, text, first=(pid == 0))
                     )
        pid += 1

    title = report.get("title", "") or ""
    department = (report.get("department") or "").strip()
    author = (report.get("author") or "").strip()
    report_date = (report.get("report_date") or "").strip()
    summary = (report.get("summary") or "").strip()
    sections = report.get("sections", []) or []

    # 제목 (가운데, 16pt bold)
    add(1, 2, title)

    # 머리말 (부서 · 보고일자 · 작성자)
    meta = "  ·  ".join([v for v in (department, report_date, author) if v])
    if meta:
        add(1, 3, meta)

    add(0, 0, "")  # 빈 줄

    # 요약
    if summary:
        add(0, 1, "□ 요약")
        add(0, 0, summary)
        add(0, 0, "")

    # 섹션
    for sec in sections:
        sec_title = (sec.get("title") or "").strip()
        contents = sec.get("content", []) or []
        if sec_title:
            add(0, 1, f"■ {sec_title}")
        for item in contents:
            if not item or not str(item).strip():
                continue
            item = str(item).strip()
            level = _item_indent_level(item)
            para_pr = 2 if level == 1 else 0
            # 마커가 없으면 개조식 기호(○) 부여
            body = item if _MARKER_RE.match(item) else f"○ {item}"
            add(para_pr, 0, body)
        add(0, 0, "")  # 섹션 간 빈 줄

    body = "".join(paras)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
        'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
        'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core">'
        + body
        + '</hs:sec>'
    )


# ===========================================
# 패키지 조립
# ===========================================
def _validate_xml(name: str, content: str):
    """well-formed 검증 (개발/런타임 안전장치)"""
    try:
        etree.fromstring(content.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        raise ValueError(f"HWPX 내부 XML({name}) 생성 오류: {e}") from e


def build_hwpx(report: Dict[str, Any]) -> bytes:
    """report dict → HWPX 바이너리(zip)"""
    title = report.get("title", "업무보고") or "업무보고"
    header_xml = _HEADER_XML
    section_xml = _build_section(report)
    content_hpf = _content_hpf(title)

    # 내부 XML well-formed 검증
    _validate_xml("header.xml", header_xml)
    _validate_xml("section0.xml", section_xml)
    _validate_xml("content.hpf", content_hpf)

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype은 반드시 첫 번째 + 무압축(STORED)
        zi = zipfile.ZipInfo("mimetype")
        zi.compress_type = zipfile.ZIP_STORED
        zf.writestr(zi, _MIMETYPE)

        zf.writestr("version.xml", _VERSION_XML.encode("utf-8"))
        zf.writestr("META-INF/container.xml", _CONTAINER_XML.encode("utf-8"))
        zf.writestr("Contents/content.hpf", content_hpf.encode("utf-8"))
        zf.writestr("Contents/header.xml", header_xml.encode("utf-8"))
        zf.writestr("Contents/section0.xml", section_xml.encode("utf-8"))
        zf.writestr("settings.xml", _SETTINGS_XML.encode("utf-8"))

    return buf.getvalue()
