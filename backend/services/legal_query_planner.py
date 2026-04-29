"""
법령 챗봇 검색계획 생성 서비스

역할:
1. 사용자의 질문을 단순 키워드가 아니라 '법률 쟁점'과 '검색계획'으로 변환
2. 검색 대상별로 법령명/자치법규명/행정규칙명과 조문 탐색 키워드 생성
3. MCP/API 검색에 사용할 구조화된 search_plans 반환

설계 원칙:
- 법률 판단과 검색계획 수립은 GPT planner가 담당
- 코드는 GPT가 만든 JSON을 검증·정규화만 수행
- 사전 기반 키워드 분기/예외처리는 사용하지 않음
- GPT planner 실패 시에도 사전 fallback이 아니라 원문 기반 통합검색만 수행
"""

import json
import re
from typing import Any, Dict, List

from openai import AsyncOpenAI

from config import settings
from services.prompt_service import prompt_service


_DEFAULT_LEGAL_QUERY_PLANNER_PROMPT = """
당신은 대한민국 법령·자치법규 검색 전문가입니다.
사용자의 질문을 단순 키워드가 아니라, 실제 답변에 필요한 법률 쟁점과 검색계획으로 변환하세요.

[목표]
- 사용자의 질문에 답하기 위해 어떤 국가법령, 자치법규, 행정규칙을 검색해야 하는지 판단합니다.
- 각 검색대상별로 조문 검색에 필요한 키워드를 만듭니다.
- 결과는 반드시 JSON만 반환합니다.

[반환 형식]
{
  "issue_summary": "질문의 법률 쟁점 요약",
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
- admrul: 행정규칙·훈령·예규
- all: 검색대상이 불명확하거나 법령/자치법규/행정규칙을 모두 봐야 하는 경우

[작성 규칙]
1. 질문의 법률 쟁점을 먼저 판단한 뒤, 필요한 검색계획을 우선순위 순으로 작성하세요.
2. 하나의 질문에 여러 법률 쟁점이 있으면 search_plans를 여러 개 생성하세요.
3. 각 search_plan의 law_name은 가능한 한 실제 검색 가능한 명칭으로 작성하세요.
4. article_keywords에는 조문 제목, 핵심 법률용어, 조문번호 후보, 실무 키워드를 포함하세요.
5. 법령명이 확실하지 않으면 law_name에는 넓은 검색어를 넣고 target은 all로 둘 수 있습니다.
6. 자치법규가 필요한 질문은 target을 ordin으로 설정하고, 가능한 경우 지자체명과 조례명을 포함하세요.
7. 행정규칙·훈령·예규·고시·지침이 필요한 질문은 target을 admrul로 설정하세요.
8. 검색계획은 보통 3~6개 이내로 작성하되, 단순 질문은 1~2개만 작성해도 됩니다.
9. 반드시 JSON만 반환하세요. 설명문, 코드블록, 마크다운은 금지합니다.
10. 존재하지 않는 법령명이나 조문번호를 단정적으로 만들지 마세요. 불확실하면 article_keywords에 개념어 중심으로 작성하세요.

[좋은 반환 예시 1]
질문: 지방자치단체가 이벤트로 시민들에게 경품을 지급할 수 있나?

{
  "issue_summary": "지방자치단체의 시민 대상 경품 지급 가능 여부",
  "search_plans": [
    {
      "target": "law",
      "law_name": "공직선거법",
      "article_keywords": ["기부행위", "금품 제공", "지방자치단체", "후보자", "제112조", "제113조"],
      "reason": "지방자치단체의 경품 제공이 공직선거법상 기부행위 제한에 해당할 수 있으므로 우선 검토가 필요함",
      "priority": 1
    },
    {
      "target": "law",
      "law_name": "지방재정법",
      "article_keywords": ["예산의 목적 외 사용금지", "지출 근거", "예산 집행"],
      "reason": "경품 구입·지급을 위한 예산 지출 가능성과 목적 외 사용 여부 검토가 필요함",
      "priority": 2
    },
    {
      "target": "law",
      "law_name": "지방자치법",
      "article_keywords": ["조례", "법령의 범위", "지방자치단체의 사무"],
      "reason": "지방자치단체가 조례 또는 자치사무 근거로 경품 지급 사업을 할 수 있는지 검토가 필요함",
      "priority": 3
    }
  ]
}

[좋은 반환 예시 2]
질문: 충주시 위원회 조례에 따르면 위원들은 몇 번까지 연임 가능해?

{
  "issue_summary": "충주시 위원회 관련 자치법규상 위원 연임 가능 횟수",
  "search_plans": [
    {
      "target": "ordin",
      "law_name": "충주시 위원회 조례",
      "article_keywords": ["위원의 임기", "임기", "연임", "위원"],
      "reason": "충주시 자치법규에서 위원의 임기와 연임 제한 조문을 확인해야 함",
      "priority": 1
    }
  ]
}

[좋은 반환 예시 3]
질문: 개인정보보호법에서 개인정보 제3자 제공 기준 알려줘

{
  "issue_summary": "개인정보의 제3자 제공 가능 기준",
  "search_plans": [
    {
      "target": "law",
      "law_name": "개인정보 보호법",
      "article_keywords": ["제3자 제공", "정보주체의 동의", "법률에 특별한 규정", "제17조"],
      "reason": "개인정보 제3자 제공의 일반 기준을 확인해야 함",
      "priority": 1
    },
    {
      "target": "law",
      "law_name": "개인정보 보호법",
      "article_keywords": ["목적 외 이용", "목적 외 제공", "제18조"],
      "reason": "제3자 제공이 목적 외 제공에 해당하는 경우도 함께 검토할 필요가 있음",
      "priority": 2
    }
  ]
}
"""


class LegalQueryPlanner:
    """법률 쟁점 기반 검색계획 생성기"""

    def __init__(self):
        self.model = "gpt-4o-mini"
        self.max_plans = 6
        self.max_article_keywords = 8

    async def create_plan(self, question: str) -> Dict[str, Any]:
        """
        질문을 법률 쟁점 및 검색계획으로 변환한다.

        처리 흐름:
        1. GPT planner 호출
        2. JSON 정리 및 파싱
        3. search_plans 정규화
        4. 실패 시 사전 기반이 아닌 원문 기반 통합검색 fallback 반환
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
                max_tokens=1200,
            )

            raw = response.choices[0].message.content.strip()
            raw = self._clean_json_text(raw)

            parsed = json.loads(raw)

            normalized = self._normalize_plan(parsed, question)

            if not normalized.get("search_plans"):
                raise ValueError("정규화 후 search_plans가 비어 있음")

            return normalized

        except Exception as e:
            print(f"[legal-query-planner] ⚠️ GPT 검색계획 생성 실패, 원문 기반 fallback 사용: {e}")
            return self._fallback_plan(question)

    def _normalize_plan(self, data: Any, question: str) -> Dict[str, Any]:
        """
        GPT가 반환한 JSON을 내부 표준 형식으로 정규화한다.
        법률적 판단은 하지 않고, 형식 검증과 값 보정만 수행한다.
        """
        if not isinstance(data, dict):
            raise ValueError("planner 결과가 dict가 아님")

        issue_summary = str(data.get("issue_summary", "")).strip() or question
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
                law_name = question

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
                cleaned_keywords = [question]

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

        normalized_plans.sort(key=lambda item: item.get("priority", 999))

        return {
            "issue_summary": issue_summary,
            "search_plans": normalized_plans[:self.max_plans],
            "source": "gpt_planner",
        }

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


legal_query_planner = LegalQueryPlanner()