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


# =========================
# 기본(폴백) 프롬프트
# =========================
_DEFAULT_SYSTEM_PROMPT = """당신은 충주시청 재난안전 담당 공무원의 일일보고서 작성을 돕는 AI 비서입니다.

다음 원칙을 반드시 지키세요:
1. 출력 형식은 반드시 **Markdown(.md)** 형식으로 작성.
2. 공문서 문체 사용. 경어체(~합니다, ~입니다) 금지. 단어형 종결 사용(예: "발생", "완료", "조치 중").
3. 개인정보(보고자 이름) 노출 금지. 부서명/기관명은 그대로 사용 가능.
4. 객관적 사실만 기술. 추측/과장 표현 금지.
5. 주어진 사건 데이터 외의 내용을 창작하지 말 것.
6. 숫자는 정확히 반영. 카운트가 0인 항목은 "해당없음"으로 표기.
7. 유형별 발생현황, 조치상황은 반드시 Markdown 표 형식으로 작성.
8. 주요 사건은 읍면동별로 묶어 Markdown 표(읍면동|재난유형|상태|요약)로 작성.
"""


_DEFAULT_SUMMARY_PROMPT = """다음은 {report_date} 기준 충주시 재난상황 집계 데이터입니다.

[집계 데이터]
- 총 사건 수: {total}건
- 조치완료(해제 포함): {completed}건
- 조치중: {in_progress}건
- 주요 유형: {top_types}
- 주요 발생지역: {top_emds}

이 데이터를 바탕으로 일일보고서 상단에 들어갈 한 문장의 요약문을 작성하세요.
분량은 100자 이내, 공문서 문체로 작성하세요.

요약문만 출력하고 다른 설명은 붙이지 마세요.
"""


_DEFAULT_BODY_PROMPT = """다음은 {report_date} 기준 충주시 재난상황 집계 및 주요 사건 목록입니다.

[집계]
- 총 사건 수: {total}건
- 유형별: {type_breakdown}
- 상태별: {status_breakdown}

[주요 사건 목록]
{incident_list}

위 데이터를 바탕으로 아래 형식의 Markdown 일일보고서를 작성하세요.
공문서 문체(단어형 종결). 경어체 금지.

---

# {report_date} 재난상황 일일보고

## 1. 재난상황 총괄
(총괄 요약 2~3줄. 총 사건 수, 주요 유형, 주요 지역 포함)

## 2. 유형별 발생현황

| 재난유형 | 건수 | 비고 |
|---------|------|------|
| (유형명) | N건 | |

## 3. 조치상황

| 상태 | 건수 |
|------|------|
| (상태명) | N건 |

## 4. 주요 사건

| 읍면동 | 재난유형 | 상태 | 요약 |
|-------|---------|------|------|
| (읍면동) | (유형) | (상태) | (요약 30자 이내) |

## 5. 향후 조치계획
- (실제 데이터에 기반한 조치 계획 2~3항목)

---

주의: 표는 반드시 Markdown 표 문법(| col | col |)을 사용하고, 데이터는 제공된 사건 목록 기반으로만 작성하세요.
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
    """사건 리스트에서 집계 데이터 추출"""
    type_counter = Counter(i.get("incident_type") for i in incidents if i.get("incident_type"))
    status_counter = Counter(i.get("status") for i in incidents if i.get("status"))
    emd_counter = Counter((i.get("emd") or "미분류") for i in incidents)

    completed = sum(status_counter.get(s, 0) for s in COMPLETED_STATUSES)
    in_progress = sum(status_counter.get(s, 0) for s in IN_PROGRESS_STATUSES)

    return {
        "total": len(incidents),
        "completed": completed,
        "in_progress": in_progress,
        "type_counter": type_counter,
        "status_counter": status_counter,
        "emd_counter": emd_counter,
    }


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


def _format_incident_list_for_gpt(incidents: List[Dict], limit: int = 20) -> str:
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
    return (
        f"{report_date} 기준 총 {agg['total']}건 분석, "
        f"완료 {agg['completed']}건, 조치중 {agg['in_progress']}건"
    )


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
    type_counter = agg["type_counter"]
    status_counter = agg["status_counter"]

    top3 = (
        ", ".join([f"{incident_label(k)} {v}건" for k, v in type_counter.most_common(3)])
        if type_counter else "해당없음"
    )

    # 유형별 표
    type_rows = [
        [incident_label(code), f"{count}건", ""]
        for code, count in type_counter.most_common()
    ] or [["해당없음", "0건", ""]]
    type_table = _md_table(["재난유형", "건수", "비고"], type_rows)

    # 상태별 표
    status_rows = [
        [status_label(code), f"{count}건"]
        for code, count in status_counter.most_common()
    ] or [["해당없음", "0건"]]
    status_table = _md_table(["상태", "건수"], status_rows)

    # 주요 사건 표 (읍면동별 정렬)
    inc_sorted = sorted(incidents[:20], key=lambda x: x.get("emd") or "")
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

    return (
        f"# {report_date} 재난상황 일일보고\n\n"
        f"## 1. 재난상황 총괄\n\n"
        f"- {report_date} 기준 카카오톡 상황보고 분석 결과, 총 **{agg['total']}건** 유효 사건 확인\n"
        f"- 주요 유형: {top3}\n"
        f"- 조치완료·해제: {agg['completed']}건 / 조치중: {agg['in_progress']}건\n\n"
        f"## 2. 유형별 발생현황\n\n"
        f"{type_table}\n\n"
        f"## 3. 조치상황\n\n"
        f"{status_table}\n\n"
        f"## 4. 주요 사건\n\n"
        f"{incident_table}\n\n"
        f"## 5. 향후 조치계획\n\n"
        f"- 조치중·모니터링 사건 지속 현장 예찰 및 후속조치 추진\n"
        f"- 반복 발생 지역 원인분석 및 항구복구 필요성 검토\n"
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