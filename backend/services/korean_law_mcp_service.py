"""
korean-law-mcp CLI 연동 서비스

목표:
- Python mcp 패키지 없이 동작
- Dockerfile에서 npm install -g korean-law-mcp 설치된 CLI를 subprocess로 호출
- 국가법령 / 자치법규 / 행정규칙 검색 지원
- 실패 시 law_chatbot.py의 기존 law.go.kr 직접 API fallback이 작동하도록 [] 또는 "" 반환

전제:
- Dockerfile에 npm install -g korean-law-mcp 추가
- LAW_API_OC 환경변수는 기존 그대로 사용
- korean-law-mcp 패키지가 제공하는 CLI 명령어는 korean-law 기준으로 호출
"""

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from config import settings

logger = logging.getLogger(__name__)


class KoreanLawMCPService:
    """korean-law-mcp CLI 래퍼 서비스"""

    def __init__(self):
        self.enabled = str(getattr(settings, "KOREAN_LAW_MCP_ENABLED", "true")).lower() == "true"
        self.timeout = int(getattr(settings, "KOREAN_LAW_MCP_TIMEOUT", 25))

        # npm install -g korean-law-mcp 시 생성되는 CLI
        self.cli_command = getattr(settings, "KOREAN_LAW_MCP_CLI_COMMAND", "korean-law")

        # 국가법령
        self.search_tool = getattr(settings, "KOREAN_LAW_MCP_SEARCH_TOOL", "search_law")
        self.text_tool = getattr(settings, "KOREAN_LAW_MCP_TEXT_TOOL", "get_law_text")

        # 통합검색
        self.all_search_tool = getattr(settings, "KOREAN_LAW_MCP_ALL_SEARCH_TOOL", "search_all")

        # 자치법규
        self.ordinance_search_tool = getattr(
            settings,
            "KOREAN_LAW_MCP_ORDINANCE_SEARCH_TOOL",
            "search_ordinance",
        )
        self.ordinance_text_tool = getattr(
            settings,
            "KOREAN_LAW_MCP_ORDINANCE_TEXT_TOOL",
            "get_ordinance",
        )

        # 행정규칙: 훈령·예규·고시·공고
        self.admin_rule_search_tool = getattr(
            settings,
            "KOREAN_LAW_MCP_ADMIN_RULE_SEARCH_TOOL",
            "search_admin_rule",
        )
        self.admin_rule_text_tool = getattr(
            settings,
            "KOREAN_LAW_MCP_ADMIN_RULE_TEXT_TOOL",
            "get_admin_rule",
        )

    def _law_oc(self) -> str:
        """
        korean-law-mcp는 LAW_OC 환경변수를 사용.
        기존 프로젝트는 LAW_API_OC를 사용하므로 같은 값을 LAW_OC로 넘김.
        """
        return getattr(settings, "LAW_API_OC", "") or os.getenv("LAW_OC", "")

    async def _run_cli(self, args: List[str]) -> Optional[str]:
        """
        korean-law CLI 실행.
        실패하면 None 반환하여 기존 law.go.kr API fallback이 작동하도록 함.
        """
        if not self.enabled:
            logger.info("[korean-law-mcp] disabled")
            return None

        law_oc = self._law_oc()
        if not law_oc:
            logger.warning("[korean-law-mcp] LAW_API_OC/LAW_OC 미설정")
            return None

        env = os.environ.copy()
        env["LAW_OC"] = law_oc

        cmd = [self.cli_command] + args

        try:
            logger.info(f"[korean-law-mcp] CLI 호출: {' '.join(cmd)}")

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                logger.warning(f"[korean-law-mcp] CLI timeout: {' '.join(cmd)}")
                return None

            out = stdout.decode("utf-8", errors="ignore").strip()
            err = stderr.decode("utf-8", errors="ignore").strip()

            if proc.returncode != 0:
                logger.warning(
                    f"[korean-law-mcp] CLI 실패 rc={proc.returncode} | "
                    f"cmd={' '.join(cmd)} | stderr={err[:500]}"
                )
                return None

            if not out:
                logger.warning(f"[korean-law-mcp] CLI stdout 비어있음 | stderr={err[:500]}")
                return None

            return out

        except FileNotFoundError:
            logger.warning(
                f"[korean-law-mcp] CLI 명령어를 찾을 수 없음: {self.cli_command}. "
                f"Dockerfile에 npm install -g korean-law-mcp 설치 필요"
            )
            return None
        except Exception as e:
            logger.warning(f"[korean-law-mcp] CLI 실행 예외: {e}")
            return None

    def _try_parse_json(self, text: str) -> Any:
        """
        CLI 출력에서 JSON 추출 시도.
        """
        if not text:
            return None

        cleaned = text.strip()
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(cleaned)
        except Exception:
            pass

        array_match = re.search(r"(\[[\s\S]*\])", cleaned)
        if array_match:
            try:
                return json.loads(array_match.group(1))
            except Exception:
                pass

        obj_match = re.search(r"(\{[\s\S]*\})", cleaned)
        if obj_match:
            try:
                return json.loads(obj_match.group(1))
            except Exception:
                pass

        return cleaned

    def _extract_items(self, raw: Any) -> List[Dict[str, Any]]:
        """
        CLI/MCP 검색 결과 구조가 버전에 따라 다를 수 있으므로 방어적으로 list[dict] 추출.
        """
        if raw is None:
            return []

        if isinstance(raw, list):
            return [x for x in raw if isinstance(x, dict)]

        if isinstance(raw, dict):
            for key in [
                "results",
                "items",
                "laws",
                "ordinances",
                "adminRules",
                "admin_rules",
                "data",
                "documents",
                "law",
                "result",
            ]:
                value = raw.get(key)
                if isinstance(value, list):
                    return [x for x in value if isinstance(x, dict)]

            if any(
                k in raw
                for k in [
                    "lawName",
                    "ordinanceName",
                    "adminRuleName",
                    "법령명",
                    "자치법규명",
                    "행정규칙명",
                    "name",
                    "title",
                    "mst",
                    "MST",
                    "ordinSeq",
                    "법령일련번호",
                    "자치법규일련번호",
                ]
            ):
                return [raw]

        return []

    def _pick(self, data: Dict[str, Any], *keys: str, default: str = "") -> str:
        """여러 후보 키 중 첫 번째 유효값 반환"""
        for key in keys:
            value = data.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return default

    def _normalize_search_item(self, item: Dict[str, Any], target: str = "law") -> Optional[Dict[str, Any]]:
        """
        korean-law 검색 결과를 기존 law_chatbot.py의 api_results 형식으로 맞춤.
        """
        mst = self._pick(
            item,
            "mst",
            "MST",
            "id",
            "lawId",
            "law_id",
            "ordinSeq",
            "ordin_seq",
            "adminRuleId",
            "admin_rule_id",
            "법령일련번호",
            "법령ID",
            "자치법규일련번호",
            "행정규칙일련번호",
        )

        name = self._pick(
            item,
            "lawName",
            "law_name",
            "ordinanceName",
            "ordinance_name",
            "adminRuleName",
            "admin_rule_name",
            "name",
            "title",
            "법령명",
            "법령명한글",
            "자치법규명",
            "행정규칙명",
        )

        if not name:
            return None

        return {
            "id": mst,
            "name": name,
            "type": target,
            "category": self._pick(
                item,
                "lawType",
                "law_type",
                "category",
                "type",
                "법령구분명",
                "자치법규종류",
                "행정규칙종류",
            ),
            "ministry": self._pick(item, "ministry", "소관부처명"),
            "region": self._pick(item, "region", "localGov", "지자체기관명", "자치단체명"),
            "enforcement_date": self._pick(
                item,
                "enforcementDate",
                "enforcement_date",
                "effectiveDate",
                "시행일자",
            ),
            "status": self._pick(item, "status", "현행연혁코드"),
            "source": "korean-law-mcp-cli",
            "raw": item,
        }

    def _text_to_fallback_items(self, text: str, target: str = "law") -> List[Dict[str, Any]]:
        """
        CLI가 JSON이 아니라 표/텍스트로 출력하는 경우 최소한의 검색 결과로 변환.
        """
        if not text:
            return []

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        items: List[Dict[str, Any]] = []

        for line in lines:
            if len(items) >= 10:
                break

            if line.startswith("[") or line.startswith("{"):
                continue
            if "검색" in line and "결과" in line:
                continue

            name = line
            name = re.sub(r"^\d+[\.\)]\s*", "", name).strip()
            name = re.sub(r"\s{2,}.*$", "", name).strip()

            if 2 <= len(name) <= 100:
                items.append({
                    "id": "",
                    "name": name,
                    "type": target,
                    "category": "",
                    "ministry": "",
                    "region": "",
                    "enforcement_date": "",
                    "status": "",
                    "source": "korean-law-mcp-cli-text",
                    "raw": {"line": line},
                })

        return items

    async def search_law(self, query: str, target: str = "law", display: int = 10) -> List[Dict[str, Any]]:
        """
        국가법령 검색.
        공식 MCP 도구명: search_law
        """
        if target == "ordin":
            return []

        if not query or not query.strip():
            return []

        text = await self._run_cli([
            self.search_tool,
            "--query",
            query.strip(),
        ])

        if not text:
            return []

        raw = self._try_parse_json(text)
        items = self._extract_items(raw)

        normalized: List[Dict[str, Any]] = []

        if items:
            for item in items[:display]:
                row = self._normalize_search_item(item, target="law")
                if row:
                    row["source"] = "korean-law-mcp-law"
                    normalized.append(row)
        else:
            normalized = self._text_to_fallback_items(text, target="law")[:display]
            for row in normalized:
                row["source"] = "korean-law-mcp-law-text"

        return normalized

    async def search_ordinance(self, query: str, display: int = 10) -> List[Dict[str, Any]]:
        """
        자치법규 검색.
        공식 MCP 도구명: search_ordinance
        """
        if not query or not query.strip():
            return []

        q = query.strip()

        # 충주시 플랫폼이므로 자치법규 질문은 충주시를 보강
        if "충주" not in q:
            q = f"충주시 {q}"

        text = await self._run_cli([
            self.ordinance_search_tool,
            "--query",
            q,
        ])

        if not text:
            return []

        raw = self._try_parse_json(text)
        items = self._extract_items(raw)

        normalized: List[Dict[str, Any]] = []

        if items:
            for item in items[:display]:
                row = self._normalize_search_item(item, target="ordin")
                if row:
                    row["source"] = "korean-law-mcp-ordinance"
                    normalized.append(row)
        else:
            normalized = self._text_to_fallback_items(text, target="ordin")[:display]
            for row in normalized:
                row["source"] = "korean-law-mcp-ordinance-text"

        return normalized

    async def search_admin_rule(self, query: str, display: int = 10) -> List[Dict[str, Any]]:
        """
        행정규칙 검색: 훈령·예규·고시·공고
        공식 MCP 도구명: search_admin_rule
        """
        if not query or not query.strip():
            return []

        text = await self._run_cli([
            self.admin_rule_search_tool,
            "--query",
            query.strip(),
        ])

        if not text:
            return []

        raw = self._try_parse_json(text)
        items = self._extract_items(raw)

        normalized: List[Dict[str, Any]] = []

        if items:
            for item in items[:display]:
                row = self._normalize_search_item(item, target="admrul")
                if row:
                    row["source"] = "korean-law-mcp-admin-rule"
                    normalized.append(row)
        else:
            normalized = self._text_to_fallback_items(text, target="admrul")[:display]
            for row in normalized:
                row["source"] = "korean-law-mcp-admin-rule-text"

        return normalized

    async def search_all(self, query: str, display: int = 10) -> List[Dict[str, Any]]:
        """
        통합 검색.
        공식 MCP 도구명: search_all
        """
        if not query or not query.strip():
            return []

        text = await self._run_cli([
            self.all_search_tool,
            "--query",
            query.strip(),
        ])

        if not text:
            return []

        raw = self._try_parse_json(text)
        items = self._extract_items(raw)

        normalized: List[Dict[str, Any]] = []
        for item in items[:display]:
            row = self._normalize_search_item(item, target="law")
            if row:
                row["source"] = "korean-law-mcp-all"
                normalized.append(row)

        return normalized

