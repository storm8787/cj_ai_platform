import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { FolderOpen, Plus, Eye, Download, ChevronLeft, ChevronRight, Search, FileText } from 'lucide-react';

export default function ArchiveBoard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [boards, setBoards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isAdmin, setIsAdmin] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    checkAdmin();
    fetchBoards();
  }, [page]);

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

  const fetchBoards = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      const response = await api.get(`/api/board/list/archive?page=${page}&limit=10`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setBoards(response.data.boards);
      setTotalPages(response.data.total_pages);
    } catch (error) {
      console.error('목록 조회 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  };

  const filteredBoards = boards.filter(board =>
    board.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center shadow-lg">
            <FolderOpen className="text-white" size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">자료실</h1>
            <p className="text-slate-400 text-sm">업무에 필요한 자료를 다운로드하세요</p>
          </div>
        </div>
        
        {isAdmin && (
          <button
            onClick={() => navigate('/board/archive/write')}
            className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg transition-colors"
          >
            <Plus size={18} />
            자료 등록
          </button>
        )}
      </div>

      {/* 검색 */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
          <input
            type="text"
            placeholder="제목 검색..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
          />
        </div>
      </div>

      {/* 게시글 목록 */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center">
            <div className="w-8 h-8 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin mx-auto"></div>
          </div>
        ) : filteredBoards.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            등록된 자료가 없습니다.
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-slate-800/50">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-medium text-slate-300">제목</th>
                <th className="px-6 py-4 text-center text-sm font-medium text-slate-300 w-40">첨부파일</th>
                <th className="px-6 py-4 text-center text-sm font-medium text-slate-300 w-32">작성일</th>
                <th className="px-6 py-4 text-center text-sm font-medium text-slate-300 w-20">조회</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {filteredBoards.map((board) => (
                <tr
                  key={board.id}
                  onClick={() => navigate(`/board/archive/${board.id}`)}
                  className="hover:bg-slate-800/50 cursor-pointer transition-colors"
                >
                  <td className="px-6 py-4">
                    <span className="text-white hover:text-cyan-400">{board.title}</span>
                  </td>
                  <td className="px-6 py-4 text-center">
                    {board.file_name ? (
                      <span className="inline-flex items-center gap-1 text-sm text-emerald-400">
                        <FileText size={14} />
                        {board.file_name.length > 15 
                          ? board.file_name.substring(0, 15) + '...' 
                          : board.file_name}
                      </span>
                    ) : (
                      <span className="text-slate-500 text-sm">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-center text-sm text-slate-400">
                    {formatDate(board.created_at)}
                  </td>
                  <td className="px-6 py-4 text-center text-sm text-slate-400">
                    <span className="flex items-center justify-center gap-1">
                      <Eye size={14} />
                      {board.view_count}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-2 mt-6">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={18} />
          </button>
          
          <span className="px-4 py-2 text-slate-300">
            {page} / {totalPages}
          </span>
          
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      )}
    </div>
  );
}