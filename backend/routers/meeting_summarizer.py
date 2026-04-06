"""
회의요약기 API (GPT 기반)
DB 프롬프트 우선 + 하드코딩 fallback 유지
"""
import os
import re
import time
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from openai import OpenAI

from config import settings
from services.prompt_service import prompt_service

router = APIRouter()

# OpenAI 클라이언트
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# 모델 설정
FULL_MODEL = "gpt-4o"
SUMMARY_TOKENS = 3000

# 충주시 부서/지역 데이터 (하드코딩)
DEPARTMENTS = [
    "홍보담당관", "감사담당관", "안전행정국", "자치행정과", "기획예산과", "안전총괄과",
    "정보통신과", "회계과", "경제교통국", "경제과", "투자유치과", "신성장산업과",
    "교통정책과", "차량민원과", "건설국", "허가민원과", "도시계획과", "건축과",
    "도로과", "복지국", "복지정책과", "노인복지과", "장애인복지과", "여성청소년과",
    "생활민원국", "민원봉사과", "토지정보과", "세정과", "징수과", "위생과",
    "문화체육관광국", "문화예술과", "체육진흥과", "관광과", "평생학습과",
    "농업정책국", "농정과", "친환경농산과", "농식품유통과", "축수산과",
    "푸른도시국", "정원도시과", "균형개발과", "하천과", "산림과",
    "환경국", "수질환경과", "대기환경과", "자원순환과",
    "보건소", "보건과", "건강증진과", "질병관리과",
    "농업기술센터", "농업기술과", "농업교육과", "과수육성과",
    "상수도사업소", "하수도사업소", "시립도서관", "박물관", "의회사무국"
]

LOCATIONS = [
    "주덕읍", "살미면", "수안보면", "대소원면", "신니면", "노은면", "앙성면",
    "중앙탑면", "금가면", "동량면", "산척면", "엄정면", "소태면",
    "성내.충인동", "교현.안림동", "교현2동", "용산동", "지현동", "문화동",
    "호암.직동", "달천동", "봉방동", "칠금.금릉동", "연수동", "목행.용탄동"
]

# 3단계 상세도별 설정
MODE_CONFIG = {
    "최소": {
        "주제당_문장수": "1개",
        "문장당_길이": "20~30자",
        "설명": "핵심 키워드만 간단히 서술"
    },
    "간략": {
        "주제당_문장수": "1~2개",
        "문장당_길이": "30~60자",
        "설명": "요점과 간단한 배경을 포함하여 요약"
    },
    "표준": {
        "주제당_문장수": "4~6개",
        "문장당_길이": "200~300자 이상",
        "설명": "배경→현황→문제점→대응→향후 계획까지 종합적으로 기술"
    }
}

# 입력 길이 기준
INPUT_LENGTH_THRESHOLDS = {
    "아주짧음": 50,
    "짧음": 200,
    "보통": 500,
    "긴편": 2000,
}


# ========================================
# 프롬프트 기본값 (DB에 없을 때 사용)
# ========================================
_DEFAULT_SUMMARY_PROMPT_FOCUSED = """당신은 행정기관 회의록 요약 전문가입니다.

다음은 특정 발화자({focus_pattern})의 발언 내용입니다. 이 발화자의 발언을 주제별로 분류하고 {mode} 수준으로 요약해주세요.
{anti_hallucination}
{short_note}
## 요약 원칙:
1. **주제 추출**: 발화자의 발언을 논리적 주제로 분류
2. **{mode} 상세도**: {mode_description} - 각 주제별로 {sentences_per_topic} ({sentence_length})
3. **자연스러운 문체**: 행정문서체이지만 읽기 쉽게 작성
4. **원문 충실**: 원문에 없는 내용은 절대 추가하지 않음

## 문체 가이드:
- 종결어미: "~하도록 할 예정", "~에 대해 논의함", "~을 추진 중" 등
- 구어체 배제: 문서체로 변환

## 출력 형식:
▣ 주제명
◦ 내용 설명

---
발화자 발언 내용:
{text}
---
발화자의 발언을 주제별로 분류하고 {mode} 상세도로 요약해 주세요 (원문에 없는 내용 추가 금지):"""

