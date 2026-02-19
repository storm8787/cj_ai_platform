"""출장보고 생성기 API - GPT Vision 활용"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
import datetime
import base64
import time
import io
import os
from openai import OpenAI

router = APIRouter()

# OpenAI 클라이언트
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class AnalysisResult(BaseModel):
    """AI 분석 결과"""
    report_type: str  # 행사참석, 출장방문, 시설점검, 민원현장, 환경점검
    report_type_icon: str
    extracted_info: dict
    main_content: List[str]
    photos_analysis: List[dict]
    confidence: float


class ReportGenerateRequest(BaseModel):
    """보고서 생성 요청"""
    report_type: str
    extracted_info: dict
    main_content: List[str]
    reporter_name: str
    reporter_dept: str
    additional_notes: str = ""


class ReportResponse(BaseModel):
    """보고서 생성 응답"""
    report_text: str
    generation_time: float


# 보고서 유형별 설정
REPORT_TYPES = {
    "행사참석": {
        "icon": "🎤",
        "fields": ["행사명", "일시", "장소", "주최", "참석인원"],
        "template": "행사 참석 보고"
    },
    "출장방문": {
        "icon": "🏢",
        "fields": ["방문목적", "일시", "방문기관", "면담자"],
        "template": "출장 결과 보고"
    },
    "시설점검": {
        "icon": "🏗️",
        "fields": ["점검위치", "점검대상", "발견사항", "위험도"],
        "template": "현장 점검 보고"
    },
    "민원현장": {
        "icon": "🚨",
        "fields": ["민원위치", "민원내용", "현장상황", "조치계획"],
        "template": "민원 현장 확인 보고"
    },
    "환경점검": {
        "icon": "🌳",
        "fields": ["점검위치", "점검항목", "측정결과", "적합여부"],
        "template": "환경 점검 보고"
    }
}


def encode_image_to_base64(image_bytes: bytes) -> str:
    """이미지를 base64로 인코딩"""
    return base64.b64encode(image_bytes).decode('utf-8')


def get_image_media_type(filename: str) -> str:
    """파일 확장자로 미디어 타입 결정"""
    ext = filename.lower().split('.')[-1]
    media_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }
    return media_types.get(ext, 'image/jpeg')


@router.post("/analyze-images")
async def analyze_images(
    images: List[UploadFile] = File(...),
    reporter_name: str = Form(default=""),
    reporter_dept: str = Form(default="")
):
    """이미지 분석 - GPT Vision 사용"""
    start_time = time.time()
    
    if not images:
        raise HTTPException(status_code=400, detail="이미지를 업로드해주세요.")
    
    if len(images) > 10:
        raise HTTPException(status_code=400, detail="이미지는 최대 10장까지 가능합니다.")
    
    try:
        # 이미지들을 base64로 변환
        image_contents = []
        for i, image in enumerate(images):
            image_bytes = await image.read()
            base64_image = encode_image_to_base64(image_bytes)
            media_type = get_image_media_type(image.filename)
            
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{base64_image}",
                    "detail": "high"  # 고해상도 분석
                }
            })
        
        # GPT Vision 분석 프롬프트
        analysis_prompt = """당신은 공무원 현장 보고서 작성을 도와주는 AI 비서입니다.
업로드된 사진들을 분석하여 다음 정보를 JSON 형식으로 추출해주세요.

## 분석 항목

1. **report_type**: 사진 내용을 보고 가장 적합한 보고서 유형을 판단
   - "행사참석": 설명회, 세미나, 회의, 축제, 행사 등 (현수막, 발표자, 청중이 보이면)
   - "출장방문": 타 기관 방문, 벤치마킹, 업무협의 (회의실, 명패, 기관 로고 등)
   - "시설점검": 도로, 건물, 시설물 점검 (포트홀, 균열, 공사현장 등)
   - "민원현장": 민원 확인, 불법행위 (쓰레기, 불법주정차, 무단점거 등)
   - "환경점검": 환경 관련 점검 (하천, 대기, 소음 측정 등)

2. **extracted_info**: 보고서 유형에 맞는 정보 추출
   - 행사참석: 행사명(현수막에서), 장소(실내/실외, 규모), 참석인원(추정), 주최기관(로고에서)
   - 출장방문: 방문기관(간판/로고에서), 장소 특징
   - 시설점검: 위치(간판/표지판에서), 문제유형, 규모/크기 추정, 위험도
   - 민원현장: 위치, 민원유형, 현장상황
   - 환경점검: 위치, 점검대상

3. **main_content**: 사진에서 파악된 주요 내용 (리스트, 최대 5개)
   - PPT/발표자료가 보이면 내용 추출
   - 현수막/배너 텍스트 추출
   - 현장 상황 설명

