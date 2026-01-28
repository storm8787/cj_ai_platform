"""
게시판 API - 공지사항, 자료실, 묻고답하기
"""
from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
import httpx
from datetime import datetime

from config import settings

router = APIRouter()

SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Content-Type": "application/json"
}


# ===========================================
# 📋 모델
# ===========================================
class BoardCreate(BaseModel):
    title: str
    content: str
    board_type: str  # 'notice', 'qna', 'archive'


class BoardUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class AnswerCreate(BaseModel):
    content: str


class BoardResponse(BaseModel):
    id: str
    board_type: str
    title: str
    content: str
    author_email: str
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    created_at: str
    view_count: int
    answers: Optional[List[dict]] = None


# ===========================================
# 🔧 헬퍼 함수
# ===========================================
async def get_user_from_token(authorization: str) -> dict:
    """토큰에서 사용자 정보 추출"""
    if not authorization:
        raise HTTPException(status_code=401, detail="인증 필요")
    
    token = authorization.replace("Bearer ", "")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={**HEADERS, "Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰")
        
        return response.json()


async def get_user_role(user_id: str, token: str) -> str:
    """사용자 권한 조회"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/user_profiles?id=eq.{user_id}&select=role",
            headers={**HEADERS, "Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0].get('role', 'user')
        
        return 'user'


async def check_admin(authorization: str) -> tuple:
    """관리자 권한 확인, (user, is_admin) 반환"""
    user = await get_user_from_token(authorization)
    token = authorization.replace("Bearer ", "")
    role = await get_user_role(user['id'], token)
    return user, role == 'admin'


# ===========================================
# 🌐 게시글 API
# ===========================================
@router.get("/list/{board_type}")
async def get_board_list(
    board_type: str,
    page: int = 1,
    limit: int = 10,
    authorization: Optional[str] = Header(None)
):
    """게시글 목록 조회"""
    user = await get_user_from_token(authorization)
    token = authorization.replace("Bearer ", "")
    
    offset = (page - 1) * limit
    
    async with httpx.AsyncClient() as client:
        # 게시글 목록
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/boards?board_type=eq.{board_type}&select=id,title,author_email,created_at,view_count,file_name&order=created_at.desc&offset={offset}&limit={limit}",
            headers={**HEADERS, "Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="목록 조회 실패")
        
        boards = response.json()
        
        # 전체 개수
        count_response = await client.get(
            f"{SUPABASE_URL}/rest/v1/boards?board_type=eq.{board_type}&select=id",
            headers={**HEADERS, "Authorization": f"Bearer {token}", "Prefer": "count=exact"}
        )
        
        total = int(count_response.headers.get('content-range', '0/0').split('/')[-1] or 0)
        
        # QnA인 경우 답변 여부 확인
        if board_type == 'qna':
            for board in boards:
                answer_response = await client.get(
                    f"{SUPABASE_URL}/rest/v1/board_answers?board_id=eq.{board['id']}&select=id&limit=1",
                    headers={**HEADERS, "Authorization": f"Bearer {token}"}
                )
                board['has_answer'] = len(answer_response.json()) > 0
        
        return {
            "boards": boards,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }


@router.get("/detail/{board_id}")
async def get_board_detail(
    board_id: str,
    authorization: Optional[str] = Header(None)
):
    """게시글 상세 조회"""
    user = await get_user_from_token(authorization)
    token = authorization.replace("Bearer ", "")
    
    async with httpx.AsyncClient() as client:
        # 게시글 조회
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/boards?id=eq.{board_id}&select=*",
            headers={**HEADERS, "Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200 or not response.json():
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")
        
        board = response.json()[0]
        
        # 조회수 증가
        await client.patch(
            f"{SUPABASE_URL}/rest/v1/boards?id=eq.{board_id}",
            headers={**HEADERS, "Authorization": f"Bearer {token}"},
            json={"view_count": board['view_count'] + 1}
        )
        
        # QnA인 경우 답변도 조회
        if board['board_type'] == 'qna':
            answer_response = await client.get(
                f"{SUPABASE_URL}/rest/v1/board_answers?board_id=eq.{board_id}&select=*&order=created_at.asc",
                headers={**HEADERS, "Authorization": f"Bearer {token}"}
            )
            board['answers'] = answer_response.json() if answer_response.status_code == 200 else []
        
        return board


@router.post("/create")
async def create_board(
    board: BoardCreate,
    authorization: Optional[str] = Header(None)
):
    """게시글 작성"""
    user, is_admin = await check_admin(authorization)
    token = authorization.replace("Bearer ", "")
    
    # 권한 체크: 공지사항, 자료실은 관리자만
    if board.board_type in ['notice', 'archive'] and not is_admin:
        raise HTTPException(status_code=403, detail="관리자만 작성할 수 있습니다")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/boards",
            headers={**HEADERS, "Authorization": f"Bearer {token}", "Prefer": "return=representation"},
            json={
                "board_type": board.board_type,
                "title": board.title,
                "content": board.content,
                "author_id": user['id'],
                "author_email": user['email']
            }
        )
        
        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=500, detail="게시글 작성 실패")
        
        return {"success": True, "message": "게시글이 작성되었습니다", "data": response.json()[0]}


@router.post("/create-with-file")
async def create_board_with_file(
    title: str = Form(...),
    content: str = Form(...),
    board_type: str = Form(...),
    file: Optional[UploadFile] = File(None),
    authorization: Optional[str] = Header(None)
):
    """파일 첨부 게시글 작성 (자료실용)"""
    user, is_admin = await check_admin(authorization)
    token = authorization.replace("Bearer ", "")
    
    # 권한 체크
    if board_type in ['notice', 'archive'] and not is_admin:
        raise HTTPException(status_code=403, detail="관리자만 작성할 수 있습니다")
    
    file_url = None
    file_name = None
    
    # 파일 업로드
    if file:
        file_content = await file.read()
        file_name = file.filename
        # 파일 확장자 추출
        file_ext = file_name.split('.')[-1] if '.' in file_name else 'bin'
        # UUID로 안전한 파일명 생성
        import uuid
        safe_filename = f"{uuid.uuid4().hex}.{file_ext}"
        storage_path = f"{board_type}/{datetime.now().strftime('%Y%m%d')}_{safe_filename}"
        
        async with httpx.AsyncClient() as client:
            upload_response = await client.post(
                f"{SUPABASE_URL}/storage/v1/object/boards/{storage_path}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": file.content_type or "application/octet-stream"
                },
                content=file_content
            )
            
            print(f"Upload response: {upload_response.status_code} - {upload_response.text}")
            
            if upload_response.status_code in [200, 201]:
                file_url = f"{SUPABASE_URL}/storage/v1/object/public/boards/{storage_path}"
            else:
                print(f"Upload failed: {upload_response.text}")
    
    # 게시글 저장
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/boards",
            headers={**HEADERS, "Authorization": f"Bearer {token}", "Prefer": "return=representation"},
            json={
                "board_type": board_type,
                "title": title,
                "content": content,
                "author_id": user['id'],
                "author_email": user['email'],
                "file_url": file_url,
                "file_name": file_name
            }
        )
        
        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=500, detail="게시글 작성 실패")
        
        return {"success": True, "message": "게시글이 작성되었습니다", "data": response.json()[0]}


@router.put("/update/{board_id}")
async def update_board(
    board_id: str,
    board: BoardUpdate,
    authorization: Optional[str] = Header(None)
):
    """게시글 수정"""
    user, is_admin = await check_admin(authorization)
    token = authorization.replace("Bearer ", "")
    
    # 기존 게시글 확인
    async with httpx.AsyncClient() as client:
        existing = await client.get(
            f"{SUPABASE_URL}/rest/v1/boards?id=eq.{board_id}&select=author_id,board_type",
            headers={**HEADERS, "Authorization": f"Bearer {token}"}
        )
        
        if not existing.json():
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")
        
        existing_board = existing.json()[0]
        
        # 권한 체크: 작성자 또는 관리자
        if existing_board['author_id'] != user['id'] and not is_admin:
            raise HTTPException(status_code=403, detail="수정 권한이 없습니다")
        
        # 업데이트
        update_data = {"updated_at": datetime.now().isoformat()}
        if board.title:
            update_data["title"] = board.title
        if board.content:
            update_data["content"] = board.content
        
        response = await client.patch(
            f"{SUPABASE_URL}/rest/v1/boards?id=eq.{board_id}",
            headers={**HEADERS, "Authorization": f"Bearer {token}"},
            json=update_data
        )
        
        if response.status_code not in [200, 204]:
            raise HTTPException(status_code=500, detail="수정 실패")
        
        return {"success": True, "message": "게시글이 수정되었습니다"}


@router.delete("/delete/{board_id}")
async def delete_board(
    board_id: str,
    authorization: Optional[str] = Header(None)
):
    """게시글 삭제"""
    user, is_admin = await check_admin(authorization)
    token = authorization.replace("Bearer ", "")
    
    async with httpx.AsyncClient() as client:
        # 기존 게시글 확인
        existing = await client.get(
            f"{SUPABASE_URL}/rest/v1/boards?id=eq.{board_id}&select=author_id",
            headers={**HEADERS, "Authorization": f"Bearer {token}"}
        )
        
        if not existing.json():
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")
        
        existing_board = existing.json()[0]
        
        # 권한 체크
        if existing_board['author_id'] != user['id'] and not is_admin:
            raise HTTPException(status_code=403, detail="삭제 권한이 없습니다")
        
        # 삭제
        response = await client.delete(
            f"{SUPABASE_URL}/rest/v1/boards?id=eq.{board_id}",
            headers={**HEADERS, "Authorization": f"Bearer {token}"}
        )
        
        if response.status_code not in [200, 204]:
            raise HTTPException(status_code=500, detail="삭제 실패")
        
        return {"success": True, "message": "게시글이 삭제되었습니다"}


# ===========================================
# 🌐 답변 API (QnA용)
# ===========================================
@router.post("/answer/{board_id}")
async def create_answer(
    board_id: str,
    answer: AnswerCreate,
    authorization: Optional[str] = Header(None)
):
    """답변 작성 (관리자만)"""
    user, is_admin = await check_admin(authorization)
    token = authorization.replace("Bearer ", "")
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="관리자만 답변할 수 있습니다")
    
    async with httpx.AsyncClient() as client:
        # 게시글 존재 확인
        board_check = await client.get(
            f"{SUPABASE_URL}/rest/v1/boards?id=eq.{board_id}&board_type=eq.qna&select=id",
            headers={**HEADERS, "Authorization": f"Bearer {token}"}
        )
        
        if not board_check.json():
            raise HTTPException(status_code=404, detail="질문을 찾을 수 없습니다")
        
        # 답변 작성
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/board_answers",
            headers={**HEADERS, "Authorization": f"Bearer {token}", "Prefer": "return=representation"},
            json={
                "board_id": board_id,
                "content": answer.content,
                "author_id": user['id'],
                "author_email": user['email']
            }
        )
        
        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=500, detail="답변 작성 실패")
        
        return {"success": True, "message": "답변이 등록되었습니다", "data": response.json()[0]}


@router.delete("/answer/{answer_id}")
async def delete_answer(
    answer_id: str,
    authorization: Optional[str] = Header(None)
):
    """답변 삭제"""
    user, is_admin = await check_admin(authorization)
    token = authorization.replace("Bearer ", "")
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="관리자만 삭제할 수 있습니다")
    
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{SUPABASE_URL}/rest/v1/board_answers?id=eq.{answer_id}",
            headers={**HEADERS, "Authorization": f"Bearer {token}"}
        )
        
        if response.status_code not in [200, 204]:
            raise HTTPException(status_code=500, detail="삭제 실패")
        
        return {"success": True, "message": "답변이 삭제되었습니다"}


@router.get("/status")
async def get_status():
    """서비스 상태"""
    return {"status": "active", "service": "게시판 API"}