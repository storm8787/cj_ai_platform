"""
사업 타임라인 생성기 (Project Timeline Planner)
- 4단계 구조: 계획 → 계약 → 시행 → 완료
- 단계별 세부 업무 자동 생성 (법령 챗봇 선택적 연동)
- 다중 포맷 내보내기 (PNG, XLSX, PPTX)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import json
import io
import base64
import logging
import httpx

from services.openai_service import OpenAIService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/timeline", tags=["timeline"])

INTERNAL_BASE_URL = "http://localhost:8000"


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────

class TimelineTask(BaseModel):
    name: str = Field(..., description="단계명")
    start_month: int = Field(..., ge=1, le=12)
    end_month: int = Field(..., ge=1, le=12)
    start_year: int = Field(...)
    end_year: int = Field(...)
    category: Optional[str] = Field(None, description="계획/계약/시행/완료")
    is_milestone: bool = Field(False)


class TimelineData(BaseModel):
    title: str = Field(...)
    tasks: list[TimelineTask] = Field(...)
    base_year: int = Field(...)


class AutoSuggestRequest(BaseModel):
    project_name: str = Field(...)
    project_description: Optional[str] = Field(None)
    budget: Optional[str] = Field(None)
    deadline: Optional[str] = Field(None)
    project_type: Optional[str] = Field(None)
    contract_type: Optional[str] = Field(None)


class ExportRequest(BaseModel):
    timeline: TimelineData
    format: str = Field(..., pattern="^(png|xlsx|pptx)$")


class DetailTasksRequest(BaseModel):
    task_name: str = Field(...)
    task_category: str = Field(..., description="계획/계약/시행/완료")
    project_name: str = Field(...)
    project_type: Optional[str] = Field(None)
    contract_type: Optional[str] = Field(None)
    budget: Optional[str] = Field(None)
    project_description: Optional[str] = Field(None)


# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────

CATEGORIES = [
    {"value": "계획", "label": "계획", "color": "#7F77DD", "description": "기본계획 수립, 사전 심의/검토"},
    {"value": "계약", "label": "계약", "color": "#3B8BD4", "description": "입찰, 평가, 계약체결"},
    {"value": "시행", "label": "시행", "color": "#1D9E75", "description": "실제 사업 수행"},
    {"value": "완료", "label": "완료", "color": "#D85A30", "description": "준공검사, 정산, 하자보증"},
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


def _clean_json(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1] if "\n" in clean else clean
    if clean.endswith("```"):
        clean = clean[:-3]
    return clean.strip()


def _type_label(v):
    return next((t["label"] for t in PROJECT_TYPES if t["value"] == v), v) if v else ""


def _contract_label(v):
    return next((c["label"] for c in CONTRACT_TYPES if c["value"] == v), v) if v else ""


# ──────────────────────────────────────────────
# GPT 자동 일정 추천
# ──────────────────────────────────────────────

SUGGEST_PROMPT = """당신은 한국 지방자치단체의 사업 일정 전문가입니다.

사업 일정을 4단계로 구분하여 추천하세요:
- "계획": 기본계획 수립, 사전 심의/검토, 일상감사, 예산확보 등
- "계약": 설계서/과업지시서 작성, 입찰공고, 제안평가, 계약체결 등
- "시행": 실제 사업 수행 (공사, 개발, 용역수행 등)
- "완료": 준공검사/검수, 대가지급, 정산, 하자보증 등

규칙:
1. category는 반드시 "계획", "계약", "시행", "완료" 중 하나
2. is_milestone은 항상 false
3. 사용자가 완료 목표 시기를 지정한 경우, 반드시 해당 시기 이내에 모든 일정 완료. 초과 불가. 부족하면 압축.
4. 사업 설명의 기술/방법론을 단계명과 summary에 반영
5. 계약 방식이 지정된 경우 해당 절차 반영:
   - 수의계약: 견적 징구 → 계약체결 (간소)
   - 소액수의계약: 견적비교 → 계약체결
   - 제한경쟁(적격심사): 설계서 → 입찰공고 → 적격심사 → 낙찰 → 계약
   - 제한경쟁(협상): 제안요청서 → 제안서접수 → 기술평가 → 협상 → 계약
   - 일반경쟁입찰: 설계서 → 입찰공고 → 개찰 → 낙찰 → 계약
   - 긴급계약: 긴급사유서 → 수의계약
