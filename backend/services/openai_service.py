"""OpenAI API 서비스"""
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
        system_prompt: str = "당신은 충주시청 업무를 돕는 AI 어시스턴트입니다. 정확하고 명확하게 답변하세요."
    ) -> str:
        """텍스트 생성"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
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
