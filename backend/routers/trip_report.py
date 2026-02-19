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
    reporter_dept: str = Form(default=""),
    force_report_type: str = Form(default="")  # 재분석 시 강제 유형 지정
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
        
        # 강제 유형 지정 시 해당 유형으로 분석
        type_instruction = ""
        if force_report_type and force_report_type in REPORT_TYPES:
            type_instruction = f"""
## 중요: 보고서 유형 지정됨
사용자가 "{force_report_type}" 유형으로 지정했습니다.
반드시 이 유형에 맞는 관점으로 사진을 분석하고, 해당 유형의 필드를 추출해주세요.
report_type은 반드시 "{force_report_type}"으로 설정하세요.
"""
        
        # GPT Vision 분석 프롬프트 (대폭 개선)
        analysis_prompt = f"""당신은 공무원 현장 보고서 작성을 도와주는 AI 비서입니다.
업로드된 사진들을 분석하여 다음 정보를 JSON 형식으로 추출해주세요.
{type_instruction}
## 보고서 유형 판단 기준

1. **행사참석**: 설명회, 세미나, 회의, 축제, 행사
   - 현수막, 배너, 발표자, 청중, 무대, 좌석 배치가 보이면
   - 필드: 행사명, 일시, 장소, 주최, 참석인원

2. **출장방문**: 타 기관 방문, 벤치마킹, 업무협의
   - 회의실, 명패, 기관 로고, 방문객 출입증이 보이면
   - 필드: 방문목적, 일시, 방문기관, 면담자

3. **시설점검**: 도로, 건물, 시설물 점검
   - 포트홀, 균열, 공사현장, CCTV, 가로등, 시설물 파손이 보이면
   - 필드: 점검위치, 점검대상, 발견사항, 위험도

4. **민원현장**: 민원 확인, 불법행위, 현장 조치
   - 쓰레기, 불법주정차, 무단점거, 청소/수거 작업, 민원처리 현장이 보이면
   - 필드: 민원위치, 민원유형, 현장상황, 조치결과

5. **환경점검**: 환경 관련 점검
   - 하천, 대기, 소음 측정, 환경오염이 보이면
   - 필드: 점검위치, 점검항목, 측정결과, 적합여부

## 정보 추출 규칙 (중요!)

### 1. 현수막/배너 정보 정확히 매핑
- "일자: YYYY.MM.DD" 또는 "일시: ..." → extracted_info.일시에 정확히 입력
- "장소: OOO" → extracted_info.장소에 정확히 입력  
- "주최: OOO" 또는 로고 → extracted_info.주최에 정확히 입력
- 행사명/사업명 → extracted_info.행사명에 정확히 입력

### 2. 표/절차도/차트 내용 반드시 추출
- 단계별 절차가 보이면 main_content에 순서대로 기재
- 예: "1단계: 과제 공모 → 2단계: 제안서 제출 → 3단계: 선정평가..."
- 표의 주요 항목과 내용을 요약하여 추출

### 3. 위치 특정 최대한 노력
- 간판, 표지판, 버스정류장명, 건물명, 도로명 등에서 위치 추론
- "확인 필요" 대신 추정 위치라도 기재
- 예: "앙성면 버스정류장 인근", "OO동 관내 도로변"

### 4. 수치/정량 정보 정확히 추출
- 참석인원, 수거량, 면적, 개수 등 숫자 정보는 정확히 기재
- 추정치인 경우 "약 50명", "약 30kg" 등으로 표시

### 5. 사진별 핵심 요소 상세 분석
- 각 사진에서 보이는 텍스트는 모두 추출
- 작업 현장이면: 장비, 인원, 작업 내용 파악
- 시설물이면: 상태, 손상 정도, 위치 특징 파악

## 응답 형식 (JSON)

```json
{{
  "report_type": "행사참석|출장방문|시설점검|민원현장|환경점검 중 하나",
  "extracted_info": {{
    // 유형별 필드 (위 기준 참고)
  }},
  "main_content": [
    "사진에서 파악된 주요 내용 1",
    "사진에서 파악된 주요 내용 2",
    "표/절차도 내용이 있으면 여기에 포함",
    "수치 정보가 있으면 여기에 포함"
  ],
  "photos_analysis": [
    {{
      "photo_index": 1,
      "description": "사진에 대한 상세 설명",
      "detected_text": "인식된 모든 텍스트 (현수막, 간판, PPT, 표 등)",
      "key_elements": ["주요 요소1", "주요 요소2"]
    }}
  ],
  "confidence": 0.0~1.0
}}
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
            max_tokens=2500,
            temperature=0.2
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
        
        # 보고서 유형별 맞춤 프롬프트 (대폭 강화)
        type_specific_guide = {
            "행사참석": """
