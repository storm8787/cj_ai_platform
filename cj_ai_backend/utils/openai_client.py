import os
from openai import OpenAI


def get_openai_client():
    """OpenAI 클라이언트 싱글톤"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다")
    
    return OpenAI(api_key=api_key)