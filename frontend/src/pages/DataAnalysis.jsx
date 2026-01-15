import { useState, useRef, useEffect } from 'react';
import { 
  BarChart3, Upload, Send, Bot, User, Loader2, 
  FileSpreadsheet, Trash2, Table, Hash 
} from 'lucide-react';
import { dataAnalysisApi } from '../services/api';

function DataAnalysis() {
  const [fileInfo, setFileInfo] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '안녕하세요! 엑셀 파일을 업로드하면 데이터에 대해 자유롭게 질문할 수 있습니다.'
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // 스크롤 자동 이동
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 파일 업로드
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await dataAnalysisApi.upload(formData);
      setFileInfo(response.data);
      
      // 업로드 성공 메시지
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `✅ "${response.data.file_name}" 파일이 업로드되었습니다!\n\n📊 행: ${response.data.row_count}개\n📋 열: ${response.data.col_count}개\n\n이제 데이터에 대해 자유롭게 질문해보세요!`
      }]);
    } catch (err) {
      setError(err.response?.data?.detail || '파일 업로드에 실패했습니다.');
    } finally {
      setUploading(false);
    }
  };

  // 질문 전송
  const handleSubmit = async (question = input) => {
    if (!question.trim() || loading || !fileInfo) return;

    const userMessage = { role: 'user', content: question };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await dataAnalysisApi.analyze({
        file_id: fileInfo.file_id,
        question: question
      });

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.data.answer,
        success: response.data.success
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '죄송합니다. 분석 중 오류가 발생했습니다.',
        isError: true
      }]);
    } finally {
      setLoading(false);
    }
  };

  // 빠른 질문
  const quickQuestions = [
    '총 몇 줄이야?',
    '컬럼 정보 보여줘',
    '기본 통계량 알려줘',
    '결측값 확인해줘'
  ];

  // 대화 초기화
  const handleReset = async () => {
    if (fileInfo) {
      try {
        await dataAnalysisApi.deleteFile(fileInfo.file_id);
      } catch (e) {
        // 무시
      }
    }
    setFileInfo(null);
    setMessages([{
      role: 'assistant',
      content: '안녕하세요! 엑셀 파일을 업로드하면 데이터에 대해 자유롭게 질문할 수 있습니다.'
    }]);
    setInput('');
    setError('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <BarChart3 className="text-cyan-400" size={28} />
          <div>
            <h1 className="text-2xl font-bold text-white">AI 통계분석 챗봇</h1>
            <p className="text-sm text-slate-400">
              엑셀 파일을 업로드하고 자연어로 데이터를 분석하세요
            </p>
          </div>
        </div>

        {fileInfo && (
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            <Trash2 size={18} />
            초기화
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 좌측: 파일 업로드 & 정보 */}
        <div className="lg:col-span-1 space-y-4">
          {/* 파일 업로드 */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Upload size={20} />
              데이터 업로드
            </h3>

            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              onChange={handleFileUpload}
              className="hidden"
              id="file-upload"
            />
            
            <label
              htmlFor="file-upload"
              className={`
                block w-full p-6 border-2 border-dashed rounded-xl text-center cursor-pointer
                transition-colors
                ${uploading 
                  ? 'border-gray-300 bg-gray-50' 
                  : 'border-cyan-300 hover:border-cyan-500 hover:bg-cyan-50'}
              `}
            >
              {uploading ? (
                <div className="flex flex-col items-center">
                  <Loader2 size={32} className="animate-spin text-cyan-600 mb-2" />
                  <p className="text-gray-600">업로드 중...</p>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <FileSpreadsheet size={32} className="text-cyan-600 mb-2" />
                  <p className="text-gray-700 font-medium">파일 선택</p>
                  <p className="text-sm text-gray-500 mt-1">xlsx, xls, csv</p>
                </div>
              )}
            </label>

            {error && (
              <p className="mt-3 text-sm text-red-600">{error}</p>
            )}
          </div>

          {/* 파일 정보 */}
          {fileInfo && (
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Table size={20} />
                데이터 정보
              </h3>

              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">파일명</span>
                  <span className="font-medium text-gray-900 truncate max-w-[150px]">
                    {fileInfo.file_name}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">행 수</span>
                  <span className="font-medium text-cyan-600">{fileInfo.row_count.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">열 수</span>
                  <span className="font-medium text-cyan-600">{fileInfo.col_count}</span>
                </div>
              </div>

              {/* 컬럼 목록 */}
              <div className="mt-4 pt-4 border-t border-gray-200">
                <p className="text-sm font-medium text-gray-700 mb-2">컬럼 목록</p>
                <div className="max-h-48 overflow-y-auto space-y-1">
                  {fileInfo.columns.map((col, idx) => (
                    <div key={idx} className="flex items-center justify-between text-sm py-1">
                      <span className="text-gray-600 truncate max-w-[120px]">{col.name}</span>
                      <span className="text-xs text-gray-400">{col.dtype}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 우측: 채팅 */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-lg flex flex-col h-[600px]">
          {/* 빠른 질문 */}
          {fileInfo && (
            <div className="p-4 border-b border-gray-200">
              <p className="text-sm text-gray-600 mb-2">⚡ 빠른 질문</p>
              <div className="flex flex-wrap gap-2">
                {quickQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSubmit(q)}
                    disabled={loading}
                    className="px-3 py-1.5 text-sm bg-cyan-50 text-cyan-700 rounded-full
                             hover:bg-cyan-100 transition-colors disabled:opacity-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 채팅 영역 */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-full bg-cyan-100 flex items-center justify-center flex-shrink-0">
                    <Bot size={18} className="text-cyan-600" />
                  </div>
                )}
                
                <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-first' : ''}`}>
                  <div className={`
                    px-4 py-3 rounded-2xl whitespace-pre-wrap
                    ${msg.role === 'user' 
                      ? 'bg-cyan-600 text-white rounded-tr-sm' 
                      : msg.isError 
                        ? 'bg-red-50 text-red-700 rounded-tl-sm'
                        : 'bg-gray-100 text-gray-800 rounded-tl-sm'}
                  `}>
                    {msg.content}
                  </div>
                </div>

                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0">
                    <User size={18} className="text-slate-600" />
                  </div>
                )}
              </div>
            ))}

            {/* 로딩 */}
            {loading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-cyan-100 flex items-center justify-center">
                  <Bot size={18} className="text-cyan-600" />
                </div>
                <div className="px-4 py-3 bg-gray-100 rounded-2xl rounded-tl-sm">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* 입력 영역 */}
          <div className="p-4 border-t border-gray-200">
            <form 
              onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
              className="flex gap-2"
            >
              <input
                type="text"
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg 
                         focus:outline-none focus:ring-2 focus:ring-cyan-500
                         disabled:bg-gray-50"
                placeholder={fileInfo ? "데이터에 대해 질문하세요..." : "먼저 파일을 업로드해주세요"}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading || !fileInfo}
              />
              <button
                type="submit"
                disabled={loading || !input.trim() || !fileInfo}
                className="px-6 py-3 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg 
                         transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <Loader2 size={20} className="animate-spin" />
                ) : (
                  <Send size={20} />
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DataAnalysis;
