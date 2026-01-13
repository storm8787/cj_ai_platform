"""Supabase 서비스 - 파일 저장 및 로깅"""
import uuid
import datetime
from typing import Optional, Dict
from supabase import create_client, Client

from config import settings


class SupabaseService:
    """Supabase 파일 저장 및 로깅 서비스"""
    
    def __init__(self):
        self._client: Optional[Client] = None
    
    @property
    def client(self) -> Client:
        """Supabase 클라이언트 (싱글톤)"""
        if self._client is None:
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                raise ValueError("Supabase 설정이 없습니다")
            self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return self._client
    
    async def upload_to_storage(
        self,
        file_bytes: bytes,
        file_name: str,
        folder: str = "downloads"
    ) -> str:
        """파일을 Supabase Storage에 업로드"""
        try:
            # 고유 경로 생성
            unique_id = uuid.uuid4().hex[:8]
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            ext = file_name.split('.')[-1] if '.' in file_name else 'txt'
            storage_path = f"{folder}/{date_str}/{unique_id}.{ext}"
            
            # Storage에 업로드
            self.client.storage.from_("files").upload(
                storage_path,
                file_bytes,
                file_options={"content-type": "text/plain"}
            )
            
            return storage_path
        except Exception as e:
            print(f"❌ Storage 업로드 실패: {e}")
            raise
    
    async def log_to_database(
        self,
        feature_name: str,
        file_name: Optional[str] = None,
        storage_path: Optional[str] = None,
        file_size: Optional[int] = None,
        file_type: str = "download",
        status: str = "success",
        error_msg: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """DB에 로그 저장"""
        try:
            payload = {
                "feature_name": feature_name,
                "file_type": file_type,
                "original_name": file_name,
                "file_size": file_size,
                "file_ext": file_name.split('.')[-1] if file_name and '.' in file_name else None,
                "storage_path": storage_path,
                "status": status,
                "error_msg": error_msg,
                "metadata": metadata
            }
            
            result = self.client.table("file_logs").insert(payload).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return {}
        except Exception as e:
            print(f"❌ DB 로깅 실패: {e}")
            raise
    
    async def log_press_release(
        self,
        file_bytes: bytes,
        file_name: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """보도자료 생성 로그 (파일 업로드 + DB 저장)"""
        try:
            # 1. Storage에 업로드
            storage_path = await self.upload_to_storage(
                file_bytes=file_bytes,
                file_name=file_name,
                folder="downloads"
            )
            
            # 2. DB에 로그 저장
            result = await self.log_to_database(
                feature_name="보도자료 생성기",
                file_name=file_name,
                storage_path=storage_path,
                file_size=len(file_bytes),
                file_type="download",
                status="success",
                metadata=metadata
            )
            
            return result
        except Exception as e:
            # 실패 로그
            try:
                await self.log_to_database(
                    feature_name="보도자료 생성기",
                    file_name=file_name,
                    file_type="download",
                    status="fail",
                    error_msg=str(e),
                    metadata=metadata
                )
            except:
                pass
            raise
    
    async def log_error(
        self,
        feature_name: str,
        error_message: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """에러 로그"""
        try:
            result = await self.log_to_database(
                feature_name=feature_name,
                file_type="error",
                status="fail",
                error_msg=error_message,
                metadata=metadata
            )
            return result
        except Exception as e:
            print(f"❌ 에러 로그 실패: {e}")
            return {}