import { useState, useRef, useEffect } from 'react';
import { Scale, Send, User, Bot, Loader2, ChevronDown, ExternalLink } from 'lucide-react';
import api from '../services/api';

const SEARCH_SCOPES = [
  { value: 'all', label: '전체 (법령+자치법규)' },
  { value: 'national', label: '국가법령' },
  { value: 'local', label: '충주시 자치법규' },
];

const QUICK_QUESTIONS = [
  '충주시 출산 지원 조례에서 지원금 대상은?',
  '지방공무원 연가일수 규정 알려줘',
  '개인정보보호법에서 공무원이 주의할 사항은?',
  '충주시 건축 조례 주요 내용 알려줘',
];

function LawChatbot() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '안녕하세요! 국가법령 및 충주시 자치법규에 대해 답변드리는 AI 챗봇입니다. 궁금한 점을 물어보세요.',
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [scope, setScope] = useState('all');
  const [showReferences, setShowReferences] = useState({});

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // 스크롤 자동 이동
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 질문 전송
  const handleSubmit = async (question = input) => {
    if (!question.trim() || loading) return;

    const userMessage = { role: 'user', content: question };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const chatHistory = messages.map(m => ({
        role: m.role,
        content: m.content,
      }));

      const response = await api.post('/api/law-chatbot/ask', {
        question: question,
        search_scope: scope,
        chat_history: chatHistory,
      });

      const data = response.data;
      const assistantMessage = {
        role: 'assistant',
        content: data.answer || '답변을 생성할 수 없습니다.',
        references: data.references || [],
        search_info: data.search_info || {},
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '죄송합니다. 답변 생성 중 오류가 발생했습니다. 다시 시도해주세요.',
        isError: true,
      }]);
      console.error(err);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  // 빠른 질문 클릭
  const handleQuickQuestion = (question) => {
    handleSubmit(question);
  };

  // 참고자료 토글
  const toggleReferences = (index) => {
    setShowReferences(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="h-[calc(100vh-12rem)] flex flex-col animate-fadeIn">
        {/* 상단 컨트롤 */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Scale className="text-cyan-400" size={24} />
            <h1 className="text-2xl font-bold text-white">법령·자치법규 챗봇</h1>
          </div>

          {/* 검색 범위 선택 */}
          <select
            className="px-4 py-2 bg-slate-800 border border-slate-700 text-white rounded-lg focus:outline-none focus:border-cyan-500"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
          >
            {SEARCH_SCOPES.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        {/* 빠른 질문 버튼 */}
        <div className="flex flex-wrap gap-2 mb-4">
          {QUICK_QUESTIONS.map((q, i) => (
            <button
              key={i}
              onClick={() => handleQuickQuestion(q)}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 rounded-full
                       hover:bg-cyan-500/20 transition-colors disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>

        {/* 채팅 영역 */}
        <div className="flex-1 overflow-y-auto bg-white rounded-xl border border-slate-200 p-4 space-y-4">
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
                  px-4 py-3 rounded-2xl
                  ${msg.role === 'user'
                    ? 'bg-cyan-600 text-white rounded-tr-sm'
                    : msg.isError
                      ? 'bg-red-50 text-red-700 rounded-tl-sm'
                      : 'bg-gray-100 text-gray-800 rounded-tl-sm'}
                `}>
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                </div>

                {/* 참고자료 */}
                {msg.references && msg.references.length > 0 && (
                  <div className="mt-2">
                    <button
                      onClick={() => toggleReferences(index)}
                      className="flex items-center gap-1 text-sm text-cyan-600 hover:text-cyan-700"
                    >
                      <ChevronDown
                        size={16}
                        className={`transition-transform ${showReferences[index] ? 'rotate-180' : ''}`}
                      />
                      참조 법령 {msg.references.length}건
                    </button>

                    {showReferences[index] && (
                      <div className="mt-2 space-y-2">
                        {msg.references.map((ref, refIndex) => (
                          <div key={refIndex} className="p-3 bg-gray-50 rounded-lg text-sm">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="px-2 py-0.5 bg-cyan-100 text-cyan-700 rounded text-xs">
                                {ref.type === '충주시 자치법규' ? '🏘️ 자치법규' : `🏛️ ${ref.type || '법령'}`}
                              </span>
                              {ref.article && (
                                <span className="text-gray-500 text-xs">{ref.article}</span>
                              )}
                            </div>
                            <div className="flex items-center justify-between">
                              <p className="text-gray-700 font-medium">{ref.name}</p>
                              {ref.url && (
                                <a
                                  href={ref.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-cyan-600 hover:text-cyan-700 ml-2 flex-shrink-0"
                                  title="국가법령정보센터에서 보기"
                                >
                                  <ExternalLink size={14} />
                                </a>
                              )}
                            </div>
                            {ref.enforcement_date && (
                              <p className="text-gray-400 text-xs mt-1">시행: {ref.enforcement_date}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* 검색 정보 */}
                {msg.search_info && (msg.search_info.vector_count > 0 || msg.search_info.api_count > 0) && (
                  <div className="mt-1 flex gap-3 text-xs text-gray-400">
                    {msg.search_info.vector_count > 0 && (
                      <span>🏘️ 자치법규 {msg.search_info.vector_count}건</span>
                    )}
                    {msg.search_info.api_count > 0 && (
                      <span>🏛️ 법령 {msg.search_info.api_count}건</span>
                    )}
                    {msg.search_info.detail_count > 0 && (
                      <span>📄 본문 {msg.search_info.detail_count}건</span>
                    )}
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0">
                  <User size={18} className="text-slate-600" />
                </div>
              )}
            </div>
          ))}

          {/* 로딩 표시 */}
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
        <div className="mt-4">
          <form
            onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
            className="flex gap-2"
          >
            <input
              ref={inputRef}
              type="text"
              className="flex-1 px-4 py-3 bg-slate-800 border border-slate-700 text-white rounded-lg
                       placeholder-slate-400 focus:outline-none focus:border-cyan-500"
              placeholder="법령이나 자치법규에 대해 질문하세요..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-cyan-500 hover:bg-cyan-600 text-white font-medium rounded-lg
                       transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loading ? (
                <Loader2 size={20} className="animate-spin" />
              ) : (
                <Send size={20} />
              )}
            </button>
          </form>
          <p className="text-center text-xs text-slate-500 mt-2">
            ※ AI 답변은 참고용이며, 정확한 법령 해석은 담당부서에 확인하시기 바랍니다
          </p>
        </div>
      </div>
    </div>
  );
}

export default LawChatbot;