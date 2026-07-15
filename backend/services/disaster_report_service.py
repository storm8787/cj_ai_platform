"""
재난상황 일일보고서 생성 서비스

변경사항 (v7.1):
- GPT 기반 요약(summary_text) 및 본문(report_text) 자연어화
- prompt_service 연동으로 관리자 페이지에서 프롬프트 수정 가능
- GPT 호출 실패 시 템플릿 기반 폴백(기존 방식)으로 자동 전환
- 라벨 상수는 disaster_constants에서 import
- 개인정보(보고자 이름)는 프롬프트에 포함하지 않음
- OpenAIService(AsyncOpenAI) 사용, model="gpt-4o" 명시 override
- 호출측은 반드시 await 사용 (비동기 함수)
"""

import logging
from collections import Counter
from typing import Dict, List, Optional

from services.disaster_constants import (
    COMPLETED_STATUSES,
    IN_PROGRESS_STATUSES,
    incident_label,
    status_label,
)

logger = logging.getLogger(__name__)


# 일일보고서 품질 확보를 위해 gpt-4o 고정
REPORT_MODEL = "gpt-4o"

# 주요 사건 표에 나열할 최대 건수 (초과분은 읍면동별 그룹 요약으로 흡수)
MAX_INCIDENTS_IN_REPORT = 50


# =========================
# 기본(폴백) 프롬프트
# =========================
_DEFAULT_SYSTEM_PROMPT = """당신은 충주시청 재난안전상황실에서 상급자 보고용 일일 상황보고를 작성하는 실무 담당자다.
계획서·홍보문이 아니라, 실제 접수된 사건 데이터를 사실 그대로 정리하는 상황보고를 작성한다.

[작성 원칙]
1. 출력은 Markdown(.md). 유형별·상태별 집계는 Markdown 표로 작성한다.
2. 종결은 명사형(~함, ~임, ~됨, ~예정, ~필요, 발생, 완료, 조치 중)으로 한다.
   경어체(~합니다/~입니다)와 완결서술문(~한다/~했다)은 쓰지 않는다.
3. 제공된 집계 수치와 사건 목록에 있는 사실만 기술한다.
   피해 규모·발생 원인·복구 계획·예산·투입 인력·법령·협조 부서는
   데이터에 명시되지 않았으면 절대 지어내지 않는다.
4. 확인되지 않은 항목은 창작하지 말고 "확인 필요" 또는 해당 항목을 생략한다.
5. 숫자는 제공된 집계와 정확히 일치시킨다. 합계가 맞지 않게 임의 추정하지 않는다.
   건수가 0인 항목은 "해당없음"으로 표기한다.
6. 개인정보(보고자·신고자 이름, 연락처)는 보고서에 절대 포함하지 않는다.
   부서명·기관명(소방·경찰·한전 등)은 데이터에 있으면 사용 가능하다.

[상태값 해석 기준]
- 발생(reported): 접수되었으나 조치 착수 전. "접수", "신고 접수"로 표현.
- 조치중(in_progress): 현재 진행 중. "조치 중", "작업 진행 중"으로 표현. 완료로 쓰지 않는다.
- 조치완료(completed): 현장 조치가 끝남. "조치완료"로 표현.
- 이상없음(no_issue): 확인 결과 문제 없음. "현장 확인 결과 이상없음"으로 표현. 완료 건수에 포함하지 않는다.
- 해제·종결(closed): 통제 해제/상황 종료. "해제", "상황 종결"로 표현.
- 모니터링(monitoring): 임시조치 후 관찰 중. "지속 예찰", "상황 관리 중"으로 표현.

[문체]
- 기본은 개조식(명사형 항목). 총괄과 참고사항만 2~3줄 짧은 서술을 허용한다.

[금지 표현]
혁신적·선제적·체계적·최적화·만전·총력·크게 기여·적극 대응·철저히·안전 조치 강화·
재발 방지에 만전·지속적으로 강화 등 근거 없는 수식어와 홍보체.
"기타 발생 사건에 대한 ○○ 강화 예정" 같은 사건 특정 없는 뭉뚱그린 계획 문장 금지.
문단마다 같은 표현을 반복하지 않는다. 감상·다짐·각오 문장을 넣지 않는다.
"""