## 행사참석 보고서 특화 지침
- 행사에서 얻은 핵심 정보를 구체적으로 기술
- 발표자료/절차도에서 추출한 내용이 있으면 단계별로 정리
- 시사점: 우리 시 업무와 연결하여 구체적으로 작성
- 향후계획: "관련 부서 공유 예정", "사업 신청 검토 예정" 등 구체적 후속조치

예시 시사점:
- 타 지자체 AI 서비스 도입 사례 참고하여 우리 시 적용 방안 검토 필요
- 사업 공모 일정 확인, 관련 부서와 참여 여부 협의 필요

예시 향후계획:
- 사업 공모 시 참여 검토할 예정임
- 관련 내용 부서 내 공유 및 업무 참고자료로 활용할 계획임""",

            "출장방문": """
## 출장방문 보고서 특화 지침
- 방문 목적과 면담 내용을 구체적으로 기술
- 벤치마킹 사항은 우리 시 도입 가능성과 연결
- 시사점: 타 기관 우수사례, 도입 시 예상 효과 등
- 향후계획: "추가 협의 예정", "도입 방안 검토 예정" 등

예시 시사점:
- 해당 기관 시스템 도입 시 업무 효율 약 30% 향상 기대
- 우리 시 실정에 맞게 일부 기능 수정 적용 필요

예시 향후계획:
- 도입 관련 세부 사항 추가 협의할 예정임
- 예산 확보 방안 검토 후 내년도 사업계획 반영 검토할 계획임""",

            "시설점검": """
## 시설점검 보고서 특화 지침
- 점검 대상, 위치, 상태를 명확히 기술
- 문제점 발견 시 위험도와 긴급성 명시
- 시사점: 안전 문제, 추가 점검 필요사항 등
- 향후계획: 보수 일정, 예산 확보, 추가 점검 계획 등

예시 시사점:
- 시설물 노후로 인한 안전사고 우려, 조속한 보수 필요
- 유사 시설물 일제 점검 필요성 대두

예시 향후계획:
- 긴급 보수 작업 2주 내 완료 예정임
- 관련 예산 확보 후 전면 교체 추진할 계획임
- 유사 시설물 일제 점검 실시할 예정임""",

            "민원현장": """
## 민원현장 보고서 특화 지침
- 민원 내용, 현장 확인 결과, 조치 내용을 구체적으로 기술
- 조치 완료 시 "조치완료", 진행 중이면 "조치 중" 명시
- 수거량, 처리량 등 수치 정보가 있으면 정확히 기재
- 시사점: 민원 발생 원인, 재발 방지 방안 등
- 향후계획: 민원 회신, 추가 조치, 모니터링 계획 등

예시 시사점:
- 해당 지역 방치쓰레기 상습 투기 지역으로 확인됨
- 주기적 순찰 및 단속 강화 필요

예시 향후계획:
- 민원인에게 처리 결과 회신 완료함
- 해당 지역 주 1회 순찰 강화할 예정임
- CCTV 설치 검토할 계획임""",

            "환경점검": """
