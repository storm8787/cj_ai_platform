"""
업무보고 생성기 API - 공무원 행정문서 스타일
섹션별 특성에 맞는 차별화된 프롬프트 적용
DB 프롬프트 우선 + 하드코딩 fallback 유지
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import re
from datetime import datetime

from config import settings
from services.prompt_service import prompt_service

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

LENGTH_RULES = {
    "간략": {"items_per_section": "3~4", "detail_level": "핵심만 간략히"},
    "표준": {"items_per_section": "4~6", "detail_level": "구체적 내용 포함"},
    "상세": {"items_per_section": "6~8", "detail_level": "매우 상세하게"},
}


# ===========================================
# 🎯 섹션별 작성 스타일 정의 (핵심!)
# ===========================================
SECTION_STYLES = {
    "추진배경": {
        "style": "서술형",
        "guide": "왜 이 사업/정책이 필요한지 배경과 필요성을 구체적 수치와 함께 2~3문장으로 상세히 기술",
        "example": "관내 5대 범죄 발생건수가 전년 대비 12% 증가(2024년 1,234건 → 2025년 1,382건)하여 주민 안전 강화를 위한 대책 마련이 시급한 실정임. 특히 야간 시간대 이면도로에서의 범죄 발생률이 높아 CCTV 사각지대 해소가 필요함"
    },
    "현황": {
        "style": "서술형",
        "guide": "현재 상황을 구체적 수치와 함께 객관적으로 기술. 문제점이나 부족한 점도 함께 언급",
        "example": "현재 관내 방범용 CCTV는 총 856대가 운영 중이며, 이 중 5년 이상 노후 장비가 274대(32%)로 화질 저하 및 야간 식별 어려움이 발생하고 있음. CCTV 사각지대는 이면도로 23개소, 공원 주변 15개소 등 총 38개소로 파악됨"
    },
    "현황분석": {
        "style": "서술형",
        "guide": "현재 상황을 분석하여 문제점과 원인을 구체적으로 기술",
        "example": "현재 관내 방범 인프라 현황을 분석한 결과, CCTV 밀도가 인구 1,000명당 3.2대로 도내 평균(4.5대) 대비 낮은 수준임. 특히 신규 택지개발지구의 경우 입주 후 2년이 경과하였으나 방범시설 설치가 미비한 상황임"
    },
    "문제점": {
        "style": "서술형",
        "guide": "현재 발생하고 있는 문제점을 구체적 사례와 수치로 기술",
        "example": "첫째, 노후 CCTV 장비의 해상도 저하로 범인 식별이 어려워 검거율이 하락(전년 대비 8%p 감소)하고 있음. 둘째, 야간 조명 부족 지역에서 촬영된 영상의 활용도가 현저히 낮음"
    },
    "사업개요": {
        "style": "서술형",
        "guide": "사업의 전체적인 개요를 목적, 대상, 규모 등을 포함하여 기술",
        "example": "본 사업은 시민 안전 강화를 위해 범죄 취약지역에 고화질 CCTV를 신규 설치하는 사업으로, 총 사업비 3억원을 투입하여 15개 지점에 50대의 CCTV를 설치할 계획임"
    },
    "현안문제": {
        "style": "서술형",
        "guide": "현재 당면한 문제 상황을 긴급성과 심각성 중심으로 기술",
        "example": "최근 관내 ○○동 일원에서 연속 절도사건이 발생(1주일간 5건)하여 주민 불안이 가중되고 있으며, 해당 지역은 CCTV 미설치 구간으로 범인 검거에 어려움을 겪고 있음"
    },
    "상황개요": {
        "style": "서술형",
        "guide": "발생한 상황의 전체적인 개요를 육하원칙에 따라 기술",
        "example": "2026. 1. 15.(월) 14:30경 ○○동 주민센터 앞 도로에서 차량 2대 추돌사고가 발생하였으며, 인명피해는 없으나 차량 파손 및 교통 정체가 발생함"
    },
    "사건개요": {
        "style": "서술형",
        "guide": "사건의 경위를 시간 순서대로 구체적으로 기술",
        "example": "2026. 1. 15.(월) 14:30경 ○○교차로에서 신호위반 차량이 횡단보도를 건너던 보행자를 충격하는 사고가 발생함. 피해자는 인근 병원으로 이송되어 치료 중이며 생명에는 지장이 없는 것으로 확인됨"
    },
    "추진일정": {
        "style": "나열형",
        "guide": "시기:내용 형태로 간결하게 나열. 문장형 종결어미 사용 금지",
        "example": "실시설계: 2026. 1~2월 / 공사발주: 2026. 3월 / 설치공사: 2026. 4~5월 / 준공: 2026. 6월"
    },
    "소요예산": {
        "style": "나열형",
        "guide": "항목:금액 형태로 간결하게 나열. 총액을 먼저 제시하고 세부내역 기술",
        "example": "총 사업비: 3억원 / 장비구입비: 2억원(CCTV 50대, 저장장치 등) / 설치공사비: 0.8억원 / 통신비: 0.2억원(연간)"
    },
    "협조사항": {
        "style": "나열형",
        "guide": "기관명:협조내용 형태로 간결하게 나열",
        "example": "○○경찰서: CCTV 영상 연계 및 실시간 모니터링 / 한국전력: 전용 전력 인입 협조 / 통신사: 전용회선 설치"
    },
    "추진경과": {
        "style": "나열형",
        "guide": "시기:추진내용 형태로 시간순 나열",
        "example": "2025. 6월: 사업계획 수립 / 2025. 9월: 실시설계 완료 / 2025. 11월: 공사 착공 / 2026. 1월: 공정률 60% 진행 중"
    },
    "향후일정": {
        "style": "나열형",
        "guide": "시기:예정내용 형태로 간결하게 나열",
        "example": "2026. 2월: 시설물 설치 완료 / 2026. 3월: 시운전 및 검수 / 2026. 4월: 정식 운영 개시"
    },
    "보고일시": {
        "style": "나열형",
        "guide": "날짜, 시간, 보고자 등을 간결하게 기술",
        "example": "보고일시: 2026. 1. 27.(월) 14:00 / 보고자: ○○과 ○○○ / 보고대상: 시장"
    },
    "발생일시": {
        "style": "나열형",
        "guide": "발생 일시와 장소를 간결하게 기술",
        "example": "발생일시: 2026. 1. 15.(월) 14:30경 / 발생장소: ○○동 ○○로 123 앞 교차로"
    },
    "참석자": {
        "style": "나열형",
        "guide": "소속:직급 성명 형태로 나열",
        "example": "○○과: 과장 ○○○, 담당 ○○○ / ○○경찰서: 경위 ○○○ / ○○업체: 대표 ○○○"
    },
    "회의일시": {
        "style": "나열형",
        "guide": "일시, 장소, 참석인원 등을 간결하게 기술",
        "example": "일시: 2026. 1. 20.(월) 10:00~12:00 / 장소: 시청 3층 대회의실 / 참석: 15명"
    },
    "기대효과": {
        "style": "효과형",
        "guide": "정량적 목표(수치)와 정성적 효과를 모두 포함하여 2~3문장으로 기술",
        "example": "CCTV 설치 완료 시 관내 5대 범죄 발생률 20% 감소 및 범인 검거율 15%p 향상이 예상됨. 또한 실시간 모니터링 체계 구축으로 긴급상황 대응시간이 단축되어 시민 체감안전도가 크게 향상될 것으로 기대됨"
    },
    "추진목표": {
        "style": "효과형",
        "guide": "달성하고자 하는 목표를 정량적 수치와 함께 기술",
        "example": "2026년 말까지 관내 CCTV 사각지대 38개소 중 30개소(79%)를 해소하고, 노후 CCTV 274대 중 150대를 고화질 장비로 교체하여 영상 활용률을 현재 65%에서 90%까지 향상시킬 계획임"
    },
    "개선목표": {
        "style": "효과형",
        "guide": "개선을 통해 달성하고자 하는 목표를 구체적으로 기술",
        "example": "노후 장비 교체 및 신규 설치를 통해 CCTV 영상품질을 HD급 이상으로 향상시키고, 야간 식별률을 현재 40%에서 85%까지 개선하여 범죄 예방 및 검거 효율성을 높이고자 함"
    },
    "추진계획": {
        "style": "방안형",
        "guide": "무엇을, 어디에, 얼마나 할 것인지 구체적으로 기술",
        "example": "범죄 취약지역 15개소에 고화질(200만 화소 이상) CCTV 50대를 신규 설치하고, 경찰서 관제센터와 실시간 영상 연계 시스템을 구축할 계획임. 설치 대상지는 주민 의견수렴 및 경찰서 협의를 거쳐 우선순위를 선정함"
    },
    "세부내용": {
        "style": "방안형",
        "guide": "추진계획의 세부 실행방안을 구체적으로 기술",
        "example": "CCTV 사양은 200만 화소 이상, 야간 적외선 기능, 360도 회전형으로 선정하고, 저장장치는 30일 이상 영상 보관이 가능한 4TB 이상 규격을 적용함. 설치 지점별로 전력 및 통신 인프라를 사전 점검하여 추가 공사 여부를 확인함"
    },
    "세부추진계획": {
        "style": "방안형",
        "guide": "단계별, 분야별 세부 추진방안을 구체적으로 기술",
        "example": "1단계(1~3월): 설계용역 및 대상지 확정, 2단계(4~5월): 장비 구매 및 설치공사, 3단계(6월): 시운전 및 경찰서 연계. 설치 완료 후 1개월간 시범운영을 통해 문제점을 보완한 뒤 정식 운영을 개시함"
    },
    "개선대책": {
        "style": "방안형",
        "guide": "문제 해결을 위한 구체적 대책을 기술",
        "example": "노후 CCTV 교체 사업을 연차별로 추진하여 2028년까지 전체 장비의 HD급 전환을 완료하고, 야간 취약지역에는 보안등과 CCTV를 연계 설치하여 야간 식별률을 개선함"
    },
    "대응방안": {
        "style": "방안형",
        "guide": "위험요소나 문제에 대한 대응방안을 구체적으로 기술",
        "example": "긴급 상황 발생 시 통합관제센터에서 경찰서로 즉시 영상을 전송하고, 현장 출동 경찰관에게 실시간 위치정보를 제공하는 체계를 구축함. 장비 고장 시 24시간 내 A/S가 가능하도록 유지보수 계약을 체결함"
    },
    "개선방안": {
        "style": "방안형",
        "guide": "현재 문제점을 개선하기 위한 구체적 방안 기술",
        "example": "영상 화질 개선을 위해 기존 SD급 장비를 순차적으로 HD급으로 교체하고, 야간 촬영 품질 향상을 위해 적외선 조명장치를 추가 설치함. 또한 AI 영상분석 기능을 도입하여 이상행동 자동 감지 체계를 구축함"
    },
    "조치사항": {
        "style": "방안형",
        "guide": "이미 취한 조치 또는 취할 조치를 구체적으로 기술",
        "example": "사고 발생 즉시 현장에 담당 직원을 파견하여 상황을 파악하고, 피해자 지원 및 2차 사고 예방을 위한 안전조치를 시행함. 관계기관(경찰서, 소방서)에 상황을 통보하고 공동 대응 체계를 가동함"
    },
    "후속대책": {
        "style": "방안형",
        "guide": "향후 취할 후속 조치를 구체적으로 기술",
        "example": "유사 사고 재발 방지를 위해 해당 구간에 과속방지턱 및 보행자 안전시설을 추가 설치하고, 사고다발지점 안내표지를 설치하여 운전자 주의를 환기시킬 계획임"
    },
    "현상진단": {
        "style": "분석형",
        "guide": "현재 상황을 객관적으로 진단하고 분석 결과를 기술",
        "example": "관내 방범 인프라 현황을 진단한 결과, CCTV 설치 밀도는 도내 평균 대비 28% 낮고, 특히 신규 개발지역의 방범시설 설치율이 42%에 불과한 것으로 나타남"
    },
    "문제분석": {
        "style": "분석형",
        "guide": "문제의 원인을 분석하여 구체적으로 기술",
        "example": "범죄 발생률 증가의 주요 원인을 분석한 결과, 첫째 CCTV 사각지대 증가, 둘째 야간 조명 부족, 셋째 순찰 인력 부족 순으로 파악됨. 특히 신규 택지지구의 경우 입주 후 방범시설 설치가 지연되어 범죄 취약성이 높아진 것으로 분석됨"
    },
    "위험요소": {
        "style": "분석형",
        "guide": "잠재적 위험요소를 식별하고 분석 결과를 기술",
        "example": "사업 추진 시 예상되는 위험요소로는 첫째 예산 확보 지연(가능성 30%), 둘째 민원 발생(설치 반대), 셋째 공사 지연(동절기 작업 제한) 등이 있으며, 각 위험요소별 대응방안을 사전에 마련할 필요가 있음"
    },
    "분석결과": {
        "style": "분석형",
        "guide": "데이터 분석 결과를 객관적 수치와 함께 기술",
        "example": "최근 3년간 범죄 발생 데이터를 분석한 결과, CCTV 설치 지역의 범죄 발생률이 미설치 지역 대비 평균 35% 낮은 것으로 나타났으며, 특히 야간 시간대(22시~06시) 효과가 더욱 뚜렷함(42% 감소)"
    },
    "시사점": {
        "style": "분석형",
        "guide": "분석 결과에서 도출된 시사점을 기술",
        "example": "이번 분석을 통해 CCTV 설치의 범죄 예방 효과가 실증적으로 확인되었으며, 특히 야간 취약지역에 대한 우선 설치가 효과적임을 알 수 있음. 향후 CCTV 설치 계획 수립 시 범죄 발생 빈도와 시간대를 고려한 전략적 배치가 필요함"
    },
    "주요동향": {
        "style": "분석형",
        "guide": "관련 분야의 최신 동향을 객관적으로 기술",
        "example": "최근 스마트시티 추진에 따라 전국 지자체에서 AI 기반 영상분석 CCTV 도입이 확대되고 있으며, 행안부에서도 2026년까지 전국 통합관제센터의 AI 전환을 권고하고 있음"
    },
    "영향분석": {
        "style": "분석형",
        "guide": "정책이나 사업이 미치는 영향을 분석하여 기술",
        "example": "CCTV 추가 설치 시 예상되는 영향을 분석한 결과, 긍정적 측면으로는 범죄 예방 효과 및 주민 안심 효과가 있으며, 부정적 측면으로는 사생활 침해 우려 및 유지관리 비용 증가가 예상됨"
    },
    "추진전략": {
        "style": "방안형",
        "guide": "목표 달성을 위한 전략적 접근방법을 기술",
        "example": "3대 추진전략으로 첫째 범죄 취약지역 우선 설치, 둘째 경찰서 연계 실시간 모니터링 체계 구축, 셋째 AI 영상분석 기술 단계적 도입을 설정하고, 이를 중심으로 사업을 추진함"
    },
    "진행현황": {
        "style": "서술형",
        "guide": "현재 진행 상황을 구체적 수치와 함께 기술",
        "example": "현재 전체 사업의 60%가 완료된 상태로, 장비 구매(100% 완료), 설치공사(50% 진행 중), 네트워크 구축(70% 완료) 등 대부분의 공정이 계획대로 추진되고 있음"
    },
    "주요성과": {
        "style": "효과형",
        "guide": "그동안의 주요 성과를 정량적 수치와 함께 기술",
        "example": "금년도 CCTV 설치사업 추진 결과, 목표 대비 120%를 달성(목표 40대, 실적 48대)하였으며, 설치 완료 지역의 범죄 발생률이 전년 동기 대비 18% 감소하는 성과를 거둠"
    },
    "향후계획": {
        "style": "방안형",
        "guide": "향후 추진할 계획을 구체적으로 기술",
        "example": "2026년 하반기에는 1단계 설치 지역의 운영 성과를 분석하여 2단계 설치 대상지를 선정하고, AI 영상분석 기능 도입을 위한 시범사업을 추진할 계획임"
    },
    "현재상태": {
        "style": "서술형",
        "guide": "현재 상태를 객관적으로 기술",
        "example": "현재 사고 현장은 정리가 완료되어 정상 통행이 가능하며, 피해 차량은 견인 조치됨. 부상자는 인근 ○○병원에서 치료 중이며 생명에는 지장이 없는 것으로 확인됨"
    },
    "피해상황": {
        "style": "나열형",
        "guide": "피해 현황을 유형별로 정리하여 기술",
        "example": "인명피해: 경상 2명(○○병원 치료 중) / 재산피해: 차량 2대 파손, 가로등 1기 파손 / 교통영향: 해당 구간 30분간 교통 통제"
    },
    "결정사항": {
        "style": "나열형",
        "guide": "회의에서 결정된 사항을 항목별로 정리",
        "example": "CCTV 설치 대상지: 원안 의결(15개소) / 사업 예산: 3억원 확정 / 추진일정: 상반기 완료 목표 / 담당부서: ○○과"
    },
    "주요논의사항": {
        "style": "서술형",
        "guide": "회의에서 논의된 주요 내용을 정리",
        "example": "CCTV 설치 위치 선정 기준에 대해 논의하였으며, 범죄 발생 빈도, 주민 요청, 경찰서 의견 등을 종합적으로 고려하여 우선순위를 결정하기로 함. 예산 범위 내에서 최대한 많은 지점에 설치하되 품질을 저하시키지 않는 방향으로 추진하기로 의견을 모음"
    },
    "회의안건": {
        "style": "나열형",
        "guide": "회의 안건을 간결하게 나열",
        "example": "안건1: 2026년 CCTV 설치 대상지 선정 / 안건2: 사업 예산 및 추진일정 확정 / 안건3: 관계기관 협조사항 논의"
    },
    "분석목적": {
        "style": "서술형",
        "guide": "분석을 수행하는 목적을 기술",
        "example": "본 분석은 관내 CCTV 설치 효과를 실증적으로 검증하고, 향후 설치 계획 수립 시 참고자료로 활용하기 위해 수행함"
    },
    "분석방법": {
        "style": "나열형",
        "guide": "분석에 사용한 방법론을 기술",
        "example": "분석기간: 2023~2025년(3개년) / 분석대상: 관내 전체 CCTV 설치지역 / 분석방법: 범죄 발생 건수 비교분석, 시계열 분석"
    },
    "데이터개요": {
        "style": "나열형",
        "guide": "분석에 사용한 데이터 개요를 기술",
        "example": "데이터 출처: 경찰청 범죄통계, 시 CCTV 관제센터 / 데이터 건수: 총 15,234건 / 데이터 기간: 2023. 1. ~ 2025. 12."
    },
    "결론": {
        "style": "효과형",
        "guide": "분석이나 검토의 최종 결론을 기술",
        "example": "분석 결과를 종합하면 CCTV 설치는 범죄 예방에 실질적인 효과가 있으며, 특히 야간 취약지역에 대한 전략적 설치가 중요함. 향후 AI 영상분석 기술을 접목하여 효과를 극대화할 필요가 있음"
    },
    "성과지표": {
        "style": "나열형",
        "guide": "성과를 측정하는 지표를 나열",
        "example": "정량지표: 범죄 발생 건수, 검거율, CCTV 가동률 / 정성지표: 주민 체감안전도, 만족도 조사 결과"
    },
    "개선사항": {
        "style": "방안형",
        "guide": "개선이 필요한 사항과 방안을 기술",
        "example": "영상 저장기간이 현재 15일로 수사 활용에 제한이 있어 30일로 연장이 필요하며, 야간 화질 개선을 위해 적외선 성능이 강화된 장비로 순차 교체가 필요함"
    },
    "분석배경": {
        "style": "서술형",
        "guide": "분석을 수행하게 된 배경을 기술",
        "example": "최근 스마트시티 추진에 따른 CCTV 고도화 정책이 확대되고 있어, 우리 시의 현황을 점검하고 향후 발전방향을 모색하고자 본 분석을 수행함"
    },
    "특이사항": {
        "style": "서술형",
        "guide": "특별히 보고가 필요한 사항을 기술",
        "example": "금일 ○○동 일대에서 단수가 발생하여 주민 불편이 예상되며, 복구작업은 18:00경 완료될 예정임. 해당 지역 주민에게 개별 문자 안내를 완료함"
    },
    "후속조치": {
        "style": "나열형",
        "guide": "향후 조치할 사항을 간결하게 나열",
        "example": "피해자 지원: 의료비 지원 검토 / 재발방지: 해당 구간 안전시설 점검 / 보고: 상황 종료 시 최종 결과 보고"
    },
    "날짜": {
        "style": "나열형",
        "guide": "날짜와 관련 정보를 간결하게 기술",
        "example": "작성일: 2026. 1. 27.(월) / 작성자: ○○과 ○○○"
    },
    "주요내용": {
        "style": "서술형",
        "guide": "핵심 내용을 간결하게 기술",
        "example": "금일 ○○ 관련 민원이 3건 접수되었으며, 모두 동일 사안에 대한 중복 민원으로 확인됨. 담당 부서에서 일괄 회신 예정임"
    },
    "업무개요": {
        "style": "서술형",
        "guide": "업무의 전체적인 개요를 기술",
        "example": "○○사업 관련 중간보고 자료 작성 및 제출 업무로, 사업 추진현황과 향후 계획을 정리하여 도청에 보고함"
    },
    "처리내용": {
        "style": "서술형",
        "guide": "처리한 내용을 구체적으로 기술",
        "example": "요청받은 자료를 취합하여 정해진 양식에 맞게 작성 완료하였으며, 과장 결재 후 도청 담당자에게 이메일로 제출함"
    },
    "참고사항": {
        "style": "서술형",
        "guide": "참고가 필요한 사항을 기술",
        "example": "다음 분기 보고 시에는 성과지표 달성현황도 함께 제출해야 하므로 관련 데이터 수집이 필요함"
    },
    "작성일": {
        "style": "나열형",
        "guide": "작성일과 관련 정보를 간결하게 기술",
        "example": "작성일: 2026. 1. 27.(월) / 작성자: ○○과 ○○○ 주무관"
    },
    "발생장소": {
        "style": "나열형",
        "guide": "발생 장소를 구체적으로 기술",
        "example": "장소: ○○시 ○○동 ○○로 123(○○아파트 앞 사거리) / 관할: ○○파출소"
    },
}


# ===========================================
# 기본 프롬프트 (DB에 없을 때 사용)
# ===========================================
_DEFAULT_SYSTEM_PROMPT = (
    "당신은 대한민국 지방자치단체 공무원 업무보고서 작성 전문가입니다. "
    "섹션별 특성(서술형/나열형/효과형/방안형/분석형)에 맞게 작성합니다. "
    "반드시 JSON 형식으로만 응답하세요."
)

_DEFAULT_BUILD_PROMPT_TEMPLATE = """당신은 대한민국 지방자치단체에서 15년간 근무한 7급 공무원입니다.
실제 업무에서 사용하는 수준의 보고서를 작성해주세요.

