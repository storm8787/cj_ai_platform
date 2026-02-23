"""
출장보고 생성기 API - 안정화 최종본
- Drag&Drop은 프론트에서 처리
- 2단계 분석: (1) 유형 분류 → (2) 상세 추출
- 안정화 3종 세트:
  1) response_format(json_schema) 시도
  2) 모델/파라미터 미지원 시 자동 폴백(temperature/response_format 제거)
  3) 파싱/타입 보정(main_content 문자열→리스트, 글자쪼개짐 방지)

모델:
  * 사진 분석: gpt-5.1-chat-latest (Vision)
  * 보고서 생성/재작성: gpt-5-mini
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
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
    "회의참석": {
        "icon": "🤝",
        "fields": ["회의명", "일시", "장소", "주최기관", "참석자"],
        "template": "회의 참석 결과 보고",
        "closing_section": "협의결과",
        "closing_guide": "협의결과는 주요 결정사항, 합의내용, 이견사항 중심으로 작성.",
    },
    "벤치마킹": {
        "icon": "🏢",
        "fields": ["방문목적", "일시", "방문기관", "담당자"],
        "template": "벤치마킹 결과 보고",
        "closing_section": "우리시 적용방안",
        "closing_guide": "우리시 적용방안은 도입 가능성, 예산·인력 검토, 추진 일정 중심으로 작성.",
    },
    "교육연수": {
        "icon": "📚",
        "fields": ["교육명", "일시", "장소", "주관기관", "교육내용"],
        "template": "교육·연수 결과 보고",
        "closing_section": "적용방안",
        "closing_guide": "적용방안은 업무 활용 계획, 제도 개선 반영 여부, 공유 계획 중심으로 작성. 실습·기술 교육이면 '업무활용계획'으로 표현 가능.",
    },
    "설명회참석": {
        "icon": "🎤",
        "fields": ["행사명", "일시", "장소", "주최", "참석인원"],
        "template": "설명회·행사 참석 결과 보고",
        "closing_section": "주요내용",
        "closing_guide": "주요내용은 발표·배포 자료 핵심 내용, 질의응답 사항 중심으로 작성. 정책 참고사항이 있으면 별도 기재.",
    },
    "조사연구": {
        "icon": "🔍",
        "fields": ["조사목적", "일시", "조사지역", "조사항목"],
        "template": "조사·연구 결과 보고",
        "closing_section": "검토의견 및 우리시 반영사항",
        "closing_guide": "검토의견은 조사 결과 분석, 우리시 반영사항은 정책·제도 반영 방향과 후속 조치 계획 중심으로 작성.",
    },
    "시설점검": {
        "icon": "🏗️",
        "fields": ["점검위치", "점검대상", "발견사항", "위험도"],
        "template": "시설 점검 결과 보고",
        "closing_section": "조치계획",
        "closing_guide": "조치계획은 발견사항별 보수·개선 일정, 예산 확보 방안, 안전조치 계획 중심으로 작성.",
    },
    "민원현장": {
        "icon": "🚨",
        "fields": ["민원위치", "민원유형", "현장상황", "조치결과"],
        "template": "민원 현장 확인 보고",
        "closing_section": "재발방지 대책",
        "closing_guide": "재발방지 대책은 원인 분석, 순찰·단속 강화 계획, 민원 회신 방안 중심으로 작성.",
    },
    "환경점검": {
        "icon": "🌳",
        "fields": ["점검위치", "점검항목", "측정결과", "적합여부"],
        "template": "환경 점검 결과 보고",
        "closing_section": "조치계획",
        "closing_guide": "조치계획은 측정 결과 기반 개선 필요사항, 모니터링 계획, 관계기관 협조 방안 중심으로 작성.",
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
# 유틸리티
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


def _split_lines_like_bullets(s: str) -> List[str]:
    """문자열 main_content를 보고서용 bullet 리스트로 변환"""
    s = (s or "").strip()
    if not s:
        return []
    # 줄바꿈/구분자 기반 분리
    parts = re.split(r"[\r\n]+|•|\u2022|·| - |\s-\s", s)
    cleaned = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # 너무 짧은 단일 글자(예: '표','나'...)는 일단 제외 (나중에 join fallback)
        cleaned.append(p)
    # 만약 거의 다 1글자면 원문을 다시 문장단위로 재분리
    if cleaned and sum(1 for x in cleaned if len(x) <= 1) / len(cleaned) > 0.6:
        # 의미단위로 재시도: 마침표/세미콜론/쉼표
        parts2 = re.split(r"[。\.]|;|,", s)
        cleaned2 = [p.strip() for p in parts2 if p.strip()]
        return cleaned2[:30]
    return cleaned[:50]


def _coerce_main_content(v: Any) -> List[str]:
    """main_content 타입 보정(핵심)"""
    if v is None:
        return []
    if isinstance(v, list):
        # list인데 글자 단위로 들어온 경우(join 후 재분리)
        if v and all(isinstance(x, str) and len(x) <= 1 for x in v):
            joined = "".join(v).strip()
            return _split_lines_like_bullets(joined)
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        return _split_lines_like_bullets(v)
    return [str(v).strip()] if str(v).strip() else []


def _coerce_extracted_info(v: Any) -> Dict[str, str]:
    if isinstance(v, dict):
        return {str(k): str(val) for k, val in v.items()}
    return {}


def _coerce_photos_analysis(v: Any) -> List[Dict[str, Any]]:
    if isinstance(v, list):
        return [x for x in v if isinstance(x, dict)]
    if isinstance(v, dict):
        return [v]
    return []


def _contains_forbidden_polite(text: str) -> bool:
    patterns = [
        r"합니다", r"입니다", r"했습니다", r"됩니다", r"있습니다",
        r"드립니다", r"바랍니다", r"부탁드립니다", r"감사합니다",
        r"하겠습니다", r"드리겠습니다"
    ]
    return any(re.search(p, text) for p in patterns)


def _has_required_structure(text: str) -> bool:
    needed = ["1.", "2.", "3.", "4."]
    return all(n in text for n in needed)


def _build_image_contents(images_data: List[dict], detail: str) -> List[dict]:
    return [
        {"type": "image_url", "image_url": {"url": item["data_url"], "detail": detail}}
        for item in images_data
    ]


def _chat_create_compat(
    model: str,
    messages: list,
    max_completion_tokens: int,
    temperature: Optional[float] = None,
    response_format: Optional[dict] = None,
) -> str:
    """
    모델별 파라미터 지원 차이를 자동 흡수:
    - temperature 미지원 모델이면 제거 후 재시도
    - response_format 미지원이면 제거 후 재시도
    """
    base_kwargs = {
        "model": model,
        "messages": messages,
        "max_completion_tokens": max_completion_tokens,
    }
    if temperature is not None:
        base_kwargs["temperature"] = temperature
    if response_format is not None:
        base_kwargs["response_format"] = response_format

    def _call(kwargs):
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    # 1차
    try:
        return _call(base_kwargs)
    except Exception as e1:
        msg = str(e1)

        # temperature 미지원 → 제거
        if "temperature" in msg and "Only the default (1) value is supported" in msg:
            kwargs2 = dict(base_kwargs)
            kwargs2.pop("temperature", None)
            try:
                return _call(kwargs2)
            except Exception as e2:
                msg2 = str(e2)
                # response_format 미지원 → 제거
                if "response_format" in msg2 or "json_schema" in msg2:
                    kwargs3 = dict(kwargs2)
                    kwargs3.pop("response_format", None)
                    return _call(kwargs3)
                raise

        # response_format 미지원 → 제거
        if "response_format" in msg or "json_schema" in msg:
            kwargs2 = dict(base_kwargs)
            kwargs2.pop("response_format", None)
            return _call(kwargs2)

        raise


# ========================================
# Structured Output 스키마 (가능하면 사용)
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
                "extracted_info": {"type": "object", "additionalProperties": {"type": "string"}},
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


# ========================================
# 프롬프트
# ========================================
def _classification_prompt(force_report_type: str = "") -> str:
    force_line = ""
    if force_report_type and force_report_type in REPORT_TYPES:
        force_line = f'\n※ 사용자 지정 유형: "{force_report_type}" → report_type을 반드시 이 값으로 설정할 것.\n'

    return f"""당신은 지방자치단체 공무원 출장보고 분류 AI임.
