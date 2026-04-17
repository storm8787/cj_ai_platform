from collections import defaultdict
from typing import Dict, List, Tuple


def make_incident_key(msg: Dict) -> Tuple[str, str, str]:
    emd = (msg.get("emd") or "").strip()
    location = (msg.get("location_raw") or "").strip()
    incident_type = (msg.get("incident_type") or "inspection").strip()

    key_loc = location[:50] if location else emd
    return (emd, key_loc, incident_type)


def should_include_as_incident(msg: Dict) -> bool:
    message_type = msg.get("message_type")

    if message_type in ["system_invite", "deleted", "video"]:
        return False

    if message_type == "photo":
        return False

    text = (msg.get("raw_text") or "").strip()
    if text in ["네", "감사합니다", "네, 감사합니다", "고맙습니다", "확인"]:
        return False

    return True


def build_incidents(parsed_messages: List[Dict]) -> List[Dict]:
    groups = defaultdict(list)
    photo_buffer: List[Dict] = []

    for msg in parsed_messages:
        if msg["message_type"] == "photo":
            photo_buffer.append(msg)
            continue

        if not should_include_as_incident(msg):
            continue

        key = make_incident_key(msg)
        groups[key].append(msg)

        # 직전 사진들을 이 사건에 붙임
        if photo_buffer:
            for p in photo_buffer:
                p["_attach_to_key"] = key
            groups[key].extend(photo_buffer)
            photo_buffer = []

    incidents: List[Dict] = []

    for _, items in groups.items():
        items_sorted = sorted(items, key=lambda x: x["message_time"])
        first = items_sorted[0]
        last = items_sorted[-1]

        photo_count = sum(i.get("photo_count", 0) for i in items_sorted if i["message_type"] == "photo")

        normal_msgs = [i for i in items_sorted if i["message_type"] == "normal"]
        summary_source = normal_msgs[0] if normal_msgs else first

        # 상태 우선순위
        statuses = [i.get("status") for i in items_sorted if i.get("status")]
        final_status = "reported"
        if "closed" in statuses:
            final_status = "closed"
        elif "completed" in statuses:
            final_status = "completed"
        elif "in_progress" in statuses:
            final_status = "in_progress"
        elif "monitoring" in statuses:
            final_status = "monitoring"
        elif "no_issue" in statuses:
            final_status = "no_issue"

        # 기관 목록
        agencies = []
        for i in items_sorted:
            ag = (i.get("related_agency") or "").strip()
            if ag:
                agencies.extend([a.strip() for a in ag.split(",") if a.strip()])
        agencies = sorted(set(agencies))

        # action text
        action_texts = []
        for i in normal_msgs[:8]:
            raw = (i.get("raw_text") or "").strip()
            if raw:
                action_texts.append(" ".join(raw.split()))

        incidents.append(
            {
                "incident_time": first["message_time"],
                "first_report_time": first["message_time"],
                "last_update_time": last["message_time"],
                "emd": first.get("emd"),
                "location_raw": first.get("location_raw"),
                "location_normalized": first.get("location_raw"),
                "incident_type": first.get("incident_type") or "inspection",
                "severity": "medium",
                "status": final_status,
                "summary": summary_source.get("summary"),
                "damage_text": summary_source.get("summary"),
                "action_text": " | ".join(action_texts)[:1500],
                "related_agency": ", ".join(agencies),
                "reporter_name": first.get("sender_name"),
                "photo_count": photo_count,
                "message_count": len(items_sorted),
                "is_reportable": True,
                "raw_messages": items_sorted,
            }
        )

    return sorted(incidents, key=lambda x: x["incident_time"])