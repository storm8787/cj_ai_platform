"""
공적조서 생성기 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from openai import OpenAI

from config import settings

router = APIRouter()


class MeritReportRequest(BaseModel):
    name: str
    position: str
    department: str
    start_date: str
    award_type: str
    achievement_area: str
    merit_points: List[str]


class MeritReportResponse(BaseModel):
    result: str
    generation_time: float


@router.post("/generate", response_model=MeritReportResponse)
async def generate_merit_report(request: MeritReportRequest):
    """
    공적조서 생성
    """
    import time
    start_time = time.time()
    
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # 공적요지 포맷팅
    merit_str = "\n".join([f"{i+1}. {point}" for i, point in enumerate(request.merit_points)])
    
    prompt = f"""당신은 충주시의 공무원 공적조서를 작성하는 행정 전문가입니다.

아래 입력 정보를 바탕으로, 포상 대상 공무원의 공적조서를 다음 조건에 맞게 작성해주세요.

[기본 정보]
- 소속: {request.department}
- 직급: {request.position}
- 성명: {request.name}
- 임용일: {request.start_date}
- 표창 종류: {request.award_type}
- 공적 분야: {request.achievement_area}

- 공적요지 목록:
{merit_str}

[작성 조건]

1. 공적조서의 시작은 다음과 같이 구성합니다:
- 소속 : {request.department}
- 직급 : {request.position}
- 성명 : {request.name}

2. 도입부(서론)는 다음 기준에 따라 작성합니다:
- 첫 문장은 반드시 아래 형식을 따릅니다:
  "위 공무원은 {request.start_date} 임용된 이래로"  
- 서론에서는 "위 공무원은"이라는 표현만 사용하며, 성명, 직급은 사용하지 않습니다.
- 공직자로서의 태도, 책임감, 전문성, 해당 분야에서의 헌신을 통합적으로 서술하십시오.
- 서론 마지막 문장은 반드시 아래 형식을 따릅니다:
  "{request.achievement_area} 발전에 지대한 공로가 인정되는 바, 그 공적을 나열하면 다음과 같습니다."

3. 본문은 각 공적요지 항목별로 다음 기준에 따라 작성합니다:
- 각 항목마다 제목과 함께 두 개의 소챕터로 나누어 작성하십시오.
- 각 소챕터는 **최소 6문장 이상**으로 풍부하고 구체적으로 작성하십시오.
- 첫 번째 문단은 해당 공적요지를 기반으로 일반적인 성과, 의미, 효과를 중심으로 서술하십시오.
- 두 번째 문단은 괄호로 제시된 구체 사례가 있는 경우, 해당 사례를 중심으로 실천 내용, 추진 배경, 실행 방식, 구체적인 성과 등을 상세하게 서술하십시오.
- 본문에서는 "위 공무원"이라는 표현을 사용하지 마십시오.
- 성명과 직급은 본문 전체에서 절대 사용하지 않습니다.

4. 본문 마지막에는 아래 고정 챕터를 반드시 삽입하십시오:
- 제목: 공사생활에서 항상 남을 배려하는 모범 공직자
- 내용: 위 공무원은 평소 동료와 시민을 배려하는 따뜻한 성품을 바탕으로 직무를 수행해왔으며, 상사에게는 신뢰받는 직원으로, 동료에게는 친근한 동료로서 공직사회의 귀감이 되고 있습니다.

5. 마지막 문단은 다음 형식을 따르십시오:
"위와 같은 공로를 세운 상기인은 올바른 공직자상을 정립하고, 맡은 바 직분에 끊임없는 노력과 연구를 아끼지 않으며, 묵묵히 소신과 열정으로 {request.achievement_area} 업무를 추진해 온 바, {request.award_type}에 추천하고자 합니다."

[기타 작성 지침]
- 모든 문장은 과거형 서술체(예: ~하였습니다, ~기여하였습니다)로 작성하십시오.
- 문장은 간결하면서도 구체적이고 사실 중심이어야 합니다.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=3000
        )
        
        result = response.choices[0].message.content
        generation_time = round(time.time() - start_time, 2)
        
        return MeritReportResponse(
            result=result,
            generation_time=generation_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공적조서 생성 실패: {str(e)}")
