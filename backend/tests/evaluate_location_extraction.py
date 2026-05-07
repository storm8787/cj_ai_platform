"""
위치 추출 정확도 전용 평가 스크립트

사용법:
    cd backend
    python tests/evaluate_location_extraction.py

평가 항목:
    1. 기본 위치 추출 (읍면동 + 장소명)
    2. 행정기관 컨텍스트 차단 (과에서는 이후 도로명 오인 방지)
    3. 복합 위치 표현 (X 앞 삼거리, X 옆 Y길)
    4. 별칭 EMD 중복 방지 (칠금동→칠금금릉동 별칭 시 중복 없이 추출)
    5. trailing non-location 단어 차단 (수위, 상황 등)
    6. 연속 맥락 텍스트 (119 및 도로관리사업소 오인 방지)
    7. 시설 랜드마크 (주민센터 앞, 아파트 앞 등)
    8. 리(里) 단위 지명
    9. 읍면동만 추출되는 케이스 (세부 위치 없는 경우)
"""

import importlib.util
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _load(name, filepath):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_c = _load("services.disaster_constants", PROJECT_ROOT / "services" / "disaster_constants.py")
_fake = types.ModuleType("services")
_fake.disaster_constants = _c  # type: ignore
sys.modules.setdefault("services", _fake)

_parser = _load(
    "services.disaster_parser_service",
    PROJECT_ROOT / "services" / "disaster_parser_service.py",
)

extract_location_raw = _parser.extract_location_raw
extract_emd = _parser.extract_emd

PASS = "PASS"
FAIL = "FAIL"

# ─────────────────────────────────────────────────────────────────────────────
# 테스트 케이스 정의
# ─────────────────────────────────────────────────────────────────────────────
TEST_CASES = [
    # (카테고리, 입력 텍스트, 기대값_부분포함_체크, 기대값_제외_체크, 설명)
    # 기대값_부분포함_체크: 결과에 이 문자열이 포함되어야 함
    # 기대값_제외_체크: 결과에 이 문자열이 포함되면 안 됨

    # ── 1. 기본 위치 추출 ──────────────────────────────────────────────────
    ("기본", "호암동 천변산책로 도로 침수 신고 접수되었습니다. 수위 약 30cm 가량 올라온 상태입니다.",
     "천변산책로", None, "천변산책로 추출"),

    ("기본", "연수동 남산등산로 입구 쪽 나무 쓰러짐 신고 들어왔습니다.",
     "남산등산로", None, "남산등산로 추출"),

    ("기본", "수안보면 수안보로 산사태 발생 신고. 사면 토사 유출로 도로 통제 중입니다.",
     "수안보로", None, "수안보로 추출"),

    ("기본", "달천동 참샘골 마을안길 도로 파손 발생 신고. 집중 호우로 노면 웅덩이 다수.",
     "참샘골 마을안길", None, "마을안길 추출"),

    ("기본", "금가면 창동교 진입로 침수 신고. 집중호우로 인근 하천 범람.",
     "창동교 진입로", None, "진입로 추출"),

    ("기본", "살미면 동아교 교량 균열 발생 신고 접수. 상판 균열 확인.",
     "동아교", None, "교량 추출"),

    ("기본", "교현동 교현천 산책로 일부 구간 침수 발생. 수위 상승으로 산책로 접근 통제 중입니다.",
     "교현천 산책로", None, "산책로 추출"),

    ("기본", "지현동 주민센터 앞 맨홀 역류 신고. 오수맨홀 역류로 주변 침수.",
     "주민센터 앞", None, "주민센터 앞 추출"),

    # ── 2. 행정기관 컨텍스트 차단 ──────────────────────────────────────────
    ("컨텍스트차단", "연수동 호우주의보 해제알림 도로과와 자원순환과에서는 내일 아침 동부외곽순환도로에서 추가 작업 예정입니다.",
     "연수동", "동부외곽순환도로", "부서 이후 도로명 오인 방지"),

    ("컨텍스트차단", "교현동 교현천 산책로 수위 점검 완료. 도로관리사업소에서는 내일 추가 점검 예정.",
     "교현천", "내일", "사업소 이후 텍스트 오인 방지"),

    ("컨텍스트차단", "칠금동 금릉로 신고 접수. 안전총괄과에서 확인하겠습니다.",
     "금릉로", "안전총괄과", "확인 이후 텍스트 오인 방지"),

    # ── 3. 119/조직명 포함 텍스트 위치 오인 방지 ──────────────────────────
    ("조직명오인", "신니면 백현리 절개지 사면 토사유출 구간 차단 완료. 119 및 도로관리사업소 출동 요청합니다.",
     "백현리", "119 및 도로", "119 및 도로관리사업소 오인 방지"),

    ("조직명오인", "노은면 노은로 현장 점검 완료. 119 출동 완료. 도로 이상없음 확인하였습니다.",
     "노은로", "119", "119 출동 오인 방지"),

    # ── 4. 복합 위치 표현 ──────────────────────────────────────────────────
    ("복합위치", "어제 폭우로 인해 한국관 앞 삼거리 도로에 물이 고인다는 신고가 있었는데 도로과 확인 요망.",
     "한국관 앞 삼거리", None, "X 앞 삼거리 패턴"),

    ("복합위치", "봉방동 시청 앞 교차로 침수 신고. 차량 통제 중입니다.",
     "시청 앞 교차로", None, "X 앞 교차로 패턴"),

    ("복합위치", "지현동 주민센터 옆 골목 침수. 배수 불량 상태입니다.",
     "주민센터 옆", None, "X 옆 Y 패턴"),

    # ── 5. 별칭 EMD 중복 방지 ─────────────────────────────────────────────
    ("별칭중복", "칠금동 금릉로 싱크홀 발생. 노면 파손 심각. 즉시 통제 요합니다.",
     "금릉로", "칠금동 금릉로", "별칭(칠금동) 중복 없이 공식 EMD만 사용"),

    ("별칭중복", "칠금동 금릉로 싱크홀 긴급 안전봉 설치 완료. 도로 통제 유지합니다.",
     "금릉로", "칠금금릉동 칠금동", "별칭 중복 방지 - EMD가 두번 안나와야 함"),

    # ── 6. trailing 비위치 단어 차단 ─────────────────────────────────────
    ("비위치제거", "목행동 용탄교 주변 수위 급격히 상승 중. 하상도로 침수 우려.",
     "용탄교", "수위", "수위는 위치가 아님"),

    ("비위치제거", "주덕읍 삼탄천 수위 급격히 상승 중. 제방 월류 위험.",
     "삼탄천", "수위", "수위는 위치가 아님"),

    ("비위치제거", "교현동 교현천 하천변 수위 상승으로 산책로 접근 통제.",
     "교현천 하천변", "수위", "trailing 수위 제거"),

    # ── 7. 리(里) 단위 지명 ──────────────────────────────────────────────
    ("리단위", "중앙탑면 탑평리 낙석 발생 신고 접수. 도로에 낙석 다수.",
     "중앙탑면", None, "탑평리→중앙탑면 역조회"),

    ("리단위", "신니면 백현리 절개지 토사유출 발생. 도로 일부 토사 유입.",
     "신니면", None, "백현리 포함 메시지 신니면 추출"),

    # ── 8. 읍면동만 추출 (세부 위치 없는 경우) ─────────────────────────
    ("EMD만", "앙성면 현황 이상없습니다. 특이사항 없음.",
     "앙성면", None, "EMD만 반환"),

    ("EMD만", "대소원면 황정리 정전 발생. 한전 출동 요청합니다.",
     "대소원면", None, "EMD 반환"),

    ("EMD만", "봉방동 충주천 하천변 도로 침수 신고. 수위 지속 상승 중입니다.",
     "봉방동", "수위", "봉방동 추출, 수위 미포함"),

    # ── 9. 대괄호 표기 처리 ──────────────────────────────────────────────
    ("대괄호", "[호암직동] 천변산책로 수위 상승. 진입 통제 중입니다.",
     "천변산책로", None, "대괄호 EMD 처리"),

    ("대괄호", "[연수동] 남산등산로 입구 나무 쓰러짐 신고.",
     "남산등산로", None, "대괄호 + 장소명"),
]


