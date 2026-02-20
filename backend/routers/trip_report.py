"""
출장보고 생성기 API - 최종 완성본
- 2단계 분석: (1) 유형 분류(low) → (2) 상세 추출(high)
- Structured Outputs + Pydantic 검증 + fallback 파싱
- 공문서 문체 자동 교정 (금지어/구조 깨짐 감지 시 1회 재작성)
- 모델:
  * 사진 분석: gpt-5.1-chat-latest (Vision)
  * 보고서 생성/재작성: gpt-5-mini
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime
import base64
import time
import os
import json
import re

from openai import OpenAI

router = APIRouter()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 모델 설정 (환경변수로 변경 가능)
ANALYSIS_MODEL = os.getenv("TRIP_ANALYSIS_MODEL", "gpt-5.1-chat-latest")
REPORT_MODEL = os.getenv("TRIP_REPORT_MODEL", "gpt-5-mini")

MAX_IMAGES = int(os.getenv("TRIP_MAX_IMAGES", "10"))
MAX_IMAGE_BYTES = int(os.getenv("TRIP_MAX_IMAGE_BYTES", str(8 * 1024 * 1024)))  # 8MB


# ========================================
# 보고서 유형별 설정
# ========================================
REPORT_TYPES = {
    "행사참석": {
        "icon": "🎤",
        "fields": ["행사명", "일시", "장소", "주최", "참석인원"],
        "template": "행사 참석 보고",
    },
    "출장방문": {
        "icon": "🏢",
        "fields": ["방문목적", "일시", "방문기관", "면담자"],
        "template": "출장 결과 보고",
    },
    "시설점검": {
        "icon": "🏗️",
        "fields": ["점검위치", "점검대상", "발견사항", "위험도"],
        "template": "현장 점검 보고",
    },
    "민원현장": {
        "icon": "🚨",
        "fields": ["민원위치", "민원유형", "현장상황", "조치결과"],
        "template": "민원 현장 확인 보고",
    },
    "환경점검": {
        "icon": "🌳",
        "fields": ["점검위치", "점검항목", "측정결과", "적합여부"],
        "template": "환경 점검 보고",
    },
}


# ========================================
# Pydantic 모델
# ========================================
class PhotoAnalysisItem(BaseModel):
    photo_index: int = Field(..., ge=1)
    description: str = ""
    detected_text: str = ""
    key_elements: List[str] = []


class AnalysisResult(BaseModel):
    report_type: str
    report_type_icon: str
    extracted_info: Dict[str, str] = {}
    main_content: List[str] = []
    photos_analysis: List[PhotoAnalysisItem] = []
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class ReportGenerateRequest(BaseModel):
    report_type: str
    extracted_info: Dict[str, str] = {}
    main_content: List[str] = []
    photos_analysis: List[Dict[str, Any]] = []
    reporter_name: str = ""
    reporter_dept: str = ""
    additional_notes: str = ""


class ReportResponse(BaseModel):
    report_text: str
    generation_time: float


# ========================================
# 유틸리티 함수
# ========================================
def _encode_image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def _get_image_media_type(upload: UploadFile) -> str:
    if upload.content_type and upload.content_type.startswith("image/"):
        return upload.content_type
    filename = (upload.filename or "").lower()
    ext = filename.split(".")[-1] if "." in filename else ""
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }.get(ext, "image/jpeg")


def _safe_json_extract(text: str) -> dict:
    """JSON 파싱 실패 시 코드블록 제거 후 재시도"""
    if not text:
        raise ValueError("empty response")
    
    t = text.strip()
    if "```" in t:
        parts = t.split("```")
        candidates = [p for p in parts if "{" in p and "}" in p]
        if candidates:
            t = candidates[0].strip()
            if t.lower().startswith("json"):
                t = t[4:].strip()
    
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no json object found")
    return json.loads(t[start:end + 1])


def _contains_forbidden_polite(text: str) -> bool:
    """공문서 금지 경어체 탐지"""
    patterns = [
        r"합니다", r"입니다", r"했습니다", r"됩니다", r"있습니다",
        r"드립니다", r"바랍니다", r"부탁드립니다", r"감사합니다",
        r"하겠습니다", r"드리겠습니다", r"되겠습니다"
    ]
    for p in patterns:
        if re.search(p, text):
            return True
    return False


def _has_required_structure(text: str) -> bool:
    """보고서 필수 구조(1~4항목) 존재 여부"""
    needed = ["1.", "2.", "3.", "4."]
    return all(n in text for n in needed)


def _build_image_contents(images_data: List[dict], detail: str) -> List[dict]:
    return [
        {
            "type": "image_url",
            "image_url": {"url": item["data_url"], "detail": detail},
        }
        for item in images_data
    ]


def _chat_create(
    model: str,
    messages: list,
    max_tokens: int,
    temperature: float,
    response_format: Optional[dict] = None
) -> str:
    kwargs = dict(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature
    )
    if response_format:
        kwargs["response_format"] = response_format
    
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


# ========================================
# 분석 프롬프트 (2단계)
# ========================================
CLASSIFY_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "trip_report_classification",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "report_type": {"type": "string", "enum": list(REPORT_TYPES.keys())},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "rationale": {"type": "string"},
            },
            "required": ["report_type", "confidence", "rationale"],
        },
    },
}

EXTRACT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "trip_report_extraction",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "report_type": {"type": "string", "enum": list(REPORT_TYPES.keys())},
                "extracted_info": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
                "main_content": {"type": "array", "items": {"type": "string"}},
                "photos_analysis": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "photo_index": {"type": "integer", "minimum": 1},
                            "description": {"type": "string"},
                            "detected_text": {"type": "string"},
                            "key_elements": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["photo_index", "description", "detected_text", "key_elements"],
                    },
                },
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["report_type", "extracted_info", "main_content", "photos_analysis", "confidence"],
        },
    },
}


def _classification_prompt(force_report_type: str = "") -> str:
    force_line = ""
    if force_report_type and force_report_type in REPORT_TYPES:
        force_line = f'\n※ 사용자 지정 유형: "{force_report_type}" → report_type을 반드시 이 값으로 설정할 것.\n'

    return f"""당신은 지방자치단체 공무원 출장보고 분류 AI임.