사진을 보고 아래 8개 유형 중 하나로 분류하라.
{force_line}
[유형]
- 회의참석: 회의/협의/간담회 (회의실·좌석 배치·명패·화이트보드·회의 자료 등)
- 벤치마킹: 타 기관 방문/우수사례 견학 (기관 로고·시설 투어·담당자 면담·출입증 등)
- 교육연수: 교육/연수/강의/워크숍 (강의실·PPT·강사·교재·수강 좌석 등)
- 설명회참석: 설명회/박람회/포럼/행사/세미나 (현수막·배너·발표·무대·전시 부스 등)
- 조사연구: 현지 조사/연구/실태 파악 (조사 장비·측정·인터뷰·현장 기록 등)
- 시설점검: 도로/건물/시설물 안전점검 (파손·균열·공사현장·안전점검표 등)
- 민원현장: 민원 확인/현장 조치 (불법행위·쓰레기·정비·단속·민원처리 등)
- 환경점검: 환경 관련 측정/점검 (하천·대기·소음·측정장비·오염 현장 등)

출력은 반드시 JSON 단독으로만 반환하라.
키: report_type, confidence(0~1), rationale
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

[출력 형식]
- 반드시 JSON 단독 출력
- main_content는 "배열"이어야 함 (문자열 금지)
  예: ["절차 1: ...", "절차 2: ..."]