_DEFAULT_SUMMARY_PROMPT = """다음은 {report_date} 충주시 재난상황 집계다.

- 총 접수: {total}건
- 조치완료·해제 종결: {completed}건
- 조치 중: {in_progress}건
- 주요 유형: {top_types}
- 주요 발생지역: {top_emds}

위 수치만 사용해 보고서 상단 요약문 1문장을 작성한다.

[규칙]
- 100자 이내, 명사형 종결.
- "총 {total}건 접수, 조치완료·종결 {completed}건, 조치 중 {in_progress}건" 흐름을 기본으로 하되
  주요 유형·지역을 자연스럽게 덧붙인다.
- {in_progress}가 0이면 "조치 중 사건 없음", {total}이 0이면 "금일 접수 사건 없음"으로 처리한다.
- 과장·평가·전망(크게 감소, 안정적 등)을 넣지 않는다. 수치에 없는 내용을 추가하지 않는다.
- 요약문 한 문장만 출력한다.
"""


_DEFAULT_BODY_PROMPT = """다음은 {report_date} 충주시 재난상황 집계 및 사건 목록이다.

[집계]
- 총 접수: {total}건
- 유형별: {type_breakdown}
- 상태별: {status_breakdown}
   (상태별에 나온 모든 상태 건수를 아래 '조치상황' 표에 빠짐없이 반영할 것)
- 읍면동별: {emd_breakdown}

[사건 목록]  (형식: [읍면동] 위치 / 유형 / 상태 / 요약)
{incident_list}

위 데이터만 근거로 아래 구조의 Markdown 상황보고를 작성한다.
데이터에 없는 피해·원인·계획·예산·협조부서는 만들지 않는다. 명사형 종결.

---

# {report_date} 재난상황 일일보고

## 1. 총괄
- 총 {total}건 접수. 상태별 현황과 주요 유형·지역을 2~3줄로 요약(수치는 위 집계와 일치).

## 2. 유형별 발생현황

| 재난유형 | 건수 | 비고 |
|---------|------|------|
| (유형명) | N건 | |

(유형별 집계의 모든 유형을 건수 내림차순으로. 없으면 "해당없음")

## 3. 조치상황

| 상태 | 건수 |
|------|------|
| (상태명) | N건 |

(상태별 집계의 모든 상태를 반영: 발생/조치중/조치완료/모니터링/이상없음/해제·종결)

## 4. 읍면동별 발생현황
- 사건이 있는 읍면동을 건수 내림차순으로 개조식 정리. 없으면 "해당없음".

## 5. 주요 사건

| 읍면동 | 재난유형 | 상태 | 요약 |
|-------|---------|------|------|
| (읍면동) | (유형) | (상태) | (요약 30자 이내) |

(사건 목록 기반, 읍면동 정렬. 요약은 30자 이내, 원문 사실만)

## 6. 미조치·조치중 사건
- 상태가 '발생' 또는 '조치중'인 사건만 개조식으로 별도 정리.
- 각 항목: "○○동 ○○ 관련 신고 접수 — 관계부서 확인 및 후속조치 필요" 형태.
- 해당 사건이 없으면 "조치 중 사건 없음".

## 7. 향후 조치계획
- 사건 목록의 '향후계획/조치현황'에 실제 명시된 내용만 해당 사건과 함께 기술
  (예: 사건 요약에 "복구 예정"이 있으면 "○○동 ○○ 구간 복구 예정").
- 조치중·모니터링 사건은 "지속 예찰 및 후속조치", 미조치 사건은 "관계부서 확인 필요"로만 기술.
- 데이터에 없는 원인분석·항구복구·예산·협조·"안전 조치 강화"는 쓰지 않음.
- 사건을 특정하지 않은 뭉뚱그린 문장("기타 사건 지속 점검 강화 예정" 등) 금지. 근거 없으면 "특이 계획 없음".

## 8. 참고사항
- 위치가 읍면동까지만 확인된 사건, 미분류 사건 등 데이터 한계를 사실대로 기재. 없으면 생략.

---

주의: 모든 표는 Markdown 표 문법(| col | col |)을 사용하고, 수치는 위 집계와 정확히 일치시킨다.
"""


