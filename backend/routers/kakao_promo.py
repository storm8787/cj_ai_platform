"""
카카오채널 홍보문구 생성기 API
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI

from config import settings
from services.prompt_service import prompt_service

router = APIRouter()

# OpenAI 클라이언트
client = OpenAI(api_key=settings.OPENAI_API_KEY)


# ===== 프롬프트 기본값 (DB에 없을 때 사용) =====
_DEFAULT_TEMPLATES = {
    "시정홍보": """당신은 충주시청 홍보 담당자입니다.
아래 내용을 바탕으로 카카오톡 채널용 홍보 메시지를 작성해주세요.

[작성 규칙]
- 첫 줄: 눈에 띄는 이모지 + 핵심 제목 (15자 이내)
- 본문: 핵심 내용 요약 (3~4줄)
- 마지막: 참여/문의 안내 또는 해시태그

[톤앤매너]
- 친근하고 따뜻한 말투
- 시민 눈높이에 맞춘 쉬운 설명
- 충주시민에게 도움이 되는 정보 강조

[원본 내용]
{content}

위 내용으로 카카오톡 채널 홍보 메시지를 작성해주세요.""",

    "정책공지": """당신은 충주시청 정책홍보 담당자입니다.
아래 정책/공지 내용을 카카오톡 채널용 메시지로 변환해주세요.

[작성 규칙]
- 첫 줄: 📢 또는 관련 이모지 + 핵심 제목
- 대상/기간/신청방법 등 핵심정보 명확히
- 문의처 안내 포함

[톤앤매너]
- 공식적이되 딱딱하지 않게
- 핵심 정보를 빠뜨리지 않도록

[원본 내용]
{content}

위 내용으로 정책 공지 메시지를 작성해주세요.""",

    "문화행사": """당신은 충주시 문화관광 홍보 담당자입니다.
아래 행사 정보를 매력적인 카카오톡 채널 메시지로 작성해주세요.

[작성 규칙]
- 첫 줄: 🎉 또는 행사 관련 이모지 + 제목
- 일시/장소/참가비 등 핵심정보
- 참여 방법 및 문의처

[톤앤매너]
- 설레고 기대되는 분위기
- 참여 욕구를 자극하는 문구

[원본 내용]
{content}

위 내용으로 문화행사 홍보 메시지를 작성해주세요.""",

    "축제": """당신은 충주시 축제 홍보 담당자입니다.
아래 축제 정보를 열정적인 카카오톡 채널 메시지로 작성해주세요.

[작성 규칙]
- 첫 줄: 🎊 또는 축제 관련 이모지 + 축제명
- 기간/장소/주요 프로그램
- 참여 안내 및 해시태그

[톤앤매너]
- 축제의 즐거움과 설렘 전달
- 충주만의 특색 강조

[원본 내용]
{content}

위 내용으로 축제 홍보 메시지를 작성해주세요.""",

    "이벤트": """당신은 충주시 SNS 이벤트 담당자입니다.
아래 이벤트 내용을 참여를 유도하는 카카오톡 채널 메시지로 작성해주세요.

[작성 규칙]
- 첫 줄: 🎁 또는 이벤트 관련 이모지 + 제목
- 참여방법 간단명료하게
- 경품/혜택 명확히 안내
- 기간 강조

[톤앤매너]
- 참여하고 싶게 만드는 매력적인 문구
- 쉽고 간단하다는 느낌

[원본 내용]
{content}

위 내용으로 이벤트 홍보 메시지를 작성해주세요.""",

    "재난알림": """당신은 충주시 재난안전 담당자입니다.
아래 재난/안전 정보를 긴급한 카카오톡 채널 메시지로 작성해주세요.

[작성 규칙]
- 첫 줄: ⚠️ 또는 🚨 + 긴급/주의 제목
- 핵심 주의사항 명확히
- 행동요령 간단히
- 문의처/신고처 안내

[톤앤매너]
- 긴급하고 진지한 톤
- 불필요한 수식어 없이 명확하게

[원본 내용]
{content}

위 내용으로 재난알림 메시지를 작성해주세요.""",

    "기타": """당신은 충주시청 홍보 담당자입니다.
아래 내용을 카카오톡 채널용 홍보 메시지로 작성해주세요.

[작성 규칙]
- 첫 줄: 적절한 이모지 + 핵심 제목
- 본문: 핵심 내용 3~4줄
- 마지막: 안내 또는 해시태그

[톤앤매너]
- 친근하고 읽기 쉽게
- 충주시민 눈높이에 맞춰

[원본 내용]
{content}

위 내용으로 홍보 메시지를 작성해주세요."""
}


def _get_promo_template(category: str) -> str:
    """카테고리별 프롬프트 가져오기 (DB 우선, 없으면 기본값)"""
    return prompt_service.get(
        "kakao_promo", category,
        default=_DEFAULT_TEMPLATES.get(category, _DEFAULT_TEMPLATES["기타"])
    )


class PromoRequest(BaseModel):
    category: str
    content: str


class PromoResponse(BaseModel):
    result: str
    category: str


@router.get("/categories")
async def get_categories():
    """카테고리 목록 조회"""
    return {
        "categories": [
            {"value": "시정홍보", "label": "🏛️ 시정홍보"},
            {"value": "정책공지", "label": "📢 정책공지"},
            {"value": "문화행사", "label": "🎭 문화행사"},
            {"value": "축제", "label": "🎊 축제"},
            {"value": "이벤트", "label": "🎁 이벤트"},
            {"value": "재난알림", "label": "⚠️ 재난알림"},
            {"value": "기타", "label": "📝 기타"},
        ]
    }


@router.post("/generate", response_model=PromoResponse)
async def generate_promo(request: PromoRequest):
    """홍보문구 생성"""
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="내용을 입력해주세요.")
    
    if request.category not in _DEFAULT_TEMPLATES:
        raise HTTPException(status_code=400, detail="잘못된 카테고리입니다.")
    
    try:
        prompt_template = _get_promo_template(request.category)
        prompt = prompt_template.format(content=request.content)
        
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        
        result = completion.choices[0].message.content
        
        return PromoResponse(
            result=result,
            category=request.category
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"생성 실패: {str(e)}")


@router.post("/generate-with-image")
async def generate_promo_with_image(
    category: str = Form(...),
    content: str = Form(default=""),
    image: UploadFile = File(default=None)
):
    """이미지 OCR + 텍스트로 홍보문구 생성"""
    final_content = content or ""
    
    # 이미지가 있으면 OCR 처리 (GPT-4 Vision 사용)
    if image:
        try:
            import base64
            image_bytes = await image.read()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # 이미지 MIME 타입 확인
            content_type = image.content_type or "image/jpeg"
            
            # GPT-4 Vision으로 이미지 텍스트 추출
            ocr_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "이 이미지에서 모든 텍스트를 추출해주세요. 텍스트만 출력하고 다른 설명은 하지 마세요."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{content_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            ocr_text = ocr_response.choices[0].message.content
            final_content = ocr_text + "\n" + final_content
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"이미지 처리 실패: {str(e)}")
    
    if not final_content.strip():
        raise HTTPException(status_code=400, detail="텍스트 또는 이미지를 입력해주세요.")
    
    # 홍보문구 생성
    try:
        prompt_template = _get_promo_template(category)
        prompt = prompt_template.format(content=final_content)
        
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        
        result = completion.choices[0].message.content
        
        return {
            "result": result,
            "category": category,
            "extracted_text": final_content if image else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"생성 실패: {str(e)}")