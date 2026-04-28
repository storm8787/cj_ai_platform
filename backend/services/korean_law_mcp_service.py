"""
korean-law-mcp 연동 서비스

목표:
- 국가법령 검색/본문조회 시 korean-law-mcp를 우선 사용
- MCP 실패 시 기존 law.go.kr 직접 API 호출로 fallback 가능하도록 None/[] 반환
- 자치법규 벡터스토어 검색은 기존 law_chatbot.py에서 그대로 유지

전제:
- Dockerfile에서 npm install -g korean-law-mcp 설치
- 환경변수 LAW_OC 또는 LAW_API_OC 사용
- MCP 서버 명령: korean-law-mcp
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from config import settings

logger = logging.getLogger(__name__)


class KoreanLawMCPService:
    """korean-law-mcp Python 클라이언트 래퍼"""

    def __init__(self):
        self.enabled = getattr(settings, "KOREAN_LAW_MCP_ENABLED", "true").lower() == "true"
        self.command = getattr(settings, "KOREAN_LAW_MCP_COMMAND", "korean-law-mcp")
        self.timeout = int(getattr(settings, "KOREAN_LAW_MCP_TIMEOUT", 25))
        self.search_tool = getattr(settings, "KOREAN_LAW_MCP_SEARCH_TOOL", "search_law")
        self.text_tool = getattr(settings, "KOREAN_LAW_MCP_TEXT_TOOL", "get_law_text")
        self.all_search_tool = getattr(settings, "KOREAN_LAW_MCP_ALL_SEARCH_TOOL", "search_all")

    def _law_oc(self) -> str:
        """
        korean-law-mcp는 LAW_OC 환경변수를 사용.
        기존 프로젝트는 LAW_API_OC를 사용 중이므로 동일 값을 LAW_OC로 전달.
        """
        return getattr(settings, "LAW_API_OC", "") or getattr(settings, "LAW_OC", "")

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Any]:
        """
        MCP stdio 방식으로 도구 호출.
        mcp Python SDK가 없거나, MCP 서버 실행 실패 시 None 반환.
        """
        if not self.enabled:
            return None

        law_oc = self._law_oc()
        if not law_oc:
            logger.warning("[korean-law-mcp] LAW_API_OC/LAW_OC 미설정")
            return None

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except Exception as e:
            logger.warning(f"[korean-law-mcp] mcp Python SDK 로드 실패: {e}")
            return None

        server_params = StdioServerParameters(
            command=self.command,
            args=[],
            env={
                "LAW_OC": law_oc,
            },
        )

        try:
            async def _run():
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments)
                        return self._normalize_tool_result(result)

            return await asyncio.wait_for(_run(), timeout=self.timeout)

        except Exception as e:
            logger.warning(
                f"[korean-law-mcp] 도구 호출 실패 | tool={tool_name} | args={arguments} | error={e}"
            )
            return None

    def _normalize_tool_result(self, result: Any) -> Any:
        """
        MCP 응답을 Python 객체로 정규화.
        - TextContent JSON 문자열이면 dict/list로 변환
        - 일반 텍스트면 문자열 반환
        """
        if result is None:
            return None

        # MCP CallToolResult는 content 배열을 갖는 경우가 많음
        content = getattr(result, "content", None)
        if content is None:
            return result

        texts: List[str] = []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                texts.append(text)

        if not texts:
            return result

        merged = "\n".join(texts).strip()

        # JSON이면 객체로 변환
        try:
            return json.loads(merged)
        except Exception:
            return merged

    def _extract_items(self, raw: Any) -> List[Dict[str, Any]]:
        """
        MCP 검색 결과 구조가 버전에 따라 달라질 수 있으므로 최대한 방어적으로 list[dict] 추출.
        """
        if raw is None:
            return []

        if isinstance(raw, list):
            return [x for x in raw if isinstance(x, dict)]

        if isinstance(raw, dict):
            for key in ["results", "items", "laws", "data", "documents"]:
                value = raw.get(key)
                if isinstance(value, list):
                    return [x for x in value if isinstance(x, dict)]

            # 단건 결과
            if any(k in raw for k in ["lawName", "법령명", "name", "mst", "MST"]):
                return [raw]

        if isinstance(raw, str):
            # 텍스트 응답은 검색 결과 목록으로 정규화하기 어려우므로 빈 배열
            return []

        return []

    def _pick(self, data: Dict[str, Any], *keys: str, default: str = "") -> str:
        for key in keys:
            value = data.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return default

    def _normalize_search_item(self, item: Dict[str, Any], target: str = "law") -> Optional[Dict[str, Any]]:
        """
        korean-law-mcp 검색 결과를 기존 law_chatbot.py의 api_results 형식으로 맞춤.
        기존 프론트는 references/search_info 형식을 그대로 기대하므로 호환성이 중요.
        """
        mst = self._pick(
            item,
            "mst", "MST", "id", "lawId", "law_id", "법령일련번호", "법령ID", "자치법규일련번호",
        )
        name = self._pick(
            item,
            "lawName", "law_name", "name", "title", "법령명", "법령명한글", "자치법규명",
        )

        if not name:
            return None

        return {
            "id": mst,
            "name": name,
            "type": target,
            "category": self._pick(item, "lawType", "category", "법령구분명", "자치법규종류"),
            "ministry": self._pick(item, "ministry", "소관부처명"),
            "region": self._pick(item, "region", "지자체기관명", "자치단체명"),
            "enforcement_date": self._pick(item, "enforcementDate", "enforcement_date", "시행일자"),
            "status": self._pick(item, "status", "현행연혁코드"),
            "source": "korean-law-mcp",
            "raw": item,
        }

    async def search_law(self, query: str, target: str = "law", display: int = 10) -> List[Dict[str, Any]]:
        """
        국가법령 검색.
        target은 기존 호환을 위해 받지만, MCP 우선 적용 대상은 law 중심.
        """
        if target == "ordin":
            # 자치법규는 기존 벡터스토어 및 기존 API fallback을 우선 유지
            return []

        raw = await self._call_tool(
            self.search_tool,
            {
                "query": query,
            },
        )

        items = self._extract_items(raw)
        normalized: List[Dict[str, Any]] = []

        for item in items[:display]:
            row = self._normalize_search_item(item, target="law")
            if row:
                normalized.append(row)

        return normalized

    async def search_all(self, query: str, display: int = 10) -> List[Dict[str, Any]]:
        """
        통합검색 도구가 사용 가능한 경우 확장용.
        현재 law_chatbot.py에서는 우선 국가법령 검색 위주로 사용 권장.
        """
        raw = await self._call_tool(
            self.all_search_tool,
            {
                "query": query,
            },
        )

        items = self._extract_items(raw)
        normalized: List[Dict[str, Any]] = []

        for item in items[:display]:
            row = self._normalize_search_item(item, target="law")
            if row:
                normalized.append(row)

        return normalized

    async def get_law_text(
        self,
        mst: str = "",
        law_name: str = "",
        article: str = "",
        question: str = "",
    ) -> str:
        """
        법령 본문/조문 조회.
        korean-law-mcp README 기준 get_law_text는 mst, jo 사용 예시가 있음.
        article이 없으면 전문 또는 도구 기본 결과를 요청.
        """
        if not mst and not law_name:
            return ""

        args: Dict[str, Any] = {}

        if mst:
            args["mst"] = mst
        if law_name:
            args["lawName"] = law_name
        if article:
            args["jo"] = article

        raw = await self._call_tool(self.text_tool, args)
        if raw is None:
            return ""

        if isinstance(raw, str):
            return raw[:12000]

        if isinstance(raw, dict):
            # 자주 나올 수 있는 본문 키 방어적 처리
            for key in ["text", "content", "body", "lawText", "조문내용", "본문"]:
                value = raw.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()[:12000]

            try:
                return json.dumps(raw, ensure_ascii=False, indent=2)[:12000]
            except Exception:
                return str(raw)[:12000]

        if isinstance(raw, list):
            try:
                return json.dumps(raw, ensure_ascii=False, indent=2)[:12000]
            except Exception:
                return str(raw)[:12000]

        return str(raw)[:12000]

    async def check_connection(self) -> Dict[str, Any]:
        """MCP 연결 상태 확인"""
        if not self.enabled:
            return {
                "enabled": False,
                "connected": False,
                "reason": "KOREAN_LAW_MCP_ENABLED=false",
            }

        if not self._law_oc():
            return {
                "enabled": True,
                "connected": False,
                "reason": "LAW_API_OC/LAW_OC 미설정",
            }

        try:
            results = await self.search_law("헌법", display=1)
            return {
                "enabled": True,
                "connected": len(results) > 0,
                "result_count": len(results),
                "command": self.command,
            }
        except Exception as e:
            return {
                "enabled": True,
                "connected": False,
                "reason": str(e),
                "command": self.command,
            }


korean_law_mcp_service = KoreanLawMCPService()