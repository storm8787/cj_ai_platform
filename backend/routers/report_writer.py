"""
업무보고 생성기 API - 공무원 행정문서 스타일
실제 지자체 업무보고서 양식에 맞춰 개선된 버전
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import re
from datetime import datetime

from config import settings

router = APIRouter()


# ===========================================
# 📋 요청/응답 모델
# ===========================================
class ReportGenerateRequest(BaseModel):
    title: str
    report_type: str
    detail_type: str
    keywords: str
    length: str = "표준"


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
        "기본 계획": ["추진배경", "현황", "추진계획", "세부내용", "추진일정", "기대효과"],
        "세부 계획": ["추진배경", "현황분석", "추진목표", "추진전략", "세부추진계획", "소요예산", "기대효과"],
        "사업 계획": ["사업개요", "추진배경", "현황", "사업내용", "추진일정", "소요예산", "협조사항", "기대효과"],
    },
    "대책 보고서": {
        "문제 해결": ["추진배경", "현황", "문제점", "개선대책", "추진일정", "기대효과"],
        "위기 관리": ["현안문제", "현황분석", "위험요소", "대응방안", "이행계획", "기대효과"],
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

# 분량 규칙 - 실제 공무원 보고서 수준으로 상향
LENGTH_RULES = {
    "간략": {"items_per_section": "3~4", "detail_level": "핵심만 간략히"},
    "표준": {"items_per_section": "4~6", "detail_level": "구체적 내용 포함"},
    "상세": {"items_per_section": "6~8", "detail_level": "매우 상세하게, 수치와 근거 포함"},
}


# ===========================================
# 🎯 개선된 프롬프트 (핵심!)
# ===========================================
def build_prompt(title: str, report_type: str, detail_type: str, keywords: str, length_key: str) -> str:
    """실제 공무원 업무보고 스타일에 최적화된 프롬프트"""
    
    sections = REPORT_STRUCTURES[report_type][detail_type]
    rule = LENGTH_RULES[length_key]
    keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
    current_year = datetime.now().year
    
    return f"""당신은 대한민국 지방자치단체에서 15년간 근무한 7급 공무원입니다.
실제 업무에서 사용하는 수준의 보고서를 작성해주세요.

## 작성할 보고서 정보
- 제목: {title}
- 유형: {report_type} > {detail_type}
- 핵심 키워드: {', '.join(keyword_list)}
- 분량: {rule['items_per_section']}개 항목/섹션, {rule['detail_level']}

## 섹션 구성
{' → '.join(sections)}

## 필수 작성 규칙

### 1. 문체 규칙 (개괄식 종결어미)
모든 문장은 반드시 아래 형태로 끝나야 함:
- "~추진할 계획임", "~완료하였음", "~검토가 필요함"
- "~으로 판단됨", "~에 해당함", "~을 시행 중임"
- "~할 예정임", "~으로 분석됨", "~이 요구됨"

절대 금지: "~했습니다", "~합니다", "~했다", "~한다"

### 2. 내용 구체성 규칙
- 반드시 구체적 숫자 포함 (예: 50대, 3억원, 15개소)
- 구체적 일정 포함 (예: 2026. 3월, 상반기, 2분기)
- 구체적 장소/대상 포함 (예: ○○동 일원, 주요 교차로 15개소)
- 키워드 "{', '.join(keyword_list)}"를 반드시 내용에 자연스럽게 포함

### 3. 섹션별 분량 규칙
- 각 섹션당 {rule['items_per_section']}개 이상의 항목 작성
- 각 항목은 1~2문장으로 구성
- 섹션별로 내용이 중복되지 않도록 차별화

### 4. 섹션별 작성 가이드

#### 추진배경/현황
- 현재 상황의 문제점이나 필요성을 구체적 수치와 함께 기술
- 예: "관내 5대 범죄 발생건수가 전년 대비 12% 증가하여 대책 마련이 시급함"

#### 추진계획/사업내용
- 구체적으로 무엇을, 얼마나, 어디에 할 것인지 명시
- 예: "주요 범죄 취약지역 15개소에 고화질 CCTV 50대 신규 설치"

#### 추진일정
- 월별 또는 분기별 구체적 일정 제시
- 예: "설계용역: 2026. 1~2월 / 공사발주: 2026. 3월 / 설치완료: 2026. 6월"

#### 소요예산 (해당시)
- 총 예산과 세부 항목별 금액 제시
- 예: "총 3억원(장비구입 2억원, 설치공사 0.8억원, 통신비 0.2억원)"

#### 협조사항 (해당시)
- 관계기관별 협조 내용 구체화
- 예: "○○경찰서: CCTV 영상 연계 및 실시간 모니터링 협조"

