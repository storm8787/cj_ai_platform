"""
사업 타임라인 생성기 (Project Timeline Planner)
- GPT 자동 일정 추천
- 수동 일정 입력
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

from services.openai_service import OpenAIService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/timeline", tags=["timeline"])


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────

class TimelineTask(BaseModel):
    """개별 일정 항목"""
    name: str = Field(..., description="단계명 (예: 기본계획 수립)")
    start_month: int = Field(..., ge=1, le=12, description="시작 월")
    end_month: int = Field(..., ge=1, le=12, description="종료 월")
    start_year: int = Field(..., description="시작 연도")
    end_year: int = Field(..., description="종료 연도")
    category: Optional[str] = Field(None, description="카테고리 (준비, 시행, 마무리 등)")
    is_milestone: bool = Field(False, description="마일스톤 여부")


class TimelineData(BaseModel):
    """타임라인 전체 데이터"""
    title: str = Field(..., description="사업명")
    tasks: list[TimelineTask] = Field(..., description="일정 목록")
    base_year: int = Field(..., description="기준 연도")


class AutoSuggestRequest(BaseModel):
    """GPT 자동 일정 추천 요청"""
    project_name: str = Field(..., description="사업명")
    project_description: Optional[str] = Field(None, description="사업 설명 (선택)")
    budget: Optional[str] = Field(None, description="예산 규모 (선택)")
    deadline: Optional[str] = Field(None, description="완료 목표 시기 (선택)")
    project_type: Optional[str] = Field(None, description="사업 유형 (선택)")


class ExportRequest(BaseModel):
    """내보내기 요청"""
    timeline: TimelineData
    format: str = Field(..., pattern="^(png|xlsx|pptx)$", description="내보내기 형식")


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
8. 마일스톤(주요 시점)에는 is_milestone: true 표시
9. 현실적이고 보수적인 일정 산출 (여유 기간 포함)

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
  "summary": "일정 산출 근거 요약 (2~3문장)"
}"""


@router.post("/suggest")
async def suggest_timeline(request: AutoSuggestRequest):
    """GPT 기반 자동 일정 추천"""
    try:
        #client = get_openai_client()
        openai_service = OpenAIService()

        # 사용자 프롬프트 구성
        user_parts = [f"사업명: {request.project_name}"]
        if request.project_description:
            user_parts.append(f"사업 설명: {request.project_description}")
        if request.budget:
            user_parts.append(f"예산 규모: {request.budget}")
        if request.deadline:
            user_parts.append(f"완료 목표: {request.deadline}")
        if request.project_type:
            user_parts.append(f"사업 유형: {request.project_type}")

        current_year = datetime.now().year
        user_parts.append(f"현재 시점: {current_year}년 {datetime.now().month}월")
        user_parts.append("위 사업의 현실적인 추진 일정을 추천해 주세요.")

        user_prompt = "\n".join(user_parts)

        result_text = await openai_service.generate_text(
            prompt=f"{SUGGEST_SYSTEM_PROMPT}\n\n{user_prompt}",
            max_tokens=2000,
            temperature=0.7
        )
        result = json.loads(result_text)
        #result = json.loads(result_text)

        # 유효성 검증
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
                "is_milestone": t.get("is_milestone", False),
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
# 사업 유형 목록
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
    {"value": "other", "label": "기타", "icon": "📌"}
]


@router.get("/project-types")
async def get_project_types():
    """사업 유형 목록 반환"""
    return {"types": PROJECT_TYPES}


# ──────────────────────────────────────────────
# PNG 내보내기
# ──────────────────────────────────────────────

