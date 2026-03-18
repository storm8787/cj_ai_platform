"""
사업 타임라인 생성기 v4
- 4단계: 계획 → 계약 → 시행 → 완료
- 세부 업무 + 소요기간 자동 산출 (법령 챗봇 선택 연동)
- 다중 포맷 내보내기 (PNG, XLSX+TODO, PPTX)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import json, io, base64, logging, httpx

from services.openai_service import OpenAIService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/timeline", tags=["timeline"])
INTERNAL_BASE_URL = "http://localhost:8000"


# ── Models ──

class TimelineTask(BaseModel):
    name: str = Field(...)
    start_month: int = Field(..., ge=1, le=12)
    end_month: int = Field(..., ge=1, le=12)
    start_year: int = Field(...)
    end_year: int = Field(...)
    category: Optional[str] = Field(None)
    is_milestone: bool = Field(False)

class TimelineData(BaseModel):
    title: str = Field(...)
    tasks: list[TimelineTask] = Field(...)
    base_year: int = Field(...)

class AutoSuggestRequest(BaseModel):
    project_name: str = Field(...)
    project_description: Optional[str] = None
    budget: Optional[str] = None
    deadline: Optional[str] = None
    project_type: Optional[str] = None
    contract_type: Optional[str] = None

class ExportDetailTask(BaseModel):
    order: Optional[int] = None
    task: str = ""
    description: Optional[str] = None
    legal_basis: Optional[str] = None
    required: bool = False
    note: Optional[str] = None
    duration: Optional[str] = None

class ExportDetailGroup(BaseModel):
    task_name: str = ""
    task_category: str = ""
    items: list[ExportDetailTask] = []

class ExportRequest(BaseModel):
    timeline: TimelineData
    format: str = Field(..., pattern="^(png|xlsx|pptx)$")
    detail_tasks: Optional[list[ExportDetailGroup]] = None

class DetailTasksRequest(BaseModel):
    task_name: str = Field(...)
    task_category: str = Field(...)
    project_name: str = Field(...)
    project_type: Optional[str] = None
    contract_type: Optional[str] = None
    budget: Optional[str] = None
    project_description: Optional[str] = None


# ── 상수 ──

CATEGORIES = [
    {"value": "계획", "label": "계획", "color": "#7F77DD"},
    {"value": "계약", "label": "계약", "color": "#3B8BD4"},
    {"value": "시행", "label": "시행", "color": "#1D9E75"},
    {"value": "완료", "label": "완료", "color": "#D85A30"},
]

PROJECT_TYPES = [
    {"value": "construction", "label": "건설/토목 공사", "icon": "🏗️"},
    {"value": "it_system", "label": "정보화/시스템 구축", "icon": "💻"},
    {"value": "facility", "label": "시설 설치/개선", "icon": "🏢"},
    {"value": "service", "label": "용역/연구 사업", "icon": "📋"},
    {"value": "event", "label": "행사/축제 기획", "icon": "🎉"},
    {"value": "policy", "label": "정책/제도 개선", "icon": "📝"},
    {"value": "welfare", "label": "복지/지원 사업", "icon": "🤝"},
    {"value": "education", "label": "교육/홍보 사업", "icon": "📚"},
    {"value": "environment", "label": "환경/녹지 사업", "icon": "🌳"},
    {"value": "other", "label": "기타", "icon": "📌"},
]

CONTRACT_TYPES = [
    {"value": "direct_small", "label": "수의계약 (2천만원 이하)", "icon": "📎"},
    {"value": "direct_medium", "label": "소액수의계약 (5천만원 이하)", "icon": "📎"},
    {"value": "limited_qualify", "label": "제한경쟁입찰 (적격심사)", "icon": "📋"},
    {"value": "limited_negotiation", "label": "제한경쟁입찰 (협상에 의한 계약)", "icon": "📋"},
    {"value": "open_competitive", "label": "일반경쟁입찰", "icon": "📢"},
    {"value": "emergency", "label": "긴급계약", "icon": "⚡"},
]

def _clean_json(text):
    c = text.strip()
    if c.startswith("```"): c = c.split("\n", 1)[1] if "\n" in c else c
    if c.endswith("```"): c = c[:-3]
    return c.strip()

def _tl(v): return next((t["label"] for t in PROJECT_TYPES if t["value"] == v), v) if v else ""
def _cl(v): return next((c["label"] for c in CONTRACT_TYPES if c["value"] == v), v) if v else ""


# ── 일정 추천 ──

SUGGEST_PROMPT = """당신은 한국 지방자치단체의 사업 일정 전문가입니다.