사진을 보고 아래 5개 유형 중 하나로 분류하라.
{force_line}
[유형]
- 행사참석: 설명회/세미나/회의/축제/행사 (현수막·배너·발표·좌석·무대 등)
- 출장방문: 타 기관 방문/벤치마킹/업무협의 (기관 로고·회의실·명패·출입증 등)
- 시설점검: 도로/건물/시설물 점검 (파손·균열·공사현장·안전점검 등)
- 민원현장: 민원 확인/현장 조치 (불법행위·쓰레기·정비·단속·민원처리 등)
- 환경점검: 환경 관련 점검 (하천·대기·소음·측정장비·오염 등)

반드시 JSON 스키마에 맞춰 report_type/confidence/rationale를 출력하라.
"""


def _extraction_prompt(report_type: str, force_report_type: str = "") -> str:
    fields = REPORT_TYPES[report_type]["fields"]
    field_lines = "\n".join([f"  - {f}" for f in fields])

    force_line = ""
    if force_report_type and force_report_type in REPORT_TYPES:
        force_line = f'\n※ 사용자 지정 유형: "{force_report_type}" → report_type을 반드시 이 값으로 설정하라.\n'

    return f"""당신은 공무원 현장 보고서 작성 보조 AI임.
사진을 근거로 '{report_type}' 유형의 보고서에 필요한 정보를 추출하라.
{force_line}
[유형 필드 - 반드시 extracted_info에 포함]
{field_lines}

[추출 규칙]
1) 현수막/배너/PPT/표/간판의 텍스트 → detected_text에 그대로 기재
2) 일시/장소/행사명/기관명 등은 extracted_info의 해당 필드에 정확히 매핑
3) 표/절차/단계가 보이면 main_content에 단계별로 정리
4) 숫자/기간/장소명은 구체적으로, 안 보이면 "확인 필요" (억지로 만들지 말 것)
5) photos_analysis는 사진 개수만큼, photo_index는 1부터

