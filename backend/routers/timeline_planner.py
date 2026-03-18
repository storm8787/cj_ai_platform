"""
사업 타임라인 생성기 (Project Timeline Planner)
- GPT 자동 일정 추천
- 단계별 세부 업무 자동 생성 (법령 챗봇 연동)
- 수동 일정 입력
- 다중 포맷 내보내기 (PNG, XLSX, PPTX)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
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
    category: Optional[str] = Field(None, description="준비/시행/마무리")
    is_milestone: bool = Field(False)


class TimelineData(BaseModel):
    title: str = Field(..., description="사업명")
    tasks: list[TimelineTask] = Field(..., description="일정 목록")
    base_year: int = Field(..., description="기준 연도")


class AutoSuggestRequest(BaseModel):
    project_name: str = Field(..., description="사업명")
    project_description: Optional[str] = Field(None, description="사업 설명")
    budget: Optional[str] = Field(None, description="예산 규모")
    deadline: Optional[str] = Field(None, description="완료 목표 시기")
    project_type: Optional[str] = Field(None, description="사업 유형")
    contract_type: Optional[str] = Field(None, description="계약 방식")


class ExportRequest(BaseModel):
    timeline: TimelineData
    format: str = Field(..., pattern="^(png|xlsx|pptx)$")


class DetailTasksRequest(BaseModel):
    task_name: str = Field(..., description="단계명")
    task_category: str = Field(..., description="카테고리 (준비/시행/마무리)")
    project_name: str = Field(..., description="사업명")
    project_type: Optional[str] = Field(None)
    contract_type: Optional[str] = Field(None)
    budget: Optional[str] = Field(None)
    project_description: Optional[str] = Field(None)


# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────

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


# ──────────────────────────────────────────────
# GPT 자동 일정 추천
# ──────────────────────────────────────────────

SUGGEST_SYSTEM_PROMPT = """당신은 한국 지방자치단체의 사업 일정 전문가입니다.
사용자가 입력한 사업 정보를 바탕으로 현실적인 추진 일정을 추천해야 합니다.

규칙:
1. 일정은 반드시 JSON 배열로 반환
2. 각 단계에는 name, start_month, end_month, start_year, end_year, category 포함
3. category는 "준비", "시행", "마무리" 중 하나
4. 실제 지자체 행정 절차를 반영 (예산편성, 입찰, 계약 등)
5. 상하반기 인사이동(1월, 7월)에 주요 일정 시작 배치 지양
6. 연말(11~12월) 결산/정산 기간 고려
7. 단계별 최소 소요기간 준수:
   - 기본계획 수립: 1~2개월
   - 설계/용역: 2~4개월
   - 입찰/계약: 1~2개월
   - 시공/집행: 사업 규모에 따라 3~12개월
   - 준공/완료/정산: 1~2개월
8. is_milestone은 항상 false로 설정하세요. 모든 단계는 기간이 있는 바(bar) 형태로 표시됩니다.
9. 현실적이고 보수적인 일정 산출 (여유 기간 포함)
10. 사용자가 완료 목표 시기를 지정한 경우, 반드시 해당 시기 이내에 모든 일정을 완료해야 합니다. 목표 시기를 초과하는 일정은 절대 불가합니다. 기간이 부족하면 각 단계를 압축하세요.
11. 사업 설명에 포함된 기술, 장비, 방법론 등을 일정 단계명과 summary에 반영하세요.
12. 계약 방식이 지정된 경우, 해당 계약 절차에 맞는 단계를 반영하세요:
    - 수의계약: 견적 징구 → 계약체결 (간소화)
    - 소액수의계약: 견적비교 → 계약체결
    - 제한경쟁(적격심사): 설계서 작성 → 입찰공고 → 적격심사 → 낙찰자결정 → 계약
    - 제한경쟁(협상): 제안요청서 → 제안서접수 → 기술평가 → 가격협상 → 계약
    - 일반경쟁입찰: 설계서 작성 → 입찰공고 → 개찰 → 낙찰자결정 → 계약
    - 긴급계약: 긴급사유서 → 수의계약 체결

