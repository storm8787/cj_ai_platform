"""
카카오톡 txt 파서 서비스

변경사항 (v7.1):
- 날짜 포맷 추가: 단축형(--- 헤더) 및 연도 누락형 대응
- infer_status 정교화:
  * '~예정' 계열은 reported로 분리 (in_progress에서 제외)
  * '~중' 계열만 in_progress
- extract_location_raw: 다양한 괄호 문자 정리
- 응답 문구 필터는 disaster_incident_service로 이동
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .disaster_constants import EMD_ALIASES, EMD_FALLBACK_BLACKLIST


# =========================
# 파일 경로 / 읍면동 목록 로드
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent
EMD_FILE = BASE_DIR / "data" / "eup_myeon_dong.txt"
RI_EMD_FILE = BASE_DIR / "data" / "ri_to_emd.json"


def load_emd_list() -> List[str]:
    if not EMD_FILE.exists():
        print(f"⚠️ 읍면동 파일 없음: {EMD_FILE}")
        return []

    try:
        lines = EMD_FILE.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = EMD_FILE.read_text(encoding="cp949").splitlines()

    emd_list = [line.strip() for line in lines if line.strip()]
    emd_list.sort(key=len, reverse=True)
    print(f"✅ 읍면동 목록 로드 완료: {len(emd_list)}건")
    return emd_list


def load_ri_to_emd() -> Dict[str, str]:
    import json
    if not RI_EMD_FILE.exists():
        return {}
    try:
        return json.loads(RI_EMD_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


EMD_LIST = load_emd_list()
RI_TO_EMD: Dict[str, str] = load_ri_to_emd()

# 리(里) 패턴: 2자 이상 한글 + 리
RI_PATTERN = re.compile(r"([가-힣]{2,6}리)")


# =========================
# 기본 정규식
# =========================
DATE_ONLY_RE_1 = re.compile(r"^\d{4}년\s*\d{1,2}월\s*\d{1,2}일(?:\s*[가-힣]+)?$")
DATE_ONLY_RE_2 = re.compile(r"^\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.\s*(?:[가-힣]+)?$")

# "--------------- 2025년 7월 15일 월요일 ---------------" 형태
DATE_DIVIDER_RE = re.compile(
    r"^-+\s*\d{4}년\s*\d{1,2}월\s*\d{1,2}일.*-+$"
)

TIME_HEADER_RE_1 = re.compile(r"^\d{4}년\s*\d{1,2}월\s*\d{1,2}일\s*(오전|오후)\s*\d{1,2}:\d{2}$")
TIME_HEADER_RE_2 = re.compile(r"^\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.\s*(오전|오후)\s*\d{1,2}:\d{2}$")

SAVE_INFO_RE = re.compile(r"^저장한 날짜\s*:")

# 연도 포함 패턴
MESSAGE_RE_KOR = re.compile(
    r"^(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*(오전|오후)\s*(\d{1,2}):(\d{2}),\s*(.+?)\s*:\s*(.*)$"
)

MESSAGE_RE_DOT = re.compile(
    r"^(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(오전|오후)\s*(\d{1,2}):(\d{2}),\s*(.+?)\s*:\s*(.*)$"
)

# 시스템 메시지 (콤마 없이 시작)
SYSTEM_LINE_RE_KOR = re.compile(
    r"^(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*(오전|오후)\s*(\d{1,2}):(\d{2})[:]\s*(.*)$"
)

SYSTEM_LINE_RE_DOT = re.compile(
    r"^(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(오전|오후)\s*(\d{1,2}):(\d{2})[:]\s*(.*)$"
)

# 대괄호 포맷 [보내는사람] [오후 3:30] 메시지 (모바일 최신 포맷)
MESSAGE_RE_BRACKET = re.compile(
    r"^\[(.+?)\]\s*\[(오전|오후)\s*(\d{1,2}):(\d{2})\]\s*(.*)$"
)

SYSTEM_RE = re.compile(r"초대했습니다|나갔습니다|들어왔습니다|내보냈습니다")
PHOTO_RE = re.compile(r"^사진(?:\s*(\d+)장)?$")
VIDEO_RE = re.compile(r"^동영상$")
DELETED_RE = re.compile(r"삭제된 메시지입니다")

# fallback용 읍면동 정규식 (2자 이상 한글 + 읍/면/동 - "출동" 등 비지명 단어 방지)
# fallback용 읍면동 정규식 (2자 이상 한글 + 읍/면/동 - "출동" 등 비지명 단어 방지)
EMD_PATTERN = re.compile(r"([가-힣]{2,12}(?:읍|면|동))")

# 주소/지번/시설형 위치 — 첫 문장 내 짧은 범위에서만 적용
# {2,15}: 공백+단어 그룹에서 최소 2자 이상 요구 → "119 및 도" 같은 단일자 오인 방지
LOCATION_HINT_PATTERNS = [
    re.compile(
        r"([가-힣a-zA-Z0-9\-]{2,20}(?:\s+[가-힣a-zA-Z0-9\-]{2,15}){0,3}"
        r"(?:로|길|번지|사거리|굴다리|삼거리|교차로|마을|공원|산책로|등산로|하천변|천변산책로|"
        r"지하차도|통로박스|경로당|고개길|제방|펌프장|진입로|출입구|진출입로|계곡|세월교|"
        r"교량|다리|하상도로|파크골프장|공사현장|맨홀|급경사지))"
    ),
]

# 복합 위치 패턴: "X 앞 Y", "X 옆 Y" 형태 (예: 한국관 앞 삼거리, 시청 앞 교차로)
_COMPOUND_LOC_PATTERN = re.compile(
    r"([가-힣a-zA-Z0-9]{2,12}"
    r"\s+(?:앞|옆|근처|주변|사이)"
    r"(?:\s+[가-힣a-zA-Z0-9]{2,10}(?:로|길|삼거리|사거리|교차로|교량|다리|진입로|입구|광장)?)?)"
)

# 자연 지형명 패턴: 문장 앞부분 "삼탄천", "충주천" 등 천/강 계열 지명
_NATURAL_GEO_PATTERN = re.compile(r"^([가-힣]{2,8}(?:천|강|저수지|호수|봉))")

# 행정기관 표현 패턴: 이 이후는 행정 조치 컨텍스트 → 위치 탐색 제외
# 예: "도로과와 자원순환과에서는", "안전총괄과에서 확인"
_ORG_CTX_PATTERN = re.compile(
    r"[가-힣]{2,10}(?:과|팀|소|부서|대)\s*(?:에서는?|와\s+[가-힣]|에서\s+(?:확인|처리|담당|출동))"
)

# 읍면동 뒤에 자주 붙는 장소 키워드
LOCATION_KEYWORDS = [
    "천변산책로", "산책로", "등산로", "하천변", "하천변도로",
    "진입로", "출입구", "진출입로", "주차장", "공원", "교량", "다리",
    "세월교", "제방", "통로박스", "파크골프장", "휴양림", "계곡",
    "하상도로", "굴다리", "삼거리", "사거리", "공사현장", "펌프장",
    "요양병원", "문화원", "경기장", "화장실", "맨홀", "급경사지",
    "교현천 산책로", "충주천 하천변 산책로", "남산등산로", "참샘골 마을안길"
]

# 괄호 정리용 문자 (위치 추출 시)
BRACKET_CHARS_RE = re.compile(r"[\[\]【】『』()〔〕「」《》]")

# 계절 구분
# 여름(4-10월): 여름 전용 유형만 분류, 겨울 유형 건너뜀
# 겨울(12,1,2월): 겨울 전용 유형만 분류, 여름 유형 건너뜀
# 전환기(3,11월): 모두 허용
SUMMER_MONTHS = frozenset({4, 5, 6, 7, 8, 9, 10})
WINTER_MONTHS = frozenset({12, 1, 2})

# 계절 전용 유형 집합 (연중 유형은 항상 적용)
WINTER_ONLY_TYPES = frozenset({"cold_wave", "heavy_snow", "icing"})
SUMMER_ONLY_TYPES = frozenset({"drainage", "flood"})

# 원인형 재난 먼저, 통제는 뒤로
# 겨울 재난(폭설·결빙·한파)을 여름 재난보다 앞에 배치하여 혼용 문장에서 겨울 유형 우선 분류
INCIDENT_TYPE_RULES = [
    (re.compile(r"산사태|토사유출|토사유실|사면|붕괴|낙석|석축이 무너|임야 사태|눈사태"), "landslide"),
    (re.compile(r"나무전도|수목전도|쓰러진 나무|전도된 나무|고목.*전도|아카시아나무.*쓰러|피해목제거|나무.*쓰러|수목.*쓰러|쓰러진.*나무|폭설.*나무|눈.*나무.*부러"), "tree_fall"),
    # 겨울 재난
    (re.compile(r"한파|동파|수도동파|계량기.*동파|동파된|동결"), "cold_wave"),
    (re.compile(r"폭설|제설|적설|강설|눈.*쌓|도로.*눈|눈.*도로|노면.*눈|제설작업"), "heavy_snow"),
    (re.compile(r"결빙|빙판|노면결빙|도로결빙|블랙아이스|빙결"), "icing"),
    # 여름/공통 재난
    (re.compile(r"배수로|맨홀|양수|펌프장|역류|준설|배수 안됨|오수맨홀|맨홀역류"), "drainage"),
    (re.compile(r"침수|범람|월류|수위상승|수위.*상승|도로침수|유실된 제방|배수불량으로 침수|하상도로.*침수|침수 우려"), "flood"),
    (re.compile(r"싱크홀|씽크홀|노면 파손|웅덩이"), "sinkhole"),
    (re.compile(r"실종|수색|인명구조"), "rescue"),
    (re.compile(r"유실|시설|공사현장|절개지|오수|정전|반파|파손|균열|교량손상|시설파손|제방파손"), "facility"),
    (re.compile(r"통제|출입 통제|통행제한|차단|통행차단|통제 유지|출입 통제 유지"), "road_control"),
    (re.compile(r"이상없음|이상 없습니다|우려 없습니다|현황.*없습니다|상황관리|점검결과 이상없습니다"), "inspection"),
]

# 상태 규칙: 예정 계열은 reported로, 진행 계열만 in_progress
# '설치 완료'는 임시 안전시설(안전봉, 차단봉) 설치이므로 completed에서 제외 → monitoring으로 처리
STATUS_RULES = [
    (re.compile(r"해제(?!\s*예정)|통행\s*재개(?!\s*가능)|개통|상황\s*종료"), "closed"),
    (re.compile(r"복구 완료|처리 완료|긴급조치 완료|제거 완료|응급복구 완료|양수 작업 완료|조치 완료|조치완료|완료했습니다|완료하였습니다|제설 완료|살포 완료|염화칼슘 살포"), "completed"),
    (re.compile(r"조치중|작업중|진행중|준설 중|투입|복구중|응급 조치 중|처리중|처리 중|수색중|제설중|제설 중|제설작업 중"), "in_progress"),
    (re.compile(r"이상없음|이상 없습니다|우려 없습니다"), "no_issue"),
    (re.compile(r"모니터링|상황관리|지속적으로 확인|관찰지역|통제 유지|설치 완료|예찰강화|예찰 강화"), "monitoring"),
    # '~예정'은 아직 시작 안 함 → reported 유지 (명시적 패턴이지만 마지막에 배치)
    (re.compile(r"예정"), "reported"),
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


def infer_incident_type(text: str, month: int = None) -> str:
    """재난 유형 분류. month(1-12) 전달 시 계절 필터 적용:
    - 여름(4-10): 겨울 전용 유형(cold_wave/heavy_snow/icing) 건너뜀
    - 겨울(12,1,2): 여름 전용 유형(drainage/flood) 건너뜀
    - 전환기(3,11) 또는 None: 모든 유형 허용
    """
    is_summer = month in SUMMER_MONTHS if month is not None else False
    is_winter = month in WINTER_MONTHS if month is not None else False

    for pattern, value in INCIDENT_TYPE_RULES:
        if is_summer and value in WINTER_ONLY_TYPES:
            continue
        if is_winter and value in SUMMER_ONLY_TYPES:
            continue
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

    # 대괄호 표기 전처리: "[호암직동] 메시지" → "호암직동 메시지"
    text_clean = re.sub(r"\[([가-힣a-zA-Z0-9\s]+)\]", r"\1 ", text)

    # 1순위: 읍면동 목록 파일 기준 (공식 행정동명)
    for emd in EMD_LIST:
        if emd in text_clean:
            return emd

    # 2순위: 별칭 매핑 (충주시 줄임 표기 → 공식 행정동)
    for alias, canonical in EMD_ALIASES.items():
        if alias in text_clean:
            return canonical

    # 3순위: 리(里) 패턴 → 상위 읍면동 역조회
    for match in RI_PATTERN.finditer(text_clean):
        ri = match.group(1)
        if ri in RI_TO_EMD:
            return RI_TO_EMD[ri]

    # 4순위: fallback regex — 공식 목록에 있는 EMD만 반환 (임의 단어 오매칭 방지)
    for match in EMD_PATTERN.finditer(text_clean):
        candidate = match.group(1)
        if candidate in EMD_FALLBACK_BLACKLIST:
            continue
        if candidate in EMD_LIST:
            return candidate
        # 별칭도 재확인
        canonical = EMD_ALIASES.get(candidate)
        if canonical:
            return canonical

    return None


def _clean_location_text(text: str) -> str:
    """위치 문자열의 괄호 및 여분 공백 정리"""
    cleaned = BRACKET_CHARS_RE.sub("", text)
    return " ".join(cleaned.split()).strip()


# 위치명 뒤에 오면 안 되는 상황/동사 키워드
_LOCATION_TAIL_STOPS = [
    "수위", "상승", "하강", "지속", "급격히",
    "조치", "완료", "입니다", "발생", "신고", "긴급", "처리",
    "나무", "낙석", "토사", "침수", "정전", "사고", "현장", "작업",
    "관리", "통제", "차단", "협조", "요청", "확인",
    "정리", "마무리", "에서는", "으로부터", "으로 인해",
]


def _trim_location_tail(loc: str) -> str:
    """위치 문자열 뒤에 붙은 재난 상황 동사구를 제거. 3자 미만이면 빈 문자열 반환."""
    for stop in _LOCATION_TAIL_STOPS:
        loc = loc.split(stop)[0].strip()
    if len(loc.replace(" ", "")) < 3:
        return ""
    return loc


def _clip_for_location(text: str) -> str:
    """
    위치 탐색용 텍스트 전처리:
    1. 행정기관 표현(과에서는, 과와 등) 이전까지만 사용
    2. 첫 줄(개행 기준)으로 제한
    3. 최대 100자 제한
    이렇게 하면 "도로과와 자원순환과에서는 ... 동부외곽순환도로" 같은
    행정 조치 문맥 뒤의 도로명이 위치로 잘못 추출되는 것을 방지.
    """
    m = _ORG_CTX_PATTERN.search(text)
    if m:
        text = text[:m.start()].strip()
    text = text.split("\n")[0]
    return text[:100]


def _find_emd_text_form(text: str, emd: str) -> Optional[str]:
    """텍스트에서 emd에 해당하는 실제 표기(별칭 포함)를 찾아 반환."""
    if emd in text:
        return emd
    for alias, canonical in EMD_ALIASES.items():
        if canonical == emd and alias in text:
            return alias
    return None


def _fmt_loc(emd: Optional[str], emd_text: Optional[str], loc: str) -> str:
    """
    emd + loc 최종 조합. 별칭 EMD 중복 제거.
    예) emd=칠금금릉동, emd_text=칠금동, loc='칠금동 금릉로' → '칠금금릉동 금릉로'
    """
    if not loc:
        return emd or ""
    # 별칭이 loc에 이미 포함된 경우 제거
    if emd_text and emd_text != emd and emd_text in loc:
        loc = " ".join(loc.replace(emd_text, "").split())
    if not loc:
        return emd or ""
    if emd and emd not in loc:
        return f"{emd} {loc}".strip()
    return loc.strip()


def extract_location_raw(text: str) -> Optional[str]:
    text = text or ""
    emd = extract_emd(text)
    emd_text = _find_emd_text_form(text, emd) if emd else None

    # 1. 읍면동 뒤 첫 문장에서 장소 키워드 조합
    if emd_text and emd_text in text:
        after_emd = text.split(emd_text, 1)[1].strip()
        # 행정기관 문맥 절단 + 첫 문장
        first_sentence = re.split(r"[.,。\n]", _clip_for_location(after_emd))[0].strip()

        # 1a. 복합 위치 ("한국관 앞 삼거리" 등) 우선 탐색
        compound = _COMPOUND_LOC_PATTERN.search(first_sentence)
        if compound:
            candidate = _trim_location_tail(_clean_location_text(compound.group(1)))
            if candidate:
                return _fmt_loc(emd, emd_text, candidate)

        # 1b. LOCATION_KEYWORDS 기반 (prefix를 _trim_location_tail로 정제하여 비위치 단어 제거)
        for keyword in sorted(LOCATION_KEYWORDS, key=len, reverse=True):
            if keyword in first_sentence:
                idx = first_sentence.find(keyword)
                prefix = first_sentence[:idx].strip()
                prefix_clean = _trim_location_tail(prefix)
                candidate = _clean_location_text(
                    f"{prefix_clean} {keyword}".strip() if prefix_clean else keyword
                )
                if candidate:
                    return _fmt_loc(emd, emd_text, candidate)

        # 1c. 자연 지형명 fallback (천, 강, 저수지 등) — keywords 미매칭 시
        ngm = _NATURAL_GEO_PATTERN.match(first_sentence)
        if ngm:
            candidate = _clean_location_text(ngm.group(1))
            if candidate:
                return _fmt_loc(emd, emd_text, candidate)

        # 1d. 리(里) 단위 지명 — RI_TO_EMD에 등록된 경우만 (백현리, 탑평리 등)
        ri_match = RI_PATTERN.search(first_sentence)
        if ri_match:
            ri_name = ri_match.group(1)
            if ri_name in RI_TO_EMD:
                candidate = _clean_location_text(ri_name)
                if candidate:
                    return _fmt_loc(emd, emd_text, candidate)

    # 2. 행정기관 문맥 절단 후 정규식 fallback
    clipped = _clip_for_location(text)

    # 2a. 복합 위치 패턴 먼저
    compound = _COMPOUND_LOC_PATTERN.search(clipped)
    if compound:
        loc = _trim_location_tail(_clean_location_text(compound.group(1)))
        if loc and len(loc.replace(" ", "")) >= 3:
            return _fmt_loc(emd, emd_text, loc)

    # 2b. 주소형 패턴
    for pattern in LOCATION_HINT_PATTERNS:
        match = pattern.search(clipped)
        if match:
            loc = _clean_location_text(_trim_location_tail(match.group(1)))
            if not loc:
                continue
            return _fmt_loc(emd, emd_text, loc)

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

    # 구분선 형태 날짜에서 추출한 최근 날짜 (대괄호 포맷 보완용)
    current_date: Optional[Dict[str, int]] = None

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

        # 저장 정보 스킵
        if SAVE_INFO_RE.match(line):
            continue

        # 구분선 형태 날짜 ("-------- 2025년 7월 15일 월요일 --------")
        div_match = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", line)
        if DATE_DIVIDER_RE.match(line) and div_match:
            current_date = {
                "year": int(div_match.group(1)),
                "month": int(div_match.group(2)),
                "day": int(div_match.group(3)),
            }
            continue

        # 단독 날짜 / 시각 헤더 스킵 (단, 날짜는 current_date로 기억)
        if DATE_ONLY_RE_1.match(line) or DATE_ONLY_RE_2.match(line):
            dm = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", line)
            if dm:
                current_date = {
                    "year": int(dm.group(1)),
                    "month": int(dm.group(2)),
                    "day": int(dm.group(3)),
                }
            continue
        if TIME_HEADER_RE_1.match(line) or TIME_HEADER_RE_2.match(line):
            continue

        # 일반 메시지 (연도 포함)
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

        # 대괄호 포맷 [이름] [오후 3:30] 메시지 (연도 없음 → current_date 사용)
        br = MESSAGE_RE_BRACKET.match(line)
        if br and current_date:
            flush_current()
            sender = br.group(1).strip()
            ampm = br.group(2)
            hour = br.group(3)
            minute = br.group(4)
            text = br.group(5)
            try:
                hh = _to_24h(int(hour), ampm)
                dt = datetime(
                    current_date["year"],
                    current_date["month"],
                    current_date["day"],
                    hh,
                    int(minute),
                )
                current = {
                    "message_time": dt.isoformat(),
                    "sender_name": sender,
                    "raw_text": text,
                }
                continue
            except (ValueError, KeyError):
                pass

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

        # 메시지 타임스탬프에서 월 추출 → 계절 필터 적용
        msg_month: int = None
        try:
            msg_month = datetime.fromisoformat(msg["message_time"]).month
        except (ValueError, KeyError, TypeError):
            pass

        incident_type = infer_incident_type(text, msg_month)

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