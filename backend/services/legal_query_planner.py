"""
법령 챗봇 검색계획 생성 서비스

역할:
1. 사용자의 질문을 단순 키워드가 아니라 '법률 쟁점'과 '검색계획'으로 변환
2. 검색 대상별로 법령명/자치법규명/행정규칙명과 조문 탐색 키워드 생성
3. MCP/API 검색에 사용할 구조화된 search_plans 반환

설계 원칙:
- 법률 판단과 검색계획 수립은 GPT planner가 담당
- 코드는 GPT가 만든 JSON을 검증·정규화만 수행
- 법률 키워드 사전 기반 분기/예외처리는 사용하지 않음
- GPT planner 실패 시에도 사전 fallback이 아니라 원문 기반 통합검색만 수행
- planner가 특정 법령을 잘못 짚더라도, 원문/쟁점 기반 all 검색계획을 추가해 누락 가능성을 낮춤
"""

import json
from typing import Any, Dict, List

from openai import AsyncOpenAI

from config import settings
from services.prompt_service import prompt_service


_DEFAULT_LEGAL_QUERY_PLANNER_PROMPT = """
당신은 대한민국 법령·자치법규 검색 전문가입니다.
사용자의 질문을 단순 키워드가 아니라, 실제 답변에 필요한 법률 쟁점과 검색계획으로 변환하세요.

[핵심 목표]
- 사용자의 질문에 답하기 위해 어떤 국가법령, 자치법규, 행정규칙을 검색해야 하는지 판단합니다.
- 단순히 떠오르는 일반 법령명이 아니라, 질문을 직접 규율하는 특별법·개별법·시행령·규칙·고시·지침까지 검토합니다.
- 각 검색대상별로 조문 탐색에 필요한 키워드를 만듭니다.
- 결과는 반드시 JSON만 반환합니다.

[반환 형식]
{
  "issue_summary": "질문의 법률 쟁점 요약",
  "search_confidence": "high | medium | low",
  "search_plans": [
    {
      "target": "law | ordin | admrul | all",
      "law_name": "검색할 법령명 또는 자치법규명 또는 행정규칙명",
      "article_keywords": ["조문 탐색 키워드1", "조문 탐색 키워드2"],
      "reason": "왜 이 법령/조례/규칙을 봐야 하는지",
      "priority": 1
    }
  ]
}

[target 기준]
- law: 국가법령
- ordin: 자치법규
- admrul: 행정규칙·훈령·예규·고시·지침
- all: 검색대상이 불명확하거나 법령/자치법규/행정규칙을 모두 봐야 하는 경우

[검색계획 작성 원칙]
1. 질문의 법률 쟁점을 먼저 판단한 뒤, 필요한 검색계획을 우선순위 순으로 작성하세요.
2. 일반법보다 질문을 직접 규율하는 특별법·개별법·하위법령을 우선 고려하세요.
3. 특정 제도명, 금액, 수당, 허가, 보조금, 과태료, 점용, 계약, 개인정보, 청렴, 복무, 여비, 휴직, 조례 등 실무 용어가 있으면 해당 제도를 직접 다루는 법령·시행령·규칙을 우선 추론하세요.
4. 법령명이 불확실하면 확실하지 않은 법령명을 단정하지 말고 target을 all로 설정한 넓은 검색계획을 포함하세요.
5. 하나의 질문에 여러 법률 쟁점이 있으면 search_plans를 여러 개 생성하세요.
6. 각 search_plan의 law_name은 가능한 한 실제 검색 가능한 명칭으로 작성하세요.
7. article_keywords에는 조문 제목, 핵심 법률용어, 조문번호 후보, 실무 키워드를 포함하세요.
8. 자치법규가 필요한 질문은 target을 ordin으로 설정하고, 가능한 경우 지자체명과 조례명을 포함하세요.
9. 행정규칙·훈령·예규·고시·지침이 필요한 질문은 target을 admrul로 설정하세요.
10. 사용자의 질문에 오타가 의심되면, issue_summary와 article_keywords에는 자연스러운 정정 표현도 함께 반영하세요.
11. 검색계획은 보통 3~6개 이내로 작성하되, 단순 질문은 1~2개만 작성해도 됩니다.
12. 마지막에는 누락 방지를 위해 질문 원문 또는 쟁점 요약을 활용한 target=all 검색계획을 1개 포함하는 것이 좋습니다.
13. 반드시 JSON만 반환하세요. 설명문, 코드블록, 마크다운은 금지합니다.
14. 존재하지 않는 법령명이나 조문번호를 단정적으로 만들지 마세요. 불확실하면 article_keywords에 개념어 중심으로 작성하세요.

[스스로 점검할 사항]
- 질문을 직접 규율하는 법령을 놓치지 않았는가?
- 일반법만 보고 특별법·개별법을 누락하지 않았는가?
- 금액·수당·절차·제재·허가·보조금처럼 구체 기준을 묻는 질문인데, 해당 기준을 담은 시행령·규칙·고시·지침을 빠뜨리지 않았는가?
- 자치법규 질문인데 국가법령만 검색하도록 만들지 않았는가?
- 법령명이 불확실한데도 하나의 법령명만 단정하지 않았는가?
- 원문 기반 보완검색 계획이 포함되어 있는가?

[주의]
- 검색계획은 답변이 아닙니다.
- 검색계획은 실제 조문을 찾기 위한 경로입니다.
- 확실하지 않은 조문번호는 article_keywords에 후보로만 넣고, 최종 답변에서 단정하지 마세요.
"""