## 작성할 보고서 정보
- 제목: {title}
- 유형: {report_type} > {detail_type}
- 핵심 키워드: {keywords_joined}
- 분량: 섹션당 {items_per_section}개 항목

## 섹션 구성
{sections_joined}

## 문체 규칙 (개괄식 종결어미)
- 서술형 섹션: "~임", "~음", "~함", "~됨" 등으로 문장 종결
- 나열형 섹션: "항목: 내용" 형태로 간결하게 (문장형 종결어미 불필요)
- 절대 금지: "~했습니다", "~합니다", "~했다", "~한다"

## 핵심 규칙
1. 키워드 "{keywords_joined}"를 반드시 내용에 자연스럽게 포함
2. 구체적 숫자(수량, 금액, 일정, 비율 등)를 반드시 포함
3. 각 섹션의 스타일(서술형/나열형/효과형/방안형/분석형)에 맞게 작성
4. 섹션 간 내용 중복 금지

## 섹션별 작성 가이드
{section_guide_text}

## 출력 형식
마크다운, 이모지, 불릿 기호 없이 순수 JSON만 출력하세요.

{{
  "title": "{title}",
  "type": "{report_type}",
  "detailType": "{detail_type}",
  "summary": "보고서 핵심 내용을 3~4문장으로 요약 (구체적 수치 포함, 개괄식 종결어미)",
  "sections": [
    {{
      "title": "섹션명",
      "order": 1,
      "content": [
        "첫 번째 항목 - 해당 섹션 스타일에 맞게 작성",
        "두 번째 항목",
        "세 번째 항목",
        "네 번째 항목"
      ]
    }}
  ],
  "metadata": {{
    "generatedAt": "{generated_at}",
    "totalSections": {total_sections},
    "keywords": {keywords_json}
  }}
}}
"""


# ===========================================
# 🎯 프롬프트 생성 함수
# ===========================================
def build_prompt(title: str, report_type: str, detail_type: str, keywords: str, length_key: str) -> str:
    """섹션별 특성을 반영한 프롬프트 생성"""
    sections = REPORT_STRUCTURES[report_type][detail_type]
    rule = LENGTH_RULES[length_key]
    keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]

    section_guides = []
    for sec in sections:
        if sec in SECTION_STYLES:
            style_info = SECTION_STYLES[sec]
            section_guides.append(
                f"""