반드시 JSON 스키마에 맞춰 출력하라.
"""


# ========================================
# API: 이미지 분석
# ========================================
@router.post("/analyze-images")
async def analyze_images(
    images: List[UploadFile] = File(...),
    reporter_name: str = Form(default=""),
    reporter_dept: str = Form(default=""),
    force_report_type: str = Form(default=""),
):
    start_time = time.time()

    if not images:
        raise HTTPException(status_code=400, detail="이미지를 업로드해주세요.")
    if len(images) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"이미지는 최대 {MAX_IMAGES}장까지 가능합니다.")

    # 이미지 준비
    images_data: List[dict] = []
    for idx, upload in enumerate(images, start=1):
        if upload.content_type and not upload.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"이미지 파일만 업로드 가능합니다. ({upload.filename})")
        
        b = await upload.read()
        if not b:
            raise HTTPException(status_code=400, detail=f"빈 파일입니다. ({upload.filename})")
        if len(b) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=400, detail=f"파일 용량이 너무 큽니다. ({upload.filename})")
        
        media_type = _get_image_media_type(upload)
        data_url = f"data:{media_type};base64,{_encode_image_to_base64(b)}"
        images_data.append({"index": idx, "data_url": data_url})

    try:
        # 1단계: 분류 (low detail - 비용 절감)
        classify_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _classification_prompt(force_report_type)},
                    *_build_image_contents(images_data, detail="low"),
                ],
            }
        ]

        try:
            classify_text = _chat_create(
                model=ANALYSIS_MODEL,
                messages=classify_messages,
                max_tokens=600,
                temperature=0.1,
                response_format=CLASSIFY_SCHEMA,
            )
            classify_json = json.loads(classify_text)
        except Exception:
            classify_text = _chat_create(
                model=ANALYSIS_MODEL,
                messages=classify_messages,
                max_tokens=600,
                temperature=0.1,
            )
            classify_json = _safe_json_extract(classify_text)

        classified_type = classify_json.get("report_type") or "행사참석"
        if force_report_type and force_report_type in REPORT_TYPES:
            classified_type = force_report_type

        # 2단계: 상세 추출 (high detail - 정확도)
        extract_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _extraction_prompt(classified_type, force_report_type)},
                    *_build_image_contents(images_data, detail="high"),
                ],
            }
        ]

        try:
            extract_text = _chat_create(
                model=ANALYSIS_MODEL,
                messages=extract_messages,
                max_tokens=2500,
                temperature=0.1,
                response_format=EXTRACT_SCHEMA,
            )
            extract_json = json.loads(extract_text)
        except Exception:
            extract_text = _chat_create(
                model=ANALYSIS_MODEL,
                messages=extract_messages,
                max_tokens=2500,
                temperature=0.1,
            )
            extract_json = _safe_json_extract(extract_text)

        # 최종 유형 확정
        report_type = extract_json.get("report_type") or classified_type
        if force_report_type and force_report_type in REPORT_TYPES:
            report_type = force_report_type

        # 필드 보강
        fields = REPORT_TYPES[report_type]["fields"]
        extracted_info = extract_json.get("extracted_info") or {}
        for f in fields:
            extracted_info.setdefault(f, "")

        # Pydantic 검증
        validated = AnalysisResult(
            report_type=report_type,
            report_type_icon=REPORT_TYPES.get(report_type, {}).get("icon", "📄"),
            extracted_info={k: str(v) for k, v in extracted_info.items()},
            main_content=[str(x) for x in (extract_json.get("main_content") or []) if str(x).strip()],
            photos_analysis=[PhotoAnalysisItem(**p) for p in (extract_json.get("photos_analysis") or [])],
            confidence=float(extract_json.get("confidence") or classify_json.get("confidence") or 0.6),
        )

        return {
            "success": True,
            "analysis": validated.model_dump(),
            "analysis_time": round(time.time() - start_time, 2),
            "image_count": len(images_data),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 분석 실패: {str(e)}")


# ========================================
# API: 보고서 생성 (공문서 문체 완벽 버전)
# ========================================
@router.post("/generate-report")
async def generate_report(request: ReportGenerateRequest):
    start_time = time.time()

    try:
        report_type = request.report_type if request.report_type in REPORT_TYPES else "행사참석"
        type_info = REPORT_TYPES[report_type]
        fields = type_info["fields"]

        # 입력 정보 텍스트
        info_lines = []
        for f in fields:
            v = (request.extracted_info or {}).get(f, "")
            info_lines.append(f"  - {f}: {v if v else '(미입력)'}")
        
        extra_keys = [k for k in (request.extracted_info or {}).keys() if k not in fields]
        for k in extra_keys:
            v = (request.extracted_info or {}).get(k, "")
            if v:
                info_lines.append(f"  - {k}: {v}")

        info_text = "\n".join(info_lines)
        content_text = "\n".join([f"  - {item}" for item in (request.main_content or []) if str(item).strip()])

        # 사진 분석 근거
        photo_lines = []
        for p in (request.photos_analysis or []):
            idx = p.get("photo_index")
            desc = (p.get("description") or "").strip()
            det = (p.get("detected_text") or "").strip()
            if idx and desc:
                line = f"  - 사진 {idx}: {desc}"
                if det:
                    line += f' (인식 텍스트: "{det}")'
                photo_lines.append(line)
        photos_text = "\n".join(photo_lines) if photo_lines else "  - (사진 분석 정보 없음)"

        # 유형별 가이드
        type_guides = {
            "행사참석": "행사 핵심내용, 발표자료/절차 정리. 시사점은 우리 시 적용방안, 향후계획은 후속조치/공유계획 중심.",
            "출장방문": "방문목적, 면담내용, 우수사례 정리. 시사점은 도입가능성, 향후계획은 추가협의/예산검토 중심.",
            "시설점검": "점검위치, 발견사항, 위험도 명확화. 시사점은 안전문제, 향후계획은 보수일정/예산확보 중심.",
            "민원현장": "민원내용, 현장상황, 조치결과 명확화. 시사점은 재발방지, 향후계획은 순찰강화/민원회신 중심.",
            "환경점검": "점검항목, 측정결과, 적합여부 명확화. 시사점은 환경상태, 향후계획은 모니터링/개선조치 중심.",
        }

        # ========================================
        # 공문서 문체 프롬프트 (핵심!)
        # ========================================
        report_prompt = f"""당신은 대한민국 지방자치단체 공문서 작성 전문가임.
