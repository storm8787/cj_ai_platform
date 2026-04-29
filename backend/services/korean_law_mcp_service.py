"""
Korean Law MCP CLI 연동 서비스

역할:
- korean-law CLI를 통해 국가법령/자치법규/행정규칙 검색
- 검색 결과를 law_chatbot.py에서 쓰기 쉬운 공통 dict 형식으로 정규화
- CLI 실패 시 빈 배열 반환하여 기존 law.go.kr API fallback 가능하게 함

전제:
- Dockerfile에서 npm install -g korean-law-mcp 설치
- CLI 명령어는 기본값 korean-law
"""

import asyncio
import json
import shlex
import time
from typing import Any, Dict, List, Optional

from config import settings


class KoreanLawMCPService:
    # MCP CLI가 연속 N회 실패하면 일정 시간 동안 호출을 skip한다.
    # 현재 korean-law-mcp는 MCP 서버(JSON-RPC stdio) 프로토콜이라
    # CLI 형태 호출이 작동하지 않을 수 있는데, 매 검색마다 timeout을 기다리는 비용을 줄이기 위함.
    _FAIL_THRESHOLD = 3
    _FAIL_BACKOFF_SEC = 300  # 5분간 호출 skip

    def __init__(self):
        self.enabled = bool(getattr(settings, "KOREAN_LAW_MCP_ENABLED", True))
        self.command = getattr(settings, "KOREAN_LAW_MCP_COMMAND", "korean-law") or "korean-law"
        self.timeout = int(getattr(settings, "KOREAN_LAW_MCP_TIMEOUT", 15) or 15)
        self._fail_count = 0
        self._skip_until = 0.0

    # =====================================================
    # 공통 CLI 실행
    # =====================================================

    async def _run_cli(self, args: List[str], timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        korean-law CLI 실행.
        self.command가 "node /path/index.js"처럼 공백 포함 명령일 수도 있어 shlex.split 처리.
        연속 실패가 임계치를 넘으면 backoff 기간 동안 호출을 skip해 응답 속도를 보호한다.
        """
        if not self.enabled:
            return {"ok": False, "stdout": "", "stderr": "MCP disabled", "returncode": -1}

        now = time.monotonic()
        if now < self._skip_until:
            return {
                "ok": False,
                "stdout": "",
                "stderr": "MCP skipped (in backoff after consecutive failures)",
                "returncode": -2,
            }

        timeout = timeout or self.timeout

        base_cmd = shlex.split(self.command)
        cmd = base_cmd + args

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                print(f"[korean-law-mcp] CLI timeout: {' '.join(cmd)}")
                return {
                    "ok": False,
                    "stdout": "",
                    "stderr": "timeout",
                    "returncode": -999,
                    "cmd": " ".join(cmd),
                }

            out = stdout.decode("utf-8", errors="ignore").strip()
            err = stderr.decode("utf-8", errors="ignore").strip()

            if process.returncode != 0:
                print(
                    f"[korean-law-mcp] CLI 실패 rc={process.returncode} | "
                    f"cmd={' '.join(cmd)} | stderr={err}"
                )
                self._record_failure()
                return {
                    "ok": False,
                    "stdout": out,
                    "stderr": err,
                    "returncode": process.returncode,
                    "cmd": " ".join(cmd),
                }

            self._fail_count = 0
            self._skip_until = 0.0
            return {
                "ok": True,
                "stdout": out,
                "stderr": err,
                "returncode": process.returncode,
                "cmd": " ".join(cmd),
            }

        except FileNotFoundError:
            print(
                f"[korean-law-mcp] CLI 명령어를 찾을 수 없음: {self.command}. "
                "Dockerfile에 npm install -g korean-law-mcp 설치 필요"
            )
            self._record_failure()
            return {
                "ok": False,
                "stdout": "",
                "stderr": "command not found",
                "returncode": -404,
                "cmd": " ".join(cmd),
            }

        except Exception as e:
            print(f"[korean-law-mcp] CLI 실행 예외: {e}")
            self._record_failure()
            return {
                "ok": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "cmd": " ".join(cmd),
            }

    def _record_failure(self) -> None:
        self._fail_count += 1
        if self._fail_count >= self._FAIL_THRESHOLD:
            self._skip_until = time.monotonic() + self._FAIL_BACKOFF_SEC
            print(
                f"[korean-law-mcp] 연속 {self._fail_count}회 실패 → "
                f"{self._FAIL_BACKOFF_SEC}초간 호출 skip"
            )

    def _parse_stdout_json(self, stdout: str) -> Any:
        if not stdout:
            return None

        text = stdout.strip()

        try:
            return json.loads(text)
        except Exception:
            pass

        # stdout 안에 JSON이 섞여 나오는 경우 대비
        start_obj = text.find("{")
        end_obj = text.rfind("}")
        start_arr = text.find("[")
        end_arr = text.rfind("]")

        candidates = []

        if start_obj >= 0 and end_obj > start_obj:
            candidates.append(text[start_obj:end_obj + 1])

        if start_arr >= 0 and end_arr > start_arr:
            candidates.append(text[start_arr:end_arr + 1])

        for c in candidates:
            try:
                return json.loads(c)
            except Exception:
                continue

        return None

    def _unwrap_items(self, data: Any) -> List[Dict[str, Any]]:
        """
        MCP/CLI 응답 형태가 다양할 수 있어 최대한 유연하게 list[dict]로 변환
        """
        if data is None:
            return []

        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]

        if isinstance(data, dict):
            for key in [
                "items",
                "results",
                "laws",
                "ordinances",
                "admin_rules",
                "data",
                "list",
                "documents",
            ]:
                value = data.get(key)
                if isinstance(value, list):
                    return [x for x in value if isinstance(x, dict)]

            # 단일 객체가 결과처럼 보이면 1개짜리 list로 반환
            if any(k in data for k in ["name", "law_name", "법령명한글", "자치법규명", "행정규칙명"]):
                return [data]

        return []

    def _pick_first(self, item: Dict[str, Any], keys: List[str], default: str = "") -> str:
        for key in keys:
            value = item.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return default

    def _normalize_search_items(self, raw_items: List[Dict[str, Any]], target: str) -> List[Dict[str, Any]]:
        normalized = []

        for item in raw_items:
            if not isinstance(item, dict):
                continue

            if target == "ordin":
                name = self._pick_first(item, [
                    "name",
                    "ordinance_name",
                    "자치법규명",
                    "law_name",
                    "법령명한글",
                    "title",
                ])
                item_id = self._pick_first(item, [
                    "id",
                    "ordin_seq",
                    "ordinance_id",
                    "자치법규일련번호",
                    "MST",
                    "mst",
                    "law_id",
                ])
                category = self._pick_first(item, [
                    "category",
                    "자치법규종류",
                    "자치법규구분",
                    "법령구분명",
                ], "자치법규")
                region = self._pick_first(item, [
                    "region",
                    "지자체기관명",
                    "자치단체명",
                ], "충주시")

            elif target == "admrul":
                name = self._pick_first(item, [
                    "name",
                    "admin_rule_name",
                    "행정규칙명",
                    "law_name",
                    "법령명한글",
                    "title",
                ])
                item_id = self._pick_first(item, [
                    "id",
                    "admin_rule_id",
                    "행정규칙일련번호",
                    "MST",
                    "mst",
                    "law_id",
                ])
                category = self._pick_first(item, [
                    "category",
                    "행정규칙종류",
                    "법령구분명",
                ], "행정규칙")
                region = ""

            else:
                name = self._pick_first(item, [
                    "name",
                    "law_name",
                    "법령명한글",
                    "title",
                ])
                item_id = self._pick_first(item, [
                    "id",
                    "mst",
                    "MST",
                    "law_id",
                    "법령일련번호",
                ])
                category = self._pick_first(item, [
                    "category",
                    "법령구분명",
                    "type_name",
                ], "법령")
                region = ""

            if not name:
                continue

            enforcement_date = self._pick_first(item, [
                "enforcement_date",
                "시행일자",
                "effective_date",
            ])

            content = self._pick_first(item, [
                "content",
                "article_content",
                "text",
                "본문",
                "조문내용",
            ])

            normalized.append({
                "id": item_id,
                "name": name,
                "type": target,
                "category": category,
                "region": region,
                "enforcement_date": enforcement_date,
                "source": "korean-law-mcp",
                "raw": item,
                "content": content,
            })

        return normalized

    async def _search(self, tool_name: str, query: str, target: str, display: int = 10) -> List[Dict[str, Any]]:
        args = [
            tool_name,
            "--query",
            query,
        ]

        if display:
            args.extend(["--display", str(display)])

        result = await self._run_cli(args)

        if not result.get("ok"):
            return []

        data = self._parse_stdout_json(result.get("stdout", ""))
        raw_items = self._unwrap_items(data)

        return self._normalize_search_items(raw_items, target=target)

    # =====================================================
    # 검색 함수
    # =====================================================

    async def search_law(self, query: str, target: str = "law", display: int = 10) -> List[Dict[str, Any]]:
        """
        국가법령 검색
        """
        return await self._search(
            tool_name="search_law",
            query=query,
            target="law",
            display=display,
        )

    async def search_ordinance(self, query: str, display: int = 10) -> List[Dict[str, Any]]:
        """
        자치법규 검색.
        지자체명은 GPT planner가 law_name에 직접 명시하도록 위임 (강제 prefix 제거).
        """
        return await self._search(
            tool_name="search_ordinance",
            query=query,
            target="ordin",
            display=display,
        )

    async def search_admin_rule(self, query: str, display: int = 10) -> List[Dict[str, Any]]:
        """
        행정규칙·훈령·예규 검색
        """
        return await self._search(
            tool_name="search_admin_rule",
            query=query,
            target="admrul",
            display=display,
        )

    # =====================================================
    # 본문 조회 함수
    # =====================================================

    async def _get_text_by_candidates(self, candidates: List[List[str]]) -> str:
        """
        MCP CLI의 상세조회 명령명이 버전별로 다를 수 있어 후보를 순차 시도.
        성공한 stdout을 그대로 반환.
        """
        for args in candidates:
            result = await self._run_cli(args, timeout=self.timeout)

            if not result.get("ok"):
                continue

            stdout = result.get("stdout", "").strip()

            if not stdout:
                continue

            data = self._parse_stdout_json(stdout)

            if isinstance(data, dict):
                for key in [
                    "text",
                    "content",
                    "law_text",
                    "ordinance_text",
                    "admin_rule_text",
                    "article_content",
                    "본문",
                    "조문내용",
                ]:
                    value = data.get(key)
                    if value and len(str(value).strip()) > 20:
                        return str(value).strip()

                # dict 전체를 문자열로라도 제공
                return json.dumps(data, ensure_ascii=False)

            if isinstance(data, list):
                return json.dumps(data, ensure_ascii=False)

            if len(stdout) > 20:
                return stdout

        return ""

    async def get_law_text(
        self,
        mst: str = "",
        law_name: str = "",
        question: str = "",
    ) -> str:
        """
        국가법령 전문 조회.
        MST(일련번호) 우선 시도 → law_name 기반 시도 순으로 fallback.
        """
        candidates: List[List[str]] = []

        if mst:
            candidates.extend([
                ["get_law_text", "--mst", mst],
                ["get_law_text", "--id", mst],
            ])

        if law_name:
            candidates.extend([
                ["get_law_text", "--query", law_name],
                ["get_law_text", "--name", law_name],
            ])

        return await self._get_text_by_candidates(candidates)

    async def get_ordinance_text(
        self,
        ordin_seq: str = "",
        ordinance_name: str = "",
    ) -> str:
        """
        자치법규 전문 조회.
        ID 우선 → 이름 기반 순으로 fallback.
        """
        candidates: List[List[str]] = []

        if ordin_seq:
            candidates.extend([
                ["get_ordinance_text", "--id", ordin_seq],
                ["get_ordinance_text", "--ordin_seq", ordin_seq],
            ])

        if ordinance_name:
            candidates.extend([
                ["get_ordinance_text", "--query", ordinance_name],
                ["get_ordinance_text", "--name", ordinance_name],
            ])

        return await self._get_text_by_candidates(candidates)

    async def get_admin_rule_text(
        self,
        admin_rule_id: str = "",
        admin_rule_name: str = "",
    ) -> str:
        """
        행정규칙 전문 조회.
        ID 우선 → 이름 기반 순으로 fallback.
        """
        candidates: List[List[str]] = []

        if admin_rule_id:
            candidates.extend([
                ["get_admin_rule_text", "--id", admin_rule_id],
            ])

        if admin_rule_name:
            candidates.extend([
                ["get_admin_rule_text", "--query", admin_rule_name],
                ["get_admin_rule_text", "--name", admin_rule_name],
            ])

        return await self._get_text_by_candidates(candidates)

    # =====================================================
    # 상태 확인
    # =====================================================

    async def check_connection(self) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "enabled": False,
                "connected": False,
                "reason": "disabled",
                "mode": "cli",
                "command": self.command,
            }

        try:
            items = await self.search_law("헌법", display=1)

            return {
                "enabled": True,
                "connected": len(items) > 0,
                "result_count": len(items),
                "mode": "cli",
                "command": self.command,
            }

        except Exception as e:
            return {
                "enabled": True,
                "connected": False,
                "reason": str(e),
                "mode": "cli",
                "command": self.command,
            }


korean_law_mcp_service = KoreanLawMCPService()