반드시 아래 JSON 형식만 반환하세요 (다른 텍스트 없이):
{
  "tasks": [
    {
      "name": "단계명",
      "start_month": 3,
      "end_month": 4,
      "start_year": 2026,
      "end_year": 2026,
      "category": "준비",
      "is_milestone": false
    }
  ],
  "summary": "일정 산출 근거 요약 (2~3문장, 사업 설명 및 계약 방식 반영)"
}"""


def _clean_json_response(text: str) -> str:
    """GPT 응답에서 JSON 부분만 추출"""
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1] if "\n" in clean else clean
    if clean.endswith("```"):
        clean = clean[:-3]
    return clean.strip()


def _get_type_label(value: str) -> str:
    return next((t["label"] for t in PROJECT_TYPES if t["value"] == value), value)


def _get_contract_label(value: str) -> str:
    return next((c["label"] for c in CONTRACT_TYPES if c["value"] == value), value)


@router.post("/suggest")
async def suggest_timeline(request: AutoSuggestRequest):
    """GPT 기반 자동 일정 추천"""
    try:
        openai_service = OpenAIService()

        user_parts = [f"사업명: {request.project_name}"]
        if request.project_description:
            user_parts.append(f"사업 설명: {request.project_description}")
        if request.budget:
            user_parts.append(f"예산 규모: {request.budget}")
        if request.deadline:
            user_parts.append(f"완료 목표: {request.deadline}")
        if request.project_type:
            user_parts.append(f"사업 유형: {_get_type_label(request.project_type)}")
        if request.contract_type:
            user_parts.append(f"계약 방식: {_get_contract_label(request.contract_type)}")

        current_year = datetime.now().year
        user_parts.append(f"현재 시점: {current_year}년 {datetime.now().month}월")
        user_parts.append("위 사업의 현실적인 추진 일정을 추천해 주세요.")

        user_prompt = "\n".join(user_parts)

        result_text = await openai_service.generate_text(
            prompt=f"{SUGGEST_SYSTEM_PROMPT}\n\n{user_prompt}",
            max_tokens=2000,
            temperature=0.7
        )

        result = json.loads(_clean_json_response(result_text))

        tasks = result.get("tasks", [])
        validated_tasks = []
        for t in tasks:
            validated_tasks.append({
                "name": t.get("name", "미정"),
                "start_month": max(1, min(12, t.get("start_month", 1))),
                "end_month": max(1, min(12, t.get("end_month", 1))),
                "start_year": t.get("start_year", current_year),
                "end_year": t.get("end_year", current_year),
                "category": t.get("category", "시행"),
                "is_milestone": False,
            })

        return {
            "success": True,
            "tasks": validated_tasks,
            "summary": result.get("summary", ""),
            "project_name": request.project_name,
        }

    except json.JSONDecodeError as e:
        logger.error(f"GPT 응답 JSON 파싱 실패: {e}")
        raise HTTPException(status_code=500, detail="AI 응답을 파싱할 수 없습니다.")
    except Exception as e:
        logger.error(f"일정 추천 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
# 단계별 세부 업무 생성 (법령 챗봇 연동)
# ──────────────────────────────────────────────

DETAIL_TASKS_PROMPT = """당신은 한국 지방자치단체의 사업 관리 전문가입니다.
주어진 사업의 특정 단계에 대해 세부 업무(TODO) 목록을 생성해야 합니다.

규칙:
1. 해당 단계에서 실제로 수행해야 하는 구체적인 업무를 나열하세요.
2. 각 업무에는 법적 근거가 있으면 반드시 포함하세요.
3. 예산 규모에 따른 법정 의무사항(감리, 심의, 검토 등)을 반드시 반영하세요.
4. 계약 방식에 따른 세부 절차를 반영하세요.
5. 사업 유형별 특수 절차를 반영하세요:
   - 정보화사업: 보안성검토, SW과업심의, 정보화사전협의, SW사업감리 등
   - 건설공사: 설계심의, 안전관리계획, 환경영향평가, 건설사업관리 등
   - 용역사업: 과업지시서 작성, 중간보고, 최종보고, 성과심의 등
   - 행사/축제: 안전관리계획, 도로점용허가, 소음신고 등
