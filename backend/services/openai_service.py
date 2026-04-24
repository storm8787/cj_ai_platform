"""OpenAI API 서비스"""
from typing import Optional

from openai import AsyncOpenAI
from config import settings


class OpenAIService:
    """OpenAI API 호출 서비스"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: str = "당신은 충주시청 업무를 돕는 AI 어시스턴트입니다. 정확하고 명확하게 답변하세요.",
        model: Optional[str] = None,
    ) -> str:
        """
        텍스트 생성

        Args:
            prompt: 사용자 프롬프트
            max_tokens: 최대 토큰 수
            temperature: 창의성(0.0~2.0)
            system_prompt: 시스템 프롬프트
            model: 사용할 모델명. 지정하지 않으면 settings.OPENAI_MODEL 사용.
                   특정 기능에서 다른 모델을 쓰고 싶을 때 override (예: "gpt-4o")
        """
        try:
            response = await self.client.chat.completions.create(
                model=model or self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"❌ OpenAI API 오류: {e}")
            raise

    async def get_embedding(self, text: str) -> list:
        """텍스트 임베딩 생성 (OpenAI 모델)"""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ 임베딩 생성 오류: {e}")
            raise