## 환경점검 보고서 특화 지침
- 점검 항목, 측정 결과, 기준치 대비 적합 여부 명시
- 수치 데이터는 정확히 기재 (단위 포함)
- 시사점: 환경 상태 평가, 개선 필요사항 등
- 향후계획: 지속 모니터링, 개선 조치 계획 등

예시 시사점:
- 측정 결과 기준치 이내로 양호한 상태 확인됨
- 일부 지점 기준치 근접, 지속 모니터링 필요

예시 향후계획:
- 월 1회 정기 측정 지속할 예정임
- 기준치 초과 시 즉시 개선 조치 추진할 계획임"""
        }
        
        # 보고서 생성 프롬프트 (공문서 문체 + 실무 반영)
        report_prompt = f"""당신은 충주시 공무원 보고서 작성 전문가입니다.
아래 정보를 바탕으로 '{type_info["template"]}'를 작성해주세요.

{type_specific_guide.get(report_type, "")}

## 입력 정보
{info_text}

## 현장에서 파악된 내용
{content_text}

## 보고자 정보
- 보고자: {request.reporter_dept} {request.reporter_name}
- 보고일: {datetime.datetime.now().strftime('%Y. %m. %d.')}

## 추가 요청사항
{request.additional_notes if request.additional_notes else "없음"}

## 공문서 문체 작성 규칙 (필수 준수)

### 1. 문장 종결 형태 (가장 중요!)
- 본문: "~임", "~함", "~됨", "~있음" (명사형 종결)
- 계획: "~할 예정임", "~추진할 계획임", "~검토 중임"
- 완료: "~완료함", "~조치함", "~확인함"
- 절대 금지: "~합니다", "~입니다", "~했습니다" (경어체 절대 사용 금지)

### 2. 항목 기술 방식
- 개조식 활용: "ㅇ", "-" 기호 사용
- 핵심 내용 먼저, 부연 설명은 하위 항목으로
- 수치/일정은 구체적으로 명시 (입력된 수치 그대로 활용)

### 3. 시사점/향후계획 작성 규칙
- 일반적이고 뻔한 내용 금지 (예: "문제 심각성 재확인", "필요성 인식")
- 구체적인 후속 조치, 일정, 담당 부서 등 명시
- 입력된 데이터(수치, 현황)를 활용하여 구체적으로 작성

### 4. 보고서 구조
```
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
   ㅇ 사진 1: (설명)
   ㅇ 사진 2: (설명)
   ※ 실제 사진은 별도 첨부

4. 시사점 및 향후 계획
   ㅇ 시사점
     - (구체적이고 실무적인 시사점)
   ㅇ 향후 계획
     - (구체적인 후속 조치) 예정임
     - (일정/담당 포함) 추진할 계획임
```

### 5. 좋은 예시 vs 나쁜 예시

시사점 작성:
❌ "방치쓰레기 문제 심각성 재확인"
✅ "연수동 일대 방치쓰레기 상습 투기 지역으로, 주기적 단속 강화 필요"

❌ "AI 기술 도입 필요성 인식"  
✅ "공공부문 AI 서비스 지원사업 활용 시 업무 효율화 가능, 신청 검토 필요"

향후계획 작성:
❌ "개선 방안 검토할 예정임"
✅ "3월 중 관련 부서 협의 후 사업 신청 여부 결정할 예정임"

❌ "추가 협의 추진할 계획임"
✅ "수거량 120kg 처리 완료, 해당 지역 주 1회 순찰 강화할 계획임"

위 규칙을 철저히 준수하여 실무에서 바로 사용 가능한 보고서를 작성해주세요."""

        # GPT 호출
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 대한민국 지방자치단체 공문서 작성 전문가입니다. 공문서 문체(명사형 종결, 개조식)를 철저히 준수합니다. '~합니다', '~입니다' 같은 경어체는 절대 사용하지 않습니다. 시사점과 향후계획은 구체적이고 실무적으로 작성합니다."},
                {"role": "user", "content": report_prompt}
            ],
            max_tokens=2500,
            temperature=0.3
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