def _generate_png(timeline: TimelineData) -> bytes:
    """타임라인 PNG 이미지 생성"""
    from PIL import Image, ImageDraw, ImageFont
    import os

    tasks = timeline.tasks
    title = timeline.title

    # 레이아웃 설정
    LEFT_LABEL_W = 280
    MONTH_COL_W = 100
    ROW_H = 56
    HEADER_H = 70
    TITLE_H = 50
    LEGEND_H = 50
    PADDING = 24

    # 월 범위 계산
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

    # 폰트
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
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

    # 카테고리별 색상
    CATEGORY_COLORS = {
        "준비": {"fill": (238, 237, 254), "bar": (127, 119, 221), "text": (60, 52, 137)},
        "시행": {"fill": (225, 245, 238), "bar": (29, 158, 117), "text": (8, 80, 65)},
        "마무리": {"fill": (250, 236, 231), "bar": (216, 90, 48), "text": (113, 43, 19)},
    }
    DEFAULT_COLOR = {"fill": (230, 241, 251), "bar": (55, 138, 221), "text": (12, 68, 124)}

    # 타이틀
    bbox = draw.textbbox((0, 0), title, font=font_bold)
    tw = bbox[2] - bbox[0]
    draw.text(((TOTAL_W - tw) / 2, 16), title, fill=(44, 44, 42), font=font_bold)

    # 월 헤더
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

    # 행
    row_top = header_y + 30
    for idx, task in enumerate(tasks):
        y = row_top + idx * ROW_H
        colors = CATEGORY_COLORS.get(task.category, DEFAULT_COLOR)

        # 배경
        if idx % 2 == 0:
            draw.rectangle([PADDING, y, TOTAL_W - PADDING, y + ROW_H], fill=(250, 250, 248))
        draw.line([PADDING, y + ROW_H, TOTAL_W - PADDING, y + ROW_H], fill=(230, 228, 222), width=1)

        # 레이블
        label_text = task.name
        if task.is_milestone:
            label_text = "◆ " + label_text
        draw.text((PADDING + 12, y + (ROW_H - 18) / 2), label_text, fill=(44, 44, 42), font=font)

        # 간트 바
        start_idx = month_index.get((task.start_year, task.start_month), 0)
        end_idx = month_index.get((task.end_year, task.end_month), num_months - 1)
        bar_x1 = chart_x + start_idx * MONTH_COL_W + 6
        bar_x2 = chart_x + (end_idx + 1) * MONTH_COL_W - 6
        bar_y = y + 14
        bar_h = ROW_H - 28

        if task.is_milestone:
            # 마일스톤: 다이아몬드
            cx = (bar_x1 + bar_x2) / 2
            cy = bar_y + bar_h / 2
            s = 12
            draw.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill=colors["bar"])
        else:
            draw.rounded_rectangle([bar_x1, bar_y, bar_x2, bar_y + bar_h], radius=5, fill=colors["fill"], outline=colors["bar"], width=2)
            # 기간 텍스트
            months_span = end_idx - start_idx + 1
            if months_span > 1 and (bar_x2 - bar_x1) > 60:
                span_text = f"{months_span}개월"
                bbox = draw.textbbox((0, 0), span_text, font=font_small)
                stw = bbox[2] - bbox[0]
                draw.text(((bar_x1 + bar_x2 - stw) / 2, bar_y + 4), span_text, fill=colors["text"], font=font_small)

    # 세로 그리드
    for i in range(num_months + 1):
        x = chart_x + i * MONTH_COL_W
        draw.line([x, row_top, x, row_top + len(tasks) * ROW_H], fill=(238, 236, 230), width=1)

    # 범례
    legend_y = row_top + len(tasks) * ROW_H + 16
    lx = PADDING + 16
    for cat, colors in CATEGORY_COLORS.items():
        draw.rounded_rectangle([lx, legend_y + 2, lx + 14, legend_y + 16], radius=3, fill=colors["bar"])
        draw.text((lx + 20, legend_y), cat, fill=(68, 68, 65), font=font_small)
        bbox = draw.textbbox((0, 0), cat, font=font_small)
        lx += 20 + (bbox[2] - bbox[0]) + 28

    # 테두리
    draw.rectangle([0, 0, TOTAL_W - 1, TOTAL_H - 1], outline=(211, 209, 199), width=1)

    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(150, 150))
    return buf.getvalue()


# ──────────────────────────────────────────────
# XLSX 내보내기
# ──────────────────────────────────────────────