_DEFAULT_SUMMARY_PROMPT_ALL = """당신은 행정기관 회의록 요약 전문가입니다.

다음 전체 회의록의 핵심 내용을 주제별로 분류하여 {mode} 수준으로 요약하세요.
{anti_hallucination}
{short_note}
## 요약 원칙:
1. **주제 추출**: 회의 전체 내용을 논리적 주제로 분류
2. **{mode} 상세도**: {mode_description} - 각 주제별로 {sentences_per_topic} ({sentence_length})
3. **자연스러운 문체**: 행정문서체이지만 읽기 쉽게 작성
4. **균형감**: 모든 참석자의 중요 발언을 적절히 반영
5. **원문 충실**: 원문에 없는 내용은 절대 추가하지 않음

## 문체 가이드:
- 종결어미: "~하도록 할 예정", "~에 대해 논의함", "~을 추진 중" 등
- 구어체 배제: 문서체로 변환

## 출력 형식:
▣ 주제명
◦ 내용 설명

---
전체 회의록:
{text}
---
회의 내용을 주제별로 분류하고 {mode} 상세도로 요약해 주세요 (원문에 없는 내용 추가 금지):"""

_DEFAULT_DIRECTIVE_PROMPT = """당신은 행정기관 회의록을 '지시사항' 형태로 정리하는 전문가입니다.
{anti_hallucination}
{length_note}
다음 텍스트를 검토하여 {scope} 주제별 핵심 내용을 정리하되, 
**원문에 있는 내용만** 지시사항 형태로 변환하세요.

## 작성 규칙
- 원문에 내용이 충분하면: 각 주제별 4~6문장
- 원문이 짧으면: 원문 길이에 맞게 간결하게 작성
- "~임/~됨/~필요함/~바람" 표현은 "~할 것"으로 변환
- **원문에 없는 구체적 날짜, 수치, 부서명, 담당자를 생성하지 말 것**

## 출력 형식
▣ 주제명
◦ 지시형으로 변환된 내용

---
분석 대상 텍스트{who}:
{text}
---
위 지침에 따라 원문 내용만 사용하여 지시사항 형태로 변환:"""


# ===== Pydantic 모델 =====
class SummarizeRequest(BaseModel):
    text: str
    summary_mode: str = "표준"
    focus_pattern: Optional[str] = None
    extract_actions: bool = True
    directive_mode: bool = False
    auto_adjust_mode: bool = True


class ActionItem(BaseModel):
    task: str
    assignee: str
    deadline: str
    details: str


class SummarizeResponse(BaseModel):
    summary: str
    actions: List[ActionItem] = []
    analysis_stats: Dict[str, Any]


# ===== 유틸리티 함수 =====
def detect_input_length_category(text: str) -> str:
    """입력 텍스트 길이를 카테고리로 분류"""
    char_count = len(text.strip())
    if char_count < INPUT_LENGTH_THRESHOLDS["아주짧음"]:
        return "아주짧음"
    elif char_count < INPUT_LENGTH_THRESHOLDS["짧음"]:
        return "짧음"
    elif char_count < INPUT_LENGTH_THRESHOLDS["보통"]:
        return "보통"
    else:
        return "긴편"


def get_effective_mode(original_mode: str, text: str, auto_adjust: bool = True) -> tuple:
    """입력 길이에 따라 실제 적용할 모드 결정"""
    if not auto_adjust:
        return original_mode, ""

    length_category = detect_input_length_category(text)

    if length_category == "아주짧음":
        if original_mode in ["표준", "간략"]:
            return "최소", f"입력이 매우 짧아 '{original_mode}' → '최소' 모드로 자동 조정됨"
        return "최소", ""
    elif length_category == "짧음":
        if original_mode == "표준":
            return "간략", f"입력이 짧아 '표준' → '간략' 모드로 자동 조정됨"
        return original_mode, ""
    elif length_category == "보통":
        if original_mode == "표준":
            return "간략", f"입력 길이에 맞춰 '표준' → '간략' 모드로 조정됨"
        return original_mode, ""
    else:
        return original_mode, ""


def get_anti_hallucination_instruction(length_category: str) -> str:
    """입력 길이에 따른 할루시네이션 방지 지침"""
    if length_category in ["아주짧음", "짧음"]:
        return """
## ⚠️ 중요: 짧은 입력 처리 규칙
- 입력된 내용만을 기반으로 요약하세요. 없는 내용을 절대 추가하지 마세요.
- 입력이 짧으면 출력도 짧아야 합니다.
- 원문에 언급되지 않은 부서명, 일정, 구체적 수치, 행사명, 담당자 등을 생성하지 마세요.
"""
    elif length_category == "보통":
        return """
## 주의: 내용 충실도
- 원문에 있는 내용만 요약하세요.
- 언급되지 않은 세부사항을 추가하지 마세요.
"""
    else:
        return """
## 참고: 원문 충실도
- 원문의 내용을 충실히 반영하되, 추측성 내용은 피하세요.
"""


