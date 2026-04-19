import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# =========================
# 파일 경로 / 읍면동 목록 로드
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent
EMD_FILE = BASE_DIR / "data" / "eup_myeon_dong.txt"


def load_emd_list() -> List[str]:
    if not EMD_FILE.exists():
        print(f"⚠️ 읍면동 파일 없음: {EMD_FILE}")
        return []

    try:
        lines = EMD_FILE.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = EMD_FILE.read_text(encoding="cp949").splitlines()

    emd_list = [line.strip() for line in lines if line.strip()]
    # 긴 이름 먼저 매칭하도록 정렬
    emd_list.sort(key=len, reverse=True)
    print(f"✅ 읍면동 목록 로드 완료: {len(emd_list)}건")
    return emd_list


EMD_LIST = load_emd_list()


# =========================
# 기본 정규식
# =========================
DATE_ONLY_RE_1 = re.compile(r"^\d{4}년\s*\d{1,2}월\s*\d{1,2}일(?:\s*[가-힣]+)?$")
DATE_ONLY_RE_2 = re.compile(r"^\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.\s*(?:[가-힣]+)?$")

TIME_HEADER_RE_1 = re.compile(r"^\d{4}년\s*\d{1,2}월\s*\d{1,2}일\s*(오전|오후)\s*\d{1,2}:\d{2}$")
TIME_HEADER_RE_2 = re.compile(r"^\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.\s*(오전|오후)\s*\d{1,2}:\d{2}$")

SAVE_INFO_RE = re.compile(r"^저장한 날짜\s*:")

MESSAGE_RE_KOR = re.compile(
    r"^(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*(오전|오후)\s*(\d{1,2}):(\d{2}),\s*(.+?)\s*:\s*(.*)$"
)

MESSAGE_RE_DOT = re.compile(
    r"^(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(오전|오후)\s*(\d{1,2}):(\d{2}),\s*(.+?)\s*:\s*(.*)$"
)

# 콤마 없이 시스템 메시지 시작하는 경우
SYSTEM_LINE_RE_KOR = re.compile(
    r"^(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*(오전|오후)\s*(\d{1,2}):(\d{2})[:]\s*(.*)$"
)

SYSTEM_LINE_RE_DOT = re.compile(
    r"^(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(오전|오후)\s*(\d{1,2}):(\d{2})[:]\s*(.*)$"
)

SYSTEM_RE = re.compile(r"초대했습니다|나갔습니다|들어왔습니다")
PHOTO_RE = re.compile(r"^사진(?:\s*(\d+)장)?$")
VIDEO_RE = re.compile(r"^동영상$")
DELETED_RE = re.compile(r"삭제된 메시지입니다")

# fallback용 읍면동 정규식
EMD_PATTERN = re.compile(r"([가-힣]{1,12}(?:읍|면|동))")

# 주소/지번/시설형 위치
LOCATION_HINT_PATTERNS = [
    re.compile(
        r"([가-힣0-9\-\s]+(?:로|길|번지|리|산\d+[\-\d]*|사거리|굴다리|삼거리|마을|공원|산책로|등산로|하천변|천변산책로|지하차도|통로박스|경로당|고개길|제방|펌프장|병원|시장|휴양림|주차장|진입로|출입구|진출입로|계곡|세월교|교량|다리|하상도로|파크골프장|운동장|주차장입구|산책로입구|공사현장|요양병원|문화원|경기장|화장실|맨홀|급경사지))"
    ),
]

# 읍면동 뒤에 자주 붙는 장소 키워드
LOCATION_KEYWORDS = [
    "천변산책로", "산책로", "등산로", "하천변", "하천변도로",
    "진입로", "출입구", "진출입로", "주차장", "공원", "교량", "다리",
    "세월교", "제방", "통로박스", "파크골프장", "휴양림", "계곡",
    "하상도로", "굴다리", "삼거리", "사거리", "공사현장", "펌프장",
    "요양병원", "문화원", "경기장", "화장실", "맨홀", "급경사지",
    "교현천 산책로", "충주천 하천변 산책로", "남산등산로", "참샘골 마을안길"
]

