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

from typing import Dict, List


# 내부 코드 → 화면 표시 라벨
INCIDENT_TYPE_LABELS: Dict[str, str] = {
    "road_control": "도로통제",
    "landslide": "산사태·토사유출",
    "tree_fall": "나무전도",
    "flood": "침수·범람",
    "sinkhole": "싱크홀·노면파손",
    "drainage": "배수·맨홀·양수",
    "facility": "시설물 이상",
    "inspection": "기타/미분류",
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