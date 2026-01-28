import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { ArrowLeft, Edit, Trash2, Download, MessageCircle, Send, User } from 'lucide-react';

export default function BoardDetail() {
  const { boardType, id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [board, setBoard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [answerContent, setAnswerContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const boardTypeNames = {
    notice: '공지사항',
    archive: '자료실',
    qna: '묻고답하기'
  };

  useEffect(() => {
    checkAdmin();
    fetchBoard();
  }, [id]);

  const checkAdmin = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await api.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setIsAdmin(response.data.isAdmin);
    } catch (error) {
      console.error('권한 확인 실패:', error);
    }
  };

  const fetchBoard = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      const response = await api.get(`/api/board/detail/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setBoard(response.data);
    } catch (error) {
      console.error('게시글 조회 실패:', error);
      alert('게시글을 찾을 수 없습니다.');
      navigate(-1);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('정말 삭제하시겠습니까?')) return;

    try {
      const token = localStorage.getItem('access_token');
      await api.delete(`/api/board/delete/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert('삭제되었습니다.');
      navigate(`/board/${boardType}`);
    } catch (error) {
      alert('삭제 실패: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleAnswerSubmit = async () => {
    if (!answerContent.trim()) {
      alert('답변 내용을 입력해주세요.');
      return;
    }

    try {
      setSubmitting(true);
      const token = localStorage.getItem('access_token');
      await api.post(`/api/board/answer/${id}`, 
        { content: answerContent },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setAnswerContent('');
      fetchBoard();
    } catch (error) {
      alert('답변 등록 실패: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSubmitting(false);
    }
  };

  const handleAnswerDelete = async (answerId) => {
    if (!confirm('답변을 삭제하시겠습니까?')) return;

    try {
      const token = localStorage.getItem('access_token');
      await api.delete(`/api/board/answer/${answerId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchBoard();
    } catch (error) {
      alert('삭제 실패: ' + (error.response?.data?.detail || error.message));
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const canEdit = board && (isAdmin || board.author_id === user?.id);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex justify-center">
          <div className="w-8 h-8 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin"></div>
        </div>
      </div>
    );
  }

  if (!board) return null;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* 뒤로가기 */}
      <button
        onClick={() => navigate(`/board/${boardType}`)}
        className="flex items-center gap-2 text-slate-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft size={18} />
        {boardTypeNames[boardType]} 목록
      </button>

      {/* 게시글 */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        {/* 헤더 */}
        <div className="p-6 border-b border-slate-800">
          <h1 className="text-2xl font-bold text-white mb-4">{board.title}</h1>
          <div className="flex items-center justify-between text-sm text-slate-400">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <User size={14} />
                {board.author_email?.split('@')[0]}
              </span>
              <span>{formatDate(board.created_at)}</span>
              <span>조회 {board.view_count}</span>
            </div>
            
            {canEdit && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate(`/board/${boardType}/edit/${id}`)}
                  className="flex items-center gap-1 px-3 py-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                >
                  <Edit size={14} />
                  수정
                </button>
                <button
                  onClick={handleDelete}
                  className="flex items-center gap-1 px-3 py-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
                >
                  <Trash2 size={14} />
                  삭제
                </button>
              </div>
            )}
          </div>
        </div>

        {/* 첨부파일 (자료실) */}
        {board.file_url && (
          <div className="px-6 py-4 border-b border-slate-800 bg-slate-800/30">
            <a
              href={board.file_url}
              download={board.file_name}
              className="inline-flex items-center gap-2 text-cyan-400 hover:text-cyan-300"
            >
              <Download size={16} />
              {board.file_name}
            </a>
          </div>
        )}

        {/* 본문 */}
        <div className="p-6">
          <div className="prose prose-invert max-w-none">
            <p className="text-slate-300 whitespace-pre-wrap leading-relaxed">
              {board.content}
            </p>
          </div>
        </div>
      </div>

      {/* 답변 섹션 (QnA) */}
      {boardType === 'qna' && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <MessageCircle size={20} />
            답변 {board.answers?.length > 0 && `(${board.answers.length})`}
          </h2>

          {/* 기존 답변 목록 */}
          {board.answers?.length > 0 && (
            <div className="space-y-4 mb-6">
              {board.answers.map((answer) => (
                <div
                  key={answer.id}
                  className="bg-slate-800/50 border border-slate-700 rounded-xl p-5"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 bg-cyan-500/20 text-cyan-400 text-xs rounded-full">
                        관리자
                      </span>
                      <span className="text-sm text-slate-400">
                        {answer.author_email?.split('@')[0]}
                      </span>
                      <span className="text-sm text-slate-500">
                        {formatDate(answer.created_at)}
                      </span>
                    </div>
                    
                    {isAdmin && (
                      <button
                        onClick={() => handleAnswerDelete(answer.id)}
                        className="text-slate-500 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                  <p className="text-slate-300 whitespace-pre-wrap">{answer.content}</p>
                </div>
              ))}
            </div>
          )}

          {/* 답변 작성 (관리자만) */}
          {isAdmin && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h3 className="text-sm font-medium text-slate-300 mb-3">답변 작성</h3>
              <textarea
                value={answerContent}
                onChange={(e) => setAnswerContent(e.target.value)}
                placeholder="답변을 입력하세요..."
                rows={4}
                className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 resize-none"
              />
              <div className="flex justify-end mt-3">
                <button
                  onClick={handleAnswerSubmit}
                  disabled={submitting}
                  className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg transition-colors disabled:opacity-50"
                >
                  <Send size={16} />
                  {submitting ? '등록 중...' : '답변 등록'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}