# 발화자 패턴
_SP_LABEL = re.compile(r"^\s*(참석자\s*\d+|시장|부시장|과장|팀장|주무관|\d{1,3}:|[가-힣]+\s*:)")


def _propagate_last_label(text: str) -> str:
    """라벨이 한 번만 찍힌 텍스트 -> 각 줄에 라벨 복제"""
    out, last = [], ""
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if _SP_LABEL.match(ln):
            last = _SP_LABEL.match(ln).group(1)
            out.append(ln)
        else:
            out.append(f"{last} {ln}" if last else ln)
    return "\n".join(out)


def _split_by_speaker(text: str) -> List[tuple]:
    """발화자별로 텍스트 분할"""
    blocks, spk, buf = [], None, []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if m := _SP_LABEL.match(ln):
            if spk and buf:
                blocks.append((spk, "\n".join(buf).strip()))
            spk, buf = m.group(1).strip(), [ln]
        else:
            buf.append(ln)
    if spk and buf:
        blocks.append((spk, "\n".join(buf).strip()))
    return blocks


def _filter_focus(text: str, pattern: Optional[str]) -> str:
    """특정 발화자에 집중"""
    if not pattern:
        return text
    try:
        rg = re.compile(pattern, re.I)
        filtered_blocks = []
        for spk, blk in _split_by_speaker(text):
            if rg.search(spk):
                filtered_blocks.append(blk)
        return "\n\n".join(filtered_blocks) if filtered_blocks else text
    except Exception:
        return text


def _is_similar(term1: str, term2: str) -> bool:
    """간단한 문자열 유사도 체크"""
    if abs(len(term1) - len(term2)) > 2:
        return False
    if len(term1) < 2 or len(term2) < 2:
        return False
    same_chars = sum(1 for c1, c2 in zip(term1, term2) if c1 == c2)
    similarity = same_chars / max(len(term1), len(term2))
    return similarity >= 0.7


def enhance_text_with_terms(text: str) -> tuple:
    """충주 특화용어로 텍스트 보정"""
    enhanced_text = text
    corrections = []

    potential_terms = re.findall(r'[가-힣]{2,8}', text)
    unique_terms = list(set(potential_terms))[:30]

    for term in unique_terms:
        for dept in DEPARTMENTS:
            if _is_similar(term, dept) and term != dept:
                enhanced_text = enhanced_text.replace(term, dept)
                corrections.append(f"{term}→{dept}")
                break

        for loc in LOCATIONS:
            if _is_similar(term, loc) and term != loc:
                enhanced_text = enhanced_text.replace(term, loc)
                corrections.append(f"{term}→{loc}")
                break

    return enhanced_text, corrections[:10]


def build_summary_prompt(text: str, mode: str, focus_pattern: Optional[str], is_focused: bool) -> str:
    """요약 프롬프트 생성"""
    config = MODE_CONFIG[mode]
    length_category = detect_input_length_category(text)
    anti_hallucination = get_anti_hallucination_instruction(length_category)

    short_note = ""
    if length_category in ["아주짧음", "짧음"]:
        short_note = f"""
## 📌 입력 길이 참고
현재 입력은 **{len(text)}자**로 짧은 편입니다. 
- 출력 분량도 이에 맞게 간결하게 유지하세요.
"""

    if is_focused:
        template = prompt_service.get(
            "meeting_summarizer",
            "summary_prompt_focused",
            default=_DEFAULT_SUMMARY_PROMPT_FOCUSED
        )
        return template.format(
            focus_pattern=focus_pattern,
            mode=mode,
            anti_hallucination=anti_hallucination,
            short_note=short_note,
            mode_description=config["설명"],
            sentences_per_topic=config["주제당_문장수"],
            sentence_length=config["문장당_길이"],
            text=text,
        )

    template = prompt_service.get(
        "meeting_summarizer",
        "summary_prompt_all",
        default=_DEFAULT_SUMMARY_PROMPT_ALL
    )
    return template.format(
        mode=mode,
        anti_hallucination=anti_hallucination,
        short_note=short_note,
        mode_description=config["설명"],
        sentences_per_topic=config["주제당_문장수"],
        sentence_length=config["문장당_길이"],
        text=text,
    )