# =========================
# prompt_service 로드 (실패 시 폴백)
# =========================
def _get_prompt(key: str, default: str) -> str:
    """prompt_service.get() 래퍼. 모듈 미로드 시 default 반환."""
    try:
        from services.prompt_service import prompt_service
        return prompt_service.get("disaster_report", key, default=default)
    except Exception as e:
        logger.warning("prompt_service unavailable, using default for '%s': %s", key, e)
        return default


# =========================
# OpenAI 서비스 (프로젝트 공용)
# =========================
def _get_openai_service():
    """OpenAIService 인스턴스 획득. 실패 시 None."""
    try:
        from services.openai_service import OpenAIService
        return OpenAIService()
    except Exception as e:
        logger.warning("OpenAIService unavailable: %s", e)
        return None


# =========================
# 집계 유틸
# =========================
def _aggregate(incidents: List[Dict]) -> Dict:
    """사건 리스트에서 집계 데이터 추출.

    상태별 개별 카운트를 모두 반환해 총계와 상태별 합계가 일치하도록 함.
    - completed(하위호환): completed + closed 합산 (총괄/DB 카운트용)
    - in_progress(하위호환): in_progress
    - reported/monitoring/no_issue/closed_only/completed_only: 상태별 개별 카운트
    - no_issue(이상없음)는 completed(완료)에 포함하지 않음 → 사실 왜곡 방지
    """
    type_counter = Counter(i.get("incident_type") for i in incidents if i.get("incident_type"))
    status_counter = Counter(i.get("status") for i in incidents if i.get("status"))
    emd_counter = Counter((i.get("emd") or "미분류") for i in incidents)

    completed = sum(status_counter.get(s, 0) for s in COMPLETED_STATUSES)  # completed + closed
    in_progress = sum(status_counter.get(s, 0) for s in IN_PROGRESS_STATUSES)

    return {
        "total": len(incidents),
        "completed": completed,
        "in_progress": in_progress,
        # 상태별 개별 카운트 (총계 = 이들의 합)
        "reported": status_counter.get("reported", 0),
        "in_progress_only": status_counter.get("in_progress", 0),
        "completed_only": status_counter.get("completed", 0),
        "monitoring": status_counter.get("monitoring", 0),
        "no_issue": status_counter.get("no_issue", 0),
        "closed": status_counter.get("closed", 0),
        "type_counter": type_counter,
        "status_counter": status_counter,
        "emd_counter": emd_counter,
    }


def _format_emd_breakdown(emd_counter: Counter) -> str:
    """읍면동별 집계 텍스트. 미분류는 뒤로."""
    if not emd_counter:
        return "해당없음"
    parts = [f"{k} {v}건" for k, v in emd_counter.most_common() if k != "미분류"]
    unknown = emd_counter.get("미분류", 0)
    if unknown:
        parts.append(f"미분류 {unknown}건")
    return ", ".join(parts) if parts else "해당없음"


def _format_top_types(type_counter: Counter, n: int = 3) -> str:
    if not type_counter:
        return "해당없음"
    parts = [f"{incident_label(k)} {v}건" for k, v in type_counter.most_common(n)]
    return ", ".join(parts)


def _format_top_emds(emd_counter: Counter, n: int = 3) -> str:
    if not emd_counter:
        return "해당없음"
    parts = [f"{k} {v}건" for k, v in emd_counter.most_common(n)]
    return ", ".join(parts)


