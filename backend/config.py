"""
Azure Container Apps 백엔드 설정
"""
import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API 키
    OPENAI_API_KEY: str = ""
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    
    # GitHub (뉴스 새로고침용)
    GITHUB_TOKEN: str = ""
    GIST_ID: str = ""
    GITHUB_REPO: str = ""
    
    # CORS 설정
    CORS_ORIGINS: str = "http://localhost:5173"
    
    # 벡터스토어 경로
    VECTORSTORE_PATH: str = "/app/data/vectorstores"
    ELECTION_VECTORSTORE_PATH: str = "/app/data/election_law/vectorstores"
    
    # OpenAI 설정
    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "jhgan/ko-sroberta-multitask"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """CORS 허용 도메인 리스트"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 싱글톤 인스턴스
settings = Settings()