class LegalQueryPlanner:
    """법률 쟁점 기반 검색계획 생성기"""

    def __init__(self):
        self.model = "gpt-4o-mini"
        self.max_plans = 7
        self.max_article_keywords = 10

    async def create_plan(self, question: str) -> Dict[str, Any]:
        """
        질문을 법률 쟁점 및 검색계획으로 변환한다.

        처리 흐름:
        1. GPT planner 호출
        2. JSON 정리 및 파싱
        3. search_plans 정규화
        4. 원문/쟁점 기반 all 검색계획 자동 보강
        5. 실패 시 사전 기반이 아닌 원문 기반 통합검색 fallback 반환
        """
        question = (question or "").strip()

        if not question:
            return self._fallback_plan(question)

        planner_prompt = prompt_service.get(
            "law_chatbot",
            "legal_query_planner_prompt",
            default=_DEFAULT_LEGAL_QUERY_PLANNER_PROMPT,
        )

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": planner_prompt},
                    {"role": "user", "content": question},
                ],
                temperature=0.1,
                max_tokens=1500,
            )

            raw = response.choices[0].message.content.strip()
            raw = self._clean_json_text(raw)

            parsed = json.loads(raw)

            normalized = self._normalize_plan(parsed, question)

            if not normalized.get("search_plans"):
                raise ValueError("정규화 후 search_plans가 비어 있음")

            normalized = self._append_raw_query_plan(normalized, question)

            return normalized

        except Exception as e:
            print(f"[legal-query-planner] ⚠️ GPT 검색계획 생성 실패, 원문 기반 fallback 사용: {e}")
            return self._fallback_plan(question)

    def _normalize_plan(self, data: Any, question: str) -> Dict[str, Any]:
        """
        GPT가 반환한 JSON을 내부 표준 형식으로 정규화한다.

        중요:
        - 법률적 판단은 하지 않음
        - 법령명 사전 매핑도 하지 않음
        - 형식 검증, 공백 제거, 중복 제거만 수행
        """
        if not isinstance(data, dict):
            raise ValueError("planner 결과가 dict가 아님")

        issue_summary = str(data.get("issue_summary", "")).strip() or question

        search_confidence = str(data.get("search_confidence", "medium")).strip().lower()
        if search_confidence not in ("high", "medium", "low"):
            search_confidence = "medium"

        raw_plans = data.get("search_plans", [])

        if not isinstance(raw_plans, list):
            raise ValueError("search_plans가 list가 아님")

        normalized_plans: List[Dict[str, Any]] = []

        for idx, raw_plan in enumerate(raw_plans):
            if not isinstance(raw_plan, dict):
                continue

            target = str(raw_plan.get("target", "all")).strip().lower()
            if target not in ("law", "ordin", "admrul", "all"):
                target = "all"

            law_name = str(raw_plan.get("law_name", "")).strip()
            if not law_name:
                law_name = issue_summary or question

            article_keywords = raw_plan.get("article_keywords", [])

            if isinstance(article_keywords, str):
                article_keywords = [article_keywords]

            if not isinstance(article_keywords, list):
                article_keywords = []

            cleaned_keywords: List[str] = []
            for keyword in article_keywords:
                keyword_text = str(keyword).strip()
                if keyword_text and keyword_text not in cleaned_keywords:
                    cleaned_keywords.append(keyword_text)

            if not cleaned_keywords:
                cleaned_keywords = [issue_summary or question]

            reason = str(raw_plan.get("reason", "")).strip()

            priority = raw_plan.get("priority", idx + 1)
            try:
                priority = int(priority)
            except Exception:
                priority = idx + 1

            normalized_plans.append({
                "target": target,
                "law_name": law_name,
                "article_keywords": cleaned_keywords[:self.max_article_keywords],
                "reason": reason,
                "priority": priority,
            })

        normalized_plans = self._dedupe_plans(normalized_plans)
        normalized_plans.sort(key=lambda item: item.get("priority", 999))

        return {
            "issue_summary": issue_summary,
            "search_confidence": search_confidence,
            "search_plans": normalized_plans[:self.max_plans],
            "source": "gpt_planner",
        }

    def _append_raw_query_plan(self, plan: Dict[str, Any], question: str) -> Dict[str, Any]:
        """
        planner가 특정 법령을 잘못 짚는 경우를 줄이기 위한 범용 보강.

        중요:
        - 사전 기반 아님
        - 특정 법령명을 코드에서 추론하지 않음
        - 질문 원문과 GPT가 만든 issue_summary를 all 검색에 태움
        """
        issue_summary = str(plan.get("issue_summary", "")).strip() or question
        search_plans = plan.get("search_plans", [])

        if not isinstance(search_plans, list):
            search_plans = []

        raw_keywords = []
        for item in [question, issue_summary]:
            item = str(item).strip()
            if item and item not in raw_keywords:
                raw_keywords.append(item)

        raw_plan = {
            "target": "all",
            "law_name": issue_summary or question,
            "article_keywords": raw_keywords,
            "reason": "특정 법령명 누락을 방지하기 위한 질문 원문·쟁점 기반 통합 보완검색",
            "priority": 999,
        }

        # 이미 같은 all 보완검색이 있으면 추가하지 않음
        exists = False
        for existing in search_plans:
            if not isinstance(existing, dict):
                continue

            if (
                existing.get("target") == "all"
                and str(existing.get("law_name", "")).strip() in {question, issue_summary}
            ):
                exists = True
                break

        if not exists:
            search_plans.append(raw_plan)

        search_plans = self._dedupe_plans(search_plans)
        search_plans.sort(key=lambda item: item.get("priority", 999))

        plan["search_plans"] = search_plans[:self.max_plans]
        return plan

    def _fallback_plan(self, question: str) -> Dict[str, Any]:
        """
        GPT planner 실패 시 사용하는 최소 fallback.

        중요:
        - 사전 기반 법령 추론을 하지 않음
        - 질문 원문을 그대로 all 검색에 넘김
        - 코드가 법률 판단을 대신하지 않도록 설계
        """
        raw_query = (question or "").strip() or "법령 검색"

        return {
            "issue_summary": raw_query,
            "search_confidence": "low",
            "search_plans": [
                {
                    "target": "all",
                    "law_name": raw_query,
                    "article_keywords": [raw_query],
                    "reason": "GPT 검색계획 생성 실패로 인한 원문 기반 통합검색",
                    "priority": 1,
                }
            ],
            "source": "fallback_raw_query",
        }

    def _clean_json_text(self, text: str) -> str:
        """
        GPT 응답에서 JSON 객체만 추출한다.
        코드블록이나 앞뒤 설명이 섞여도 최대한 JSON 부분만 남긴다.
        """
        text = (text or "").strip()
        text = text.replace("```json", "").replace("```", "").strip()

        start = text.find("{")
        end = text.rfind("}")

        if start >= 0 and end >= 0 and end > start:
            return text[start:end + 1]

        return text

    def _dedupe_plans(self, plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        검색계획 중복 제거.
        법령 사전 매핑 없이 target/law_name/article_keywords 기준으로만 단순 중복 제거.
        """
        seen = set()
        unique: List[Dict[str, Any]] = []

        for plan in plans:
            if not isinstance(plan, dict):
                continue

            target = str(plan.get("target", "all")).strip()
            law_name = str(plan.get("law_name", "")).strip()

            article_keywords = plan.get("article_keywords", [])
            if isinstance(article_keywords, list):
                keyword_key = "|".join(str(k).strip() for k in article_keywords if str(k).strip())
            else:
                keyword_key = str(article_keywords).strip()

            key = f"{target}::{law_name}::{keyword_key}"

            if key in seen:
                continue

            seen.add(key)
            unique.append(plan)

        return unique


legal_query_planner = LegalQueryPlanner()