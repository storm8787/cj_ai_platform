"""
업무보고 결과(report dict) → HWPX(OWPML) 바이너리 생성기

방식(중요):
- 손으로 짠 OWPML 대신, 실제 한글에서 저장된 충주시 서식(REF)을 '템플릿'으로 사용한다.
  → header.xml / settings.xml / secPr / version.xml 등 스타일·글꼴·여백 정의를 그대로 재사용하므로
    한글에서의 열림·서식이 참고 문서와 동일하게 보장된다.
- 본문(section0.xml)만 코드로 생성하며, 참고 서식이 정의한 charPr/paraPr ID를 참조한다.
- 새 pip 의존성 없이 표준 zipfile + 기존 lxml만 사용.

참고 서식(REF-A: 충주시 보고 양식)에서 추출한 스타일:
- 여백: 좌우 15mm / 상 20mm (secPr에 포함, 템플릿 그대로 사용)
- 글꼴/크기: 제목·대분류 = HY헤드라인M 16pt(charPr 29), 본문 = 휴먼명조 15pt(charPr 31),
  머리말 = 휴먼고딕 15pt(charPr 18)
- 정렬: 가운데 paraPr 28 / 대분류 paraPr 35 / 본문 paraPr 36
- 목차 기호 체계: □(대분류) · ❍(중분류) · -(소분류) · ※(참고)

템플릿 자산: backend/services/templates/hwpx/
"""
from typing import Dict, Any, List, Tuple
from io import BytesIO
import os
import re
import zipfile

from lxml import etree


# ===========================================
# 템플릿 로드 (REF 서식에서 추출)
# ===========================================
_TPL_DIR = os.path.join(os.path.dirname(__file__), "templates", "hwpx")


def _load_tpl(name: str) -> str:
    with open(os.path.join(_TPL_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


_HEADER_XML = _load_tpl("header.xml")
_SETTINGS_XML = _load_tpl("settings.xml")
_CONTAINER_RDF = _load_tpl("container.rdf")
_MANIFEST_XML = _load_tpl("manifest.xml")
_VERSION_XML = _load_tpl("version.xml")
_SECPR_XML = _load_tpl("secpr.xml").strip()      # <hp:secPr ...>...</hp:secPr>
_SEC_OPEN = _load_tpl("sec_open.txt").strip()    # <hs:sec ...ns...>

_MIMETYPE = b"application/hwp+zip"

# ── REF 서식의 스타일 ID (header.xml에 정의됨) ──
_STYLE = "0"           # 바탕글
_CHAR_TITLE = "29"     # HY헤드라인M 16pt (제목·□대분류)
_CHAR_BODY = "31"      # 휴먼명조 15pt (❍·-·※ 본문)
_CHAR_META = "18"      # 휴먼고딕 15pt (머리말)
_PARA_CENTER = "28"    # 가운데 정렬
_PARA_HEADING = "35"   # 대분류(양쪽)
_PARA_BODY = "36"      # 본문(양쪽)

# charPr → 글자높이(HWPUNIT), lineseg 높이 계산용
_CHAR_HEIGHT = {"29": 1600, "31": 1500, "18": 1500}

# 본문 영역 폭: A4(59528) - 좌(4251) - 우(4251)
_HORZSIZE = 59528 - 4251 - 4251


# ===========================================
# 개조식 기호/레벨 처리
# ===========================================
# 이미 들어있는 불릿/마커 (제거 후 표준 기호로 치환)
_LEADING_MARKER = re.compile(
    r"^\s*("
    r"[□❍○●◦▪·•*∙‣]"              # 불릿류
    r"|[-–‐]"                        # 대시류
    r"|[가-힣][.)]"                  # 한글 소분류 가. 나)
    r"|[①-⑳]"                        # 원문자
    r"|\d{1,2}[.)]"                  # 숫자 1. 1)
    r")\s*"
)


def _classify_item(text: str) -> Tuple[str, str]:
    """항목 텍스트 → (표준기호, 본문). 레벨에 맞는 기호(❍/-/※)를 부여."""
    raw = (text or "").strip()
    if not raw:
        return "", ""

    # 참고성 항목(※로 시작) → ※ 유지
    if raw[0] == "※":
        return "※", raw[1:].strip()

    m = _LEADING_MARKER.match(raw)
    marker = m.group(1) if m else ""
    body = _LEADING_MARKER.sub("", raw, count=1).strip() if m else raw

    # 소분류(한글 가./원문자/대시)면 - 레벨, 그 외는 ❍ 레벨
    if marker and (re.match(r"[가-힣][.)]", marker) or re.match(r"[①-⑳]", marker) or marker in "-–‐"):
        return "-", body
    return "❍", body


# ===========================================
# 문단 생성
# ===========================================
def _esc(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _lineseg(char_id: str) -> str:
    h = _CHAR_HEIGHT.get(char_id, 1500)
    baseline = int(h * 0.85)
    spacing = int(h * 0.4)
    return (
        '<hp:linesegarray>'
        f'<hp:lineseg textpos="0" vertpos="0" vertsize="{h}" textheight="{h}" '
        f'baseline="{baseline}" spacing="{spacing}" horzpos="0" horzsize="{_HORZSIZE}" flags="393216"/>'
        '</hp:linesegarray>'
    )


def _p(pid: int, para: str, char: str, text: str, first: bool = False) -> str:
    t = f"<hp:t>{_esc(text)}</hp:t>" if text else "<hp:t></hp:t>"
    if first:
        # 첫 문단: secPr을 담은 run + 텍스트 run
        runs = f'<hp:run charPrIDRef="{char}">{_SECPR_XML}</hp:run><hp:run charPrIDRef="{char}">{t}</hp:run>'
    else:
        runs = f'<hp:run charPrIDRef="{char}">{t}</hp:run>'
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para}" styleIDRef="{_STYLE}" '
        f'pageBreak="0" columnBreak="0" merged="0">{runs}{_lineseg(char)}</hp:p>'
    )


def _build_section(report: Dict[str, Any]) -> str:
    paras: List[str] = []
    pid = 0

    def add(para: str, char: str, text: str):
        nonlocal pid
        paras.append(_p(pid, para, char, text, first=(pid == 0)))
        pid += 1

    title = (report.get("title") or "").strip()
    department = (report.get("department") or "").strip()
    author = (report.get("author") or "").strip()
    report_date = (report.get("report_date") or "").strip()
    summary = (report.get("summary") or "").strip()
    sections = report.get("sections", []) or []

    # 제목 (가운데, HY헤드라인M 16pt)
    add(_PARA_CENTER, _CHAR_TITLE, title or "업무보고")

    # 머리말 (부서 · 보고일자 · 작성자)
    meta = "  ·  ".join([v for v in (department, report_date, author) if v])
    if meta:
        add(_PARA_CENTER, _CHAR_META, meta)

    add(_PARA_BODY, _CHAR_BODY, "")  # 빈 줄

    # 요약 → □ 요약 + 본문
    if summary:
        add(_PARA_HEADING, _CHAR_TITLE, "□ 요약")
        add(_PARA_BODY, _CHAR_BODY, summary)
        add(_PARA_BODY, _CHAR_BODY, "")

    # 섹션 → □ 대분류 + ❍/-/※ 항목
    for sec in sections:
        sec_title = (sec.get("title") or "").strip()
        contents = sec.get("content", []) or []
        if sec_title:
            add(_PARA_HEADING, _CHAR_TITLE, f"□ {sec_title}")
        for item in contents:
            if not item or not str(item).strip():
                continue
            symbol, body = _classify_item(str(item))
            if not body:
                continue
            if symbol == "-":
                # 소분류: 들여쓰기(전각 공백) + -
                add(_PARA_BODY, _CHAR_BODY, f"　- {body}")
            elif symbol == "※":
                add(_PARA_BODY, _CHAR_BODY, f"※ {body}")
            else:
                add(_PARA_BODY, _CHAR_BODY, f"❍ {body}")
        add(_PARA_BODY, _CHAR_BODY, "")  # 섹션 간 빈 줄

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        + _SEC_OPEN
        + "".join(paras)
        + "</hs:sec>"
    )


