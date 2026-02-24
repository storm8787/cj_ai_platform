"""
Azure Container Apps 백엔드 설정

⚠️ 실제 키 값은 여기에 넣지 마세요!
- 로컬 개발: .env 파일에 작성
- 배포: Azure Portal → Container Apps → 환경 변수에 설정
"""
import os
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # OpenAI API
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # DeepL API (번역기용)
    DEEPL_API_KEY: str = ""
    
    # Kakao API (주소-좌표 변환용)
    KAKAO_API_KEY: str = ""
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    
    # GitHub (뉴스 관련)
    GITHUB_TOKEN: str = ""
    GIST_ID: str = ""
    GITHUB_REPO: str = ""
    
    # 국가법령정보센터 API (법령·자치법규 챗봇용)
    LAW_API_OC: str = ""
    
    # CORS 설정
    CORS_ORIGINS: str = "http://localhost:5173"
    
    # 벡터스토어 경로
    VECTORSTORE_PATH: str = "/app/data/vectorstores"
    ELECTION_VECTORSTORE_PATH: str = "/app/data/election_law/vectorstores"
    
    # 임베딩 모델
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