6. 상하반기 인사이동(1월, 7월) 주요 일정 시작 지양
7. 연말(11~12월) 결산/정산 기간 고려
8. 현실적이고 보수적인 일정 산출

반드시 아래 JSON만 반환 (다른 텍스트 없이):
{
  "tasks": [
    {"name": "단계명", "start_month": 3, "end_month": 4, "start_year": 2026, "end_year": 2026, "category": "계획", "is_milestone": false}
  ],
  "summary": "일정 산출 근거 요약 (2~3문장)"
}"""


@router.post("/suggest")
async def suggest_timeline(request: AutoSuggestRequest):
    try:
        svc = OpenAIService()
        parts = [f"사업명: {request.project_name}"]
        if request.project_description:
            parts.append(f"사업 설명: {request.project_description}")
        if request.budget:
            parts.append(f"예산 규모: {request.budget}")
        if request.deadline:
            parts.append(f"완료 목표: {request.deadline}")
        if request.project_type:
            parts.append(f"사업 유형: {_type_label(request.project_type)}")
        if request.contract_type:
            parts.append(f"계약 방식: {_contract_label(request.contract_type)}")

        now = datetime.now()
        parts.append(f"현재 시점: {now.year}년 {now.month}월")
        parts.append("위 사업의 현실적인 추진 일정을 추천해 주세요.")

        result_text = await svc.generate_text(
            prompt=f"{SUGGEST_PROMPT}\n\n" + "\n".join(parts),
            max_tokens=2000, temperature=0.7
        )
        result = json.loads(_clean_json(result_text))

        valid_categories = {"계획", "계약", "시행", "완료"}
        validated = []
        for t in result.get("tasks", []):
            cat = t.get("category", "시행")
            if cat not in valid_categories:
                cat = "시행"
            validated.append({
                "name": t.get("name", "미정"),
                "start_month": max(1, min(12, t.get("start_month", 1))),
                "end_month": max(1, min(12, t.get("end_month", 1))),
                "start_year": t.get("start_year", now.year),
                "end_year": t.get("end_year", now.year),
                "category": cat,
                "is_milestone": False,
            })

        return {
            "success": True,
            "tasks": validated,
            "summary": result.get("summary", ""),
            "project_name": request.project_name,
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI 응답을 파싱할 수 없습니다.")
    except Exception as e:
        logger.error(f"일정 추천 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
# 단계별 세부 업무 생성
# ──────────────────────────────────────────────

# 계획/계약 단계: 법령 챗봇 + GPT
DETAIL_PROMPT_WITH_LAW = """당신은 한국 지방자치단체의 사업 관리 전문가입니다.
주어진 단계의 세부 업무(TODO) 목록을 생성하세요.

규칙:
1. 해당 단계에서 실제 수행할 구체적 업무 나열
2. 법적 근거가 있으면 반드시 포함
3. 예산 규모에 따른 법정 의무사항 반영 (감리, 심의 기준금액 등)
4. 계약 방식에 따른 절차 반영
5. 사업 유형별 특수 절차:
   - 정보화: 보안성검토, SW과업심의, 정보화사전협의, SW감리 등
   - 건설: 설계심의, 안전관리계획, 환경영향평가, 건설사업관리 등
   - 용역: 과업지시서, 중간보고, 성과심의 등
   - 행사: 안전관리계획, 도로점용허가 등
6. 아래 법령 검색 결과가 있으면 참고하여 정확한 근거 포함