- photos_analysis는 사진 개수만큼 배열
  photo_index는 1부터 시작

[추출 규칙]
1) 현수막/배너/PPT/표/간판의 텍스트 → detected_text에 그대로 기재
2) 일시/장소/행사명/기관명 등은 extracted_info의 해당 필드에 정확히 매핑
3) 표/절차/단계가 보이면 main_content에 단계별로 요약(한 줄 1개)
4) 숫자/기간/장소명은 구체적으로, 안 보이면 "확인 필요" (억지로 만들지 말 것)
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
        # gpt-5.1-chat-latest는 temperature 제약이 있을 수 있어 "None"으로 호출(=파라미터 미전달)
        analysis_temperature=None

        # 1) 분류
        classify_messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": _classification_prompt(force_report_type)},
                *_build_image_contents(images_data, detail="low"),
            ],
        }]

        classify_json = None
        # (1) 스키마 시도
        try:
            classify_text = _chat_create_compat(
                model=ANALYSIS_MODEL,
                messages=classify_messages,
                max_completion_tokens=600,
                temperature=analysis_temperature,
                response_format=CLASSIFY_SCHEMA,
            )
            classify_json = json.loads(classify_text)
        except Exception:
            # (2) 일반 JSON 강제 출력
            classify_text = _chat_create_compat(
                model=ANALYSIS_MODEL,
                messages=classify_messages,
                max_completion_tokens=600,
                temperature=analysis_temperature,
                response_format=None,
            )
            classify_json = _safe_json_extract(classify_text)

        classified_type = (classify_json.get("report_type") or "회의참석").strip()
        if classified_type not in REPORT_TYPES:
            classified_type = "회의참석"

        if force_report_type and force_report_type in REPORT_TYPES:
            classified_type = force_report_type

        # 2) 상세 추출
        extract_messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": _extraction_prompt(classified_type, force_report_type)},
                *_build_image_contents(images_data, detail="high"),
            ],
        }]

        extract_json = None
        try:
            extract_text = _chat_create_compat(
                model=ANALYSIS_MODEL,
                messages=extract_messages,
                max_completion_tokens=2500,
                temperature=analysis_temperature,
                response_format=EXTRACT_SCHEMA,
            )
            extract_json = json.loads(extract_text)
        except Exception:
            extract_text = _chat_create_compat(
                model=ANALYSIS_MODEL,
                messages=extract_messages,
                max_completion_tokens=2500,
                temperature=analysis_temperature,
                response_format=None,
            )
            extract_json = _safe_json_extract(extract_text)

        report_type = (extract_json.get("report_type") or classified_type).strip()
        if force_report_type and force_report_type in REPORT_TYPES:
            report_type = force_report_type
        if report_type not in REPORT_TYPES:
            report_type = classified_type

        # ===== 타입 보정(핵심) =====
        extracted_info = _coerce_extracted_info(extract_json.get("extracted_info"))
        main_content = _coerce_main_content(extract_json.get("main_content"))
        photos_analysis_raw = _coerce_photos_analysis(extract_json.get("photos_analysis"))

        # 필드 보강
        fields = REPORT_TYPES[report_type]["fields"]
        for f in fields:
            extracted_info.setdefault(f, "")

        # photos_analysis pydantic
        photos_items: List[PhotoAnalysisItem] = []
        for p in photos_analysis_raw:
            try:
                photos_items.append(PhotoAnalysisItem(
                    photo_index=int(p.get("photo_index") or 1),
                    description=str(p.get("description") or ""),
                    detected_text=str(p.get("detected_text") or ""),
                    key_elements=[str(x) for x in (p.get("key_elements") or []) if str(x).strip()],
                ))
            except Exception:
                continue

        confidence = extract_json.get("confidence")
        if confidence is None:
            confidence = classify_json.get("confidence")
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.6
        confidence = max(0.0, min(1.0, confidence))

        validated = AnalysisResult(
            report_type=report_type,
            report_type_icon=REPORT_TYPES.get(report_type, {}).get("icon", "📄"),
            extracted_info={k: str(v) for k, v in extracted_info.items()},
            main_content=main_content,
            photos_analysis=photos_items,
            confidence=confidence,
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
# API: 보고서 생성
# ========================================
@router.post("/generate-report")
async def generate_report(request: ReportGenerateRequest):
    start_time = time.time()

    try:
        report_type = request.report_type if request.report_type in REPORT_TYPES else "회의참석"
        type_info = REPORT_TYPES[report_type]
        fields = type_info["fields"]
        closing_section = type_info["closing_section"]
        closing_guide = type_info["closing_guide"]

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

        # main_content도 혹시 프론트에서 문자열로 넘어오면 방어
        mc = _coerce_main_content(request.main_content)
        content_text = "\n".join([f"  - {item}" for item in mc if str(item).strip()])

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

        type_guides = {
            "회의참석": "회의 안건, 토의 내용, 결정사항 정리.",
            "벤치마킹": "방문 목적, 우수사례 내용, 시사점 정리.",
            "교육연수": "교육 과정, 주요 내용, 실습 결과 정리.",
            "설명회참석": "발표 내용, 배포 자료 핵심, 질의응답 정리.",
            "조사연구": "조사 방법, 결과 수치, 분석 내용 정리.",
            "시설점검": "점검 위치, 발견사항, 위험도 명확화.",
            "민원현장": "민원 내용, 현장 상황, 조치 결과 명확화.",
            "환경점검": "점검 항목, 측정 결과, 적합 여부 명확화.",
        }

        report_prompt = f"""당신은 대한민국 지방자치단체 공문서 작성 전문가임.
아래 입력을 근거로 '{type_info["template"]}'를 작성하라.

[유형별 가이드]
{type_guides.get(report_type, "")}
4번 항목({closing_section}): {closing_guide}

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

[필수 규칙]
- 경어체(~합니다/~입니다) 절대 금지
- 명사형 종결 사용: ~임/~함/~됨 금지, 반드시 단어로 종결
  예시(나쁨): "논의할 예정임", "검토됨", "추진함"
  예시(좋음): "논의 예정", "검토 완료", "추진 계획"
- 개조식 문체, 간결하게 작성
- 보고서 구조 반드시 유지:
  1. 출장 개요
  2. 주요 내용
  3. 사진 및 참고
  4. {closing_section}
"""

        # gpt-5-mini는 temperature 가능하므로 사용
        def _chat(model, messages, max_completion_tokens, temperature):
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=max_completion_tokens,
                temperature=temperature
            )
            return resp.choices[0].message.content or ""

        text = _chat(
            model=REPORT_MODEL,
            messages=[
                {"role": "system", "content": "공문서 문체(단어형 종결, 개조식) 준수. 경어체 절대 금지. ~임/~함/~됨 금지. '논의 예정', '검토 완료'처럼 명사·동사원형으로 종결. 1~4 구조 유지."},
                {"role": "user", "content": report_prompt},
            ],
            max_completion_tokens=2500,
            temperature=1.0,
        )

        if _contains_forbidden_polite(text) or not _has_required_structure(text):
            rewrite_prompt = f"""아래 보고서를 공문서 문체로 재작성하라.
- 경어체 → 단어형 종결로 변환
- ~임/~함/~됨 → 명사/동사원형으로 변환
  예: "논의할 예정임" → "논의 예정"
  예: "검토됨" → "검토 완료"
  예: "추진함" → "추진 계획"
- 구조(1~4) 유지
- 내용/수치/고유명사 변경 금지, 새로운 사실 추가 금지

[원문]
{text}
"""
            text = _chat(
                model=REPORT_MODEL,
                messages=[
                    {"role": "system", "content": "공문서 문체 교정 전용. 내용 변경 금지. ~임/~함/~됨 → 단어형 종결로 변환. 구조(1~4) 유지."},
                    {"role": "user", "content": rewrite_prompt},
                ],
                max_completion_tokens=2500,
                temperature=1.0,
            )

        return ReportResponse(
            report_text=text,
            generation_time=round(time.time() - start_time, 2)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 생성 실패: {str(e)}")


@router.get("/report-types")
async def get_report_types():
    return {
        "types": [
            {"id": key, "name": key, "icon": val["icon"], "fields": val["fields"]}
            for key, val in REPORT_TYPES.items()
        ]
    }