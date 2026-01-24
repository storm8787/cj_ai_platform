"""
업무보고 생성기 API - 공무원 행정문서 스타일
Azure Container Apps 배포용
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import re
from datetime import datetime

from config import settings
from services.openai_service import OpenAIService

router = APIRouter()
openai_service = OpenAIService()


# ===========================================
# 📋 요청/응답 모델
# ===========================================
class ReportGenerateRequest(BaseModel):
    title: str
    report_type: str  # 계획 보고서, 대책 보고서, 상황 보고서, 분석 보고서, 기타 보고서
    detail_type: str  # 세부 유형
    keywords: str     # 쉼표 구분
    length: str = "표준"  # 간략, 표준, 상세


class ReportSection(BaseModel):
    title: str
    order: int
    content: List[str]


class ReportResponse(BaseModel):
    title: str
    type: str
    detail_type: str
    summary: str
    sections: List[ReportSection]
    metadata: Dict[str, Any]
    success: bool


class StructureResponse(BaseModel):
    report_types: Dict[str, Dict[str, List[str]]]
    length_options: List[str]


# ===========================================
# 📚 보고서 구조 정의
# ===========================================
REPORT_STRUCTURES: Dict[str, Dict[str, List[str]]] = {
    "계획 보고서": {
        "기본 계획": ["배경", "목적", "추진계획", "주요내용", "기대효과"],
        "세부 계획": ["배경", "현황", "추진목표", "추진전략", "세부추진계획", "기대효과"],
        "사업 계획": ["사업개요", "추진배경", "사업내용", "추진일정", "소요예산", "기대효과"],
    },
    "대책 보고서": {
        "문제 해결": ["목적", "현황", "문제점", "대책", "효과"],
        "위기 관리": ["현안문제", "위험요소", "대응방안", "이행계획", "기대효과"],
        "개선안": ["현상진단", "문제분석", "개선목표", "개선방안", "실행계획", "기대효과"],
    },
    "상황 보고서": {
        "현황": ["보고일시", "상황개요", "현재상태", "조치사항", "향후계획"],
        "진행 상황": ["사업개요", "추진경과", "진행현황", "주요성과", "문제점", "향후계획"],
        "사건 보고": ["발생일시", "발생장소", "사건개요", "피해상황", "조치사항", "후속대책"],
    },
    "분석 보고서": {
        "데이터 분석": ["분석목적", "분석방법", "데이터개요", "분석결과", "시사점", "결론"],
        "성과 분석": ["사업개요", "분석목적", "성과지표", "분석결과", "개선사항", "결론"],
        "동향 분석": ["분석배경", "주요동향", "영향분석", "대응방안", "결론"],
    },
    "기타 보고서": {
        "간략 메모": ["날짜", "주요내용", "특이사항", "후속조치"],
        "회의 결과": ["회의일시", "참석자", "회의안건", "주요논의사항", "결정사항", "향후일정"],
        "업무 메모": ["작성일", "업무개요", "처리내용", "참고사항", "후속조치"],
    },
}

LENGTH_RULES = {
    "간략": {"paragraphs_per_section": 1, "sentences_per_paragraph": "2~3"},
    "표준": {"paragraphs_per_section": 2, "sentences_per_paragraph": "3~4"},
    "상세": {"paragraphs_per_section": 3, "sentences_per_paragraph": "4~5"},
}


# ===========================================
# 🎯 공무원 문체 프롬프트 (핵심!)
# ===========================================
def build_prompt(title: str, report_type: str, detail_type: str, keywords: str, length_key: str) -> str:
    """공무원 업무보고 스타일에 최적화된 프롬프트 생성"""
    
    sections = REPORT_STRUCTURES[report_type][detail_type]
    rule = LENGTH_RULES[length_key]
    keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
    
    # 공무원 문체 예시 (개괄식 종결어미)
    style_examples = """
[올바른 공무원 문체 예시]
✓ "~추진할 계획임"
✓ "~완료하였음"
✓ "~검토가 필요함"
✓ "~으로 판단됨"
✓ "~에 해당함"
✓ "~을 시행 중임"
✓ "~할 예정임"
✓ "~으로 분석됨"
✓ "~이 요구됨"
✓ "~에 따른 것임"

[잘못된 문체 - 절대 사용 금지]
✗ "~했습니다" (존댓말)
✗ "~했다" (과거형 평서체)
✗ "~하겠습니다" (의지형)
✗ "~해야 한다" (당위형)
✗ "~하고 있습니다" (진행형 존댓말)
"""

    # 문장 구조 가이드
    sentence_guide = """
