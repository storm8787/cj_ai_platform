from collections import Counter
from typing import Dict, List


INCIDENT_LABELS = {
    "road_control": "도로통제",
    "landslide": "산사태·토사유출",
    "tree_fall": "나무전도",
    "flood": "침수·범람",
    "sinkhole": "싱크홀·노면파손",
    "drainage": "배수·맨홀·양수",
    "facility": "시설물 이상",
    "inspection": "예찰·이상없음",
}

STATUS_LABELS = {
    "reported": "발생",
    "in_progress": "조치중",
    "completed": "조치완료",
    "monitoring": "모니터링",
    "no_issue": "이상없음",
    "closed": "해제·종결",
}


def generate_daily_report(report_date: str, incidents: List[Dict]) -> Dict:
    incident_counter = Counter(i.get("incident_type") for i in incidents)
    status_counter = Counter(i.get("status") for i in incidents)

    major_items = []
    for incident in incidents[:15]:
        label_type = INCIDENT_LABELS.get(incident.get("incident_type"), incident.get("incident_type"))
        label_status = STATUS_LABELS.get(incident.get("status"), incident.get("status"))
        emd = incident.get("emd") or ""
        loc = incident.get("location_raw") or ""
        summary = incident.get("summary") or ""

        line = f"  ◦ {emd} {loc} / {label_type} / {label_status} / {summary}".strip()
        major_items.append(line)

    type_lines = []
    for code, count in incident_counter.most_common():
        label = INCIDENT_LABELS.get(code, code)
        type_lines.append(f"  ◦ {label} : {count}건")

    status_lines = []
    for code, count in status_counter.most_common():
        label = STATUS_LABELS.get(code, code)
        status_lines.append(f"  ◦ {label} : {count}건")

    summary_text = (
        f"{report_date} 기준 총 {len(incidents)}건 분석, "
        f"완료 {status_counter.get('completed', 0) + status_counter.get('closed', 0)}건, "
        f"조치중 {status_counter.get('in_progress', 0)}건"
    )

    report_text = (
        f"1. 재난상황 총괄\n"
        f"  ◦ {report_date} 기준 카카오톡 상황보고 분석 결과, 총 {len(incidents)}건의 유효 사건이 확인되었음\n"
        f"  ◦ 주요 유형은 "
        f"{', '.join([f'{INCIDENT_LABELS.get(k, k)} {v}건' for k, v in incident_counter.most_common(3)]) if incident_counter else '해당없음'}"
        f"으로 분석되었음\n\n"

        f"2. 유형별 발생현황\n"
        f"{chr(10).join(type_lines) if type_lines else '  ◦ 해당없음'}\n\n"

        f"3. 조치상황\n"
        f"{chr(10).join(status_lines) if status_lines else '  ◦ 해당없음'}\n\n"

        f"4. 주요 사건\n"
        f"{chr(10).join(major_items) if major_items else '  ◦ 해당없음'}\n\n"

        f"5. 향후 조치계획\n"
        f"  ◦ 조치중 및 모니터링 상태 사건에 대하여 지속적인 현장 예찰 및 후속조치 추진\n"
        f"  ◦ 반복 발생 지역에 대해서는 원인분석 및 항구복구 필요성 검토\n"
    )

    return {
        "title": f"{report_date} 재난상황 일일보고",
        "summary_text": summary_text,
        "report_text": report_text,
        "total_incident_count": len(incidents),
        "completed_count": status_counter.get("completed", 0) + status_counter.get("closed", 0),
        "in_progress_count": status_counter.get("in_progress", 0),
    }