"""
재난 사건 재구성 서비스

변경사항 (v7.1):
- 상태 흐름 기반 그룹핑: closed 상태를 만나면 해당 사건 종결,
  이후 같은 (emd, location, type) 메시지가 오면 새 사건으로 인식
- 위치 유사도 80% 이상이면 동일 위치로 병합 (SequenceMatcher)
- incident_type 재계산: 첫 메시지가 'inspection'이면 후속 메시지의
  실제 유형으로 다수결 재산정
- 사진 메시지는 직전 활성 사건에 부착 (기존 유지)
"""

from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple


LOCATION_SIMILARITY_THRESHOLD = 0.80


def _normalize_location(text: str) -> str:
    """위치 문자열 정규화 (공백/특수문자 제거)"""
    if not text:
        return ""
    t = text.strip().lower()
    for ch in ["[", "]", "(", ")", "【", "】", "『", "』", ",", ".", " "]:
        t = t.replace(ch, "")
    return t


def _location_similarity(a: str, b: str) -> float:
    """두 위치 문자열의 유사도(0~1)"""
    na = _normalize_location(a)
    nb = _normalize_location(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def should_include_as_incident(msg: Dict) -> bool:
    """사건 후보로 볼 메시지인지 판정"""
    import re

    message_type = msg.get("message_type")

    if message_type in ["system_invite", "deleted", "video"]:
        return False

    if message_type == "photo":
        return False

    text = (msg.get("raw_text") or "").strip()

    # 짧은 단순 응답 메시지 필터 (정규식 기반)
    if len(text) <= 8 and re.match(
        r"^(네\.?|넵\.?|확인\.?|확인했습니다\.?|감사|고맙|수고|굿|ㅇㅋ|ok)",
        text,
        re.IGNORECASE,
    ):
        return False

    if not text:
        return False

    return True


def _find_active_incident(
    active_incidents: List[Dict],
    msg: Dict,
) -> Optional[int]:
    """
    현재 메시지가 속할 활성 사건의 인덱스 찾기.
    찾지 못하면 None 반환 (→ 새 사건 생성).

    매칭 기준:
    - emd 동일
    - incident_type 동일 (inspection은 와일드카드로 모두 허용)
    - location 유사도 ≥ 임계값

    활성 사건만 대상 (closed 상태 사건은 제외됨).
    """
    msg_emd = (msg.get("emd") or "").strip()
    msg_type = (msg.get("incident_type") or "inspection").strip()
    msg_loc = (msg.get("location_raw") or "").strip()

    if not msg_emd:
        return None

    best_idx: Optional[int] = None
    best_score: float = 0.0

    for idx, incident in enumerate(active_incidents):
        if incident.get("_closed"):
            continue

        inc_emd = (incident.get("emd") or "").strip()
        inc_type = (incident.get("incident_type") or "inspection").strip()
        inc_loc = (incident.get("location_raw") or "").strip()

        if inc_emd != msg_emd:
            continue

        # inspection은 와일드카드로 허용 (나중에 재계산됨)
        if msg_type != inc_type and msg_type != "inspection" and inc_type != "inspection":
            continue

        sim = _location_similarity(msg_loc, inc_loc)
        if sim >= LOCATION_SIMILARITY_THRESHOLD and sim > best_score:
            best_idx = idx
            best_score = sim

    return best_idx


def _recalculate_incident_type(msgs: List[Dict]) -> str:
    """
    사건에 속한 메시지들의 incident_type을 다수결로 재계산.
    inspection은 무의미하므로 다른 유형 우선.
    """
    types = [
        m.get("incident_type", "inspection")
        for m in msgs
        if m.get("message_type") == "normal"
    ]
    if not types:
        return "inspection"

    # inspection이 아닌 유형 중 최다
    non_inspection = [t for t in types if t != "inspection"]
    if non_inspection:
        counter = Counter(non_inspection)
        return counter.most_common(1)[0][0]

    return "inspection"


def _resolve_final_status(statuses: List[str]) -> str:
    """상태 우선순위 결정 (마지막으로 나온 결정적 상태 기준)"""
    if not statuses:
        return "reported"

    # 뒤에서부터 확인 (시간순으로 정렬되어 있다고 가정)
    # 최종 결정적 상태 우선: closed > completed
    for s in reversed(statuses):
        if s in ["closed", "completed"]:
            return s

    # 진행중 상태
    for s in reversed(statuses):
        if s == "in_progress":
            return s

    # 모니터링/이상없음
    for s in reversed(statuses):
        if s in ["monitoring", "no_issue"]:
            return s

    return "reported"


def build_incidents(parsed_messages: List[Dict]) -> List[Dict]:
    """
    메시지 리스트로부터 사건 목록을 재구성.

    - 시간순 정렬된 메시지를 순회
    - 각 메시지에 대해 활성 사건 중 매칭되는 것이 있으면 병합, 없으면 신규 사건
    - closed 상태가 나오면 해당 사건을 _closed=True로 표시 → 이후 매칭 대상에서 제외
    - 사진 메시지는 직전 활성 사건(가장 최근에 추가된 사건)에 부착
    """
    # 시간순 정렬
    sorted_msgs = sorted(parsed_messages, key=lambda x: x.get("message_time") or "")

    active_incidents: List[Dict] = []
    last_active_idx: Optional[int] = None

    for msg in sorted_msgs:
        message_type = msg.get("message_type")

        # 사진 메시지 → 직전 활성 사건에 부착
        if message_type == "photo":
            if last_active_idx is not None and last_active_idx < len(active_incidents):
                active_incidents[last_active_idx]["_messages"].append(msg)
            continue

        # 사건 후보가 아닌 메시지는 무시
        if not should_include_as_incident(msg):
            continue

        # 활성 사건 중 매칭 찾기
        match_idx = _find_active_incident(active_incidents, msg)

        if match_idx is not None:
            # 기존 사건에 병합
            incident = active_incidents[match_idx]
            incident["_messages"].append(msg)

            # 상태가 closed이면 사건 종결 처리
            if msg.get("status") == "closed":
                incident["_closed"] = True

            last_active_idx = match_idx
        else:
            # 새 사건 생성
            new_incident = {
                "emd": msg.get("emd"),
                "location_raw": msg.get("location_raw"),
                "incident_type": msg.get("incident_type") or "inspection",
                "_messages": [msg],
                "_closed": msg.get("status") == "closed",
            }
            active_incidents.append(new_incident)
            last_active_idx = len(active_incidents) - 1

    # 최종 사건 데이터 구성
    incidents: List[Dict] = []
    for incident in active_incidents:
        msgs = sorted(incident["_messages"], key=lambda x: x.get("message_time") or "")
        normal_msgs = [m for m in msgs if m.get("message_type") == "normal"]

        if not normal_msgs:
            continue

        first_normal = normal_msgs[0]
        last_msg = msgs[-1]

        # incident_type 재계산 (inspection 우선순위 낮춤)
        final_type = _recalculate_incident_type(normal_msgs)

        # 상태 재결정
        statuses = [m.get("status") for m in normal_msgs if m.get("status")]
        final_status = _resolve_final_status(statuses)

        # 위치는 가장 상세한 것 선택 (가장 긴 location_raw)
        best_location = max(
            (m.get("location_raw") or "" for m in normal_msgs),
            key=len,
            default="",
        ) or first_normal.get("emd") or ""

        # 사진 수
        photo_count = sum(
            m.get("photo_count", 0) for m in msgs if m.get("message_type") == "photo"
        )

        # 관련 기관
        agencies = []
        for m in normal_msgs:
            ag = (m.get("related_agency") or "").strip()
            if ag:
                agencies.extend([a.strip() for a in ag.split(",") if a.strip()])
        agencies = sorted(set(agencies))

        # 조치 내용 텍스트
        action_texts = []
        for m in normal_msgs[:8]:
            raw = (m.get("raw_text") or "").strip()
            if raw:
                action_texts.append(" ".join(raw.split()))

        incidents.append(
            {
                "incident_time": first_normal["message_time"],
                "first_report_time": first_normal["message_time"],
                "last_update_time": last_msg["message_time"],
                "emd": first_normal.get("emd"),
                "location_raw": best_location,
                "location_normalized": best_location,
                "incident_type": final_type,
                "severity": "medium",
                "status": final_status,
                "summary": first_normal.get("summary"),
                "damage_text": first_normal.get("summary"),
                "action_text": " | ".join(action_texts)[:1500],
                "related_agency": ", ".join(agencies),
                "reporter_name": first_normal.get("sender_name"),
                "photo_count": photo_count,
                "message_count": len(msgs),
                "is_reportable": True,
                "raw_messages": msgs,
            }
        )

    return sorted(incidents, key=lambda x: x["incident_time"])