반드시 아래 JSON만 반환:
{
  "detail_tasks": [
    {"order": 1, "task": "업무명", "description": "설명", "legal_basis": "근거법령 또는 null", "required": true, "note": "참고사항 또는 null"}
  ]
}"""

# 시행 단계: GPT만 (법령 불필요)
DETAIL_PROMPT_EXECUTE = """당신은 한국 지방자치단체의 사업 관리 전문가입니다.
사업의 시행 단계에서 실제 수행할 세부 작업을 구체적으로 분해하세요.

규칙:
1. 사업 내용을 바탕으로 실제 작업 공정을 세부적으로 나눠주세요
2. 공사: 가설공사, 토공, 기초, 골조, 포장, 마감 등 공종별 분해
3. 시스템구축: 요구분석, 설계, 개발, 단위테스트, 통합테스트, 데이터이관, 시범운영 등
4. 용역: 착수보고, 현황조사, 분석, 중간보고, 성과물작성, 최종보고 등
5. 행사/축제: 기획, 섭외, 홍보, 시설설치, 리허설, 본행사, 철거 등
6. 각 작업에 대한 구체적 설명 포함
7. 법적 근거는 불필요 (legal_basis는 null)

반드시 아래 JSON만 반환:
{
  "detail_tasks": [
    {"order": 1, "task": "작업명", "description": "구체적 설명", "legal_basis": null, "required": true, "note": "참고사항 또는 null"}
  ]
}"""

# 완료 단계: 법령 + GPT 혼합
DETAIL_PROMPT_COMPLETE = """당신은 한국 지방자치단체의 사업 관리 전문가입니다.
사업 완료 단계의 세부 업무를 생성하세요.

규칙:
1. 법정 필수 절차를 먼저 나열 (준공검사, 대가지급, 정산, 하자보증 등)
2. 법적 근거가 있는 항목은 반드시 근거 포함
3. 사업 유형별 마무리 업무도 포함:
   - 정보화: 데이터 이관, 운영 인수인계, 교육, 유지보수 계약
   - 건설: 준공도서 작성, 시설물 등록, 관리 이관
   - 용역: 최종보고회, 성과물 납품, 성과심의
   - 행사: 정산, 결과보고서, 성과분석
4. 아래 법령 검색 결과가 있으면 참고

