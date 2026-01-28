import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { ArrowLeft, Send, Upload, X } from 'lucide-react';

export default function BoardWrite() {
  const { boardType } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  const boardTypeNames = {
    notice: '공지사항',
    archive: '자료실',
    qna: '묻고답하기'
  };

  const placeholders = {
    notice: {
      title: '공지사항 제목을 입력하세요',
      content: '공지 내용을 입력하세요'
    },
    archive: {
      title: '자료 제목을 입력하세요',
      content: '자료에 대한 설명을 입력하세요'
    },
    qna: {
      title: '질문 제목을 입력하세요',
      content: '질문 내용을 상세히 작성해주세요'
    }
  };

  useEffect(() => {
    checkPermission();
  }, []);

  const checkPermission = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await api.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setIsAdmin(response.data.isAdmin);

      // 공지사항, 자료실은 관리자만
      if ((boardType === 'notice' || boardType === 'archive') && !response.data.isAdmin) {
        alert('관리자만 작성할 수 있습니다.');
        navigate(`/board/${boardType}`);
      }
    } catch (error) {
      console.error('권한 확인 실패:', error);
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      // 100MB 제한
      if (selectedFile.size > 100 * 1024 * 1024) {
        alert('파일 크기는 100MB를 초과할 수 없습니다.');
        return;
      }
      setFile(selectedFile);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!title.trim()) {
      alert('제목을 입력해주세요.');
      return;
    }
    if (!content.trim()) {
      alert('내용을 입력해주세요.');
      return;
    }

    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');

      if (file && boardType === 'archive') {
        // 파일 첨부 (자료실)
        const formData = new FormData();
        formData.append('title', title);
        formData.append('content', content);
        formData.append('board_type', boardType);
        formData.append('file', file);

        await api.post('/api/board/create-with-file', formData, {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        });
      } else {
        // 일반 게시글
        await api.post('/api/board/create',
          { title, content, board_type: boardType },
          { headers: { Authorization: `Bearer ${token}` } }
        );
      }

      alert('게시글이 등록되었습니다.');
      navigate(`/board/${boardType}`);
    } catch (error) {
      alert('등록 실패: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

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

      {/* 폼 */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h1 className="text-xl font-bold text-white mb-6">
          {boardTypeNames[boardType]} 작성
        </h1>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 제목 */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              제목 <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={placeholders[boardType]?.title}
              className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
          </div>

          {/* 내용 */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              내용 <span className="text-red-400">*</span>
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={placeholders[boardType]?.content}
              rows={12}
              className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 resize-none"
            />
          </div>

          {/* 파일 첨부 (자료실만) */}
          {boardType === 'archive' && (
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                첨부파일
              </label>
              
              {file ? (
                <div className="flex items-center gap-3 p-4 bg-slate-800 border border-slate-700 rounded-lg">
                  <Upload size={20} className="text-cyan-400" />
                  <span className="text-white flex-1">{file.name}</span>
                  <span className="text-slate-400 text-sm">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </span>
                  <button
                    type="button"
                    onClick={() => setFile(null)}
                    className="text-slate-400 hover:text-red-400"
                  >
                    <X size={18} />
                  </button>
                </div>
              ) : (
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-slate-700 rounded-lg cursor-pointer hover:border-cyan-500 transition-colors">
                  <Upload size={24} className="text-slate-500 mb-2" />
                  <span className="text-slate-400 text-sm">클릭하여 파일 선택</span>
                  <span className="text-slate-500 text-xs mt-1">최대 100MB</span>
                  <input
                    type="file"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </label>
              )}
            </div>
          )}

          {/* 버튼 */}
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={() => navigate(`/board/${boardType}`)}
              className="px-6 py-2.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-6 py-2.5 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              <Send size={16} />
              {loading ? '등록 중...' : '등록'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}