6. 준비 단계: 사전 행정절차, 심의, 검토, 일상감사 등
7. 시행 단계: 실제 작업을 세부 공정으로 분해
   - 공사: 세부 공종별 분해 (가설공사, 토공, 포장, 마감 등)
   - 시스템구축: 분석, 설계, 개발, 테스트, 이행 등
   - 용역: 착수, 중간점검, 성과물 작성 등
8. 마무리 단계: 검수, 준공검사, 정산, 하자보증 등

아래에 법령 검색 결과가 제공되면 이를 참고하여 정확한 법적 근거를 포함하세요.

반드시 아래 JSON 형식만 반환하세요 (다른 텍스트 없이):
{
  "detail_tasks": [
    {
      "order": 1,
      "task": "세부 업무명",
      "description": "구체적인 설명 (1~2문장)",
      "legal_basis": "근거 법령 (없으면 null)",
      "required": true,
      "note": "참고사항 (없으면 null)"
    }
  ]
}"""


async def _query_law_chatbot(question: str) -> str:
    """법령 챗봇 API 내부 호출"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{INTERNAL_BASE_URL}/api/law-chatbot/ask",
                json={
                    "question": question,
                    "search_scope": "all"
                }
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("answer", "")
            else:
                logger.warning(f"법령 챗봇 호출 실패: {response.status_code}")
                return ""
    except Exception as e:
        logger.warning(f"법령 챗봇 연동 실패 (GPT 자체 지식 활용): {e}")
        return ""


@router.post("/detail-tasks")
async def generate_detail_tasks(request: DetailTasksRequest):
    """단계별 세부 업무 자동 생성 (법령 챗봇 연동)"""
    try:
        openai_service = OpenAIService()

        type_label = _get_type_label(request.project_type) if request.project_type else ""
        contract_label = _get_contract_label(request.contract_type) if request.contract_type else ""

        # 법령 챗봇 질의 구성
        law_queries = []

        if request.task_category == "준비":
            if type_label:
                law_queries.append(f"{type_label} 사업 사전 행정절차 필수사항 (심의, 검토, 협의)")
            if request.budget:
                law_queries.append(f"{type_label} 사업 예산 {request.budget} 규모 법정 필수 절차 (감리, 심의 기준금액)")
            law_queries.append("지방자치단체 사업 일상감사 대상 기준")

        elif request.task_category == "시행":
            if contract_label:
                law_queries.append(f"{contract_label} 계약 세부 절차와 법적 근거")
            if type_label:
                law_queries.append(f"{type_label} 사업 시행 단계 법정 의무사항")

        elif request.task_category == "마무리":
            if type_label:
                law_queries.append(f"{type_label} 사업 완료 후 필수 절차 (준공검사, 정산, 하자보증)")

        # 법령 챗봇 호출
        law_results = []
        for query in law_queries:
            result = await _query_law_chatbot(query)
            if result:
                law_results.append(result)

        law_context = ""
        if law_results:
            law_context = "\n\n[법령 검색 결과 참고]\n" + "\n---\n".join(law_results)

        # GPT 프롬프트 구성
        user_parts = [
            f"사업명: {request.project_name}",
            f"현재 단계: {request.task_name} ({request.task_category})",
        ]
        if type_label:
            user_parts.append(f"사업 유형: {type_label}")
        if contract_label:
            user_parts.append(f"계약 방식: {contract_label}")
        if request.budget:
            user_parts.append(f"예산 규모: {request.budget}")
        if request.project_description:
            user_parts.append(f"사업 설명: {request.project_description}")

        user_parts.append("\n위 단계에서 수행해야 할 세부 업무 목록을 생성해 주세요.")

        user_prompt = "\n".join(user_parts)
        full_prompt = f"{DETAIL_TASKS_PROMPT}{law_context}\n\n{user_prompt}"

        result_text = await openai_service.generate_text(
            prompt=full_prompt,
            max_tokens=2000,
            temperature=0.5
        )

        result = json.loads(_clean_json_response(result_text))

        return {
            "success": True,
            "task_name": request.task_name,
            "detail_tasks": result.get("detail_tasks", []),
            "law_referenced": len(law_results) > 0,
        }

    except json.JSONDecodeError as e:
        logger.error(f"세부 업무 JSON 파싱 실패: {e}")
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


# ──────────────────────────────────────────────
# PNG 내보내기
# ──────────────────────────────────────────────