[문장 작성 규칙]
1. 한 문장은 40자 내외로 간결하게 작성
2. 주어-목적어-서술어 순서 준수
3. 불필요한 조사나 접속사 최소화
4. 숫자/통계는 구체적으로 명시
5. 각 항목은 핵심 내용만 개조식으로 기술

[문단 구성]
- 각 섹션의 content는 개조식 문장의 배열
- 한 항목당 1~2문장으로 구성
- 번호나 불릿 기호 없이 문장만 작성
"""

    return f"""당신은 대한민국 지방자치단체 공무원의 업무보고서 작성을 돕는 전문 AI입니다.

{style_examples}

{sentence_guide}

[작성 요청]
- 제목: {title}
- 보고서 유형: {report_type} > {detail_type}
- 구조: {' → '.join(sections)}
- 분량: 섹션당 {rule['paragraphs_per_section']}개 항목, 항목당 {rule['sentences_per_paragraph']}문장
- 핵심 키워드: {', '.join(keyword_list)}

[필수 준수사항]
1. 모든 문장은 반드시 개괄식 종결어미(~임, ~함, ~됨, ~음)로 끝낼 것
2. "~다", "~습니다" 형태의 종결어미 절대 금지
3. 마크다운, 이모지, 특수기호 사용 금지
4. 번호 목록(1., 2.), 불릿(-, •, *) 사용 금지
5. 각 content 항목은 순수 문장으로만 구성

[출력 형식]
반드시 아래 JSON 스키마를 정확히 따를 것. 추가 설명 없이 JSON만 출력.

