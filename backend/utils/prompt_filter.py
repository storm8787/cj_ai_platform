"""프롬프트 인젝션 및 개인정보 필터링"""
import re
from typing import Tuple

# 금지 키워드
FORBIDDEN_KEYWORDS = [
    "ignore previous",
    "ignore all",
    "disregard",
    "forget everything",
    "new instructions",
    "override",
    "system prompt",
    "jailbreak",
    "DAN",
    "developer mode",
]

# 개인정보 패턴
PERSONAL_INFO_PATTERNS = [
    # 주민등록번호
    r'\d{6}[-\s]?\d{7}',
    # 전화번호
    r'010[-\s]?\d{4}[-\s]?\d{4}',
    r'0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}',
    # 신용카드 번호
    r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',
    # 계좌번호 (일반적인 패턴)
    r'\d{3,6}[-\s]?\d{2,6}[-\s]?\d{2,6}',
    # 이메일 (민감 정보로 간주하지 않음, 필요시 추가)
]


def check_text_security(text: str) -> Tuple[bool, str]:
    """
    텍스트 보안 검사
    
    Args:
        text: 검사할 텍스트
    
    Returns:
        (is_safe, message) 튜플
    """
    if not text:
        return True, "OK"
    
    text_lower = text.lower()
    
    # 1. 금지 키워드 검사
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword.lower() in text_lower:
            return False, f"보안 규칙 위반: 허용되지 않는 표현이 포함되어 있습니다."
    
    # 2. 개인정보 패턴 검사
    for pattern in PERSONAL_INFO_PATTERNS:
        if re.search(pattern, text):
            return False, "개인정보가 포함된 것으로 보입니다. 개인정보를 제거하고 다시 시도해주세요."
    
    # 3. 프롬프트 인젝션 패턴 검사
    injection_patterns = [
        r'<\s*system\s*>',
        r'\[\s*system\s*\]',
        r'###\s*instruction',
        r'<\s*prompt\s*>',
        r'\{\{.*\}\}',  # 템플릿 인젝션
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, text_lower):
            return False, "보안 규칙 위반: 허용되지 않는 형식이 포함되어 있습니다."
    
    return True, "OK"


def sanitize_text(text: str) -> str:
    """
    텍스트 정제 (위험 요소 제거)
    
    Args:
        text: 정제할 텍스트
    
    Returns:
        정제된 텍스트
    """
    if not text:
        return ""
    
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    
    # 특수 제어 문자 제거
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # 연속 공백 정리
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()
