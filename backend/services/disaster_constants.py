"""
재난상황 대시보드 공통 상수

유형/상태 라벨을 한 곳에서 관리.
- disaster_incident_service.py
- disaster_report_service.py
- disaster_dashboard.py (라우터)
에서 import 해서 사용.

프론트엔드에도 동일한 매핑이 있으므로 (frontend/src/constants/disaster.js),
변경 시 양쪽 모두 업데이트 필요.
"""

from typing import Dict, List, Set


# 내부 코드 → 화면 표시 라벨
INCIDENT_TYPE_LABELS: Dict[str, str] = {
    "road_control": "도로통제",
    "landslide": "산사태·토사유출",
    "tree_fall": "나무전도",
    "flood": "침수·범람",
    "sinkhole": "싱크홀·노면파손",
    "drainage": "배수·맨홀·양수",
    "facility": "시설물 이상",
    "rescue": "수색·구조",
    "heavy_snow": "폭설·제설",
    "icing": "도로결빙",
    "cold_wave": "한파·동파",
    "inspection": "기타/미분류",
}

# 충주시 읍면동 별칭 → 공식 행정동 코드 매핑
# 카카오톡 메시지에서 줄임 표기를 공식 행정동으로 정규화
EMD_ALIASES: Dict[str, str] = {
    "호암동": "호암직동",
    "직동": "호암직동",
    "목행동": "목행용탄동",
    "용탄동": "목행용탄동",
    "칠금동": "칠금금릉동",
    "금릉동": "칠금금릉동",
    "교현동": "교현안림동",
    "안림동": "교현안림동",
    "교현1동": "교현안림동",
    "성내동": "성내충인동",
    "충인동": "성내충인동",
    # 읍 이름 오기/구명 하위호환
    "더덕읍": "주덕읍",
    # 면 이름 순서 오기 (가금면 → 금가면)
    "가금면": "금가면",
}

# fallback 정규식 매칭에서 제외할 비지명 한자어 (동/면/읍으로 끝나는 일반 단어)
EMD_FALLBACK_BLACKLIST: Set[str] = {
    "출동", "행동", "이동", "활동", "운동", "진동", "소동",
    "반동", "감동", "작동", "구동", "시동", "유동", "공동",
    "투동", "기동", "동동", "협동", "공동", "입동", "동행",
}

STATUS_LABELS: Dict[str, str] = {
    "reported": "발생",
    "in_progress": "조치중",
    "completed": "조치완료",
    "monitoring": "모니터링",
    "no_issue": "이상없음",
    "closed": "해제·종결",
}


# 상태 집계 그룹 (일일보고서에서 완료/진행중 합산 시 사용)
COMPLETED_STATUSES: List[str] = ["completed", "closed"]
IN_PROGRESS_STATUSES: List[str] = ["in_progress"]
MONITORING_STATUSES: List[str] = ["monitoring"]
REPORTED_STATUSES: List[str] = ["reported"]


def incident_label(code: str) -> str:
    """유형 코드를 한글 라벨로 변환. 미등록 코드는 원본 반환."""
    return INCIDENT_TYPE_LABELS.get(code, code or "미분류")


def status_label(code: str) -> str:
    """상태 코드를 한글 라벨로 변환. 미등록 코드는 원본 반환."""
    return STATUS_LABELS.get(code, code or "미분류")