{{
  "title": "{title}",
  "type": "{report_type}",
  "detailType": "{detail_type}",
  "summary": "보고서 핵심 내용을 3~4문장으로 요약. 개괄식 종결어미 사용.",
  "sections": [
    {{
      "title": "섹션명",
      "order": 1,
      "content": [
        "첫 번째 항목 내용. 개괄식 종결어미로 작성함.",
        "두 번째 항목 내용. 구체적 수치나 현황을 포함함."
      ]
    }}
  ],
  "metadata": {{
    "generatedAt": "{datetime.now().isoformat()}",
    "totalSections": {len(sections)},
    "keywords": {json.dumps(keyword_list, ensure_ascii=False)}
  }}
}}
"""


# ===========================================
# 🔧 후처리 함수
# ===========================================
TERM_CORRECTIONS = {
    # 잘못된 종결어미 → 개괄식으로 변환
    "했습니다": "하였음",
    "합니다": "함",
    "됩니다": "됨",
    "입니다": "임",
    "있습니다": "있음",
    "없습니다": "없음",
    "했다": "하였음",
    "한다": "함",
    "된다": "됨",
    "이다": "임",
    "있다": "있음",
    "없다": "없음",
    "하겠습니다": "할 예정임",
    "하겠다": "할 예정임",
    "해야 합니다": "필요함",
    "해야 한다": "필요함",
    # 행정용어 정규화
    "효율성 증대": "효율성 제고",
    "만족도 증대": "만족도 제고",
    "증대": "제고",
}

# 불릿/마커 패턴
BULLET_PATTERN = re.compile(r"^\s*([\-•\*\d]+[.)\]:]|\(?\d+\)|[가-힣][.)])\s*")
MARKDOWN_PATTERN = re.compile(r"\*\*(.*?)\*\*|\*(.*?)\*|`(.*?)`")
NUMBER_GROUP = re.compile(r'(\d{1,3})(?=(\d{3})+(?!\d))')


def add_number_commas(text: str) -> str:
    """숫자에 천단위 콤마 추가"""
    return NUMBER_GROUP.sub(r'\1,', text)


def fix_ending(sentence: str) -> str:
    """문장 종결어미를 개괄식으로 변환"""
    sentence = sentence.strip()
    if not sentence:
        return sentence
    
    # 마침표 제거 후 처리
    if sentence.endswith('.'):
        sentence = sentence[:-1]
    
    # 종결어미 변환
    for wrong, correct in TERM_CORRECTIONS.items():
        if sentence.endswith(wrong):
            sentence = sentence[:-len(wrong)] + correct
            break
    
    # 개괄식 종결어미가 아니면 추가 처리
    valid_endings = ['임', '음', '함', '됨', '있음', '없음', '요함', '예정임', '중임', '완료함', '필요함']
    has_valid_ending = any(sentence.endswith(end) for end in valid_endings)
    
    if not has_valid_ending and len(sentence) > 5:
        # 동사/형용사 어간 추출 시도
        if sentence.endswith('다'):
            sentence = sentence[:-1] + '음'
        elif sentence.endswith('요'):
            sentence = sentence[:-1] + '임'
    
    return sentence


def clean_content(text: str) -> str:
    """콘텐츠 정리"""
    # 불릿/마커 제거
    text = BULLET_PATTERN.sub("", text)
    # 마크다운 제거
    text = MARKDOWN_PATTERN.sub(r"\1\2\3", text)
    # 이모지 제거 (간단한 패턴)
    text = re.sub(r'[^\w\s가-힣.,()%~\-:/·]', '', text)
    # 연속 공백 정리
    text = re.sub(r'\s{2,}', ' ', text)
    # 천단위 콤마
    text = add_number_commas(text)
    # 단위 띄어쓰기
    text = re.sub(r'(\d)(천원|백만원|억원)', r'\1 \2', text)
    
    return text.strip()


def postprocess_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """보고서 전체 후처리"""
    result = dict(data)
    
    # 요약 처리
    if isinstance(result.get("summary"), str):
        summary = clean_content(result["summary"])
        # 요약은 여러 문장일 수 있으므로 각 문장 처리
        sentences = re.split(r'(?<=[.。])\s*', summary)
        processed_sentences = [fix_ending(s) for s in sentences if s.strip()]
        result["summary"] = ' '.join(processed_sentences)
    
    # 섹션별 처리
    processed_sections = []
    for sec in result.get("sections", []):
        sec = dict(sec)
        contents = sec.get("content", [])
        
        if isinstance(contents, str):
            contents = [contents]
        
        processed_contents = []
        for item in contents:
            if isinstance(item, str) and item.strip():
                cleaned = clean_content(item)
                fixed = fix_ending(cleaned)
                if fixed:
                    processed_contents.append(fixed)
        
        sec["content"] = processed_contents
        processed_sections.append(sec)
    
    result["sections"] = processed_sections
    return result


# ===========================================
# 🌐 API 엔드포인트
# ===========================================
@router.get("/structures", response_model=StructureResponse)
async def get_report_structures():
    """보고서 구조 및 옵션 조회"""
    return StructureResponse(
        report_types=REPORT_STRUCTURES,
        length_options=list(LENGTH_RULES.keys())
    )


@router.post("/generate", response_model=ReportResponse)
async def generate_report(request: ReportGenerateRequest):
    """업무보고서 생성"""
    
    # 유효성 검사
    if request.report_type not in REPORT_STRUCTURES:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 보고서 유형: {request.report_type}")
    
    if request.detail_type not in REPORT_STRUCTURES[request.report_type]:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 세부 유형: {request.detail_type}")
    
    if request.length not in LENGTH_RULES:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 분량 옵션: {request.length}")
    
    try:
        # 프롬프트 생성
        prompt = build_prompt(
            title=request.title,
            report_type=request.report_type,
            detail_type=request.detail_type,
            keywords=request.keywords,
            length_key=request.length
        )
        
        # GPT 호출 (JSON 모드)
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "당신은 대한민국 공무원 업무보고서 작성 전문가입니다. 반드시 JSON 형식으로만 응답하세요."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # 낮은 온도로 일관성 확보
            response_format={"type": "json_object"},
            max_tokens=4000
        )
        
        raw_content = response.choices[0].message.content or ""
        data = json.loads(raw_content)
        
        # 후처리
        data = postprocess_report(data)
        
        # 응답 구성
        sections = [
            ReportSection(
                title=sec.get("title", ""),
                order=sec.get("order", idx + 1),
                content=sec.get("content", [])
            )
            for idx, sec in enumerate(data.get("sections", []))
        ]
        
        return ReportResponse(
            title=data.get("title", request.title),
            type=data.get("type", request.report_type),
            detail_type=data.get("detailType", request.detail_type),
            summary=data.get("summary", ""),
            sections=sections,
            metadata=data.get("metadata", {}),
            success=True
        )
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"JSON 파싱 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 생성 실패: {str(e)}")


@router.get("/status")
async def get_status():
    """서비스 상태 확인"""
    return {
        "status": "active",
        "service": "업무보고 생성기",
        "version": "1.0.0",
        "supported_types": list(REPORT_STRUCTURES.keys())
    }