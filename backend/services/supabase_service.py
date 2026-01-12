"""Supabase 데이터베이스 서비스"""
from typing import Optional, Dict, Any
from datetime import datetime
from supabase import create_client, Client

from config import settings


class SupabaseService:
    """Supabase 연동 서비스"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._initialize()
    
    def _initialize(self):
        """클라이언트 초기화"""
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            try:
                self.client = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_KEY
                )
                print("✅ Supabase 연결 성공")
            except Exception as e:
                print(f"❌ Supabase 연결 실패: {e}")
                self.client = None
    
    async def log_file_generation(
        self,
        file_type: str,
        file_name: str,
        user_id: str = "anonymous",
        metadata: Optional[Dict] = None
    ) -> Optional[Dict]:
        """파일 생성 로그 저장"""
        if not self.client:
            return None
        
        try:
            data = {
                "file_type": file_type,
                "file_name": file_name,
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            result = self.client.table("file_logs").insert(data).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"❌ 로그 저장 실패: {e}")
            return None
    
    async def upload_file(
        self,
        bucket: str,
        file_path: str,
        file_content: bytes,
        content_type: str = "text/plain"
    ) -> Optional[str]:
        """파일 업로드"""
        if not self.client:
            return None
        
        try:
            result = self.client.storage.from_(bucket).upload(
                file_path,
                file_content,
                {"content-type": content_type}
            )
            
            # 공개 URL 반환
            public_url = self.client.storage.from_(bucket).get_public_url(file_path)
            return public_url
            
        except Exception as e:
            print(f"❌ 파일 업로드 실패: {e}")
            return None
    
    async def get_usage_stats(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """사용량 통계 조회"""
        if not self.client:
            return {"error": "Supabase not connected"}
        
        try:
            query = self.client.table("file_logs").select("*")
            
            if start_date:
                query = query.gte("created_at", start_date)
            if end_date:
                query = query.lte("created_at", end_date)
            
            result = query.execute()
            
            # 통계 계산
            data = result.data or []
            stats = {
                "total_count": len(data),
                "by_type": {}
            }
            
            for item in data:
                file_type = item.get("file_type", "unknown")
                stats["by_type"][file_type] = stats["by_type"].get(file_type, 0) + 1
            
            return stats
            
        except Exception as e:
            print(f"❌ 통계 조회 실패: {e}")
            return {"error": str(e)}


# 싱글톤 인스턴스
supabase_service = SupabaseService()