def _format_type_breakdown(type_counter: Counter) -> str:
    if not type_counter:
        return "해당없음"
    parts = [f"{incident_label(k)} {v}건" for k, v in type_counter.most_common()]
    return ", ".join(parts)


def _format_status_breakdown(status_counter: Counter) -> str:
    if not status_counter:
        return "해당없음"
    parts = [f"{status_label(k)} {v}건" for k, v in status_counter.most_common()]
    return ", ".join(parts)


def _format_incident_list_for_gpt(incidents: List[Dict], limit: int = MAX_INCIDENTS_IN_REPORT) -> str:
    """GPT 프롬프트용 사건 목록. 보고자 이름 제외(PII 보호)."""
    if not incidents:
        return "해당없음"

    lines = []
    for idx, inc in enumerate(incidents[:limit], start=1):
        emd = inc.get("emd") or "미분류"
        loc = inc.get("location_raw") or ""
        itype = incident_label(inc.get("incident_type"))
        stat = status_label(inc.get("status"))
        summary = (inc.get("summary") or "").strip()[:150]

        lines.append(
            f"{idx}. [{emd}] {loc} / {itype} / {stat} / {summary}".strip()
        )

    if len(incidents) > limit:
        lines.append(f"... (외 {len(incidents) - limit}건)")

    return "\n".join(lines)


# =========================
# GPT 호출 (async)
# =========================
async def _call_gpt(openai_service, system_prompt: str, user_prompt: str) -> Optional[str]:
    """
    OpenAIService.generate_text() 호출. 실패 시 None 반환.
    model="gpt-4o"로 override하여 보고서 품질 확보.
    """
    try:
        text = await openai_service.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=2000,
            temperature=0.3,
            model=REPORT_MODEL,
        )
        return text.strip() if text else None
    except Exception as e:
        logger.exception("GPT call failed: %s", type(e).__name__)
        return None


# =========================
# 폴백 템플릿 (기존 v7.0 방식)
# =========================
def _generate_fallback_summary(report_date: str, agg: Dict) -> str:
    if agg["total"] == 0:
        return f"{report_date} 기준 금일 접수 사건 없음"
    in_prog = (
        f"조치 중 {agg['in_progress']}건" if agg["in_progress"] else "조치 중 사건 없음"
    )
    return (
        f"{report_date} 기준 총 {agg['total']}건 접수, "
        f"조치완료·종결 {agg['completed']}건, {in_prog}"
    )


# =========================
# 후처리 정규화 (report_writer 원칙 이식)
# GPT가 프롬프트 규칙을 안 지켜도 코드가 최종적으로 문체를 교정.
# 표(| ...)·제목(#)·구분선은 손대지 않음 → Markdown 구조 보존.
# =========================
_ENDING_FIXES = [
    ("하였습니다", "하였음"), ("했습니다", "하였음"), ("하겠습니다", "할 예정임"),
    ("합니다", "함"), ("됩니다", "됨"), ("입니다", "임"),
    ("있습니다", "있음"), ("없습니다", "없음"),
    ("하였다", "하였음"), ("했다", "하였음"), ("한다", "함"),
    ("된다", "됨"), ("이다", "임"), ("있다", "있음"), ("없다", "없음"),
    # 일반 '~습니다'는 반드시 마지막 (구체 규칙 우선)
    ("습니다", "음"),
]


def _fix_line_ending(line: str) -> str:
    """한 줄의 종결어미를 명사형으로 교정. 매칭 없으면 원본 유지."""
    stripped = line.rstrip()
    trail = line[len(stripped):]
    core = stripped.rstrip(".")
    for wrong, right in _ENDING_FIXES:
        if core.endswith(wrong):
            return core[: -len(wrong)] + right + trail
    return line