def run_tests():
    print("=" * 70)
    print("위치 추출 정확도 평가")
    print("=" * 70)

    results = []
    by_category = {}

    for cat, text, must_include, must_exclude, desc in TEST_CASES:
        got = extract_location_raw(text)
        got_str = got or ""

        ok = True
        fail_reason = ""

        if must_include and must_include not in got_str:
            ok = False
            fail_reason = f"'{must_include}' 미포함"

        if ok and must_exclude and must_exclude in got_str:
            ok = False
            fail_reason = f"'{must_exclude}' 잘못 포함"

        status = PASS if ok else FAIL
        results.append((cat, status, text, got_str, desc, fail_reason))
        by_category.setdefault(cat, []).append(ok)

    # 카테고리별 출력
    current_cat = None
    for cat, status, text, got, desc, reason in results:
        if cat != current_cat:
            current_cat = cat
            print(f"\n[{cat}]")

        icon = "✅" if status == PASS else "❌"
        short_text = text[:50] + "..." if len(text) > 50 else text
        print(f"  {icon} {desc}")
        if status == FAIL:
            print(f"     입력: {short_text}")
            print(f"     결과: {got!r}  ← {reason}")

    # 카테고리별 요약
    print("\n" + "=" * 70)
    print("카테고리별 결과")
    print("=" * 70)
    total_pass = 0
    total_all = 0
    for cat, bools in by_category.items():
        p = sum(bools)
        n = len(bools)
        total_pass += p
        total_all += n
        icon = "✅" if p == n else "❌"
        print(f"  {icon} {cat:12s}: {p}/{n}")

    print(f"\n  총계: {total_pass}/{total_all}")
    all_pass = total_pass == total_all
    if all_pass:
        print("\n\033[92m전체 PASS\033[0m")
    else:
        print(f"\n\033[91mFAIL {total_all - total_pass}건\033[0m")

    return all_pass


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
