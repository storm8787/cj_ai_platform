"""
korean-law-mcp CLI 연동 서비스

목표:
- Python mcp 패키지 없이 동작
- Dockerfile에서 npm install -g korean-law-mcp 설치된 CLI를 subprocess로 호출
- 국가법령 검색/본문조회 시 korean-law CLI 우선 사용
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

        # GitHub에서 clone/build한 korean-law-mcp 서버를 node로 직접 실행
        self.cli_command = getattr(settings, "KOREAN_LAW_MCP_CLI_COMMAND", "node")
        self.cli_script = getattr(settings, "KOREAN_LAW_MCP_CLI_SCRIPT", "/opt/korean-law-mcp/build/index.js")

        self.search_tool = getattr(settings, "KOREAN_LAW_MCP_SEARCH_TOOL", "search_law")
        self.text_tool = getattr(settings, "KOREAN_LAW_MCP_TEXT_TOOL", "get_law_text")
        self.all_search_tool = getattr(settings, "KOREAN_LAW_MCP_ALL_SEARCH_TOOL", "search_all")

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

        #cmd = [self.cli_command] + args
        if self.cli_command == "node":
            cmd = [self.cli_command, self.cli_script] + args
        else:
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
                    f"[korean-law-mcp] CLI 실패 rc={proc.returncode} | cmd={' '.join(cmd)} | stderr={err[:500]}"
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
        - 순수 JSON
        - 설명문 + JSON 블록
        - 배열/객체 일부 포함
        모두 방어적으로 처리.
        """
        if not text:
            return None

        cleaned = text.strip()
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        # 1. 전체 JSON 파싱
        try:
            return json.loads(cleaned)
        except Exception:
            pass

        # 2. 배열 JSON 추출
        array_match = re.search(r"(\[[\s\S]*\])", cleaned)
        if array_match:
            try:
                return json.loads(array_match.group(1))
            except Exception:
                pass

        # 3. 객체 JSON 추출
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
                "data",
                "documents",
                "law",
                "result",
            ]:
                value = raw.get(key)
                if isinstance(value, list):
                    return [x for x in value if isinstance(x, dict)]

            if any(k in raw for k in ["lawName", "법령명", "name", "title", "mst", "MST", "법령일련번호"]):
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
            "법령일련번호",
            "법령ID",
            "자치법규일련번호",
        )

        name = self._pick(
            item,
            "lawName",
            "law_name",
            "name",
            "title",
            "법령명",
            "법령명한글",
            "자치법규명",
        )

        if not name:
            return None

        return {
            "id": mst,
            "name": name,
            "type": target,
            "category": self._pick(item, "lawType", "law_type", "category", "법령구분명", "자치법규종류"),
            "ministry": self._pick(item, "ministry", "소관부처명"),
            "region": self._pick(item, "region", "지자체기관명", "자치단체명"),
            "enforcement_date": self._pick(
                item,
                "enforcementDate",
                "enforcement_date",
                "시행일자",
                "effectiveDate",
            ),
            "status": self._pick(item, "status", "현행연혁코드"),
            "source": "korean-law-mcp-cli",
            "raw": item,
        }

    def _text_to_fallback_items(self, text: str, target: str = "law") -> List[Dict[str, Any]]:
        """
        CLI가 JSON이 아니라 표/텍스트로 출력하는 경우 최소한의 검색 결과로 변환.
        단, MST가 없으면 본문조회는 어려우므로 기존 API fallback에 맡기는 것이 일반적.
        """
        if not text:
            return []

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        items: List[Dict[str, Any]] = []

        for line in lines:
            if len(items) >= 10:
                break

            # 너무 설명적인 줄 제외
            if line.startswith("[") or line.startswith("{") or "검색" in line and "결과" in line:
                continue

            # 법령명 후보
            name = line
            name = re.sub(r"^\d+[\.\)]\s*", "", name).strip()
            name = re.sub(r"\s{2,}.*$", "", name).strip()

            if 2 <= len(name) <= 80:
                items.append({
                    "id": "",
                    "name": name,
                    "type": target,
                    "category": "",
                    "ministry": "",
                    "enforcement_date": "",
                    "status": "",
                    "source": "korean-law-mcp-cli-text",
                    "raw": {"line": line},
                })

        return items

    async def search_law(self, query: str, target: str = "law", display: int = 10) -> List[Dict[str, Any]]:
        """
        국가법령 검색.

        기존 law_chatbot.py에서는 target=law일 때만 이 함수를 우선 사용.
        target=ordin은 기존 자치법규 API/벡터스토어에 맡김.
        """
        if target == "ordin":
            return []

        # korean-law search_law --query "검색어"
        text = await self._run_cli([
            self.search_tool,
            "--query",
            query,
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
                    normalized.append(row)
        else:
            # JSON 파싱이 안 되는 텍스트 출력일 경우 최소 변환 시도
            normalized = self._text_to_fallback_items(text, target="law")[:display]

        return normalized

    async def search_all(self, query: str, display: int = 10) -> List[Dict[str, Any]]:
        """
        통합 검색 확장용.
        CLI에 search_all 도구가 없으면 실패 후 빈 배열 반환.
        """
        text = await self._run_cli([
            self.all_search_tool,
            "--query",
            query,
        ])

        if not text:
            return []

        raw = self._try_parse_json(text)
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

        README 예시 기준:
        korean-law get_law_text --mst 160001 --jo "제38조"

        mst가 없으면 law_name 기반 호출도 시도.
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
        if not text:
            return ""

        # 출력이 JSON인 경우 본문 키 우선 추출
        raw = self._try_parse_json(text)

        if isinstance(raw, dict):
            for key in [
                "text",
                "content",
                "body",
                "lawText",
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
            }

        if not self._law_oc():
            return {
                "enabled": True,
                "connected": False,
                "reason": "LAW_API_OC/LAW_OC 미설정",
                "mode": "cli",
                #"command": self.cli_command,
                "command": f"{self.cli_command} {self.cli_script}",
            }

        try:
            results = await self.search_law("헌법", display=1)
            return {
                "enabled": True,
                "connected": len(results) > 0,
                "result_count": len(results),
                "mode": "cli",
                #"command": self.cli_command,
                "command": f"{self.cli_command} {self.cli_script}",
            }
        except Exception as e:
            return {
                "enabled": True,
                "connected": False,
                "reason": str(e),
                "mode": "cli",
                #"command": self.cli_command,
                "command": f"{self.cli_command} {self.cli_script}",
            }


korean_law_mcp_service = KoreanLawMCPService()