def _postprocess_report_markdown(text: str) -> str:
    """생성된 Markdown 보고서 문체 후처리. 표/제목/구분선은 보존."""
    if not text:
        return text
    out = []
    for line in text.split("\n"):
        s = line.lstrip()
        if (
            not s
            or s.startswith("|")          # 표 행
            or s.startswith("#")          # 제목
            or set(s) <= set("-*_ ")      # 구분선/빈 불릿
        ):
            out.append(line)
            continue
        out.append(_fix_line_ending(line))
    return "\n".join(out)


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    """표준 Markdown 표 생성 (공백 포함, 범용 호환)."""
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    head = "| " + " | ".join(headers) + " |"
    body = "\n".join(
        "| " + " | ".join(c if c else " " for c in r) + " |"
        for r in rows
    )
    return f"{head}\n{sep}\n{body}"


def _generate_fallback_body(
    report_date: str,
    agg: Dict,
    incidents: List[Dict],
) -> str:
    """GPT 실패 시 템플릿 폴백. 데이터에 있는 사실만 사용(창작 금지)."""
    type_counter = agg["type_counter"]
    status_counter = agg["status_counter"]
    emd_counter = agg["emd_counter"]

    top3 = (
        ", ".join([f"{incident_label(k)} {v}건" for k, v in type_counter.most_common(3)])
        if type_counter else "해당없음"
    )
    top_emd = (
        ", ".join([f"{k} {v}건" for k, v in emd_counter.most_common(3) if k != "미분류"])
        or "해당없음"
    )

    # 1. 총괄
    if agg["total"] == 0:
        overview = f"- {report_date} 기준 금일 접수 사건 없음"
    else:
        overview = (
            f"- {report_date} 기준 총 {agg['total']}건 접수\n"
            f"- 조치완료·종결 {agg['completed']}건, 조치 중 {agg['in_progress']}건, "
            f"이상없음 {agg['no_issue']}건, 발생(미착수) {agg['reported']}건\n"
            f"- 주요 유형: {top3} / 주요 지역: {top_emd}"
        )

    # 2. 유형별 표
    type_rows = [
        [incident_label(code), f"{count}건", ""]
        for code, count in type_counter.most_common()
    ] or [["해당없음", "0건", ""]]
    type_table = _md_table(["재난유형", "건수", "비고"], type_rows)

    # 3. 상태별 표 (모든 상태 반영)
    status_rows = [
        [status_label(code), f"{count}건"]
        for code, count in status_counter.most_common()
    ] or [["해당없음", "0건"]]
    status_table = _md_table(["상태", "건수"], status_rows)

    # 4. 읍면동별 발생현황
    emd_lines = [
        f"- {k}: {v}건"
        for k, v in emd_counter.most_common()
        if k != "미분류"
    ]
    if emd_counter.get("미분류"):
        emd_lines.append(f"- 미분류(위치 미확인): {emd_counter['미분류']}건")
    emd_block = "\n".join(emd_lines) if emd_lines else "- 해당없음"

    # 5. 주요 사건 표 (읍면동별 정렬, 상한 적용)
    inc_sorted = sorted(
        incidents[:MAX_INCIDENTS_IN_REPORT], key=lambda x: x.get("emd") or ""
    )
    incident_rows = []
    for inc in inc_sorted:
        emd = inc.get("emd") or "미분류"
        itype = incident_label(inc.get("incident_type"))
        stat = status_label(inc.get("status"))
        summary = (inc.get("summary") or "")[:40].replace("|", "│")
        incident_rows.append([emd, itype, stat, summary])
    if not incident_rows:
        incident_rows = [["해당없음", "", "", ""]]
    incident_table = _md_table(["읍면동", "재난유형", "상태", "요약"], incident_rows)
    overflow_note = ""
    if len(incidents) > MAX_INCIDENTS_IN_REPORT:
        overflow_note = (
            f"\n\n- 표에는 상위 {MAX_INCIDENTS_IN_REPORT}건만 표기, "
            f"외 {len(incidents) - MAX_INCIDENTS_IN_REPORT}건은 읍면동별 발생현황 참조"
        )

    # 6. 미조치·조치중 사건 (발생 + 조치중만)
    pending = [
        inc for inc in incidents
        if inc.get("status") in ("reported", "in_progress")
    ]
    if pending:
        pending_lines = []
        for inc in pending[:MAX_INCIDENTS_IN_REPORT]:
            emd = inc.get("emd") or "미분류"
            loc = (inc.get("location_raw") or emd)
            itype = incident_label(inc.get("incident_type"))
            pending_lines.append(
                f"- {loc} {itype} 관련 신고 접수 — 관계부서 확인 및 후속조치 필요"
            )
        pending_block = "\n".join(pending_lines)
    else:
        pending_block = "- 조치 중 사건 없음"

    # 7. 향후 조치계획 (데이터 기반, 창작 금지)
    plan_lines = []
    if agg["in_progress"] or agg["monitoring"]:
        plan_lines.append("- 조치 중·모니터링 사건 지속 예찰 및 후속조치")
    if agg["reported"]:
        plan_lines.append("- 발생(미착수) 사건 관계부서 확인 필요")
    if not plan_lines:
        plan_lines.append("- 특이 계획 없음")
    plan_block = "\n".join(plan_lines)

    return (
        f"# {report_date} 재난상황 일일보고\n\n"
        f"## 1. 총괄\n\n"
        f"{overview}\n\n"
        f"## 2. 유형별 발생현황\n\n"
        f"{type_table}\n\n"
        f"## 3. 조치상황\n\n"
        f"{status_table}\n\n"
        f"## 4. 읍면동별 발생현황\n\n"
        f"{emd_block}\n\n"
        f"## 5. 주요 사건\n\n"
        f"{incident_table}{overflow_note}\n\n"
        f"## 6. 미조치·조치중 사건\n\n"
        f"{pending_block}\n\n"
        f"## 7. 향후 조치계획\n\n"
        f"{plan_block}\n"
    )