def build_directive_prompt(text: str, mode: str, focus_pattern: Optional[str], is_focused: bool) -> str:
    """지시사항 프롬프트 생성"""
    length_category = detect_input_length_category(text)
    anti_hallucination = get_anti_hallucination_instruction(length_category)

    length_note = ""
    if length_category in ["아주짧음", "짧음", "보통"]:
        length_note = f"""
## 📌 입력 길이 참고
현재 입력은 **{len(text)}자**입니다.
- 입력이 짧으면 출력도 짧게 유지하세요.
- 형식을 채우기 위해 없는 내용을 만들지 마세요.
"""

    who = f" (대상 발화자: {focus_pattern})" if (is_focused and focus_pattern) else ""
    scope = "해당 발화자의 발언에서" if is_focused else "전체 회의록에서"

    template = prompt_service.get(
        "meeting_summarizer",
        "directive_prompt",
        default=_DEFAULT_DIRECTIVE_PROMPT
    )
    return template.format(
        anti_hallucination=anti_hallucination,
        length_note=length_note,
        scope=scope,
        who=who,
        text=text,
    )


def extract_action_items(summary: str) -> List[Dict[str, str]]:
    """요약에서 액션 아이템 추출"""
    actions = []

    action_patterns = [
        r'([^.]*(?:추진|시행|실시|검토|준비|작성|제출|보고|개선|강화|확대|마련|설치|구축)[^.]*?)(?:하기\s*)?(?:바람|할\s*것|하기로\s*함|필요함)',
        r'([^.]*(?:까지|내|중|연내|상반기|하반기)[^.]*(?:완료|마무리|추진|제출|결정)[^.]*)',
        r'([^.]*(?:과|팀|부|센터|청)(?:에서는?)?\s*[^.]*(?:담당|처리|시행)[^.]*)'
    ]

    action_count = 0
    for pattern in action_patterns:
        matches = re.finditer(pattern, summary, re.IGNORECASE)
        for match in matches:
            if action_count >= 8:
                break

            full_match = match.group(1).strip()
            if len(full_match) > 10:
                assignee_match = re.search(r'([가-힣]+(?:과|팀|부|센터|청))', full_match)
                assignee = assignee_match.group(1) if assignee_match else "미지정"

                deadline_match = re.search(r'(\d+월\s*\d+일|\d+일까지|다음주|내주|연내|상반기|하반기)', full_match)
                deadline = deadline_match.group(1) if deadline_match else "미지정"

                actions.append({
                    "task": full_match,
                    "assignee": assignee,
                    "deadline": deadline,
                    "details": full_match
                })
                action_count += 1

    return actions


def validate_summary(summary: str, mode: str, is_focused: bool, length_category: str) -> tuple:
    """요약 결과 검증"""
    try:
        topics = summary.count("▣")
        bullets = summary.count("◦")

        if topics < 1:
            return False, "주제가 없습니다"
        if bullets < 1:
            return False, "세부 내용이 없습니다"

        content_length = len(summary.replace("▣", "").replace("◦", "").strip())

        if length_category in ["아주짧음", "짧음"]:
            if content_length < 10:
                return False, "내용이 너무 짧습니다"
            if content_length > 500:
                return False, "입력 대비 출력이 너무 깁니다"
            return True, "간단 요약 검증 통과"

        if is_focused:
            if content_length < 30:
                return False, "내용이 너무 짧습니다"
            if content_length > 3000:
                return False, "내용이 너무 깁니다"
        else:
            if content_length < 50:
                return False, "내용이 너무 짧습니다"
            if content_length > 5000:
                return False, "내용이 너무 깁니다"

        return True, "구조 검증 통과"
    except Exception as e:
        return True, f"검증 중 오류 (통과 처리): {str(e)}"


def _format_basic_summary(summary: str) -> str:
    """기본 형식으로 요약 정리"""
    lines = [line.strip() for line in summary.split('\n') if line.strip()]

    formatted_lines = []
    for line in lines:
        if not line.startswith('▣') and not line.startswith('◦'):
            if len(line) > 20:
                formatted_lines.append(f"◦ {line}")
        else:
            formatted_lines.append(line)

    if not any(line.startswith('▣') for line in formatted_lines):
        formatted_lines.insert(0, "▣ 회의 주요 내용")

    return '\n'.join(formatted_lines)