사업 일정을 4단계로 구분하여 추천하세요:
- "계획": 기본계획 수립, 사전 심의/검토, 일상감사, 예산확보 등
- "계약": 설계서/과업지시서 작성, 입찰공고, 제안평가, 계약체결 등
- "시행": 실제 사업 수행 (공사, 개발, 용역수행 등)
- "완료": 준공검사/검수, 대가지급, 정산, 하자보증 등

규칙:
1. category는 반드시 "계획", "계약", "시행", "완료" 중 하나
2. is_milestone은 항상 false
3. 완료 목표 시기 지정 시 반드시 준수. 초과 불가. 부족하면 압축.
4. 사업 설명의 기술/방법론 반영
5. 계약 방식 지정 시 해당 절차 반영
6. 상하반기 인사이동(1,7월) 주요 일정 시작 지양
7. 연말(11~12월) 결산 고려

반드시 아래 JSON만 반환:
{
  "tasks": [{"name": "단계명", "start_month": 3, "end_month": 4, "start_year": 2026, "end_year": 2026, "category": "계획", "is_milestone": false}],
  "summary": "일정 산출 근거 2~3문장"
}"""

@router.post("/suggest")
async def suggest_timeline(request: AutoSuggestRequest):
    try:
        svc = OpenAIService()
        parts = [f"사업명: {request.project_name}"]
        if request.project_description: parts.append(f"사업 설명: {request.project_description}")
        if request.budget: parts.append(f"예산 규모: {request.budget}")
        if request.deadline: parts.append(f"완료 목표: {request.deadline}")
        if request.project_type: parts.append(f"사업 유형: {_tl(request.project_type)}")
        if request.contract_type: parts.append(f"계약 방식: {_cl(request.contract_type)}")
        now = datetime.now()
        parts.append(f"현재 시점: {now.year}년 {now.month}월")
        parts.append("위 사업의 현실적인 추진 일정을 추천해 주세요.")

        rt = await svc.generate_text(prompt=f"{SUGGEST_PROMPT}\n\n" + "\n".join(parts), max_tokens=2000, temperature=0.7)
        result = json.loads(_clean_json(rt))
        valid_cats = {"계획", "계약", "시행", "완료"}
        validated = []
        for t in result.get("tasks", []):
            cat = t.get("category", "시행")
            if cat not in valid_cats: cat = "시행"
            validated.append({"name": t.get("name", "미정"), "start_month": max(1, min(12, t.get("start_month", 1))), "end_month": max(1, min(12, t.get("end_month", 1))), "start_year": t.get("start_year", now.year), "end_year": t.get("end_year", now.year), "category": cat, "is_milestone": False})
        return {"success": True, "tasks": validated, "summary": result.get("summary", ""), "project_name": request.project_name}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI 응답을 파싱할 수 없습니다.")
    except Exception as e:
        logger.error(f"일정 추천 실패: {e}"); raise HTTPException(status_code=500, detail=str(e))


# ── 세부 업무 (duration 포함) ──

DETAIL_WITH_LAW = """당신은 한국 지방자치단체의 사업 관리 전문가입니다.
주어진 단계의 세부 업무 목록을 생성하세요.

규칙:
1. 구체적인 업무 나열 + 각 업무의 예상 소요기간(duration) 산출
2. duration은 "약 3일", "1~2주", "약 1개월" 등 현실적으로 산출
3. 법적 근거가 있으면 반드시 포함
4. 예산 규모에 따른 법정 의무사항 반영
5. 계약 방식에 따른 절차 반영
6. 사업 유형별 특수 절차 반영
7. 아래 법령 검색 결과가 있으면 참고