# =========================
# 메인 진입점 (async)
# =========================
async def generate_daily_report(report_date: str, incidents: List[Dict]) -> Dict:
    """
    일일보고서 생성 (비동기).

    1순위: GPT (OpenAIService, gpt-4o) + prompt_service로 자연어화
    2순위: 템플릿 폴백 (GPT 실패 또는 설정 누락 시)

    주의: 호출측은 반드시 await 사용.
    """
    agg = _aggregate(incidents)

    # 프롬프트 로드 (prompt_service → default 폴백)
    system_prompt = _get_prompt("system_prompt", _DEFAULT_SYSTEM_PROMPT)
    summary_template = _get_prompt("summary_prompt", _DEFAULT_SUMMARY_PROMPT)
    body_template = _get_prompt("body_prompt", _DEFAULT_BODY_PROMPT)

    # OpenAI 서비스
    openai_service = _get_openai_service()

    summary_text: Optional[str] = None
    report_text: Optional[str] = None
    used_gpt = False

    if openai_service is not None:
        try:
            # 요약 생성
            summary_user_prompt = summary_template.format(
                report_date=report_date,
                total=agg["total"],
                completed=agg["completed"],
                in_progress=agg["in_progress"],
                top_types=_format_top_types(agg["type_counter"]),
                top_emds=_format_top_emds(agg["emd_counter"]),
            )
            summary_text = await _call_gpt(openai_service, system_prompt, summary_user_prompt)

            # 본문 생성
            body_user_prompt = body_template.format(
                report_date=report_date,
                total=agg["total"],
                type_breakdown=_format_type_breakdown(agg["type_counter"]),
                status_breakdown=_format_status_breakdown(agg["status_counter"]),
                emd_breakdown=_format_emd_breakdown(agg["emd_counter"]),
                incident_list=_format_incident_list_for_gpt(incidents),
            )
            report_text = await _call_gpt(openai_service, system_prompt, body_user_prompt)

            if summary_text and report_text:
                used_gpt = True
        except KeyError as e:
            # 프롬프트 템플릿에 정의되지 않은 플레이스홀더 사용 시
            logger.exception("prompt template missing key: %s", e)
        except Exception as e:
            logger.exception("GPT report generation failed: %s", type(e).__name__)

    # 폴백
    if not summary_text:
        summary_text = _generate_fallback_summary(report_date, agg)
    if not report_text:
        report_text = _generate_fallback_body(report_date, agg, incidents)

    # 후처리 정규화 (GPT/폴백 공통) — 명사형 종결 강제, 표·제목은 보존
    summary_text = _postprocess_report_markdown(summary_text)
    report_text = _postprocess_report_markdown(report_text)

    logger.info(
        "daily report generated: date=%s, incidents=%d, used_gpt=%s",
        report_date, agg["total"], used_gpt,
    )

    return {
        "title": f"{report_date} 재난상황 일일보고",
        "summary_text": summary_text,
        "report_text": report_text,
        "total_incident_count": agg["total"],
        "completed_count": agg["completed"],
        "in_progress_count": agg["in_progress"],
    }