# 원인형 재난 먼저, 통제는 뒤로
INCIDENT_TYPE_RULES = [
    (re.compile(r"산사태|토사유출|토사유실|사면|붕괴|낙석|석축이 무너|임야 사태"), "landslide"),
    (re.compile(r"나무전도|수목전도|쓰러진 나무|전도된 나무|고목.*전도|아카시아나무.*쓰러|피해목제거"), "tree_fall"),
    (re.compile(r"침수|범람|월류|수위상승|도로침수|유실된 제방|맨홀역류|배수불량으로 침수"), "flood"),
    (re.compile(r"싱크홀|씽크홀|노면 파손|웅덩이"), "sinkhole"),
    (re.compile(r"배수로|맨홀|양수|펌프장|역류|준설|배수 안됨|오수맨홀"), "drainage"),
    (re.compile(r"유실|시설|공사현장|절개지|오수|정전|반파|파손"), "facility"),
    (re.compile(r"통제|출입 통제|통행제한|차단|통행차단|통제 유지|출입 통제 유지"), "road_control"),
    (re.compile(r"이상없음|이상 없습니다|우려 없습니다|현황.*없습니다|상황관리|점검결과 이상없습니다"), "inspection"),
]

STATUS_RULES = [
    (re.compile(r"해제|통행재개|개통"), "closed"),
    (re.compile(r"완료|복구 완료|처리 완료|긴급조치 완료|제거 완료|설치 완료|응급복구 완료|양수 작업 완료"), "completed"),
    (re.compile(r"조치중|작업중|진행중|준설 중|투입|복구중|응급 조치 중|보수예정|정비예정|조치예정"), "in_progress"),
    (re.compile(r"이상없음|이상 없습니다|우려 없습니다"), "no_issue"),
    (re.compile(r"모니터링|상황관리|지속적으로 확인|관찰지역|통제 유지|예찰강화"), "monitoring"),
]

AGENCY_RULES = [
    "119", "소방", "경찰", "한전", "도로관리사업소", "농어촌공사",
    "하수과", "안전총괄과", "재난안전대책본부", "자율방재단"
]


def _to_24h(hour: int, ampm: str) -> int:
    if ampm == "오전":
        return 0 if hour == 12 else hour
    return 12 if hour == 12 else hour + 12


def parse_timestamp(year: str, month: str, day: str, ampm: str, hour: str, minute: str) -> datetime:
    hh = _to_24h(int(hour), ampm)
    return datetime(int(year), int(month), int(day), hh, int(minute))


def classify_message_type(text: str) -> Dict[str, Any]:
    stripped = (text or "").strip()

    if DELETED_RE.search(stripped):
        return {"message_type": "deleted", "photo_count": 0, "is_system": False}

    if SYSTEM_RE.search(stripped):
        return {"message_type": "system_invite", "photo_count": 0, "is_system": True}

    photo_match = PHOTO_RE.match(stripped)
    if photo_match:
        count = int(photo_match.group(1) or 1)
        return {"message_type": "photo", "photo_count": count, "is_system": False}

    if VIDEO_RE.match(stripped):
        return {"message_type": "video", "photo_count": 0, "is_system": False}

    return {"message_type": "normal", "photo_count": 0, "is_system": False}


def infer_incident_type(text: str) -> str:
    for pattern, value in INCIDENT_TYPE_RULES:
        if pattern.search(text):
            return value
    return "inspection"


def infer_status(text: str, incident_type: str) -> str:
    for pattern, value in STATUS_RULES:
        if pattern.search(text):
            return value
    if incident_type == "inspection":
        return "no_issue"
    return "reported"


