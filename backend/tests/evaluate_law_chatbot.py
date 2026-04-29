"""
법령·자치법규 챗봇 자동 평가 스크립트

실행 방법:
  # 라이브 서버 대상 전체 평가
  python evaluate_law_chatbot.py --mode live --base-url http://localhost:8000

  # Planner만 평가 (서버 없이 OPENAI_API_KEY만 필요)
  python evaluate_law_chatbot.py --mode planner

  # Mock 평가 (API 키 없이 스크립트 구조 검증용)
  python evaluate_law_chatbot.py --mode mock

환경변수:
  OPENAI_API_KEY   : GPT 플래너 호출에 필요
  LAW_CHATBOT_URL  : 라이브 서버 base URL (기본값 http://localhost:8000)
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


CASES_PATH = Path(__file__).parent / "law_chatbot_eval_cases.json"


# ─────────────────────────────────────────────────────────────
# 평가 기준 적용
# ─────────────────────────────────────────────────────────────

def evaluate_answer(answer: str, case: Dict[str, Any]) -> Dict[str, Any]:
    """
    answer 텍스트가 평가 기준을 충족하는지 점검한다.
    반환: {passed, score, details}
    """
    details = []
    total = 0
    earned = 0

    # 1) required_keywords: 모두 포함되어야 함
    for kw in case.get("required_keywords", []):
        total += 1
        if kw in answer:
            earned += 1
            details.append({"check": f"필수 키워드 포함: {kw!r}", "ok": True})
        else:
            details.append({"check": f"필수 키워드 포함: {kw!r}", "ok": False})

    # 2) required_any_of: 각 그룹에서 최소 1개 이상 포함
    for group in case.get("required_any_of", []):
        total += 1
        hit = any(kw in answer for kw in group)
        if hit:
            earned += 1
            details.append({"check": f"그룹 키워드 중 하나 이상 포함: {group}", "ok": True})
        else:
            details.append({"check": f"그룹 키워드 중 하나 이상 포함: {group}", "ok": False})

    # 3) forbidden_phrases: 포함되면 안 됨 (감점)
    for phrase in case.get("forbidden_phrases", []):
        total += 1
        if phrase not in answer:
            earned += 1
            details.append({"check": f"금지 문구 없음: {phrase!r}", "ok": True})
        else:
            details.append({"check": f"금지 문구 없음: {phrase!r}", "ok": False})

    # 4) fail_if_only: 이것만 근거로 쓰면 실패 (다른 키워드가 있으면 통과)
    for phrase in case.get("fail_if_only", []):
        only_this = phrase in answer and not any(
            kw in answer
            for kw in (
                case.get("required_keywords", [])
                + [w for g in case.get("required_any_of", []) for w in g]
            )
            if kw != phrase
        )
        total += 1
        if not only_this:
            earned += 1
            details.append({"check": f"단일 근거 회피({phrase!r}) 통과", "ok": True})
        else:
            details.append({"check": f"단일 근거 회피({phrase!r}) 실패: 이것만 근거로 사용됨", "ok": False})

    score = round(earned / total * 100, 1) if total > 0 else 100.0
    passed = all(d["ok"] for d in details)

    return {
        "passed": passed,
        "score": score,
        "earned": earned,
        "total": total,
        "details": details,
    }


# ─────────────────────────────────────────────────────────────
# Planner 평가 (서버 없이 GPT Planner만 테스트)
# ─────────────────────────────────────────────────────────────

async def evaluate_planner(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    GPT 플래너가 올바른 search_plans를 생성하는지 평가한다.
    서버 없이 OPENAI_API_KEY만 있으면 실행 가능.
    """
    sys.path.insert(0, str(Path(__file__).parent.parent))

    try:
        from services.legal_query_planner import legal_query_planner
    except ImportError as e:
        return {"passed": False, "error": f"import 실패: {e}", "plan": None}

    try:
        plan = await legal_query_planner.create_plan(case["question"])
    except Exception as e:
        return {"passed": False, "error": f"플래너 오류: {e}", "plan": None}

    plans = plan.get("search_plans", [])
    all_text = json.dumps(plan, ensure_ascii=False)

    details = []
    earned = 0
    total = 0

    # 필수 키워드가 검색계획 어딘가에 등장하는지
    for kw in case.get("required_keywords", []):
        total += 1
        if kw in all_text:
            earned += 1
            details.append({"check": f"플래너 계획에 키워드 포함: {kw!r}", "ok": True})
        else:
            details.append({"check": f"플래너 계획에 키워드 포함: {kw!r}", "ok": False})

    # required_any_of 그룹도 플래너 계획에서 확인
    for group in case.get("required_any_of", []):
        total += 1
        hit = any(kw in all_text for kw in group)
        if hit:
            earned += 1
            details.append({"check": f"플래너 계획에 그룹 중 하나 포함: {group}", "ok": True})
        else:
            details.append({"check": f"플래너 계획에 그룹 중 하나 포함: {group}", "ok": False})

    # 시행령이 law target으로 분류되는지 확인 (잘못된 admrul 분류 방지)
    for p in plans:
        if p.get("target") == "admrul":
            name = p.get("law_name", "")
            if "시행령" in name or "시행규칙" in name:
                total += 1
                details.append({
                    "check": f"시행령/시행규칙이 admrul로 잘못 분류됨: {name!r}",
                    "ok": False
                })

    score = round(earned / total * 100, 1) if total > 0 else 100.0
    passed = all(d["ok"] for d in details)

    return {
        "passed": passed,
        "score": score,
        "earned": earned,
        "total": total,
        "details": details,
        "plan": plan,
    }


# ─────────────────────────────────────────────────────────────
# Live 평가 (실행 중인 서버 대상)
# ─────────────────────────────────────────────────────────────