def _generate_png(timeline: TimelineData) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    import os

    tasks = timeline.tasks
    title = timeline.title

    LEFT_LABEL_W = 280
    MONTH_COL_W = 100
    ROW_H = 56
    HEADER_H = 70
    TITLE_H = 50
    LEGEND_H = 50
    PADDING = 24

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
        font = ImageFont.load_default()
        font_bold = font
        font_small = font

    CATEGORY_COLORS = {
        "준비": {"fill": (238, 237, 254), "bar": (127, 119, 221), "text": (60, 52, 137)},
        "시행": {"fill": (225, 245, 238), "bar": (29, 158, 117), "text": (8, 80, 65)},
        "마무리": {"fill": (250, 236, 231), "bar": (216, 90, 48), "text": (113, 43, 19)},
    }
    DEFAULT_COLOR = {"fill": (230, 241, 251), "bar": (55, 138, 221), "text": (12, 68, 124)}

    bbox = draw.textbbox((0, 0), title, font=font_bold)
    tw = bbox[2] - bbox[0]
    draw.text(((TOTAL_W - tw) / 2, 16), title, fill=(44, 44, 42), font=font_bold)

    chart_x = PADDING + LEFT_LABEL_W
    header_y = TITLE_H

    for i, (year, month) in enumerate(all_months):
        x = chart_x + i * MONTH_COL_W
        label = f"{month}월"
        if month == 1 or i == 0:
            label = f"{year}년 {month}월"
        draw.rectangle([x, header_y, x + MONTH_COL_W, header_y + 30], fill=(241, 239, 232))
        draw.rectangle([x, header_y, x + MONTH_COL_W, header_y + 30], outline=(211, 209, 199))
        bbox = draw.textbbox((0, 0), label, font=font_small)
        mw = bbox[2] - bbox[0]
        draw.text((x + (MONTH_COL_W - mw) / 2, header_y + 8), label, fill=(68, 68, 65), font=font_small)

    row_top = header_y + 30
    for idx, task in enumerate(tasks):
        y = row_top + idx * ROW_H
        colors = CATEGORY_COLORS.get(task.category, DEFAULT_COLOR)

        if idx % 2 == 0:
            draw.rectangle([PADDING, y, TOTAL_W - PADDING, y + ROW_H], fill=(250, 250, 248))
        draw.line([PADDING, y + ROW_H, TOTAL_W - PADDING, y + ROW_H], fill=(230, 228, 222), width=1)
        draw.text((PADDING + 12, y + (ROW_H - 18) / 2), task.name, fill=(44, 44, 42), font=font)

        start_idx = month_index.get((task.start_year, task.start_month), 0)
        end_idx = month_index.get((task.end_year, task.end_month), num_months - 1)
        bar_x1 = chart_x + start_idx * MONTH_COL_W + 6
        bar_x2 = chart_x + (end_idx + 1) * MONTH_COL_W - 6
        bar_y = y + 14
        bar_h = ROW_H - 28

        draw.rounded_rectangle([bar_x1, bar_y, bar_x2, bar_y + bar_h], radius=5, fill=colors["fill"], outline=colors["bar"], width=2)
        months_span = end_idx - start_idx + 1
        if months_span > 1 and (bar_x2 - bar_x1) > 60:
            span_text = f"{months_span}개월"
            bbox = draw.textbbox((0, 0), span_text, font=font_small)
            stw = bbox[2] - bbox[0]
            draw.text(((bar_x1 + bar_x2 - stw) / 2, bar_y + 4), span_text, fill=colors["text"], font=font_small)

    for i in range(num_months + 1):
        x = chart_x + i * MONTH_COL_W
        draw.line([x, row_top, x, row_top + len(tasks) * ROW_H], fill=(238, 236, 230), width=1)

    legend_y = row_top + len(tasks) * ROW_H + 16
    lx = PADDING + 16
    for cat, colors in CATEGORY_COLORS.items():
        draw.rounded_rectangle([lx, legend_y + 2, lx + 14, legend_y + 16], radius=3, fill=colors["bar"])
        draw.text((lx + 20, legend_y), cat, fill=(68, 68, 65), font=font_small)
        bbox = draw.textbbox((0, 0), cat, font=font_small)
        lx += 20 + (bbox[2] - bbox[0]) + 28

    draw.rectangle([0, 0, TOTAL_W - 1, TOTAL_H - 1], outline=(211, 209, 199), width=1)

    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(150, 150))
    return buf.getvalue()


