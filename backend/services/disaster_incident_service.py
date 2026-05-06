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

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

# 재난 내용 최소 키워드 - emd 없는 메시지가 새 사건을 생성할지 판단하는 기준
_DISASTER_CONTENT_RE = re.compile(
    r"침수|산사태|낙석|나무|싱크홀|정전|통제|복구|조치|사고|파손|유실|"
    r"피해|붕괴|역류|수위|배수|토사|실종|수색|구조|정전|사상|부상"
)


LOCATION_SIMILARITY_THRESHOLD = 0.80

# 서로 같은 사고로 볼 수 있는 유형 호환 그룹
# flood+drainage는 같은 침수 사고의 다른 단계, road_control은 원인 사고의 결과
_TYPE_COMPAT: dict = {
    "flood":        {"flood", "drainage", "road_control"},
    "drainage":     {"flood", "drainage", "road_control"},
    "landslide":    {"landslide", "road_control"},
    "tree_fall":    {"tree_fall", "road_control"},
    "sinkhole":     {"sinkhole", "road_control"},
    "road_control": {"flood", "drainage", "landslide", "tree_fall", "sinkhole", "road_control"},
    "rescue":       {"rescue"},
    "facility":     {"facility"},
    "inspection":   None,  # wildcard — 어떤 유형과도 호환
}


def _types_compatible(type_a: str, type_b: str) -> bool:
    """두 사고 유형이 같은 사건으로 병합 가능한지 판단."""
    if type_a == "inspection" or type_b == "inspection":
        return True
    if type_a == type_b:
        return True
    compat_a = _TYPE_COMPAT.get(type_a)
    if compat_a is None:  # wildcard
        return True
    return type_b in compat_a


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
    message_type = msg.get("message_type")

    if message_type in ["system_invite", "deleted", "video"]:
        return False

    if message_type == "photo":
        return False

    text = (msg.get("raw_text") or "").strip()

    if not text:
        return False

    # 짧은 단순 응답 메시지 필터 (정규식 기반)
    if len(text) <= 12 and re.match(
        r"^(네\.?|넵\.?|확인\.?|확인했습니다\.?|감사|고맙|수고|굿|ㅇㅋ|ok|알겠습니다|네\.?\s*확인)",
        text,
        re.IGNORECASE,
    ):
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

        # 유형 호환성 확인 (inspection 와일드카드 포함)
        if not _types_compatible(msg_type, inc_type):
            continue

        # 위치 미특정 사건(loc == emd 또는 비어있음)
        if not inc_loc or inc_loc == inc_emd:
            score = 0.81
        else:
            na = _normalize_location(inc_loc)
            nb = _normalize_location(msg_loc) if msg_loc else ""
            emd_n = _normalize_location(inc_emd)
            # 한쪽이 다른 쪽의 접두어인 경우 (예: "목행용탄동" vs "목행용탄동 용탄교 진입로")
            if nb and (na.startswith(nb) or nb.startswith(na)):
                score = 0.85
            else:
                score = _location_similarity(msg_loc, inc_loc)
                # EMD 제거 후 본문 비교: 같은 랜드마크(3자↑ 공통접두어) 또는 suffix 일치
                if score < LOCATION_SIMILARITY_THRESHOLD and nb:
                    na_body = na[len(emd_n):] if na.startswith(emd_n) else na
                    nb_body = nb[len(emd_n):] if nb.startswith(emd_n) else nb
                    if na_body and nb_body:
                        # 공통 접두어 3자 이상 (예: "용탄교진입로" vs "용탄교하상도로")
                        common = sum(
                            1 for a, b in zip(na_body, nb_body) if a == b
                            # zip stops at shorter → these are only leading matches
                        )
                        # zip 결과는 대응 위치별 일치이므로 첫 불일치까지만 카운트
                        common_prefix = 0
                        for ca, cb in zip(na_body, nb_body):
                            if ca == cb:
                                common_prefix += 1
                            else:
                                break
                        if common_prefix >= 3:
                            score = max(score, 0.82)
                        # suffix 일치 2자 이상 (예: "주민센터앞맨홀" vs "맨홀")
                        elif len(na_body) >= 2 and len(nb_body) >= 2:
                            shorter = na_body if len(na_body) <= len(nb_body) else nb_body
                            longer = nb_body if len(na_body) <= len(nb_body) else na_body
                            if len(shorter) >= 2 and longer.endswith(shorter):
                                score = max(score, 0.82)

        if score >= LOCATION_SIMILARITY_THRESHOLD and score > best_score:
            best_idx = idx
            best_score = score

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


def _find_incident_by_location_text(active_incidents: List[Dict], text: str) -> Optional[int]:
    """emd 없는 메시지 텍스트에 활성 사건의 위치명/emd가 포함되면 해당 사건 인덱스 반환.
    최근 사건부터 역순으로 탐색."""
    for idx in reversed(range(len(active_incidents))):
        incident = active_incidents[idx]
        if incident.get("_closed"):
            continue
        inc_emd = (incident.get("emd") or "").strip()
        inc_loc = (incident.get("location_raw") or "").strip()

        if inc_emd and inc_emd in text:
            return idx

        if inc_loc:
            loc_body = inc_loc.replace(inc_emd, "").strip()
            for token in loc_body.split():
                if len(token) >= 3 and token in text:
                    return idx
    return None


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
            msg_emd = (msg.get("emd") or "").strip()
            text = (msg.get("raw_text") or "").strip()

            # emd 없는 메시지는 재난 핵심 키워드가 없으면 새 사건을 만들지 않음
            # → 위치 텍스트 매칭 우선, 그 다음 직전 활성 사건에 첨부하거나 무시
            if not msg_emd:
                if _DISASTER_CONTENT_RE.search(text):
                    # 활성 사건 위치명/emd가 텍스트에 포함된 사건 우선 선택
                    loc_match_idx = _find_incident_by_location_text(active_incidents, text)
                    target_idx = loc_match_idx if loc_match_idx is not None else last_active_idx
                    if target_idx is not None and target_idx < len(active_incidents):
                        if not active_incidents[target_idx].get("_closed"):
                            active_incidents[target_idx]["_messages"].append(msg)
                # emd 없는 단순 조율/응답 메시지는 버림
                continue

            # 새 사건 생성 (emd 있는 경우만)
            new_incident = {
                "emd": msg_emd,
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