# =========================
# HWPX(한글) 내보내기
# =========================
def _md_report_to_sections(report_text: str) -> List[Dict]:
    """마크다운 일일보고 → hwpx_writer.build_hwpx용 sections 구조로 변환.

    - '# ' 대제목: 스킵(문서 title로 별도 처리)
    - '## ' : 새 섹션 (앞 'N. ' 번호 제거)
    - Markdown 표: 구분선/헤더 제외, 데이터행 셀을 ' · '로 결합해 한 줄로
      (hwpx_writer는 표 미지원 → 텍스트 라인으로 평탄화)
    - '-', '*' 불릿 / 숫자목록 / 일반 문단: 섹션 항목으로
    """
    import re as _re

    sections: List[Dict] = []
    current: Optional[Dict] = None
    lines = (report_text or "").split("\n")
    i = 0

    def _is_table_sep(s: str) -> bool:
        t = s.replace(" ", "")
        return len(t) > 2 and set(t) <= set("|:-") and "|" in t and "-" in t

    def _cells(row: str) -> List[str]:
        return [c.strip() for c in row.strip().strip("|").split("|")]

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # 대제목(#) 스킵
        if stripped.startswith("# "):
            i += 1
            continue

        # 섹션(##/###)
        m = _re.match(r"^#{2,3}\s+(.+)$", stripped)
        if m:
            title = _re.sub(r"^\d+\.\s*", "", m.group(1)).strip()
            current = {"title": title, "content": []}
            sections.append(current)
            i += 1
            continue

        if current is None:
            current = {"title": "", "content": []}
            sections.append(current)

        # 표 블록
        if stripped.startswith("|"):
            header_seen = False
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = lines[i].strip()
                i += 1
                if _is_table_sep(row):
                    continue
                cells = [c for c in _cells(row) if c]
                if not cells:
                    continue
                if not header_seen:
                    header_seen = True  # 헤더행 제외
                    continue
                current["content"].append(" · ".join(cells))
            continue

        # 불릿/숫자목록/문단 → 항목 (선행 마커 제거는 hwpx_writer가 처리)
        current["content"].append(stripped)
        i += 1

    return [s for s in sections if s["content"]]


def daily_report_to_hwpx_bytes(
    report_text: str,
    title: str,
    summary: str = "",
    report_date: str = "",
) -> bytes:
    """생성된 일일보고(Markdown)를 HWPX 바이너리로 변환.

    개인정보 보호: 보고자 이름은 보고서 본문에 포함되지 않으므로 그대로 변환.
    """
    from services.hwpx_writer import build_hwpx

    report = {
        "title": title or "재난상황 일일보고",
        "summary": (summary or "").strip(),
        "department": "재난안전상황실",
        "author": "",
        "report_date": report_date or "",
        "sections": _md_report_to_sections(report_text),
    }
    return build_hwpx(report)