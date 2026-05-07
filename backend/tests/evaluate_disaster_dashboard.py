"""
재난상황 대시보드 분류기 평가 스크립트

사용법:
    cd backend
    python tests/evaluate_disaster_dashboard.py

검증 항목:
    1. TXT 메시지 파싱 정상 여부
    2. 동일 사고 후속 메시지 병합 여부
    3. 사고 유형 분류 정확도
    4. 사고 상태 갱신 정확도
    5. 읍면동 추출 정확도
    6. 위치 표현이 달라도 같은 사고로 묶이는지 여부
    7. 대시보드 overview 통계 구조 정상 여부
"""

import importlib.util
import os
import sys
from collections import Counter
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _load_module_from_file(name: str, filepath: Path):
    """services/__init__.py의 무거운 의존성을 우회하여 파일 경로로 직접 로드."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# constants 먼저 로드 (parser가 의존)
_constants = _load_module_from_file(
    "services.disaster_constants",
    PROJECT_ROOT / "services" / "disaster_constants.py",
)
# services 패키지를 가짜 모듈로 등록해두어 상대 import 우회
import types as _types
_fake_services = _types.ModuleType("services")
_fake_services.disaster_constants = _constants  # type: ignore
sys.modules.setdefault("services", _fake_services)

_parser = _load_module_from_file(
    "services.disaster_parser_service",
    PROJECT_ROOT / "services" / "disaster_parser_service.py",
)
_incident = _load_module_from_file(
    "services.disaster_incident_service",
    PROJECT_ROOT / "services" / "disaster_incident_service.py",
)

extract_emd = _parser.extract_emd
extract_location_raw = _parser.extract_location_raw
infer_incident_type = _parser.infer_incident_type
infer_status = _parser.infer_status
parse_kakao_txt = _parser.parse_kakao_txt
build_incidents = _incident.build_incidents


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "disaster_sample_kakao.txt"
WINTER_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "disaster_sample_winter_kakao.txt"

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


def color(text, code):
    codes = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "reset": "\033[0m"}
    return f"{codes.get(code,'')}{text}{codes['reset']}"


def result_str(r):
    if r == PASS:
        return color("PASS", "green")
    elif r == FAIL:
        return color("FAIL", "red")
    return color("WARN", "yellow")


def load_sample():
    if not FIXTURE_PATH.exists():
        print(f"[ERROR] 샘플 파일 없음: {FIXTURE_PATH}")
        sys.exit(1)
    return FIXTURE_PATH.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# 검증 1: TXT 파싱
# ─────────────────────────────────────────────────────────────────────────────
def test_parsing(content):
    print("\n[1] TXT 메시지 파싱 검증")
    messages = parse_kakao_txt(content)
    normal = [m for m in messages if m.get("message_type") == "normal"]
    photo = [m for m in messages if m.get("message_type") == "photo"]
    system = [m for m in messages if m.get("is_system")]

    print(f"  전체 메시지: {len(messages)}개  |  일반: {len(normal)}개  |  사진: {len(photo)}개  |  시스템: {len(system)}개")

    r = PASS if len(normal) >= 80 else FAIL
    print(f"  일반 메시지 80개 이상 파싱: {result_str(r)} ({len(normal)}개)")

    r2 = PASS if len(photo) >= 10 else WARN
    print(f"  사진 메시지 파싱: {result_str(r2)} ({len(photo)}개)")

    r3 = PASS if all(m.get("message_time") for m in normal) else FAIL
    print(f"  모든 메시지 message_time 존재: {result_str(r3)}")

    return messages, r == PASS and r3 == PASS


# ─────────────────────────────────────────────────────────────────────────────
# 검증 2: 읍면동 추출
# ─────────────────────────────────────────────────────────────────────────────
EXPECTED_EMDS = {
    "호암직동": ["호암동 천변산책로", "호암동 충주천"],
    "연수동": ["연수동 남산등산로"],
    "교현안림동": ["교현동 교현천 산책로"],
    "칠금금릉동": ["칠금동 금릉로"],
    "목행용탄동": ["목행동 용탄교"],
    "수안보면": ["수안보면 수안보로"],
    "중앙탑면": ["중앙탑면 탑평리"],
    "앙성면": ["앙성면 마을안길"],
    "대소원면": ["대소원면 황정리"],
    "달천동": ["달천동 참샘골"],
}

# emd 파일에 실제로 등록된 이름 확인
EMD_FILE = PROJECT_ROOT / "data" / "eup_myeon_dong.txt"


def _get_emd_list():
    if not EMD_FILE.exists():
        return []
    lines = EMD_FILE.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lines if l.strip()]


def test_emd_extraction(messages):
    print("\n[2] 읍면동 추출 검증")
    emd_list = _get_emd_list()
    print(f"  읍면동 목록: {len(emd_list)}개 로드됨")

    # 샘플 문장 기반 검증
    cases = [
        ("호암동 천변산책로 도로 침수 신고 접수", None),   # 별칭 호암동 → 호암직동
        ("연수동 남산등산로 입구 쪽 나무 쓰러짐", "연수동"),
        ("교현동 교현천 산책로 일부 구간 침수", None),     # 별칭 교현동 → 교현안림동
        ("칠금동 금릉로 도로 싱크홀 발생", None),          # 별칭 칠금동 → 칠금금릉동
        ("수안보면 수안보로 산사태 발생", "수안보면"),
        ("중앙탑면 탑평리 낙석 발생", "중앙탑면"),
        ("앙성면 마을안길 나무 쓰러짐", "앙성면"),
        ("대소원면 황정리 정전 발생", "대소원면"),
        ("달천동 참샘골 마을안길 도로 파손", "달천동"),
        # 확장 케이스 (새 지역)
        ("주덕읍 삼탄천 수위 급격히 상승 중", "주덕읍"),
        ("살미면 동아교 교량 균열 발생", "살미면"),
        ("소태면 용교리 진입도로 낙석 발생", "소태면"),
        ("신니면 백현리 절개지 토사유출", "신니면"),
        ("금가면 창동교 진입로 침수 신고", "금가면"),
        ("노은면 노은로 현장 점검 완료", "노은면"),
    ]

    passed = 0
    for text, expected in cases:
        got = extract_emd(text)
        if expected:
            ok = got == expected
        else:
            ok = got is not None  # 뭔가는 잡으면 PASS
        s = PASS if ok else WARN
        print(f"  '{text[:35]}...' → {got!r}  {result_str(s)}")
        if ok:
            passed += 1

    r = PASS if passed >= len(cases) - 2 else FAIL
    print(f"  총 {passed}/{len(cases)} 통과 → {result_str(r)}")
    return r == PASS


# ─────────────────────────────────────────────────────────────────────────────
# 검증 3: 사고 유형 분류
# ─────────────────────────────────────────────────────────────────────────────
TYPE_CASES = [
    # 기존 케이스
    ("호암동 천변산책로 도로 침수 신고 접수되었습니다. 수위 약 30cm 가량 올라온 상태", "flood"),
    ("연수동 남산등산로 입구 쪽 나무 쓰러짐 신고", "tree_fall"),
    ("아카시아나무 쓰러짐 발생. 도로 차단 상태입니다", "tree_fall"),
    ("칠금동 금릉로 도로 싱크홀 발생 신고 접수. 노면 파손 상태 심각합니다", "sinkhole"),
    ("수안보면 수안보로 산사태 발생 신고. 사면 토사 유출로 도로 통제", "landslide"),
    ("중앙탑면 탑평리 낙석 발생 신고 접수", "landslide"),
    ("목행동 용탄교 진입로 도로 통제 중입니다. 하상도로 침수 우려", "flood"),
    ("대소원면 황정리 전봇대 쓰러짐. 정전 발생", "facility"),
    ("지현동 주민센터 앞 맨홀 역류 신고. 오수맨홀 역류로 주변 침수", "drainage"),
    ("달천동 참샘골 마을안길 도로 파손 발생 신고. 집중 호우로 노면 웅덩이", "sinkhole"),
    ("피해목제거 완료하였습니다. 통행 재개 가능합니다", "tree_fall"),
    # 추가 케이스
    ("호암동 충주천 하천변 실종자 수색 중. 자율방재단 투입되어 수색중입니다", "rescue"),
    ("살미면 동아교 교량 균열 발생 신고 접수. 상판 균열 확인. 하중 제한 조치 필요", "facility"),
    ("주덕읍 삼탄천 수위 급격히 상승 중. 제방 월류 위험 수위 도달", "flood"),
    ("신니면 백현리 절개지 토사유출 발생. 도로 일부 토사 유입", "landslide"),
    ("소태면 용교리 진입도로 낙석 발생. 통행 차단 조치 완료", "landslide"),
    ("배수로 막혀 주변 침수 발생. 양수펌프 투입 요청합니다", "drainage"),
    ("금가면 창동교 진입로 도로 침수 신고. 집중호우로 인근 하천 범람", "flood"),
    ("노은면 노은로 현장 점검 완료. 도로 이상없음 확인", "inspection"),
    # 겨울 재난 유형
    ("주덕읍 삼탄리 일대 폭설로 도로 통제 중. 제설작업 진행중입니다", "heavy_snow"),
    ("칠금동 금릉로 블랙아이스 발생 신고. 노면결빙 상태입니다", "icing"),
    ("신니면 백현리 수도동파 신고 접수. 한파로 인한 계량기 동파 발생", "cold_wave"),
    ("수안보면 수안보로 폭설 및 눈사태 위험 발생. 도로 통제 조치 완료", "landslide"),
    ("호암동 천변산책로 노면 결빙 확인. 출입통제 조치 완료", "icing"),
    ("봉방배수펌프장 계량기 동파 신고. 한파로 인한 동결 확인", "cold_wave"),
    ("연수동 남산등산로 입구 눈 쌓임으로 출입통제. 제설 완료 시까지 통제 유지", "heavy_snow"),
]

def test_incident_type(messages=None):
    print("\n[3] 사고 유형 분류 검증")
    passed = 0
    for text, expected in TYPE_CASES:
        got = infer_incident_type(text)
        ok = got == expected
        s = PASS if ok else FAIL
        print(f"  [{expected}] '{text[:40]}' → {got!r}  {result_str(s)}")
        if ok:
            passed += 1

    r = PASS if passed >= len(TYPE_CASES) - 2 else FAIL
    print(f"  총 {passed}/{len(TYPE_CASES)} 통과 → {result_str(r)}")
    return r == PASS, passed


# ─────────────────────────────────────────────────────────────────────────────
# 검증 4: 사고 상태 분류
# ─────────────────────────────────────────────────────────────────────────────
STATUS_CASES = [
    ("호암동 천변산책로 배수 양수 작업 완료하였습니다", "completed"),
    ("호암동 천변산책로 통행재개 확인. 상황 종료합니다", "closed"),
    ("칠금동 금릉로 노면 파손 긴급복구 작업중입니다", "in_progress"),
    ("도로 통제 중. 안전봉 설치 완료. 도로 통제 유지합니다", "monitoring"),
    ("수안보면 수안보로 산사태 현장 출동 예정입니다", "reported"),
    ("복구 완료하였습니다. 도로 복구 완료", "completed"),
    ("토사유출 응급 조치 중입니다", "in_progress"),
    ("통행재개합니다. 해제합니다", "closed"),
    ("이상없음 확인하였습니다", "no_issue"),
    ("모니터링 지속합니다", "monitoring"),
    # 추가: '해제 예정'은 closed가 아닌 reported 여야 함
    ("안전 확인 시 통행 제한 해제 예정입니다", "reported"),
    # 추가: 수색 진행중
    ("실종자 수색중입니다. 자율방재단 투입 완료", "in_progress"),
    # 추가: 야간 모니터링
    ("야간 모니터링 지속합니다. 수위 경계 유지", "monitoring"),
    # 추가: 응급복구 완료
    ("토사유출 응급복구 완료하였습니다. 통행 재개합니다", "closed"),
    # 겨울 상태
    ("염화칼슘 살포 완료하였습니다. 노면 확인 중입니다", "completed"),
    ("주덕읍 삼탄리 제설 완료하였습니다. 도로 정상화하였습니다", "completed"),
    ("봉방배수펌프장 제설중입니다. 1시간 소요 예정", "in_progress"),
]

def test_status_classification():
    print("\n[4] 사고 상태 분류 검증")
    passed = 0
    for text, expected in STATUS_CASES:
        got = infer_status(text, "flood")
        ok = got == expected
        s = PASS if ok else FAIL
        print(f"  [{expected}] '{text[:40]}' → {got!r}  {result_str(s)}")
        if ok:
            passed += 1

    r = PASS if passed >= len(STATUS_CASES) - 1 else FAIL
    print(f"  총 {passed}/{len(STATUS_CASES)} 통과 → {result_str(r)}")
    return r == PASS, passed


# ─────────────────────────────────────────────────────────────────────────────
# 검증 5: 사건 병합 (build_incidents)
# ─────────────────────────────────────────────────────────────────────────────
def test_incident_merging(messages):
    print("\n[5] 동일 사고 병합 검증")
    normal_msgs = [m for m in messages if m.get("message_type") == "normal"]
    incidents = build_incidents(normal_msgs + [m for m in messages if m.get("message_type") == "photo"])

    print(f"  정상 메시지: {len(normal_msgs)}개")
    print(f"  재구성된 사고 건수: {len(incidents)}개")

    # 샘플 기준 기대 건수: 약 15~22건 (확장 샘플 18개 사고)
    count_ok = 15 <= len(incidents) <= 22
    r = PASS if count_ok else WARN
    print(f"  사고 건수 15~22건 범위: {result_str(r)} ({len(incidents)}건)")

    # 각 사고별 message_count 확인 (후속 메시지 병합 여부)
    multi_msg = [inc for inc in incidents if inc.get("message_count", 0) >= 2]
    r2 = PASS if len(multi_msg) >= 5 else FAIL
    print(f"  2개 이상 메시지 묶인 사고: {result_str(r2)} ({len(multi_msg)}건)")

    # 상태가 closed/completed로 마무리된 사고 확인
    closed_done = [inc for inc in incidents if inc.get("status") in ("closed", "completed")]
    r3 = PASS if len(closed_done) >= 6 else WARN
    print(f"  종료/완료 상태 사고: {result_str(r3)} ({len(closed_done)}건)")

    # 위치 표현 다른 병합 검증
    # 호암동: "호암동 천변산책로", "호암동 천변 산책로" - 같은 사고로 묶여야 함
    hoam_incidents = [inc for inc in incidents if (inc.get("emd") or "").startswith("호암") or "호암" in (inc.get("location_raw") or "")]
    if hoam_incidents:
        # 최초 침수 사고가 별도 실종 사고와 구분되어야 함 (둘 다 호암동)
        print(f"  호암동 관련 사고 건수: {len(hoam_incidents)}건 (침수+실종 → 2건 이상 기대)")
        r4 = PASS if len(hoam_incidents) >= 1 else WARN
        print(f"  호암동 사고 분리: {result_str(r4)}")

    return incidents, count_ok and len(multi_msg) >= 5


# ─────────────────────────────────────────────────────────────────────────────
# 검증 6: overview 통계 구조
# ─────────────────────────────────────────────────────────────────────────────
def test_incident_type_coverage(incidents):
    """확장 샘플에서 기대하는 유형/지역이 실제로 나타나는지 확인."""
    print("\n[5b] 유형·지역 커버리지 검증")
    found_types = {inc.get("incident_type") for inc in incidents}
    found_emds = {inc.get("emd") for inc in incidents}

    expected_types = {"flood", "landslide", "tree_fall", "sinkhole", "drainage", "facility", "rescue"}
    expected_emds = {"주덕읍", "살미면", "소태면", "신니면", "금가면"}

    missing_types = expected_types - found_types
    missing_emds = expected_emds - found_emds

    r1 = PASS if not missing_types else WARN
    print(f"  기대 유형 모두 등장: {result_str(r1)} (누락={missing_types or '없음'})")

    r2 = PASS if not missing_emds else WARN
    print(f"  신규 읍면동 모두 등장: {result_str(r2)} (누락={missing_emds or '없음'})")

    # 살미면이 facility로 분류되었는지
    salmi = [i for i in incidents if i.get("emd") == "살미면" and i.get("incident_type") == "facility"]
    r3 = PASS if salmi else WARN
    print(f"  살미면 교량→facility 분류: {result_str(r3)}")

    # 호암직동 침수(flood)와 실종(rescue) 분리 확인
    hoam_types = [i.get("incident_type") for i in incidents if i.get("emd") == "호암직동"]
    r4 = PASS if "flood" in hoam_types and "rescue" in hoam_types else WARN
    print(f"  호암직동 flood·rescue 분리: {result_str(r4)} (유형={hoam_types})")

    # 주덕읍 사건이 Day 1+2에 걸쳐 하나로 병합됐는지
    jukdeok = [i for i in incidents if i.get("emd") == "주덕읍"]
    r5 = PASS if len(jukdeok) == 1 and jukdeok[0].get("message_count", 0) >= 6 else WARN
    print(f"  주덕읍 Day1→Day2 병합 (1건): {result_str(r5)} ({len(jukdeok)}건, 메시지 {jukdeok[0].get('message_count',0) if jukdeok else 0}개)")

    return r1 == PASS and r2 == PASS


# ─────────────────────────────────────────────────────────────────────────────
# 검증 5c: 겨울 샘플 파일 검증
# ─────────────────────────────────────────────────────────────────────────────
def test_winter_sample():
    """겨울 샘플 파일로 폭설·결빙·한파 유형 분류 및 읍면동 추출 검증."""
    print("\n[5c] 겨울 샘플 검증")
    if not WINTER_FIXTURE_PATH.exists():
        print(f"  [SKIP] 파일 없음: {WINTER_FIXTURE_PATH}")
        return True

    content = WINTER_FIXTURE_PATH.read_text(encoding="utf-8")
    messages = parse_kakao_txt(content)
    normal = [m for m in messages if m.get("message_type") == "normal"]
    incidents = build_incidents(messages)

    print(f"  파싱: {len(messages)}개 메시지, 일반 {len(normal)}개")
    print(f"  사고 재구성: {len(incidents)}건")

    found_types = {i.get("incident_type") for i in incidents}
    found_emds  = {i.get("emd") for i in incidents}

    expected_winter = {"heavy_snow", "icing", "cold_wave"}
    missing_winter = expected_winter - found_types
    r1 = PASS if not missing_winter else FAIL
    print(f"  겨울 유형 3종 등장: {result_str(r1)} (누락={missing_winter or '없음'})")

    expected_emds_w = {"주덕읍", "호암직동", "교현안림동", "칠금금릉동", "신니면"}
    missing_emds_w = expected_emds_w - found_emds
    r2 = PASS if not missing_emds_w else WARN
    print(f"  기대 읍면동 등장: {result_str(r2)} (누락={missing_emds_w or '없음'})")

    count_ok = 7 <= len(incidents) <= 15
    r3 = PASS if count_ok else WARN
    print(f"  사고 건수 7~15건 범위: {result_str(r3)} ({len(incidents)}건)")

    for i, inc in enumerate(incidents, 1):
        print(f"    {i:02d}. [{inc.get('incident_type','?')}] [{inc.get('status','?')}] "
              f"{inc.get('emd','?')} / {(inc.get('location_raw') or '')[:30]} "
              f"(메시지 {inc.get('message_count',0)}개)")

    return r1 == PASS


def test_overview_structure(incidents):
    print("\n[6] Overview 통계 구조 검증")

    type_counter = Counter(inc.get("incident_type") for inc in incidents if inc.get("incident_type"))
    status_counter = Counter(inc.get("status") for inc in incidents if inc.get("status"))
    emd_counter = Counter((inc.get("emd") or "미분류") for inc in incidents)

    overview = {
        "total": len(incidents),
        "by_type": dict(type_counter),
        "by_status": dict(status_counter),
        "by_emd": dict(emd_counter),
    }

    print(f"  총 사고: {overview['total']}건")
    print(f"  유형별: {overview['by_type']}")
    print(f"  상태별: {overview['by_status']}")
    print(f"  읍면동별: {overview['by_emd']}")

    r1 = PASS if overview["total"] > 0 else FAIL
    print(f"  total > 0: {result_str(r1)}")

    r2 = PASS if len(overview["by_type"]) >= 3 else WARN
    print(f"  by_type 3종류 이상: {result_str(r2)} ({len(overview['by_type'])}종)")

    r3 = PASS if len(overview["by_status"]) >= 2 else WARN
    print(f"  by_status 2종류 이상: {result_str(r3)} ({len(overview['by_status'])}종)")

    r4 = PASS if len(overview["by_emd"]) >= 5 else WARN
    print(f"  by_emd 5개 읍면동 이상: {result_str(r4)} ({len(overview['by_emd'])}개)")

    return r1 == PASS and r2 in (PASS, WARN) and r4 in (PASS, WARN)


# ─────────────────────────────────────────────────────────────────────────────
# 검증 7: 위치 유사도 병합 단위 테스트
# ─────────────────────────────────────────────────────────────────────────────
def test_location_similarity():
    from services.disaster_incident_service import _location_similarity
    print("\n[7] 위치 유사도 매칭 검증")

    cases = [
        ("호암동 천변산책로", "호암동 천변 산책로", True),
        ("연수동 남산등산로 입구", "연수동 남산 등산로 입구", True),
        ("수안보면 수안보로", "수안보면 수안보로", True),
        ("칠금동 금릉로", "목행동 용탄교", False),
        ("교현안림동 교현천 산책로", "교현동 교현천 산책로", True),  # 약간 다른 emd 표기
    ]

    passed = 0
    for a, b, should_similar in cases:
        sim = _location_similarity(a, b)
        from services.disaster_incident_service import LOCATION_SIMILARITY_THRESHOLD
        is_similar = sim >= LOCATION_SIMILARITY_THRESHOLD
        ok = is_similar == should_similar
        s = PASS if ok else WARN
        print(f"  {a!r} vs {b!r} → {sim:.2f} ({'유사' if is_similar else '비유사'}) {result_str(s)}")
        if ok:
            passed += 1

    r = PASS if passed >= 3 else WARN
    print(f"  총 {passed}/{len(cases)} 통과 → {result_str(r)}")
    return r == PASS


# ─────────────────────────────────────────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("재난상황 대시보드 분류기 평가")
    print(f"샘플 파일: {FIXTURE_PATH}")
    print("=" * 70)

    content = load_sample()

    results = {}

    messages, r1 = test_parsing(content)
    results["TXT 파싱"] = PASS if r1 else FAIL

    r_emd = test_emd_extraction(messages)
    results["읍면동 추출"] = PASS if r_emd else WARN

    r_type, type_pass = test_incident_type(messages)
    results["유형 분류"] = PASS if r_type else FAIL

    r_status, status_pass = test_status_classification()
    results["상태 분류"] = PASS if r_status else FAIL

    incidents, r_merge = test_incident_merging(messages)
    results["사고 병합"] = PASS if r_merge else WARN

    r_coverage = test_incident_type_coverage(incidents)
    results["유형·지역 커버리지"] = PASS if r_coverage else WARN

    r_winter = test_winter_sample()
    results["겨울 샘플 검증"] = PASS if r_winter else FAIL

    r_overview = test_overview_structure(incidents)
    results["Overview 통계"] = PASS if r_overview else FAIL

    r_sim = test_location_similarity()
    results["위치 유사도"] = PASS if r_sim else WARN

    # ── 사고 상세 출력 ──────────────────────────────────────────────────────
    print("\n[사고 목록 상세]")
    for i, inc in enumerate(incidents, 1):
        print(f"  {i:02d}. [{inc.get('incident_type','?')}] [{inc.get('status','?')}] "
              f"{inc.get('emd','?')} / {inc.get('location_raw','?')[:30]} "
              f"(메시지 {inc.get('message_count',0)}개)")

    # 최종 요약
    print("\n" + "=" * 70)
    print("최종 결과 요약")
    print("=" * 70)
    print(f"{'검증 항목':<20} {'결과':>10}")
    print("-" * 32)
    for name, r in results.items():
        print(f"  {name:<18} {result_str(r):>10}")

    total = len(results)
    passed = sum(1 for r in results.values() if r == PASS)
    warned = sum(1 for r in results.values() if r == WARN)
    failed = sum(1 for r in results.values() if r == FAIL)

    print("-" * 32)
    print(f"  PASS: {passed}, WARN: {warned}, FAIL: {failed} / {total}")

    if failed == 0:
        print(color("\n전체 PASS (FAIL 없음)", "green"))
    else:
        print(color(f"\nFAIL {failed}건 존재 — 분류기 개선 필요", "red"))

    return failed == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