async def search_unified(self, query: str, display: int = 15) -> List[Dict[str, Any]]:
    """
    통합검색용 함수.

    핵심 정책:
    - 자치법규 의심 질문이면 search_ordinance만 호출하고 종료
      ※ search_all/search_law로 넘어가지 않음
    - 행정규칙 의심 질문이면 search_admin_rule만 우선 호출
    - 일반 국가법령 질문만 search_all → search_law 순서로 검색
    """
    if not query or not query.strip():
        return []

    q = query.strip()

    local_hint_words = [
        "충주시", "충주", "조례", "규칙", "자치법규",
        "지원금", "출산", "보조금", "위원회", "시행규칙",
        "주차장", "주차요금", "감면", "수수료",
    ]

    admin_rule_hint_words = [
        "훈령", "예규", "고시", "공고", "지침", "행정규칙",
    ]

    is_local_question = any(word in q for word in local_hint_words)
    is_admin_rule_question = any(word in q for word in admin_rule_hint_words)

    # 1. 자치법규 의심 질문은 자치법규 전용 검색만 수행
    #    search_all/search_law로 넘어가면 불필요한 timeout이 발생하므로 여기서 종료
    if is_local_question:
        try:
            results = await self.search_ordinance(query=q, display=display)
            if results:
                logger.info(
                    f"[korean-law-mcp] 자치법규 검색 성공: query={q}, count={len(results)}"
                )
                return results[:display]

            logger.info(
                f"[korean-law-mcp] 자치법규 검색 결과 없음: query={q}"
            )
            return []

        except Exception as e:
            logger.warning(
                f"[korean-law-mcp] 자치법규 검색 실패: query={q}, error={e}"
            )
            return []

    # 2. 행정규칙 의심 질문은 행정규칙 전용 검색 우선
    if is_admin_rule_question:
        try:
            results = await self.search_admin_rule(query=q, display=display)
            if results:
                logger.info(
                    f"[korean-law-mcp] 행정규칙 검색 성공: query={q}, count={len(results)}"
                )
                return results[:display]

            logger.info(
                f"[korean-law-mcp] 행정규칙 검색 결과 없음: query={q}"
            )
            # 행정규칙 결과가 없으면 일반 법령으로도 이어서 검색 가능
        except Exception as e:
            logger.warning(
                f"[korean-law-mcp] 행정규칙 검색 실패: query={q}, error={e}"
            )

    # 3. 일반 통합검색
    try:
        results = await self.search_all(query=q, display=display)
        if results:
            logger.info(
                f"[korean-law-mcp] 통합검색 성공: query={q}, count={len(results)}"
            )
            return results[:display]
    except Exception as e:
        logger.warning(f"[korean-law-mcp] 통합검색 실패: query={q}, error={e}")

    # 4. 국가법령 검색
    try:
        results = await self.search_law(query=q, target="law", display=display)
        if results:
            logger.info(
                f"[korean-law-mcp] 법령검색 성공: query={q}, count={len(results)}"
            )
            return results[:display]
    except Exception as e:
        logger.warning(f"[korean-law-mcp] 법령검색 실패: query={q}, error={e}")

    return []

    async def get_law_text(
        self,
        mst: str = "",
        law_name: str = "",
        article: str = "",
        question: str = "",
    ) -> str:
        """
        국가법령 본문/조문 조회.
        공식 MCP 도구명: get_law_text
        """
        if not mst and not law_name:
            return ""

        args = [self.text_tool]

        if mst:
            args.extend(["--mst", str(mst)])
        elif law_name:
            args.extend(["--law", law_name])

        if article:
            args.extend(["--jo", article])

        text = await self._run_cli(args)
        return self._normalize_text_result(text)

    async def get_ordinance_text(
        self,
        ordin_seq: str = "",
        ordinance_name: str = "",
        article: str = "",
    ) -> str:
        """
        자치법규 전문/조문 조회.
        공식 MCP 도구명: get_ordinance
        """
        if not ordin_seq and not ordinance_name:
            return ""

        args = [self.ordinance_text_tool]

        if ordin_seq:
            args.extend(["--ordinSeq", str(ordin_seq)])
        elif ordinance_name:
            args.extend(["--name", ordinance_name])

        if article:
            args.extend(["--jo", article])

        text = await self._run_cli(args)
        return self._normalize_text_result(text)

    async def get_admin_rule_text(
        self,
        admin_rule_id: str = "",
        admin_rule_name: str = "",
        article: str = "",
    ) -> str:
        """
        행정규칙 전문/조문 조회.
        공식 MCP 도구명: get_admin_rule
        """
        if not admin_rule_id and not admin_rule_name:
            return ""

        args = [self.admin_rule_text_tool]

        if admin_rule_id:
            args.extend(["--id", str(admin_rule_id)])
        elif admin_rule_name:
            args.extend(["--name", admin_rule_name])

        if article:
            args.extend(["--jo", article])

        text = await self._run_cli(args)
        return self._normalize_text_result(text)

    def _normalize_text_result(self, text: Optional[str]) -> str:
        """본문 조회 결과 정규화"""
        if not text:
            return ""

        raw = self._try_parse_json(text)

        if isinstance(raw, dict):
            for key in [
                "text",
                "content",
                "body",
                "lawText",
                "ordinanceText",
                "adminRuleText",
                "articleText",
                "조문내용",
                "본문",
            ]:
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

        if isinstance(raw, str):
            return raw[:12000]

        return str(raw)[:12000]

    async def check_connection(self) -> Dict[str, Any]:
        """
        MCP CLI 연결 상태 확인.
        실패해도 기존 law.go.kr API fallback이 있으므로 fatal 아님.
        """
        if not self.enabled:
            return {
                "enabled": False,
                "connected": False,
                "reason": "KOREAN_LAW_MCP_ENABLED=false",
                "mode": "cli",
                "command": self.cli_command,
            }

        if not self._law_oc():
            return {
                "enabled": True,
                "connected": False,
                "reason": "LAW_API_OC/LAW_OC 미설정",
                "mode": "cli",
                "command": self.cli_command,
            }

        try:
            results = await self.search_law("헌법", display=1)

            if results:
                return {
                    "enabled": True,
                    "connected": True,
                    "result_count": len(results),
                    "mode": "cli",
                    "command": self.cli_command,
                }

            return {
                "enabled": True,
                "connected": False,
                "reason": "CLI는 실행되었으나 search_law 검색 결과를 파싱하지 못함",
                "result_count": 0,
                "mode": "cli",
                "command": self.cli_command,
            }

        except Exception as e:
            return {
                "enabled": True,
                "connected": False,
                "reason": str(e),
                "mode": "cli",
                "command": self.cli_command,
            }


korean_law_mcp_service = KoreanLawMCPService()