# ──────────────────────────────────────────────
# XLSX 내보내기
# ──────────────────────────────────────────────

def _generate_xlsx(timeline: TimelineData) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook()
    ws = wb.active
    ws.title = "사업추진일정"

    all_months = []
    for t in timeline.tasks:
        for y in range(t.start_year, t.end_year + 1):
            sm = t.start_month if y == t.start_year else 1
            em = t.end_month if y == t.end_year else 12
            for m in range(sm, em + 1):
                all_months.append((y, m))
    all_months = sorted(set(all_months))
    month_index = {ym: i for i, ym in enumerate(all_months)}

    header_font = Font(name="맑은 고딕", size=14, bold=True)
    col_header_font = Font(name="맑은 고딕", size=10, bold=True, color="FFFFFF")
    cell_font = Font(name="맑은 고딕", size=10)
    header_fill = PatternFill(start_color="2D3748", end_color="2D3748", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin", color="D1D5DB"), right=Side(style="thin", color="D1D5DB"),
        top=Side(style="thin", color="D1D5DB"), bottom=Side(style="thin", color="D1D5DB"),
    )

    CATEGORY_FILLS = {
        "준비": PatternFill(start_color="EEEDFE", end_color="EEEDFE", fill_type="solid"),
        "시행": PatternFill(start_color="E1F5EE", end_color="E1F5EE", fill_type="solid"),
        "마무리": PatternFill(start_color="FAECE7", end_color="FAECE7", fill_type="solid"),
    }
    default_fill = PatternFill(start_color="E6F1FB", end_color="E6F1FB", fill_type="solid")

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=3 + len(all_months))
    title_cell = ws.cell(row=1, column=1, value=timeline.title)
    title_cell.font = header_font
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    headers = ["단계명", "시작", "종료"] + [f"{y}년 {m}월" if m == 1 or i == 0 else f"{m}월" for i, (y, m) in enumerate(all_months)]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_idx, value=header)
        cell.font = col_header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 12
    for i in range(len(all_months)):
        col_letter = chr(68 + i) if i < 22 else None
        if col_letter:
            ws.column_dimensions[col_letter].width = 6

    for row_idx, task in enumerate(timeline.tasks, 4):
        ws.cell(row=row_idx, column=1, value=task.name).font = cell_font
        ws.cell(row=row_idx, column=1).border = thin_border
        ws.cell(row=row_idx, column=2, value=f"{task.start_year}.{task.start_month:02d}").font = cell_font
        ws.cell(row=row_idx, column=2).alignment = Alignment(horizontal="center")
        ws.cell(row=row_idx, column=2).border = thin_border
        ws.cell(row=row_idx, column=3, value=f"{task.end_year}.{task.end_month:02d}").font = cell_font
        ws.cell(row=row_idx, column=3).alignment = Alignment(horizontal="center")
        ws.cell(row=row_idx, column=3).border = thin_border

        start_idx = month_index.get((task.start_year, task.start_month), 0)
        end_idx = month_index.get((task.end_year, task.end_month), len(all_months) - 1)
        fill = CATEGORY_FILLS.get(task.category, default_fill)
        for i in range(len(all_months)):
            cell = ws.cell(row=row_idx, column=4 + i)
            cell.border = thin_border
            if start_idx <= i <= end_idx:
                cell.fill = fill
                cell.value = "■"
                cell.alignment = Alignment(horizontal="center")
                cell.font = Font(size=10, color="666666")

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ──────────────────────────────────────────────
# PPTX 내보내기
# ──────────────────────────────────────────────