#### 기대효과
- 정량적 목표와 정성적 효과 모두 포함
- 예: "5대 범죄 발생률 20% 감소 및 주민 체감안전도 향상"

### 5. 형식 규칙
- 마크다운, 이모지, 특수기호 사용 금지
- 번호 목록(1., 2.), 불릿(-, •, *) 사용 금지
- JSON 형식으로만 출력

## 출력 JSON 스키마

{{
  "title": "{title}",
  "type": "{report_type}",
  "detailType": "{detail_type}",
  "summary": "보고서 핵심 내용을 3~4문장으로 요약. 구체적 수치 포함. 개괄식 종결어미 사용.",
  "sections": [
    {{
      "title": "섹션명",
      "order": 1,
      "content": [
        "첫 번째 항목. 구체적 내용과 수치 포함. 개괄식 종결어미로 작성함",
        "두 번째 항목. 키워드를 자연스럽게 포함하여 작성함",
        "세 번째 항목. 일정이나 장소 등 구체적 정보 포함함",
        "네 번째 항목. 관련 현황이나 근거 제시함"
      ]
    }}
  ],
  "metadata": {{
    "generatedAt": "{datetime.now().isoformat()}",
    "totalSections": {len(sections)},
    "keywords": {json.dumps(keyword_list, ensure_ascii=False)}
  }}
}}

위 스키마를 정확히 따라 JSON만 출력하세요. 다른 설명 없이 JSON만 출력합니다.
"""


# ===========================================
# 🔧 후처리 함수
# ===========================================
TERM_CORRECTIONS = {
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
    "해야 합니다": "이 필요함",
    "해야 한다": "이 필요함",
}

BULLET_PATTERN = re.compile(r"^\s*([\-•\*\d]+[.)\]:]|\(?\d+\)|[가-힣][.)])\s*")
MARKDOWN_PATTERN = re.compile(r"\*\*(.*?)\*\*|\*(.*?)\*|`(.*?)`")


def add_number_commas(text: str) -> str:
    """숫자에 천단위 콤마 추가 (연도 제외)"""
    def replace_number(match):
        num = match.group(0)
        # 연도로 보이는 4자리 숫자는 제외 (19xx, 20xx)
        if len(num) == 4 and (num.startswith('19') or num.startswith('20')):
            return num
        # 그 외 큰 숫자는 콤마 추가
        if len(num) >= 4:
            return f"{int(num):,}"
        return num
    
    return re.sub(r'\b\d{4,}\b', replace_number, text)


def fix_ending(sentence: str) -> str:
    """문장 종결어미를 개괄식으로 변환"""
    sentence = sentence.strip()
    if not sentence:
        return sentence
    
    if sentence.endswith('.'):
        sentence = sentence[:-1]
    
    for wrong, correct in TERM_CORRECTIONS.items():
        if sentence.endswith(wrong):
            sentence = sentence[:-len(wrong)] + correct
            break
    
    return sentence


def clean_content(text: str) -> str:
    """콘텐츠 정리"""
    text = BULLET_PATTERN.sub("", text)
    text = MARKDOWN_PATTERN.sub(r"\1\2\3", text)
    text = re.sub(r'[^\w\s가-힣.,()%~\-:/·○△▷]', '', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = add_number_commas(text)
    
    return text.strip()


def postprocess_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """보고서 전체 후처리"""
    result = dict(data)
    
    if isinstance(result.get("summary"), str):
        summary = clean_content(result["summary"])
        sentences = re.split(r'(?<=[.。])\s*', summary)
        processed_sentences = [fix_ending(s) for s in sentences if s.strip()]
        result["summary"] = ' '.join(processed_sentences)
    
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
    
    if request.report_type not in REPORT_STRUCTURES:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 보고서 유형: {request.report_type}")
    
    if request.detail_type not in REPORT_STRUCTURES[request.report_type]:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 세부 유형: {request.detail_type}")
    
    if request.length not in LENGTH_RULES:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 분량 옵션: {request.length}")
    
    try:
        prompt = build_prompt(
            title=request.title,
            report_type=request.report_type,
            detail_type=request.detail_type,
            keywords=request.keywords,
            length_key=request.length
        )
        
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "당신은 대한민국 지방자치단체 공무원 업무보고서 작성 전문가입니다. 실제 업무에서 사용되는 수준의 구체적이고 상세한 보고서를 작성합니다. 반드시 JSON 형식으로만 응답하세요."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
            max_tokens=4000
        )
        
        raw_content = response.choices[0].message.content or ""
        data = json.loads(raw_content)
        
        data = postprocess_report(data)
        
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
        "version": "2.0.0",
        "supported_types": list(REPORT_STRUCTURES.keys())
    }