### {sec} ({style_info['style']})
- 작성방법: {style_info['guide']}
- 예시: "{style_info['example']}"
"""
            )
        else:
            section_guides.append(
                f"""
### {sec}
- 작성방법: 해당 내용을 구체적으로 기술
"""
            )

    section_guide_text = "\n".join(section_guides)

    prompt_template = prompt_service.get(
        "report_writer",
        "build_prompt_template",
        default=_DEFAULT_BUILD_PROMPT_TEMPLATE
    )

    return prompt_template.format(
        title=title,
        report_type=report_type,
        detail_type=detail_type,
        keywords_joined=", ".join(keyword_list),
        items_per_section=rule["items_per_section"],
        sections_joined=" → ".join(sections),
        section_guide_text=section_guide_text,
        generated_at=datetime.now().isoformat(),
        total_sections=len(sections),
        keywords_json=json.dumps(keyword_list, ensure_ascii=False),
    )


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
        if len(num) == 4 and (num.startswith("19") or num.startswith("20")):
            return num
        if len(num) >= 4:
            return f"{int(num):,}"
        return num

    return re.sub(r"\b\d{4,}\b", replace_number, text)


def fix_ending(sentence: str) -> str:
    """문장 종결어미를 개괄식으로 변환"""
    sentence = sentence.strip()
    if not sentence:
        return sentence

    if sentence.endswith("."):
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
    text = re.sub(r"[^\w\s가-힣.,()%~\-:/·○△▷]", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = add_number_commas(text)
    return text.strip()


def postprocess_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """보고서 전체 후처리"""
    result = dict(data)

    if isinstance(result.get("summary"), str):
        summary = clean_content(result["summary"])
        sentences = re.split(r"(?<=[.。])\s*", summary)
        processed_sentences = [fix_ending(s) for s in sentences if s.strip()]
        result["summary"] = " ".join(processed_sentences)

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

        system_prompt = prompt_service.get(
            "report_writer",
            "system_prompt",
            default=_DEFAULT_SYSTEM_PROMPT
        )

        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
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
        "version": "3.1.0",
        "supported_types": list(REPORT_STRUCTURES.keys())
    }