반드시 아래 JSON만 반환:
{
  "detail_tasks": [
    {"order": 1, "task": "업무명", "description": "설명", "legal_basis": "근거법령 또는 null", "required": true, "note": "참고사항 또는 null"}
  ]
}"""


async def _query_law_chatbot(question: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{INTERNAL_BASE_URL}/api/law-chatbot/ask",
                json={"question": question, "search_scope": "all"}
            )
            if resp.status_code == 200:
                return resp.json().get("answer", "")
    except Exception as e:
        logger.warning(f"법령 챗봇 연동 실패: {e}")
    return ""


@router.post("/detail-tasks")
async def generate_detail_tasks(request: DetailTasksRequest):
    try:
        svc = OpenAIService()
        tl = _type_label(request.project_type)
        cl = _contract_label(request.contract_type)
        cat = request.task_category

        # ── 단계별 프롬프트 & 법령 연동 분기 ──
        law_context = ""

        if cat == "계획":
            # 법령 챗봇 연동
            queries = []
            if tl:
                queries.append(f"{tl} 사업 사전 행정절차 필수사항 (심의, 검토, 협의)")
            if request.budget:
                queries.append(f"{tl} 사업 예산 {request.budget} 규모 법정 필수 절차 (감리, 심의 기준금액)")
            queries.append("지방자치단체 사업 일상감사 대상 기준")

            for q in queries:
                r = await _query_law_chatbot(q)
                if r:
                    law_context += f"\n---\n{r}"

            base_prompt = DETAIL_PROMPT_WITH_LAW

        elif cat == "계약":
            # 법령 챗봇 연동
            queries = []
            if cl:
                queries.append(f"{cl} 계약 세부 절차와 법적 근거")
            if tl:
                queries.append(f"{tl} 사업 계약 시 법정 의무사항")

            for q in queries:
                r = await _query_law_chatbot(q)
                if r:
                    law_context += f"\n---\n{r}"

            base_prompt = DETAIL_PROMPT_WITH_LAW

        elif cat == "시행":
            # GPT만 (법령 불필요)
            base_prompt = DETAIL_PROMPT_EXECUTE

        elif cat == "완료":
            # 법령 + GPT 혼합
            queries = []
            if tl:
                queries.append(f"{tl} 사업 완료 후 필수 절차 (준공검사, 정산, 하자보증)")
            queries.append("지방자치단체 계약 하자보증 기간 기준")

            for q in queries:
                r = await _query_law_chatbot(q)
                if r:
                    law_context += f"\n---\n{r}"

            base_prompt = DETAIL_PROMPT_COMPLETE

        else:
            base_prompt = DETAIL_PROMPT_WITH_LAW

        # 사용자 프롬프트 구성
        user_parts = [
            f"사업명: {request.project_name}",
            f"현재 단계: {request.task_name} ({cat})",
        ]
        if tl:
            user_parts.append(f"사업 유형: {tl}")
        if cl:
            user_parts.append(f"계약 방식: {cl}")
        if request.budget:
            user_parts.append(f"예산 규모: {request.budget}")
        if request.project_description:
            user_parts.append(f"사업 설명: {request.project_description}")
        user_parts.append("\n위 단계의 세부 업무 목록을 생성해 주세요.")

        if law_context:
            full_prompt = f"{base_prompt}\n\n[법령 검색 결과 참고]{law_context}\n\n" + "\n".join(user_parts)
        else:
            full_prompt = f"{base_prompt}\n\n" + "\n".join(user_parts)

        result_text = await svc.generate_text(
            prompt=full_prompt, max_tokens=2000, temperature=0.5
        )
        result = json.loads(_clean_json(result_text))

        return {
            "success": True,
            "task_name": request.task_name,
            "task_category": cat,
            "detail_tasks": result.get("detail_tasks", []),
            "law_referenced": bool(law_context),
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI 응답을 파싱할 수 없습니다.")
    except Exception as e:
        logger.error(f"세부 업무 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
# 목록 조회
# ──────────────────────────────────────────────

@router.get("/project-types")
async def get_project_types():
    return {"types": PROJECT_TYPES}

@router.get("/contract-types")
async def get_contract_types():
    return {"types": CONTRACT_TYPES}

@router.get("/categories")
async def get_categories():
    return {"categories": CATEGORIES}


# ──────────────────────────────────────────────
# PNG
# ──────────────────────────────────────────────

def _generate_png(timeline: TimelineData) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    import os

    tasks = timeline.tasks
    title = timeline.title

    LEFT_LABEL_W = 280; MONTH_COL_W = 100; ROW_H = 56
    HEADER_H = 70; TITLE_H = 50; LEGEND_H = 50; PADDING = 24

    all_months = []
    for t in tasks:
        for y in range(t.start_year, t.end_year + 1):
            sm = t.start_month if y == t.start_year else 1
            em = t.end_month if y == t.end_year else 12
            for m in range(sm, em + 1):
                all_months.append((y, m))
    if not all_months:
        all_months = [(timeline.base_year, m) for m in range(1, 13)]
    all_months = sorted(set(all_months))
    num_months = len(all_months)
    month_index = {ym: i for i, ym in enumerate(all_months)}

    CHART_W = num_months * MONTH_COL_W
    TOTAL_W = LEFT_LABEL_W + CHART_W + PADDING * 2
    TOTAL_H = TITLE_H + HEADER_H + len(tasks) * ROW_H + LEGEND_H + PADDING * 2

    img = Image.new("RGB", (TOTAL_W, TOTAL_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    font = font_bold = font_small = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, 16)
                font_bold = ImageFont.truetype(fp, 18)
                font_small = ImageFont.truetype(fp, 13)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default(); font_bold = font; font_small = font

    CAT_COLORS = {
        "계획": {"fill": (238, 237, 254), "bar": (127, 119, 221), "text": (60, 52, 137)},
        "계약": {"fill": (230, 241, 251), "bar": (59, 139, 212), "text": (12, 68, 124)},
        "시행": {"fill": (225, 245, 238), "bar": (29, 158, 117), "text": (8, 80, 65)},
        "완료": {"fill": (250, 236, 231), "bar": (216, 90, 48), "text": (113, 43, 19)},
    }
    DEF_COLOR = {"fill": (240, 240, 240), "bar": (150, 150, 150), "text": (80, 80, 80)}

    bbox = draw.textbbox((0, 0), title, font=font_bold)
    draw.text(((TOTAL_W - (bbox[2] - bbox[0])) / 2, 16), title, fill=(44, 44, 42), font=font_bold)

    chart_x = PADDING + LEFT_LABEL_W
    header_y = TITLE_H
    for i, (year, month) in enumerate(all_months):
        x = chart_x + i * MONTH_COL_W
        label = f"{year}년 {month}월" if (month == 1 or i == 0) else f"{month}월"
        draw.rectangle([x, header_y, x + MONTH_COL_W, header_y + 30], fill=(241, 239, 232))
        draw.rectangle([x, header_y, x + MONTH_COL_W, header_y + 30], outline=(211, 209, 199))
        bbox = draw.textbbox((0, 0), label, font=font_small)
        draw.text((x + (MONTH_COL_W - (bbox[2] - bbox[0])) / 2, header_y + 8), label, fill=(68, 68, 65), font=font_small)

    row_top = header_y + 30
    for idx, task in enumerate(tasks):
        y = row_top + idx * ROW_H
        colors = CAT_COLORS.get(task.category, DEF_COLOR)
        if idx % 2 == 0:
            draw.rectangle([PADDING, y, TOTAL_W - PADDING, y + ROW_H], fill=(250, 250, 248))
        draw.line([PADDING, y + ROW_H, TOTAL_W - PADDING, y + ROW_H], fill=(230, 228, 222), width=1)
        draw.text((PADDING + 12, y + (ROW_H - 18) / 2), task.name, fill=(44, 44, 42), font=font)

        si = month_index.get((task.start_year, task.start_month), 0)
        ei = month_index.get((task.end_year, task.end_month), num_months - 1)
        bx1 = chart_x + si * MONTH_COL_W + 6
        bx2 = chart_x + (ei + 1) * MONTH_COL_W - 6
        by = y + 14; bh = ROW_H - 28
        draw.rounded_rectangle([bx1, by, bx2, by + bh], radius=5, fill=colors["fill"], outline=colors["bar"], width=2)
        span = ei - si + 1
        if span > 1 and (bx2 - bx1) > 60:
            st = f"{span}개월"
            bbox = draw.textbbox((0, 0), st, font=font_small)
            draw.text(((bx1 + bx2 - (bbox[2] - bbox[0])) / 2, by + 4), st, fill=colors["text"], font=font_small)

    for i in range(num_months + 1):
        x = chart_x + i * MONTH_COL_W
        draw.line([x, row_top, x, row_top + len(tasks) * ROW_H], fill=(238, 236, 230), width=1)

    ly = row_top + len(tasks) * ROW_H + 16; lx = PADDING + 16
    for cat, colors in CAT_COLORS.items():
        draw.rounded_rectangle([lx, ly + 2, lx + 14, ly + 16], radius=3, fill=colors["bar"])
        draw.text((lx + 20, ly), cat, fill=(68, 68, 65), font=font_small)
        bbox = draw.textbbox((0, 0), cat, font=font_small)
        lx += 20 + (bbox[2] - bbox[0]) + 28

    draw.rectangle([0, 0, TOTAL_W - 1, TOTAL_H - 1], outline=(211, 209, 199), width=1)
    buf = io.BytesIO(); img.save(buf, format="PNG", dpi=(150, 150)); return buf.getvalue()


# ──────────────────────────────────────────────
# XLSX
# ──────────────────────────────────────────────

def _generate_xlsx(timeline: TimelineData) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook(); ws = wb.active; ws.title = "사업추진일정"
    all_months = []
    for t in timeline.tasks:
        for y in range(t.start_year, t.end_year + 1):
            sm = t.start_month if y == t.start_year else 1
            em = t.end_month if y == t.end_year else 12
            for m in range(sm, em + 1): all_months.append((y, m))
    all_months = sorted(set(all_months))
    mi = {ym: i for i, ym in enumerate(all_months)}

    hf = Font(name="맑은 고딕", size=14, bold=True)
    chf = Font(name="맑은 고딕", size=10, bold=True, color="FFFFFF")
    cf = Font(name="맑은 고딕", size=10)
    hfill = PatternFill(start_color="2D3748", end_color="2D3748", fill_type="solid")
    tb = Border(left=Side(style="thin", color="D1D5DB"), right=Side(style="thin", color="D1D5DB"),
                top=Side(style="thin", color="D1D5DB"), bottom=Side(style="thin", color="D1D5DB"))

    CF = {
        "계획": PatternFill(start_color="EEEDFE", end_color="EEEDFE", fill_type="solid"),
        "계약": PatternFill(start_color="E6F1FB", end_color="E6F1FB", fill_type="solid"),
        "시행": PatternFill(start_color="E1F5EE", end_color="E1F5EE", fill_type="solid"),
        "완료": PatternFill(start_color="FAECE7", end_color="FAECE7", fill_type="solid"),
    }
    df = PatternFill(start_color="F0F0F0", end_color="F0F0F0", fill_type="solid")

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=3 + len(all_months))
    tc = ws.cell(row=1, column=1, value=timeline.title); tc.font = hf; tc.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    headers = ["단계명", "시작", "종료"] + [f"{y}년 {m}월" if m == 1 or i == 0 else f"{m}월" for i, (y, m) in enumerate(all_months)]
    for ci, h in enumerate(headers, 1):
        c = ws.cell(row=3, column=ci, value=h); c.font = chf; c.fill = hfill; c.alignment = Alignment(horizontal="center", vertical="center"); c.border = tb
    ws.column_dimensions["A"].width = 30; ws.column_dimensions["B"].width = 12; ws.column_dimensions["C"].width = 12
    for i in range(len(all_months)):
        cl = chr(68 + i) if i < 22 else None
        if cl: ws.column_dimensions[cl].width = 6

    for ri, task in enumerate(timeline.tasks, 4):
        ws.cell(row=ri, column=1, value=task.name).font = cf; ws.cell(row=ri, column=1).border = tb
        ws.cell(row=ri, column=2, value=f"{task.start_year}.{task.start_month:02d}").font = cf
        ws.cell(row=ri, column=2).alignment = Alignment(horizontal="center"); ws.cell(row=ri, column=2).border = tb
        ws.cell(row=ri, column=3, value=f"{task.end_year}.{task.end_month:02d}").font = cf
        ws.cell(row=ri, column=3).alignment = Alignment(horizontal="center"); ws.cell(row=ri, column=3).border = tb
        si = mi.get((task.start_year, task.start_month), 0)
        ei = mi.get((task.end_year, task.end_month), len(all_months) - 1)
        fill = CF.get(task.category, df)
        for i in range(len(all_months)):
            c = ws.cell(row=ri, column=4 + i); c.border = tb
            if si <= i <= ei:
                c.fill = fill; c.value = "■"; c.alignment = Alignment(horizontal="center"); c.font = Font(size=10, color="666666")

    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()


# ──────────────────────────────────────────────
# PPTX
# ──────────────────────────────────────────────

def _generate_pptx(timeline: TimelineData) -> bytes:
    from pptx import Presentation; from pptx.util import Inches, Pt; from pptx.dml.color import RGBColor; from pptx.enum.text import PP_ALIGN

    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12), Inches(0.7))
    p = tb.text_frame.paragraphs[0]; p.text = timeline.title; p.font.size = Pt(28); p.font.bold = True; p.font.color.rgb = RGBColor(0x2D, 0x37, 0x48); p.alignment = PP_ALIGN.LEFT
    tb2 = slide.shapes.add_textbox(Inches(0.5), Inches(0.9), Inches(12), Inches(0.4))
    p2 = tb2.text_frame.paragraphs[0]; p2.text = "사업 추진 일정표"; p2.font.size = Pt(14); p2.font.color.rgb = RGBColor(0x71, 0x71, 0x71)

    all_months = []
    for t in timeline.tasks:
        for y in range(t.start_year, t.end_year + 1):
            sm = t.start_month if y == t.start_year else 1; em = t.end_month if y == t.end_year else 12
            for m in range(sm, em + 1): all_months.append((y, m))
    all_months = sorted(set(all_months)); mi = {ym: i for i, ym in enumerate(all_months)}; nm = len(all_months)

    LEFT = Inches(0.5); TOP = Inches(1.6); LW = Inches(2.8); CW = Inches(9.5); RH = Inches(0.45)
    MW = CW / nm if nm > 0 else Inches(1)

    CC = {"계획": RGBColor(0x7F, 0x77, 0xDD), "계약": RGBColor(0x3B, 0x8B, 0xD4), "시행": RGBColor(0x1D, 0x9E, 0x75), "완료": RGBColor(0xD8, 0x5A, 0x30)}

    for i, (yr, mo) in enumerate(all_months):
        x = LEFT + LW + int(MW * i)
        lb = f"'{str(yr)[2:]}.{mo}월" if (mo == 1 or i == 0) else f"{mo}월"
        hb = slide.shapes.add_textbox(x, TOP - Inches(0.35), int(MW), Inches(0.3))
        hp = hb.text_frame.paragraphs[0]; hp.text = lb; hp.font.size = Pt(9); hp.font.color.rgb = RGBColor(0x55, 0x55, 0x55); hp.alignment = PP_ALIGN.CENTER

    for idx, task in enumerate(timeline.tasks):
        y = TOP + int(RH * idx)
        lb = slide.shapes.add_textbox(LEFT, y, LW, RH); lb.text_frame.word_wrap = True
        lp = lb.text_frame.paragraphs[0]; lp.text = task.name; lp.font.size = Pt(11); lp.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
        si = mi.get((task.start_year, task.start_month), 0); ei = mi.get((task.end_year, task.end_month), nm - 1)
        bx = LEFT + LW + int(MW * si) + Inches(0.05); bw = int(MW * (ei - si + 1)) - Inches(0.1)
        by = y + Inches(0.08); bh = RH - Inches(0.16)
        shape = slide.shapes.add_shape(1, int(bx), int(by), int(bw), int(bh))
        shape.fill.solid(); shape.fill.fore_color.rgb = CC.get(task.category, RGBColor(0x99, 0x99, 0x99)); shape.line.fill.background()
        shape.text_frame.paragraphs[0].text = f"{ei - si + 1}개월"; shape.text_frame.paragraphs[0].font.size = Pt(8)
        shape.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF); shape.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    buf = io.BytesIO(); prs.save(buf); return buf.getvalue()


# ──────────────────────────────────────────────
# 내보내기
# ──────────────────────────────────────────────

@router.post("/export")
async def export_timeline(request: ExportRequest):
    try:
        fmt = request.format
        if fmt == "png":
            data = _generate_png(request.timeline); fn = f"{request.timeline.title}_일정표.png"; mime = "image/png"
        elif fmt == "xlsx":
            data = _generate_xlsx(request.timeline); fn = f"{request.timeline.title}_일정표.xlsx"; mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif fmt == "pptx":
            data = _generate_pptx(request.timeline); fn = f"{request.timeline.title}_일정표.pptx"; mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 형식")
        return {"success": True, "data": base64.b64encode(data).decode("utf-8"), "filename": fn, "mime_type": mime, "format": fmt}
    except Exception as e:
        logger.error(f"내보내기 실패: {e}"); raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def timeline_status():
    return {"status": "ok", "features": {"auto_suggest": True, "detail_tasks": True, "law_chatbot_integration": True, "export_png": True, "export_xlsx": True, "export_pptx": True}, "project_types": len(PROJECT_TYPES), "contract_types": len(CONTRACT_TYPES), "categories": len(CATEGORIES)}