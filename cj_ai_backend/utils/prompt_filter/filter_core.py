import re
from typing import Tuple, List
import pandas as pd

from .patterns import dangerous_patterns
from .keywords import banned_keywords
from .savelog import save_log


def _normalize(text: str) -> str:
    """텍스트 전처리"""
    return (text or "").strip()


def _contains_banned_keyword(text: str) -> Tuple[bool, str]:
    """욕설/비속어 등 banned_keywords 포함 여부"""
    norm = _normalize(text).lower()
    for kw in banned_keywords:
        if kw.lower() in norm:
            return True, kw
    return False, ""


def _matches_dangerous_pattern(text: str) -> Tuple[bool, str]:
    """정규식 기반 개인정보 패턴 검사"""
    norm = _normalize(text)
    for pat in dangerous_patterns:
        if re.search(pat, norm):
            return True, pat
    return False, ""


def check_text_security(text: str, field_name: str = "입력값") -> Tuple[bool, str]:
    """
    텍스트 하나 검사.
    문제가 있으면 (True, reason) 반환하고 로그 저장.
    """
    if not text:
        return False, ""

    # 1) 키워드 검사
    hit_kw, kw = _contains_banned_keyword(text)
    if hit_kw:
        reason = f"{field_name}에 금지 단어 감지: '{kw}'"
        save_log(text, True, reason)
        return True, reason

    # 2) 패턴 검사
    hit_pat, pat = _matches_dangerous_pattern(text)
    if hit_pat:
        reason = f"{field_name}에서 개인정보 패턴 감지: {pat}"
        save_log(text, True, reason)
        return True, reason

    return False, ""


def scan_dataframe_for_security(df: pd.DataFrame, field_name="엑셀업로드") -> List[str]:
    """
    엑셀 전체를 돌면서 각 셀에 대해 보안 위험 여부 검사.
    문제가 있는 경우, 경고 메시지 목록을 반환.
    """
    alerts = []
    for row_idx, row in df.iterrows():
        for col in df.columns:
            cell = str(row[col])
            is_malicious, reason = check_text_security(cell, f"{field_name} {row_idx+1}행 {col}")
            if is_malicious:
                alerts.append(reason)
    return alerts


def scan_text_lines_for_security(text: str, field_name="텍스트업로드") -> List[str]:
    """
    텍스트 파일 내용을 줄(line) 단위로 쪼개서 검사.
    문제가 있는 경우, 경고 메시지 목록을 반환.
    """
    alerts = []
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        is_malicious, reason = check_text_security(line, f"{field_name} {i}행")
        if is_malicious:
            alerts.append(reason)
    return alerts