def extract_emd(text: str) -> Optional[str]:
    text = text or ""

    # 1순위: 읍면동 목록 파일 기준
    for emd in EMD_LIST:
        if emd in text:
            return emd

    # 2순위: fallback regex
    match = EMD_PATTERN.search(text)
    return match.group(1) if match else None


def extract_location_raw(text: str) -> Optional[str]:
    text = text or ""
    emd = extract_emd(text)

    # 1. 읍면동 뒤 장소명 조합 방식
    if emd and emd in text:
        after_emd = text.split(emd, 1)[1].strip()

        for keyword in sorted(LOCATION_KEYWORDS, key=len, reverse=True):
            if keyword in after_emd:
                idx = after_emd.find(keyword)
                candidate = after_emd[: idx + len(keyword)].strip()

                # 너무 긴 문장 방지
                candidate = candidate.split("조치")[0].split("완료")[0].split("입니다")[0].strip()
                candidate = candidate.replace("[", "").replace("]", "").strip()
                candidate = " ".join(candidate.split())

                if candidate:
                    return f"{emd} {candidate}".strip()

    # 2. 정규식 기반 fallback
    for pattern in LOCATION_HINT_PATTERNS:
        match = pattern.search(text)
        if match:
            loc = " ".join(match.group(1).split()).strip()
            loc = loc.replace("[", "").replace("]", "").strip()
            if emd and emd not in loc:
                return f"{emd} {loc}".strip()
            return loc

    # 3. 최후 fallback: 읍면동만
    return emd


def extract_related_agency(text: str) -> str:
    found = [a for a in AGENCY_RULES if a in (text or "")]
    return ", ".join(found)


def normalize_summary(text: str) -> str:
    return " ".join((text or "").replace("\n", " ").split())[:300]


def parse_kakao_txt(content: str) -> List[Dict[str, Any]]:
    lines = content.splitlines()
    messages: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    def flush_current():
        nonlocal current
        if current:
            current["raw_text"] = current["raw_text"].strip()
            messages.append(current)
            current = None

    for raw_line in lines:
        line = raw_line.rstrip("\n")

        if not line.strip():
            if current:
                current["raw_text"] += "\n"
            continue

        # 저장 정보 / 날짜 헤더 / 단독 시각줄 스킵
        if SAVE_INFO_RE.match(line):
            continue
        if DATE_ONLY_RE_1.match(line) or DATE_ONLY_RE_2.match(line):
            continue
        if TIME_HEADER_RE_1.match(line) or TIME_HEADER_RE_2.match(line):
            continue

        # 일반 메시지
        m = MESSAGE_RE_KOR.match(line) or MESSAGE_RE_DOT.match(line)
        if m:
            flush_current()
            dt = parse_timestamp(*m.groups()[:6])
            sender = m.group(7).strip()
            text = m.group(8)
            current = {
                "message_time": dt.isoformat(),
                "sender_name": sender,
                "raw_text": text,
            }
            continue

        # 시스템 메시지도 메시지 경계는 잡기
        sm = SYSTEM_LINE_RE_KOR.match(line) or SYSTEM_LINE_RE_DOT.match(line)
        if sm:
            flush_current()
            dt = parse_timestamp(*sm.groups()[:6])
            text = sm.group(7).strip()
            current = {
                "message_time": dt.isoformat(),
                "sender_name": "system",
                "raw_text": text,
            }
            flush_current()
            continue

        # 멀티라인 본문 이어붙이기
        if current:
            current["raw_text"] += f"\n{line}"

    flush_current()

    parsed: List[Dict[str, Any]] = []
    for msg in messages:
        text = msg["raw_text"]
        meta = classify_message_type(text)
        incident_type = infer_incident_type(text)

        parsed.append(
            {
                **msg,
                **meta,
                "parsed_success": True,
                "emd": extract_emd(text),
                "location_raw": extract_location_raw(text),
                "incident_type": incident_type,
                "status": infer_status(text, incident_type),
                "related_agency": extract_related_agency(text),
                "summary": normalize_summary(text),
            }
        )

    return parsed