4. **photos_analysis**: 각 사진별 분석 결과
   - photo_index: 사진 번호 (1부터)
   - description: 사진 설명
   - detected_text: 인식된 텍스트 (현수막, 간판, PPT 등)
   - key_elements: 주요 요소들

5. **confidence**: 분석 신뢰도 (0.0 ~ 1.0)

## 응답 형식 (JSON)
```json
{
  "report_type": "행사참석",
  "extracted_info": {
    "행사명": "2026 청년창업 지원사업 설명회",
    "일시": "확인 필요",
    "장소": "대회의실 (약 100석 규모)",
    "주최": "충청북도",
    "참석인원": "약 50명"
  },
  "main_content": [
    "청년창업 지원금 최대 3천만원",
    "신청기간 3월~4월",
    "...추출된 내용..."
  ],
  "photos_analysis": [
    {
      "photo_index": 1,
      "description": "행사장 전경, 발표자가 단상에서 발표 중",
      "detected_text": "2026 청년창업 지원사업 설명회",
      "key_elements": ["현수막", "발표자", "청중 약 50명"]
    }
  ],
  "confidence": 0.85
}
```

반드시 위 JSON 형식으로만 응답해주세요. 다른 설명은 붙이지 마세요."""

        # GPT-4o Vision 호출
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": analysis_prompt},
                    *image_contents
                ]
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=2000,
            temperature=0.3
        )
        
        # 응답 파싱
        result_text = response.choices[0].message.content
        
        # JSON 추출 (```json ... ``` 제거)
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        import json
        analysis_result = json.loads(result_text.strip())
        
        # 아이콘 추가
        report_type = analysis_result.get("report_type", "행사참석")
        analysis_result["report_type_icon"] = REPORT_TYPES.get(report_type, {}).get("icon", "📄")
        
        # 분석 시간
        analysis_time = round(time.time() - start_time, 2)
        
        return {
            "success": True,
            "analysis": analysis_result,
            "analysis_time": analysis_time,
            "image_count": len(images)
        }
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI 응답 파싱 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 분석 실패: {str(e)}")


@router.post("/generate-report")
async def generate_report(request: ReportGenerateRequest):
    """분석 결과로 보고서 생성"""
    start_time = time.time()
    
    try:
        report_type = request.report_type
        type_info = REPORT_TYPES.get(report_type, REPORT_TYPES["행사참석"])
        
        # 추출된 정보를 텍스트로 변환
        info_text = "\n".join([f"- {k}: {v}" for k, v in request.extracted_info.items() if v])
        content_text = "\n".join([f"- {item}" for item in request.main_content if item])
        
        # 보고서 생성 프롬프트
        report_prompt = f"""당신은 공무원 보고서 작성 전문가입니다.
아래 정보를 바탕으로 '{type_info["template"]}'를 작성해주세요.

## 기본 정보
{info_text}

## 주요 내용
{content_text}

## 보고자 정보
- 보고자: {request.reporter_dept} {request.reporter_name}
- 보고일: {datetime.datetime.now().strftime('%Y. %m. %d.')}

## 추가 요청사항
{request.additional_notes if request.additional_notes else "없음"}

## 작성 지침
1. 공문서 형식으로 작성 (간접화법: ~했다, ~이다, ~라고 밝혔다)
2. 구조: 개요 → 주요내용 → 시사점/향후계획
3. 간결하고 명확하게 작성
4. 아래 형식을 따를 것

---

{type_info["template"]}

1. 개요
   • 일시: 
   • 장소: 
   • 참석자/점검자: 

2. 주요 내용
   (내용 작성)

3. 현장 사진
   (사진 설명 - 실제 사진은 별도 첨부)

4. 시사점 및 향후 계획
   (내용 작성)

---

위 형식으로 보고서를 완성해주세요."""

        # GPT 호출
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 공무원 보고서 작성 전문가입니다. 간결하고 공식적인 문체로 작성합니다."},
                {"role": "user", "content": report_prompt}
            ],
            max_tokens=2000,
            temperature=0.5
        )
        
        report_text = response.choices[0].message.content
        generation_time = round(time.time() - start_time, 2)
        
        return ReportResponse(
            report_text=report_text,
            generation_time=generation_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 생성 실패: {str(e)}")


@router.get("/report-types")
async def get_report_types():
    """보고서 유형 목록 조회"""
    return {
        "types": [
            {"id": key, "name": key, "icon": val["icon"], "fields": val["fields"]}
            for key, val in REPORT_TYPES.items()
        ]
    }