# ===== API 엔드포인트 =====
@router.get("/modes")
async def get_modes():
    """요약 모드 목록 조회"""
    return {
        "modes": [
            {"value": "최소", "label": "최소", "description": MODE_CONFIG["최소"]["설명"]},
            {"value": "간략", "label": "간략", "description": MODE_CONFIG["간략"]["설명"]},
            {"value": "표준", "label": "표준", "description": MODE_CONFIG["표준"]["설명"]},
        ]
    }


@router.get("/system-info")
async def get_system_info():
    """시스템 정보 조회"""
    return {
        "departments_count": len(DEPARTMENTS),
        "locations_count": len(LOCATIONS),
        "features": [
            "부서명 인식",
            "지역명 인식",
            "GPT-4o 고급 요약",
            "구조화 요약",
            "후처리 검증"
        ]
    }


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_meeting(request: SummarizeRequest):
    """회의록 요약"""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="회의록 텍스트를 입력해주세요.")

    start_time = time.time()

    try:
        prepped = _propagate_last_label(request.text)

        if request.focus_pattern:
            text_to_summarize = _filter_focus(prepped, request.focus_pattern)
            is_focused = True
            if not text_to_summarize.strip() or text_to_summarize == prepped:
                text_to_summarize = prepped
                is_focused = False
        else:
            text_to_summarize = prepped
            is_focused = False

        enhanced_text, corrections = enhance_text_with_terms(text_to_summarize)

        length_category = detect_input_length_category(enhanced_text)
        effective_mode, mode_msg = get_effective_mode(
            request.summary_mode,
            enhanced_text,
            request.auto_adjust_mode
        )

        if request.directive_mode:
            prompt = build_directive_prompt(enhanced_text, effective_mode, request.focus_pattern, is_focused)
        else:
            prompt = build_summary_prompt(enhanced_text, effective_mode, request.focus_pattern, is_focused)

        if length_category in ["아주짧음", "짧음"]:
            max_tokens = 500
        elif length_category == "보통":
            max_tokens = 1000
        else:
            max_tokens = SUMMARY_TOKENS if is_focused else SUMMARY_TOKENS * 2

        temperature = 0.2 if length_category in ["아주짧음", "짧음"] else 0.3

        response = client.chat.completions.create(
            model=FULL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        summary = response.choices[0].message.content.strip()

        is_valid, validation_msg = validate_summary(summary, effective_mode, is_focused, length_category)
        if not is_valid:
            summary = _format_basic_summary(summary)
            validation_msg = "기본 형식 적용"

        actions = []
        if request.extract_actions and length_category not in ["아주짧음"]:
            action_dicts = extract_action_items(summary)
            actions = [ActionItem(**a) for a in action_dicts]

        speakers = _split_by_speaker(prepped)
        processing_time = time.time() - start_time

        summary_type = "발화자 집중 요약" if is_focused else "전체 회의 요약"

        analysis_stats = {
            "speaker_count": len(speakers),
            "topic_count": summary.count("▣"),
            "keyword_count": len(corrections),
            "processing_time": round(processing_time, 1),
            "validation_status": validation_msg,
            "corrections": corrections[:5],
            "summary_type": summary_type,
            "input_length": len(request.text),
            "input_category": length_category,
            "effective_mode": effective_mode,
            "original_mode": request.summary_mode,
            "mode_adjustment": mode_msg,
        }

        return SummarizeResponse(
            summary=summary.replace("\n", "  \n"),
            actions=actions,
            analysis_stats=analysis_stats
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"요약 처리 중 오류: {str(e)}")


@router.post("/summarize-file")
async def summarize_file(
    file: UploadFile = File(...),
    summary_mode: str = Form(default="표준"),
    focus_pattern: str = Form(default=""),
    extract_actions: bool = Form(default=True),
    directive_mode: bool = Form(default=False),
    auto_adjust_mode: bool = Form(default=True)
):
    """파일 업로드 후 회의록 요약"""
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="txt 파일만 지원합니다.")

    try:
        contents = await file.read()
        text = contents.decode('utf-8')

        request = SummarizeRequest(
            text=text,
            summary_mode=summary_mode,
            focus_pattern=focus_pattern if focus_pattern else None,
            extract_actions=extract_actions,
            directive_mode=directive_mode,
            auto_adjust_mode=auto_adjust_mode
        )

        return await summarize_meeting(request)

    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="파일 인코딩을 확인해주세요. UTF-8만 지원합니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 처리 실패: {str(e)}")