반드시 아래 JSON만 반환:
{
  "detail_tasks": [
    {"order": 1, "task": "업무명", "description": "설명", "duration": "약 1주", "legal_basis": "근거법령 또는 null", "required": true, "note": "참고 또는 null"}
  ]
}"""

DETAIL_EXECUTE = """당신은 한국 지방자치단체의 사업 관리 전문가입니다.
사업 시행 단계의 세부 작업을 구체적으로 분해하세요.

규칙:
1. 사업 내용 기반으로 실제 작업 공정을 세부 분해
2. 각 작업의 예상 소요기간(duration)을 현실적으로 산출
3. 공사: 공종별 분해 (가설, 토공, 기초, 골조, 포장, 마감 등)
4. 시스템: 분석, 설계, 개발, 테스트, 데이터이관, 시범운영 등
5. 용역: 착수보고, 현황조사, 중간보고, 성과물작성, 최종보고 등
6. 행사: 기획, 섭외, 홍보, 시설설치, 리허설, 본행사, 철거 등
7. legal_basis는 null

반드시 아래 JSON만 반환:
{
  "detail_tasks": [
    {"order": 1, "task": "작업명", "description": "설명", "duration": "약 2주", "legal_basis": null, "required": true, "note": "참고 또는 null"}
  ]
}"""

DETAIL_COMPLETE = """당신은 한국 지방자치단체의 사업 관리 전문가입니다.
사업 완료 단계의 세부 업무를 생성하세요.

규칙:
1. 법정 필수 절차 먼저 (준공검사, 대가지급, 정산, 하자보증 등)
2. 각 업무의 예상 소요기간(duration) 산출
3. 법적 근거 포함
4. 사업 유형별 마무리:
   - 정보화: 데이터이관, 운영인수인계, 교육, 유지보수계약
   - 건설: 준공도서, 시설물등록, 관리이관
   - 용역: 최종보고회, 성과물납품, 성과심의
   - 행사: 정산, 결과보고서, 성과분석
5. 아래 법령 검색 결과가 있으면 참고