def _generate_pptx(timeline: TimelineData) -> bytes:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12), Inches(0.7))
    p = txBox.text_frame.paragraphs[0]
    p.text = timeline.title
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
    p.alignment = PP_ALIGN.LEFT

    txBox2 = slide.shapes.add_textbox(Inches(0.5), Inches(0.9), Inches(12), Inches(0.4))
    p2 = txBox2.text_frame.paragraphs[0]
    p2.text = "사업 추진 일정표"
    p2.font.size = Pt(14)
    p2.font.color.rgb = RGBColor(0x71, 0x71, 0x71)

    all_months = []
    for t in timeline.tasks:
        for y in range(t.start_year, t.end_year + 1):
            sm = t.start_month if y == t.start_year else 1
            em = t.end_month if y == t.end_year else 12
            for m in range(sm, em + 1):
                all_months.append((y, m))
    all_months = sorted(set(all_months))
    month_index = {ym: i for i, ym in enumerate(all_months)}
    num_months = len(all_months)

    LEFT = Inches(0.5)
    TOP = Inches(1.6)
    LABEL_W = Inches(2.8)
    CHART_W = Inches(9.5)
    ROW_H = Inches(0.45)
    MONTH_W = CHART_W / num_months if num_months > 0 else Inches(1)

    CATEGORY_COLORS = {
        "준비": RGBColor(0x7F, 0x77, 0xDD),
        "시행": RGBColor(0x1D, 0x9E, 0x75),
        "마무리": RGBColor(0xD8, 0x5A, 0x30),
    }

    for i, (year, month) in enumerate(all_months):
        x = LEFT + LABEL_W + int(MONTH_W * i)
        label = f"'{str(year)[2:]}.{month}월" if (month == 1 or i == 0) else f"{month}월"
        hb = slide.shapes.add_textbox(x, TOP - Inches(0.35), int(MONTH_W), Inches(0.3))
        hp = hb.text_frame.paragraphs[0]
        hp.text = label
        hp.font.size = Pt(9)
        hp.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
        hp.alignment = PP_ALIGN.CENTER

    for idx, task in enumerate(timeline.tasks):
        y = TOP + int(ROW_H * idx)
        lb = slide.shapes.add_textbox(LEFT, y, LABEL_W, ROW_H)
        lb.text_frame.word_wrap = True
        lp = lb.text_frame.paragraphs[0]
        lp.text = task.name
        lp.font.size = Pt(11)
        lp.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

        si = month_index.get((task.start_year, task.start_month), 0)
        ei = month_index.get((task.end_year, task.end_month), num_months - 1)
        bx = LEFT + LABEL_W + int(MONTH_W * si) + Inches(0.05)
        bw = int(MONTH_W * (ei - si + 1)) - Inches(0.1)
        by = y + Inches(0.08)
        bh = ROW_H - Inches(0.16)

        shape = slide.shapes.add_shape(1, int(bx), int(by), int(bw), int(bh))
        shape.fill.solid()
        shape.fill.fore_color.rgb = CATEGORY_COLORS.get(task.category, RGBColor(0x37, 0x8A, 0xDD))
        shape.line.fill.background()
        shape.text_frame.paragraphs[0].text = f"{ei - si + 1}개월"
        shape.text_frame.paragraphs[0].font.size = Pt(8)
        shape.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shape.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ──────────────────────────────────────────────
# 내보내기
# ──────────────────────────────────────────────

@router.post("/export")
async def export_timeline(request: ExportRequest):
    try:
        if request.format == "png":
            data = _generate_png(request.timeline)
            filename = f"{request.timeline.title}_일정표.png"
            mime = "image/png"
        elif request.format == "xlsx":
            data = _generate_xlsx(request.timeline)
            filename = f"{request.timeline.title}_일정표.xlsx"
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif request.format == "pptx":
            data = _generate_pptx(request.timeline)
            filename = f"{request.timeline.title}_일정표.pptx"
            mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 형식입니다.")

        return {
            "success": True,
            "data": base64.b64encode(data).decode("utf-8"),
            "filename": filename,
            "mime_type": mime,
            "format": request.format,
        }
    except Exception as e:
        logger.error(f"내보내기 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
# 헬스체크
# ──────────────────────────────────────────────

@router.get("/status")
async def timeline_status():
    return {
        "status": "ok",
        "features": {
            "auto_suggest": True,
            "detail_tasks": True,
            "law_chatbot_integration": True,
            "export_png": True,
            "export_xlsx": True,
            "export_pptx": True,
        },
        "project_types": len(PROJECT_TYPES),
        "contract_types": len(CONTRACT_TYPES),
    }