def _generate_xlsx(timeline: TimelineData) -> bytes:
    """타임라인 Excel 파일 생성"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook()
    ws = wb.active
    ws.title = "사업추진일정"

    # 월 범위 계산
    all_months = []
    for t in timeline.tasks:
        for y in range(t.start_year, t.end_year + 1):
            sm = t.start_month if y == t.start_year else 1
            em = t.end_month if y == t.end_year else 12
            for m in range(sm, em + 1):
                all_months.append((y, m))
    all_months = sorted(set(all_months))
    month_index = {ym: i for i, ym in enumerate(all_months)}

    # 스타일
    header_font = Font(name="맑은 고딕", size=14, bold=True)
    col_header_font = Font(name="맑은 고딕", size=10, bold=True, color="FFFFFF")
    cell_font = Font(name="맑은 고딕", size=10)
    header_fill = PatternFill(start_color="2D3748", end_color="2D3748", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin", color="D1D5DB"),
        right=Side(style="thin", color="D1D5DB"),
        top=Side(style="thin", color="D1D5DB"),
        bottom=Side(style="thin", color="D1D5DB"),
    )

    CATEGORY_FILLS = {
        "준비": PatternFill(start_color="EEEDFE", end_color="EEEDFE", fill_type="solid"),
        "시행": PatternFill(start_color="E1F5EE", end_color="E1F5EE", fill_type="solid"),
        "마무리": PatternFill(start_color="FAECE7", end_color="FAECE7", fill_type="solid"),
    }
    default_fill = PatternFill(start_color="E6F1FB", end_color="E6F1FB", fill_type="solid")

    # 타이틀
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=3 + len(all_months))
    title_cell = ws.cell(row=1, column=1, value=timeline.title)
    title_cell.font = header_font
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # 헤더 행
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

    # 데이터 행
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
    """타임라인 PowerPoint 파일 생성"""
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    slide_layout = prs.slide_layouts[6]  # Blank
    slide = prs.slides.add_slide(slide_layout)

    # 타이틀
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12), Inches(0.7))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = timeline.title
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
    p.alignment = PP_ALIGN.LEFT

    # 부제
    txBox2 = slide.shapes.add_textbox(Inches(0.5), Inches(0.9), Inches(12), Inches(0.4))
    tf2 = txBox2.text_frame
    p2 = tf2.paragraphs[0]
    p2.text = "사업 추진 일정표"
    p2.font.size = Pt(14)
    p2.font.color.rgb = RGBColor(0x71, 0x71, 0x71)

    # 월 범위
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

    # 레이아웃
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
    DEFAULT_BAR_COLOR = RGBColor(0x37, 0x8A, 0xDD)

    # 월 헤더
    for i, (year, month) in enumerate(all_months):
        x = LEFT + LABEL_W + int(MONTH_W * i)
        label = f"{month}월"
        if month == 1 or i == 0:
            label = f"'{str(year)[2:]}.{month}월"

        header_box = slide.shapes.add_textbox(x, TOP - Inches(0.35), int(MONTH_W), Inches(0.3))
        htf = header_box.text_frame
        hp = htf.paragraphs[0]
        hp.text = label
        hp.font.size = Pt(9)
        hp.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
        hp.alignment = PP_ALIGN.CENTER

    # 행
    for idx, task in enumerate(timeline.tasks):
        y = TOP + int(ROW_H * idx)

        # 레이블
        label_box = slide.shapes.add_textbox(LEFT, y, LABEL_W, ROW_H)
        ltf = label_box.text_frame
        ltf.word_wrap = True
        lp = ltf.paragraphs[0]
        lp.text = task.name
        lp.font.size = Pt(11)
        lp.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

        # 간트 바
        start_idx = month_index.get((task.start_year, task.start_month), 0)
        end_idx = month_index.get((task.end_year, task.end_month), num_months - 1)
        bar_x = LEFT + LABEL_W + int(MONTH_W * start_idx) + Inches(0.05)
        bar_w = int(MONTH_W * (end_idx - start_idx + 1)) - Inches(0.1)
        bar_y = y + Inches(0.08)
        bar_h = ROW_H - Inches(0.16)

        bar_color = CATEGORY_COLORS.get(task.category, DEFAULT_BAR_COLOR)
        shape = slide.shapes.add_shape(
            1,  # MSO_SHAPE.ROUNDED_RECTANGLE
            int(bar_x), int(bar_y), int(bar_w), int(bar_h)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = bar_color
        shape.line.fill.background()

        # 바 안에 기간 텍스트
        shape.text_frame.paragraphs[0].text = f"{end_idx - start_idx + 1}개월"
        shape.text_frame.paragraphs[0].font.size = Pt(8)
        shape.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shape.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ──────────────────────────────────────────────
# 내보내기 엔드포인트
# ──────────────────────────────────────────────

@router.post("/export")
async def export_timeline(request: ExportRequest):
    """타임라인 내보내기 (PNG/XLSX/PPTX)"""
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

        encoded = base64.b64encode(data).decode("utf-8")

        return {
            "success": True,
            "data": encoded,
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
    """타임라인 생성기 상태 확인"""
    return {
        "status": "ok",
        "features": {
            "auto_suggest": True,
            "export_png": True,
            "export_xlsx": True,
            "export_pptx": True,
        },
        "project_types": len(PROJECT_TYPES),
    }