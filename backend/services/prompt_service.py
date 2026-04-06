"""
프롬프트 중앙 관리 서비스

사용법:
    from services.prompt_service import prompt_service

    # 프롬프트 가져오기
    prompt = prompt_service.get("press_release", "system_prompt")

    # 변수 치환이 필요한 경우
    prompt = prompt_service.get("press_release", "system_prompt").format(
        department="자치행정과", manager="김태균"
    )

    # 프롬프트가 없으면 기본값 사용
    prompt = prompt_service.get("press_release", "system_prompt", default="기본 프롬프트")
"""
import time
import logging
from typing import Optional, Dict, List
from config import settings


logger = logging.getLogger(__name__)


class PromptService:
    """프롬프트 중앙 관리 서비스 (Supabase DB 기반, 메모리 캐시)"""

    def __init__(self):
        self._cache: Dict[str, str] = {}  # key: "feature::prompt_key" → value: content
        self._last_loaded: float = 0
        self._cache_ttl: int = 300  # 5분 캐시
        self._client = None

    def _get_client(self):
        """Supabase 클라이언트 (지연 초기화)"""
        if self._client is None:
            try:
                from supabase import create_client
                self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                logger.info("[prompt-service] ✅ Supabase 클라이언트 초기화 완료")
            except Exception as e:
                logger.warning(f"[prompt-service] ⚠️ Supabase 연결 실패: {e}")
                self._client = None
        return self._client

    def _load_all(self):
        """DB에서 모든 프롬프트를 캐시로 로드"""
        client = self._get_client()
        if client is None:
            logger.warning("[prompt-service] ⚠️ DB 미연결, 캐시 로드 건너뜀")
            return

        try:
            result = client.table("prompts").select(
                "feature, prompt_key, content"
            ).eq("is_active", True).execute()

            if result.data:
                self._cache.clear()
                for row in result.data:
                    cache_key = f"{row['feature']}::{row['prompt_key']}"
                    self._cache[cache_key] = row["content"]

                self._last_loaded = time.time()
                logger.info(f"[prompt-service] ✅ 프롬프트 {len(result.data)}개 로드 완료")
            else:
                self._last_loaded = time.time()
                logger.warning("[prompt-service] ⚠️ 프롬프트 테이블이 비어있음 (코드 내 기본값 사용)")
        except Exception as e:
            logger.warning(f"[prompt-service] ⚠️ 프롬프트 로드 실패: {e} (코드 내 기본값 사용)")

    def _ensure_cache(self):
        """캐시가 만료되었으면 재로드"""
        now = time.time()
        if now - self._last_loaded > self._cache_ttl:
            logger.info("[prompt-service] 🔄 캐시 만료, 프롬프트 재로드 시작")
            self._load_all()

    def get(self, feature: str, prompt_key: str, default: Optional[str] = None) -> Optional[str]:
        """
        프롬프트 가져오기

        1순위: DB 캐시에서 가져옴
        2순위: default 값 반환 (코드에 하드코딩된 기존 프롬프트)

        → 기존 코드의 프롬프트를 default로 넘기면, DB에 없어도 기존처럼 동작
        """
        self._ensure_cache()
        cache_key = f"{feature}::{prompt_key}"

        if cache_key in self._cache:
            logger.info(f"[prompt-service] [PROMPT] DB used | feature={feature} | key={prompt_key}")
            return self._cache[cache_key]

        logger.info(f"[prompt-service] [PROMPT] FALLBACK used | feature={feature} | key={prompt_key} | reason=not_found")
        return default

    def get_all_by_feature(self, feature: str) -> Dict[str, str]:
        """특정 기능의 모든 프롬프트 가져오기"""
        self._ensure_cache()
        prefix = f"{feature}::"
        result = {
            k.replace(prefix, ""): v
            for k, v in self._cache.items()
            if k.startswith(prefix)
        }
        logger.info(f"[prompt-service] 📦 feature={feature} 프롬프트 {len(result)}개 반환")
        return result

    def refresh(self):
        """캐시 강제 갱신"""
        logger.info("[prompt-service] 🔄 CACHE REFRESH 요청")
        self._last_loaded = 0
        self._load_all()
        logger.info("[prompt-service] ✅ CACHE REFRESH 완료")

    async def update(self, feature: str, prompt_key: str, content: str, changed_by: str = "") -> bool:
        """프롬프트 수정 (DB 업데이트 + 이력 저장 + 캐시 갱신)"""
        client = self._get_client()
        if client is None:
            logger.error(f"[prompt-service] ❌ UPDATE FAIL | feature={feature} | key={prompt_key} | reason=no_client")
            return False

        try:
            existing = client.table("prompts").select("id, content").eq(
                "feature", feature
            ).eq("prompt_key", prompt_key).execute()

            if existing.data:
                old_content = existing.data[0]["content"]
                prompt_id = existing.data[0]["id"]

                client.table("prompts").update({
                    "content": content
                }).eq("id", prompt_id).execute()

                client.table("prompt_history").insert({
                    "prompt_id": prompt_id,
                    "feature": feature,
                    "prompt_key": prompt_key,
                    "old_content": old_content,
                    "new_content": content,
                    "changed_by": changed_by,
                }).execute()

                logger.info(
                    f"[prompt-service] [PROMPT] UPDATED | feature={feature} | key={prompt_key} | by={changed_by or 'unknown'} | mode=update"
                )
            else:
                inserted = client.table("prompts").insert({
                    "feature": feature,
                    "prompt_key": prompt_key,
                    "content": content,
                    "description": "",
                }).execute()

                prompt_id = None
                if inserted.data:
                    prompt_id = inserted.data[0].get("id")

                if prompt_id:
                    client.table("prompt_history").insert({
                        "prompt_id": prompt_id,
                        "feature": feature,
                        "prompt_key": prompt_key,
                        "old_content": None,
                        "new_content": content,
                        "changed_by": changed_by,
                    }).execute()

                logger.info(
                    f"[prompt-service] [PROMPT] UPDATED | feature={feature} | key={prompt_key} | by={changed_by or 'unknown'} | mode=insert"
                )

            cache_key = f"{feature}::{prompt_key}"
            self._cache[cache_key] = content
            self._last_loaded = time.time()

            logger.info(f"[prompt-service] ✅ 프롬프트 업데이트 완료: {feature}/{prompt_key}")
            return True

        except Exception as e:
            logger.error(f"[prompt-service] ❌ UPDATE FAIL | feature={feature} | key={prompt_key} | msg={e}")
            return False

    async def get_history(self, feature: str, prompt_key: str, limit: int = 10) -> List[dict]:
        """프롬프트 변경 이력 조회"""
        client = self._get_client()
        if client is None:
            logger.warning(f"[prompt-service] ⚠️ 이력 조회 불가 (DB 미연결): {feature}/{prompt_key}")
            return []

        try:
            result = client.table("prompt_history").select("*").eq(
                "feature", feature
            ).eq("prompt_key", prompt_key).order(
                "changed_at", desc=True
            ).limit(limit).execute()

            count = len(result.data or [])
            logger.info(f"[prompt-service] 📜 이력 조회 완료 | feature={feature} | key={prompt_key} | count={count}")
            return result.data or []
        except Exception as e:
            logger.warning(f"[prompt-service] ⚠️ 이력 조회 실패: {e}")
            return []

    async def list_all(self) -> List[dict]:
        """모든 프롬프트 목록 조회 (관리자 페이지용)"""
        client = self._get_client()
        if client is None:
            logger.warning("[prompt-service] ⚠️ 목록 조회 불가 (DB 미연결)")
            return []

        try:
            result = client.table("prompts").select(
                "id, feature, prompt_key, description, content, is_active, updated_at"
            ).order("feature").order("prompt_key").execute()

            count = len(result.data or [])
            logger.info(f"[prompt-service] 📋 전체 프롬프트 목록 조회 완료 | count={count}")
            return result.data or []
        except Exception as e:
            logger.warning(f"[prompt-service] ⚠️ 목록 조회 실패: {e}")
            return []


# 싱글톤 인스턴스
prompt_service = PromptService()