아래 입력을 근거로 '{type_info["template"]}'를 작성하라.

[유형별 가이드]
{type_guides.get(report_type, "")}

[입력 정보]
{info_text}

[주요 내용]
{content_text if content_text else "  - (주요 내용 없음)"}

[사진 분석 근거]
{photos_text}

[보고자 정보]
  - 보고자: {request.reporter_dept} {request.reporter_name}
  - 보고일: {datetime.datetime.now().strftime('%Y. %m. %d.')}

[추가 요청사항]
{request.additional_notes if request.additional_notes else "없음"}

═══════════════════════════════════════════════════════════════
공문서 문체 규칙 (절대 준수)
═══════════════════════════════════════════════════════════════

[1] 문장 종결어미 (가장 중요!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 사용해야 할 종결어미:
  - 사실/상태: ~임, ~함, ~됨, ~있음, ~없음
  - 완료: ~완료함, ~조치함, ~확인함, ~실시함, ~추진함
  - 계획: ~할 예정임, ~추진할 계획임, ~검토 중임, ~협의할 예정임
  - 필요: ~필요함, ~요망됨, ~바람직함

❌ 절대 금지 (경어체):
  - ~합니다, ~입니다, ~됩니다, ~있습니다, ~없습니다
  - ~했습니다, ~하겠습니다, ~드립니다, ~바랍니다
  - ~감사합니다, ~부탁드립니다

[2] 공문서 표현/단어
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 사용해야 할 표현:
  - "~에 관한 사항", "~와 관련하여", "~에 따라"
  - "상기", "하기", "금번", "향후", "조속히"
  - "검토 결과", "현장 확인 결과", "조치 결과"
  - "~의 건", "~에 대하여", "~을 위하여"
  - "추진 경위", "조치 사항", "향후 계획"

❌ 피해야 할 표현:
  - "~것 같습니다", "~라고 생각합니다" → "~으로 판단됨"
  - "많이", "아주", "정말" → "상당히", "매우"
  - "빨리" → "조속히", "신속히"
  - "좋다" → "양호함", "적정함"
  - "나쁘다" → "미흡함", "부적정함"

[3] 항목 기호
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  - 1단계: ㅇ (동그라미)
  - 2단계: - (하이픈)
  - 3단계: · (가운뎃점)

[4] 보고서 구조 (반드시 유지)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{type_info["template"]}

1. 개 요
   ㅇ 일  시: 
   ㅇ 장  소: 
   ㅇ 참석자: (또는 점검자/방문자)
   ㅇ 목  적: 

2. 주요 내용
   ㅇ (핵심 내용 1)
     - 세부 사항
   ㅇ (핵심 내용 2)
     - 세부 사항

3. 현장 사진
   ㅇ 사진 1: (사진 분석 근거 기반 설명)
   ㅇ 사진 2: (사진 분석 근거 기반 설명)
   ※ 실제 사진은 별도 첨부

4. 시사점 및 향후 계획
   ㅇ 시사점
     - (구체적 시사점)
   ㅇ 향후 계획
     - (구체적 조치) 예정임
     - (일정/담당 포함) 추진할 계획임

═══════════════════════════════════════════════════════════════
예시 (좋은 예 vs 나쁜 예)
═══════════════════════════════════════════════════════════════

[시사점 작성]
❌ "방치쓰레기 문제가 심각한 것 같습니다"
✅ "해당 지역 방치쓰레기 상습 투기지역으로 확인됨, 지속적 단속 필요"

❌ "AI 기술을 도입하면 좋을 것 같습니다"
✅ "금번 사업설명회 내용 검토 결과, 우리 시 업무 적용 가능성 높음"

[향후 계획 작성]
❌ "앞으로 개선 방안을 검토하겠습니다"
✅ "3월 중 관련 부서 협의 후 사업 참여 여부 결정할 예정임"

❌ "빨리 고치겠습니다"
✅ "긴급 보수 작업 2주 내 완료 예정임, 소요 예산 500천원"

❌ "민원인한테 연락하겠습니다"
✅ "민원인에게 처리 결과 회신 완료함"

[완료 사항 작성]
❌ "쓰레기를 치웠습니다"
✅ "방치쓰레기 120kg 수거 완료함 (참여인원 3명)"

❌ "현장을 확인했습니다"
✅ "현장 확인 결과, 시설물 노후로 인한 파손 확인됨"

위 규칙을 철저히 준수하여 실무에서 즉시 사용 가능한 보고서를 작성하라.
"""

        # 1차 생성
        text = _chat_create(
            model=REPORT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "당신은 대한민국 지방자치단체 공문서 작성 전문가임. "
                               "공문서 문체(명사형 종결, 개조식)를 철저히 준수함. "
                               "경어체(~합니다, ~입니다) 절대 사용 금지. "
                               "보고서 구조(1~4항목) 반드시 유지."
                },
                {"role": "user", "content": report_prompt},
            ],
            max_tokens=2500,
            temperature=0.2,
        )

        # 문체/구조 검증 → 문제 시 1회 자동 교정
        if _contains_forbidden_polite(text) or not _has_required_structure(text):
            rewrite_prompt = f"""아래 보고서를 공문서 문체로 재작성하라.

[교정 규칙]
1. 경어체(합니다/입니다/했습니다) → 명사형 종결(~임/~함/~됨)로 변환
2. 구조(1~4항목) 반드시 유지
3. 내용/수치/고유명사는 변경 금지
4. 새로운 사실 추가 금지

[원문]
{text}

위 규칙대로 재작성하라. 내용은 유지하고 문체만 교정하라.
"""
            text = _chat_create(
                model=REPORT_MODEL,
                messages=[
                    {"role": "system", "content": "공문서 문체 교정 전용. 내용 변경 금지. 구조(1~4) 유지."},
                    {"role": "user", "content": rewrite_prompt},
                ],
                max_tokens=2500,
                temperature=0.0,
            )

        return ReportResponse(
            report_text=text,
            generation_time=round(time.time() - start_time, 2)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 생성 실패: {str(e)}")


# ========================================
# API: 보고서 유형 목록
# ========================================
@router.get("/report-types")
async def get_report_types():
    return {
        "types": [
            {"id": key, "name": key, "icon": val["icon"], "fields": val["fields"]}
            for key, val in REPORT_TYPES.items()
        ]
    }