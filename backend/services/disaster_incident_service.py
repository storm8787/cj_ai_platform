from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


def make_incident_key(msg: Dict[str, Any]) -> Tuple[str, str, str]:
    emd = msg.get("emd") or ""
    location = msg.get("location_raw") or ""
    incident_type = msg.get("incident_type") or "inspection"
    key_loc = location[:40] if location else emd
    return (emd.strip(), key_loc.strip(), incident_type)


def should_include_as_incident(msg: Dict[str, Any]) -> bool:
    if msg["message_type"] in ["system_invite", "deleted", "video"]:
        return False
    if msg["message_type"] == "photo":
        return False
    text = (msg.get("raw_text") or "").strip()
    if text in ["네", "네, 감사합니다", "감사합니다"]:
        return False
    return True


def build_incidents(parsed_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    photo_buffer: List[Dict[str, Any]] = []

    for msg in parsed_messages:
        if msg["message_type"] == "photo":
            photo_buffer.append(msg)
            continue

        if not should_include_as_incident(msg):
            continue

        key = make_incident_key(msg)
        groups[key].append(msg)

        # 바로 직전 사진을 같은 사건으로 귀속
        if photo_buffer:
            for p in photo_buffer:
                p["_attach_to_key"] = key
            groups[key].extend(photo_buffer)
            photo_buffer = []

    incidents: List[Dict[str, Any]] = []
    for _, items in groups.items():
        items_sorted = sorted(items, key=lambda x: x["message_time"])
        first = items_sorted[0]
        last = items_sorted[-1]
        photo_count = sum(i.get("photo_count", 0) for i in items_sorted if i["message_type"] == "photo")
        summary_source = next((i for i in items_sorted if i["message_type"] == "normal"), first)

        status = last.get("status") or first.get("status") or "reported"
        if any(i.get("status") == "closed" for i in items_sorted):
            status = "closed"
        elif any(i.get("status") == "completed" for i in items_sorted):
            status = "completed"
        elif any(i.get("status") == "in_progress" for i in items_sorted):
            status = "in_progress"
        elif any(i.get("status") == "monitoring" for i in items_sorted):
            status = "monitoring"

        action_texts = []
        for i in items_sorted:
            if i["message_type"] == "normal":
                action_texts.append((i.get("raw_text") or "").strip())

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
                "status": status,
                "summary": summary_source.get("summary"),
                "damage_text": summary_source.get("summary"),
                "action_text": " | ".join(action_texts[:5])[:1000],
                "related_agency": ", ".join(sorted(set(filter(None, [i.get("related_agency") for i in items_sorted])))),
                "reporter_name": first.get("sender_name"),
                "photo_count": photo_count,
                "message_count": len(items_sorted),
                "is_reportable": True,
                "raw_messages": items_sorted,
            }
        )

    return sorted(incidents, key=lambda x: x["incident_time"])