# ===========================================
# 패키징
# ===========================================
def _content_hpf(title: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<opf:package xmlns:opf="http://www.idpf.org/2007/opf/" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" version="" unique-identifier="" id="">'
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
        '<opf:itemref idref="header" linear="yes"/>'
        '<opf:itemref idref="section0" linear="yes"/>'
        '</opf:spine>'
        '</opf:package>'
    )


_CONTAINER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<ocf:container xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container" '
    'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf">'
    '<ocf:rootfiles>'
    '<ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/>'
    '<ocf:rootfile full-path="META-INF/container.rdf" media-type="application/rdf+xml"/>'
    '</ocf:rootfiles>'
    '</ocf:container>'
)


def _validate_xml(name: str, content: str):
    try:
        etree.fromstring(content.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        raise ValueError(f"HWPX 내부 XML({name}) 생성 오류: {e}") from e


def build_hwpx(report: Dict[str, Any]) -> bytes:
    """report dict → HWPX 바이너리(zip)"""
    title = (report.get("title") or "업무보고").strip() or "업무보고"
    section_xml = _build_section(report)
    content_hpf = _content_hpf(title)

    _validate_xml("section0.xml", section_xml)
    _validate_xml("content.hpf", content_hpf)

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype: 최상단 + 무압축
        zi = zipfile.ZipInfo("mimetype")
        zi.compress_type = zipfile.ZIP_STORED
        zf.writestr(zi, _MIMETYPE)

        zf.writestr("version.xml", _VERSION_XML)
        zf.writestr("META-INF/container.xml", _CONTAINER_XML)
        zf.writestr("META-INF/container.rdf", _CONTAINER_RDF)
        zf.writestr("META-INF/manifest.xml", _MANIFEST_XML)
        zf.writestr("Contents/content.hpf", content_hpf)
        zf.writestr("Contents/header.xml", _HEADER_XML)
        zf.writestr("Contents/section0.xml", section_xml)
        zf.writestr("settings.xml", _SETTINGS_XML)

    return buf.getvalue()
