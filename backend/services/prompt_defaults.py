"""
코드 하드코딩 기본 프롬프트 레지스트리

목적:
- 프롬프트는 DB(Supabase `prompts`) 우선, 없으면 코드 하드코딩 fallback으로 동작한다.
- 그런데 관리자 '프롬프트 관리' 화면은 DB에 저장된 row만 보여주므로,
  아직 DB에 seed되지 않은 프롬프트는 관리자가 보거나 수정할 수 없다.
- 이 레지스트리는 각 기능의 '코드 기본값'을 (feature, prompt_key)로 조회할 수 있게 하여,
  DB에 없는 프롬프트도 관리자 화면에 '코드 기본값(미저장)' 상태로 노출·편집할 수 있게 한다.

원칙:
- 단일 소스 유지: 기본값을 여기서 복사하지 않고, 실제 기능 모듈의 상수를 지연 참조한다.
- 지연 import: 앱 기동 시점 의존성/순환 import를 피하기 위해 함수 내부에서 import 한다.
- 레지스트리에 없는 (feature, key)는 None을 반환(없는 기본값을 지어내지 않음).
"""
from typing import Optional, Callable, Dict, Iterator, Tuple


def _report_writer_system() -> str:
    from routers.report_writer import _DEFAULT_SYSTEM_PROMPT
    return _DEFAULT_SYSTEM_PROMPT


def _report_writer_build() -> str:
    from routers.report_writer import _DEFAULT_BUILD_PROMPT_TEMPLATE
    return _DEFAULT_BUILD_PROMPT_TEMPLATE


def _report_writer_type_directive(rtype: str) -> Callable[[], str]:
    def _loader() -> str:
        from routers.report_writer import REPORT_TYPE_DIRECTIVES
        return REPORT_TYPE_DIRECTIVES[rtype]
    return _loader


# (feature, prompt_key) → 기본값 로더(지연)
_REGISTRY: Dict[Tuple[str, str], Callable[[], str]] = {
    ("report_writer", "system_prompt"): _report_writer_system,
    ("report_writer", "build_prompt_template"): _report_writer_build,
}

# 보고서 유형별 지시문도 관리자 화면에 노출 (유형명은 report_writer.REPORT_TYPE_DIRECTIVES와 일치)
for _rtype in ("계획 보고서", "대책 보고서", "상황 보고서", "분석 보고서", "기타 보고서"):
    _REGISTRY[("report_writer", f"type_directive:{_rtype}")] = _report_writer_type_directive(_rtype)


def get_default(feature: str, prompt_key: str) -> Optional[str]:
    """등록된 코드 기본값 반환. 없으면 None."""
    loader = _REGISTRY.get((feature, prompt_key))
    if loader is None:
        return None
    try:
        return loader()
    except Exception:
        return None


def iter_feature_defaults(feature: str) -> Iterator[Tuple[str, str]]:
    """특정 기능의 (prompt_key, 기본값) 쌍을 순회."""
    for (feat, key), loader in _REGISTRY.items():
        if feat != feature:
            continue
        try:
            yield key, loader()
        except Exception:
            continue


def iter_all_defaults() -> Iterator[Tuple[str, str, str]]:
    """전체 (feature, prompt_key, 기본값) 순회."""
    for (feat, key), loader in _REGISTRY.items():
        try:
            yield feat, key, loader()
        except Exception:
            continue