반드시 아래 JSON만 반환:
{
  "detail_tasks": [
    {"order": 1, "task": "업무명", "description": "설명", "duration": "약 3일", "legal_basis": "근거 또는 null", "required": true, "note": "참고 또는 null"}
  ]
}"""


async def _ask_law(q):
    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.post(f"{INTERNAL_BASE_URL}/api/law-chatbot/ask", json={"question": q, "search_scope": "all"})
            if r.status_code == 200: return r.json().get("answer", "")
    except Exception as e:
        logger.warning(f"법령 챗봇 연동 실패: {e}")
    return ""


@router.post("/detail-tasks")
async def generate_detail_tasks(request: DetailTasksRequest):
    try:
        svc = OpenAIService()
        tl = _tl(request.project_type); cl = _cl(request.contract_type)
        cat = request.task_category; law_ctx = ""

        if cat == "계획":
            qs = []
            if tl: qs.append(f"{tl} 사업 사전 행정절차 필수사항")
            if request.budget: qs.append(f"{tl} 사업 예산 {request.budget} 규모 법정 필수 절차")
            qs.append("지방자치단체 사업 일상감사 대상 기준")
            for q in qs:
                r = await _ask_law(q)
                if r: law_ctx += f"\n---\n{r}"
            bp = DETAIL_WITH_LAW

        elif cat == "계약":
            qs = []
            if cl: qs.append(f"{cl} 계약 세부 절차와 법적 근거")
            if tl: qs.append(f"{tl} 사업 계약 시 법정 의무사항")
            for q in qs:
                r = await _ask_law(q)
                if r: law_ctx += f"\n---\n{r}"
            bp = DETAIL_WITH_LAW

        elif cat == "시행":
            bp = DETAIL_EXECUTE

        elif cat == "완료":
            qs = []
            if tl: qs.append(f"{tl} 사업 완료 후 필수 절차 (준공검사, 정산, 하자보증)")
            qs.append("지방자치단체 계약 하자보증 기간 기준")
            for q in qs:
                r = await _ask_law(q)
                if r: law_ctx += f"\n---\n{r}"
            bp = DETAIL_COMPLETE
        else:
            bp = DETAIL_WITH_LAW

        up = [f"사업명: {request.project_name}", f"현재 단계: {request.task_name} ({cat})"]
        if tl: up.append(f"사업 유형: {tl}")
        if cl: up.append(f"계약 방식: {cl}")
        if request.budget: up.append(f"예산 규모: {request.budget}")
        if request.project_description: up.append(f"사업 설명: {request.project_description}")
        up.append("\n위 단계의 세부 업무와 각 업무별 예상 소요기간을 생성해 주세요.")

        fp = f"{bp}\n\n[법령 검색 결과 참고]{law_ctx}\n\n" + "\n".join(up) if law_ctx else f"{bp}\n\n" + "\n".join(up)
        rt = await svc.generate_text(prompt=fp, max_tokens=2000, temperature=0.5)
        result = json.loads(_clean_json(rt))

        return {"success": True, "task_name": request.task_name, "task_category": cat, "detail_tasks": result.get("detail_tasks", []), "law_referenced": bool(law_ctx)}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI 응답을 파싱할 수 없습니다.")
    except Exception as e:
        logger.error(f"세부 업무 생성 실패: {e}"); raise HTTPException(status_code=500, detail=str(e))


# ── 목록 ──

@router.get("/project-types")
async def get_project_types(): return {"types": PROJECT_TYPES}

@router.get("/contract-types")
async def get_contract_types(): return {"types": CONTRACT_TYPES}

@router.get("/categories")
async def get_categories(): return {"categories": CATEGORIES}


# ── PNG ──

def _generate_png(timeline):
    from PIL import Image, ImageDraw, ImageFont; import os
    tasks = timeline.tasks; title = timeline.title
    LLW = 280; MCW = 100; RH = 56; HH = 70; TH = 50; LH = 50; PAD = 24

    am = []
    for t in tasks:
        for y in range(t.start_year, t.end_year + 1):
            sm = t.start_month if y == t.start_year else 1; em = t.end_month if y == t.end_year else 12
            for m in range(sm, em + 1): am.append((y, m))
    if not am: am = [(timeline.base_year, m) for m in range(1, 13)]
    am = sorted(set(am)); nm = len(am); mi = {ym: i for i, ym in enumerate(am)}

    CW = nm * MCW; TW = LLW + CW + PAD * 2; TH2 = TH + HH + len(tasks) * RH + LH + PAD * 2
    img = Image.new("RGB", (TW, TH2), (255, 255, 255)); draw = ImageDraw.Draw(img)

    fps = ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    font = fb = fs = None
    for fp in fps:
        if os.path.exists(fp):
            try: font = ImageFont.truetype(fp, 16); fb = ImageFont.truetype(fp, 18); fs = ImageFont.truetype(fp, 13); break
            except: continue
    if font is None: font = ImageFont.load_default(); fb = font; fs = font

    CC = {"계획": {"fill": (238,237,254), "bar": (127,119,221), "text": (60,52,137)}, "계약": {"fill": (230,241,251), "bar": (59,139,212), "text": (12,68,124)}, "시행": {"fill": (225,245,238), "bar": (29,158,117), "text": (8,80,65)}, "완료": {"fill": (250,236,231), "bar": (216,90,48), "text": (113,43,19)}}
    DC = {"fill": (240,240,240), "bar": (150,150,150), "text": (80,80,80)}

    bb = draw.textbbox((0,0), title, font=fb); draw.text(((TW-(bb[2]-bb[0]))/2, 16), title, fill=(44,44,42), font=fb)

    cx = PAD + LLW; hy = TH
    for i, (yr, mo) in enumerate(am):
        x = cx + i * MCW; lb = f"{yr}년 {mo}월" if (mo == 1 or i == 0) else f"{mo}월"
        draw.rectangle([x, hy, x+MCW, hy+30], fill=(241,239,232)); draw.rectangle([x, hy, x+MCW, hy+30], outline=(211,209,199))
        bb = draw.textbbox((0,0), lb, font=fs); draw.text((x+(MCW-(bb[2]-bb[0]))/2, hy+8), lb, fill=(68,68,65), font=fs)

    rt = hy + 30
    for idx, task in enumerate(tasks):
        y = rt + idx * RH; colors = CC.get(task.category, DC)
        if idx % 2 == 0: draw.rectangle([PAD, y, TW-PAD, y+RH], fill=(250,250,248))
        draw.line([PAD, y+RH, TW-PAD, y+RH], fill=(230,228,222), width=1)
        draw.text((PAD+12, y+(RH-18)/2), task.name, fill=(44,44,42), font=font)
        si = mi.get((task.start_year, task.start_month), 0); ei = mi.get((task.end_year, task.end_month), nm-1)
        bx1 = cx+si*MCW+6; bx2 = cx+(ei+1)*MCW-6; by = y+14; bh = RH-28
        draw.rounded_rectangle([bx1, by, bx2, by+bh], radius=5, fill=colors["fill"], outline=colors["bar"], width=2)
        sp = ei-si+1
        if sp > 1 and (bx2-bx1) > 60:
            st = f"{sp}개월"; bb = draw.textbbox((0,0), st, font=fs); draw.text(((bx1+bx2-(bb[2]-bb[0]))/2, by+4), st, fill=colors["text"], font=fs)

    for i in range(nm+1): x = cx+i*MCW; draw.line([x, rt, x, rt+len(tasks)*RH], fill=(238,236,230), width=1)

    ly = rt+len(tasks)*RH+16; lx = PAD+16
    for cat, colors in CC.items():
        draw.rounded_rectangle([lx, ly+2, lx+14, ly+16], radius=3, fill=colors["bar"])
        draw.text((lx+20, ly), cat, fill=(68,68,65), font=fs)
        bb = draw.textbbox((0,0), cat, font=fs); lx += 20+(bb[2]-bb[0])+28

    draw.rectangle([0,0,TW-1,TH2-1], outline=(211,209,199), width=1)
    buf = io.BytesIO(); img.save(buf, format="PNG", dpi=(150,150)); return buf.getvalue()


# ── XLSX (시트2: 세부업무) ──

def _generate_xlsx(timeline, detail_groups=None):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook(); ws = wb.active; ws.title = "사업추진일정"
    am = []
    for t in timeline.tasks:
        for y in range(t.start_year, t.end_year+1):
            sm = t.start_month if y == t.start_year else 1; em = t.end_month if y == t.end_year else 12
            for m in range(sm, em+1): am.append((y, m))
    am = sorted(set(am)); mi = {ym: i for i, ym in enumerate(am)}

    hf = Font(name="맑은 고딕", size=14, bold=True)
    chf = Font(name="맑은 고딕", size=10, bold=True, color="FFFFFF")
    cf = Font(name="맑은 고딕", size=10)
    hfl = PatternFill(start_color="2D3748", end_color="2D3748", fill_type="solid")
    tb = Border(left=Side(style="thin", color="D1D5DB"), right=Side(style="thin", color="D1D5DB"), top=Side(style="thin", color="D1D5DB"), bottom=Side(style="thin", color="D1D5DB"))

    CF = {"계획": PatternFill(start_color="EEEDFE", end_color="EEEDFE", fill_type="solid"), "계약": PatternFill(start_color="E6F1FB", end_color="E6F1FB", fill_type="solid"), "시행": PatternFill(start_color="E1F5EE", end_color="E1F5EE", fill_type="solid"), "완료": PatternFill(start_color="FAECE7", end_color="FAECE7", fill_type="solid")}
    df = PatternFill(start_color="F0F0F0", end_color="F0F0F0", fill_type="solid")

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=3+len(am))
    tc = ws.cell(row=1, column=1, value=timeline.title); tc.font = hf; tc.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    headers = ["단계명", "시작", "종료"] + [f"{y}년 {m}월" if m==1 or i==0 else f"{m}월" for i,(y,m) in enumerate(am)]
    for ci, h in enumerate(headers, 1):
        c = ws.cell(row=3, column=ci, value=h); c.font = chf; c.fill = hfl; c.alignment = Alignment(horizontal="center", vertical="center"); c.border = tb
    ws.column_dimensions["A"].width = 30; ws.column_dimensions["B"].width = 12; ws.column_dimensions["C"].width = 12
    for i in range(len(am)):
        cl = chr(68+i) if i < 22 else None
        if cl: ws.column_dimensions[cl].width = 6

    for ri, task in enumerate(timeline.tasks, 4):
        ws.cell(row=ri, column=1, value=task.name).font = cf; ws.cell(row=ri, column=1).border = tb
        ws.cell(row=ri, column=2, value=f"{task.start_year}.{task.start_month:02d}").font = cf; ws.cell(row=ri, column=2).alignment = Alignment(horizontal="center"); ws.cell(row=ri, column=2).border = tb
        ws.cell(row=ri, column=3, value=f"{task.end_year}.{task.end_month:02d}").font = cf; ws.cell(row=ri, column=3).alignment = Alignment(horizontal="center"); ws.cell(row=ri, column=3).border = tb
        si = mi.get((task.start_year, task.start_month), 0); ei = mi.get((task.end_year, task.end_month), len(am)-1)
        fill = CF.get(task.category, df)
        for i in range(len(am)):
            c = ws.cell(row=ri, column=4+i); c.border = tb
            if si <= i <= ei: c.fill = fill; c.value = "■"; c.alignment = Alignment(horizontal="center"); c.font = Font(size=10, color="666666")

    # 시트2: 세부 업무
    if detail_groups:
        ws2 = wb.create_sheet("세부업무(TODO)")
        ws2.merge_cells(start_row=1, start_column=1, end_row=1, end_column=9)
        tc2 = ws2.cell(row=1, column=1, value=f"{timeline.title} — 세부 업무 목록")
        tc2.font = hf; tc2.alignment = Alignment(horizontal="center", vertical="center")
        ws2.row_dimensions[1].height = 36

        h2 = ["단계", "구분", "순서", "업무명", "소요기간", "설명", "법적 근거", "필수", "참고사항"]
        for ci, h in enumerate(h2, 1):
            c = ws2.cell(row=3, column=ci, value=h); c.font = chf; c.fill = hfl; c.alignment = Alignment(horizontal="center", vertical="center"); c.border = tb

        ws2.column_dimensions["A"].width = 20; ws2.column_dimensions["B"].width = 8; ws2.column_dimensions["C"].width = 6
        ws2.column_dimensions["D"].width = 30; ws2.column_dimensions["E"].width = 12; ws2.column_dimensions["F"].width = 40
        ws2.column_dimensions["G"].width = 30; ws2.column_dimensions["H"].width = 6; ws2.column_dimensions["I"].width = 30

        row = 4
        for grp in detail_groups:
            cat_fill = CF.get(grp.task_category, df)
            for dt in grp.items:
                ws2.cell(row=row, column=1, value=grp.task_name).font = cf; ws2.cell(row=row, column=1).border = tb; ws2.cell(row=row, column=1).fill = cat_fill
                ws2.cell(row=row, column=2, value=grp.task_category).font = cf; ws2.cell(row=row, column=2).border = tb; ws2.cell(row=row, column=2).alignment = Alignment(horizontal="center")
                ws2.cell(row=row, column=3, value=dt.order or 0).font = cf; ws2.cell(row=row, column=3).border = tb; ws2.cell(row=row, column=3).alignment = Alignment(horizontal="center")
                ws2.cell(row=row, column=4, value=dt.task).font = cf; ws2.cell(row=row, column=4).border = tb
                ws2.cell(row=row, column=5, value=dt.duration or "").font = cf; ws2.cell(row=row, column=5).border = tb; ws2.cell(row=row, column=5).alignment = Alignment(horizontal="center")
                ws2.cell(row=row, column=6, value=dt.description or "").font = cf; ws2.cell(row=row, column=6).border = tb
                ws2.cell(row=row, column=7, value=dt.legal_basis or "").font = cf; ws2.cell(row=row, column=7).border = tb
                ws2.cell(row=row, column=8, value="O" if dt.required else "").font = cf; ws2.cell(row=row, column=8).border = tb; ws2.cell(row=row, column=8).alignment = Alignment(horizontal="center")
                ws2.cell(row=row, column=9, value=dt.note or "").font = cf; ws2.cell(row=row, column=9).border = tb
                row += 1

    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()


# ── PPTX ──

def _generate_pptx(timeline):
    from pptx import Presentation; from pptx.util import Inches, Pt; from pptx.dml.color import RGBColor; from pptx.enum.text import PP_ALIGN
    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12), Inches(0.7))
    p = tb.text_frame.paragraphs[0]; p.text = timeline.title; p.font.size = Pt(28); p.font.bold = True; p.font.color.rgb = RGBColor(0x2D,0x37,0x48); p.alignment = PP_ALIGN.LEFT
    tb2 = slide.shapes.add_textbox(Inches(0.5), Inches(0.9), Inches(12), Inches(0.4))
    p2 = tb2.text_frame.paragraphs[0]; p2.text = "사업 추진 일정표"; p2.font.size = Pt(14); p2.font.color.rgb = RGBColor(0x71,0x71,0x71)

    am = []
    for t in timeline.tasks:
        for y in range(t.start_year, t.end_year+1):
            sm = t.start_month if y == t.start_year else 1; em = t.end_month if y == t.end_year else 12
            for m in range(sm, em+1): am.append((y, m))
    am = sorted(set(am)); mi2 = {ym: i for i, ym in enumerate(am)}; nm = len(am)
    LEFT = Inches(0.5); TOP = Inches(1.6); LW = Inches(2.8); CW2 = Inches(9.5); RH = Inches(0.45); MW = CW2/nm if nm > 0 else Inches(1)
    CC2 = {"계획": RGBColor(0x7F,0x77,0xDD), "계약": RGBColor(0x3B,0x8B,0xD4), "시행": RGBColor(0x1D,0x9E,0x75), "완료": RGBColor(0xD8,0x5A,0x30)}

    for i, (yr, mo) in enumerate(am):
        x = LEFT+LW+int(MW*i); lb = f"'{str(yr)[2:]}.{mo}월" if (mo==1 or i==0) else f"{mo}월"
        hb = slide.shapes.add_textbox(x, TOP-Inches(0.35), int(MW), Inches(0.3))
        hp = hb.text_frame.paragraphs[0]; hp.text = lb; hp.font.size = Pt(9); hp.font.color.rgb = RGBColor(0x55,0x55,0x55); hp.alignment = PP_ALIGN.CENTER

    for idx, task in enumerate(timeline.tasks):
        y = TOP+int(RH*idx)
        lb = slide.shapes.add_textbox(LEFT, y, LW, RH); lb.text_frame.word_wrap = True
        lp = lb.text_frame.paragraphs[0]; lp.text = task.name; lp.font.size = Pt(11); lp.font.color.rgb = RGBColor(0x2D,0x37,0x48)
        si = mi2.get((task.start_year, task.start_month), 0); ei = mi2.get((task.end_year, task.end_month), nm-1)
        bx = LEFT+LW+int(MW*si)+Inches(0.05); bw = int(MW*(ei-si+1))-Inches(0.1); by = y+Inches(0.08); bh = RH-Inches(0.16)
        shape = slide.shapes.add_shape(1, int(bx), int(by), int(bw), int(bh))
        shape.fill.solid(); shape.fill.fore_color.rgb = CC2.get(task.category, RGBColor(0x99,0x99,0x99)); shape.line.fill.background()
        shape.text_frame.paragraphs[0].text = f"{ei-si+1}개월"; shape.text_frame.paragraphs[0].font.size = Pt(8)
        shape.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xFF,0xFF,0xFF); shape.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    buf = io.BytesIO(); prs.save(buf); return buf.getvalue()


# ── Export ──

@router.post("/export")
async def export_timeline(request: ExportRequest):
    try:
        dg = request.detail_tasks or []
        fmt = request.format
        if fmt == "png":
            data = _generate_png(request.timeline); fn = f"{request.timeline.title}_일정표.png"; mime = "image/png"
        elif fmt == "xlsx":
            data = _generate_xlsx(request.timeline, dg); fn = f"{request.timeline.title}_일정표.xlsx"; mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif fmt == "pptx":
            data = _generate_pptx(request.timeline); fn = f"{request.timeline.title}_일정표.pptx"; mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 형식")
        return {"success": True, "data": base64.b64encode(data).decode("utf-8"), "filename": fn, "mime_type": mime, "format": fmt}
    except Exception as e:
        logger.error(f"내보내기 실패: {e}"); raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def timeline_status():
    return {"status": "ok", "features": {"auto_suggest": True, "detail_tasks_with_duration": True, "law_chatbot_integration": True, "export_png": True, "export_xlsx_with_todo": True, "export_pptx": True}}