async def evaluate_live(case: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    try:
        import httpx
    except ImportError:
        return {"passed": False, "error": "httpx 미설치 (pip install httpx)", "answer": ""}

    url = f"{base_url.rstrip('/')}/api/law-chatbot/ask"
    payload = {"question": case["question"], "search_scope": "all"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        return {"passed": False, "error": str(e), "answer": ""}

    answer = data.get("answer", "") or ""
    result = evaluate_answer(answer, case)
    result["answer_preview"] = answer[:400]
    result["search_info"] = data.get("search_info", {})
    return result


# ─────────────────────────────────────────────────────────────
# Mock 평가 (스크립트 구조 검증용)
# ─────────────────────────────────────────────────────────────

_MOCK_ANSWERS = {
    "TC-001": "공무원여비규정 제18조에 따르면 자가용 이용 시 자동차운임을 지급합니다.",
    "TC-002": "공공기관의 정보공개에 관한 법률 제9조에 따라 비공개 사유로는 개인정보, 법인 경영비밀 등이 있습니다.",
    "TC-003": "지방자치단체를 당사자로 하는 계약에 관한 법률 시행령 제25조에 따르면 수의계약 금액 기준은 2천만원 이하입니다.",
    "TC-004": "부정청탁 및 금품등 수수의 금지에 관한 법률(청탁금지법)에 따르면 음식물(식사 포함)은 3만원까지 허용됩니다.",
    "TC-005": "지방보조금 관리에 관한 법률에 따라 교부신청, 교부결정, 실적보고, 정산 절차가 필요합니다.",
    "TC-006": "도로법 위반 시 원상회복명령, 변상금 부과, 행정대집행, 과태료 부과가 가능합니다.",
    "TC-007": "지방공무원 수당 등에 관한 규정에 따라 육아휴직수당은 최초 3개월은 월봉급액의 80%를 지급합니다.",
    "TC-008": "개인정보 보호법 제17조에 따르면 정보주체의 동의를 받거나 법률상 근거가 있을 때 제3자 제공이 가능합니다.",
    "TC-009": "충주시 위원회 구성 및 운영에 관한 조례에 따르면 위원의 연임은 1회로 제한됩니다.",
    "TC-010": "경품 지급은 공직선거법상 기부행위 해당 여부를 검토해야 하며, 지방재정법상 예산집행 근거와 조례 근거가 필요합니다.",
}


async def evaluate_mock(case: Dict[str, Any]) -> Dict[str, Any]:
    answer = _MOCK_ANSWERS.get(case["id"], "")
    result = evaluate_answer(answer, case)
    result["answer_preview"] = answer
    result["note"] = "mock 답변 (실제 API 미호출)"
    return result


# ─────────────────────────────────────────────────────────────
# 결과 출력
# ─────────────────────────────────────────────────────────────

def print_summary(results: List[Dict[str, Any]]) -> None:
    passed = sum(1 for r in results if r.get("result", {}).get("passed", False))
    total = len(results)
    avg_score = sum(r.get("result", {}).get("score", 0) for r in results) / total if total else 0

    print("\n" + "=" * 60)
    print(f"  평가 결과: {passed}/{total} 통과  (평균 점수: {avg_score:.1f}점)")
    print("=" * 60)

    for r in results:
        case = r["case"]
        res = r.get("result", {})
        status = "✅ PASS" if res.get("passed") else "❌ FAIL"
        score = res.get("score", 0)
        print(f"\n[{case['id']}] {status}  {score:.1f}점  — {case['category']}")
        print(f"  Q: {case['question'][:60]}...")

        for d in res.get("details", []):
            mark = "  ✓" if d["ok"] else "  ✗"
            print(f"{mark} {d['check']}")

        if res.get("error"):
            print(f"  ⚠️ 오류: {res['error']}")


# ─────────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────────

async def main(mode: str, base_url: str, output: Optional[str], case_ids: List[str]) -> int:
    cases_data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = cases_data["cases"]

    if case_ids:
        cases = [c for c in cases if c["id"] in case_ids]

    results = []
    start = time.monotonic()

    for case in cases:
        print(f"\n▶ [{case['id']}] {case['question'][:50]}...")

        if mode == "live":
            res = await evaluate_live(case, base_url)
        elif mode == "planner":
            res = await evaluate_planner(case)
        else:
            res = await evaluate_mock(case)

        results.append({"case": case, "result": res})

        status = "PASS" if res.get("passed") else "FAIL"
        print(f"  → {status}  {res.get('score', 0):.1f}점")

    elapsed = time.monotonic() - start

    print_summary(results)
    print(f"\n  총 소요 시간: {elapsed:.1f}초")

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "mode": mode,
            "elapsed_seconds": round(elapsed, 1),
            "passed": sum(1 for r in results if r["result"].get("passed")),
            "total": len(results),
            "results": results,
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  결과 저장: {output}")

    any_failed = any(not r["result"].get("passed") for r in results)
    return 1 if any_failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="법령 챗봇 자동 평가")
    parser.add_argument(
        "--mode",
        choices=["live", "planner", "mock"],
        default="mock",
        help="live=서버 대상, planner=GPT 플래너만, mock=구조 검증",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("LAW_CHATBOT_URL", "http://localhost:8000"),
        help="라이브 서버 base URL",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="결과 JSON 저장 경로 (예: /tmp/eval_result.json)",
    )
    parser.add_argument(
        "--cases",
        nargs="*",
        default=[],
        help="특정 케이스 ID만 실행 (예: TC-001 TC-003)",
    )

    args = parser.parse_args()

    exit_code = asyncio.run(
        main(
            mode=args.mode,
            base_url=args.base_url,
            output=args.output,
            case_ids=args.cases,
        )
    )
    sys.exit(exit_code)
