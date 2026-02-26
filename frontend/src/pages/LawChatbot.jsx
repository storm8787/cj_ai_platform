import { useState, useRef, useEffect } from 'react';
import {
  Scale, Send, BookOpen, ExternalLink, Loader2,
  RotateCcw, Search, ChevronRight
} from 'lucide-react';
import api from '../services/api';

const CATEGORIES = [
  { id: 'all', name: '전체', icon: '📚' },
  { id: 'national', name: '국가법령', icon: '🏛️' },
  { id: 'local', name: '충주시 자치법규', icon: '🏘️' },
];

const SUGGESTED_QUESTIONS = [
  "충주시 출산 지원 조례에서 지원금 대상은?",
  "지방공무원 연가일수 규정 알려줘",
  "개인정보보호법에서 공무원이 주의할 사항은?",
  "충주시 도시공원 조례에서 공원 점용 허가 기준은?",
  "민원 처리에 관한 법률에서 처리기간 규정은?",
  "충주시 건축 조례 주요 내용 알려줘",
];

export default function LawChatbot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [scope, setScope] = useState('all');
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text = input) => {
    const q = (typeof text === 'string' ? text : input).trim();
    if (!q || loading) return;

    const userMsg = { role: 'user', content: q };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const chatHistory = messages.map(m => ({
        role: m.role,
        content: m.content,
      }));

      const res = await api.post('/api/law-chatbot/ask', {
        question: q,
        search_scope: scope,
        chat_history: chatHistory,
      });

      const { answer, references, search_info } = res.data;

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: answer,
        references: references || [],
        search_info: search_info || {},
      }]);
    } catch (err) {
      console.error('법령 챗봇 오류:', err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '죄송합니다. 법령 검색 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
        error: true,
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleReset = () => {
    setMessages([]);
    setInput('');
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* 헤더 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
              <Scale className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">법령정보 · 자치법규 챗봇</h1>
              <p className="text-xs text-gray-400">국가법령 + 충주시 자치법규 AI 검색</p>
            </div>
          </div>
          {messages.length > 0 && (
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm
                         text-gray-400 hover:text-white hover:bg-white/10 transition-all"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              새 대화
            </button>
          )}
        </div>
      </div>

      {/* 검색 범위 선택 */}
      <div className="flex gap-2 mb-4">
        {CATEGORIES.map(cat => (
          <button
            key={cat.id}
            onClick={() => setScope(cat.id)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              scope === cat.id
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-gray-300'
            }`}
          >
            {cat.icon} {cat.name}
          </button>
        ))}
      </div>

      {/* 채팅 영역 */}
      <div className="bg-white/[0.03] backdrop-blur-sm rounded-xl border border-white/10 
                       min-h-[500px] max-h-[600px] overflow-y-auto p-4 mb-4
                       scrollbar-thin scrollbar-thumb-white/10">

        {/* 초기 화면 */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center py-10">
            <div className="w-16 h-16 rounded-2xl bg-blue-500/10 flex items-center justify-center mb-4">
              <Scale className="w-8 h-8 text-blue-400/60" />
            </div>
            <h2 className="text-lg font-semibold text-white mb-1">
              법령 · 자치법규 AI 어시스턴트
            </h2>
            <p className="text-sm text-gray-500 mb-8 text-center">
              국가법령정보센터 실시간 검색 + 충주시 자치법규 의미 검색
            </p>

            <div className="w-full max-w-lg space-y-2">
              <p className="text-xs text-gray-500 mb-2 flex items-center gap-1">
                <Search className="w-3 h-3" /> 이런 질문을 해보세요
              </p>
              {SUGGESTED_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(q)}
                  className="w-full text-left px-4 py-2.5 rounded-lg
                             bg-white/[0.03] hover:bg-white/[0.08]
                             text-gray-300 text-sm transition-all
                             border border-white/5 hover:border-blue-500/30
                             flex items-center justify-between group"
                >
                  <span>{q}</span>
                  <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-blue-400 transition-colors" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 메시지 목록 */}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`mb-4 flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-[85%] rounded-xl px-4 py-3 ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white'
                : msg.error
                  ? 'bg-red-500/10 border border-red-500/20 text-gray-200'
                  : 'bg-white/[0.06] border border-white/5 text-gray-200'
            }`}>
              {/* 답변 텍스트 */}
              <div className="whitespace-pre-wrap text-sm leading-relaxed">
                {msg.content}
              </div>

              {/* 참조 법령 */}
              {msg.references && msg.references.length > 0 && (
                <div className="mt-3 pt-3 border-t border-white/10">
                  <p className="text-xs text-gray-400 mb-2 flex items-center gap-1">
                    <BookOpen className="w-3 h-3" /> 참조 법령
                  </p>
                  <div className="space-y-1.5">
                    {msg.references.map((ref, j) => (
                      <div key={j} className="flex items-start gap-2 text-xs">
                        <span className="mt-0.5">
                          {ref.type === '충주시 자치법규' ? '🏘️' : '🏛️'}
                        </span>
                        <div className="flex-1 min-w-0">
                          <span className="text-gray-300">{ref.name}</span>
                          {ref.article && (
                            <span className="text-gray-500 ml-1">{ref.article}</span>
                          )}
                          {ref.type && ref.type !== '충주시 자치법규' && (
                            <span className="text-gray-600 ml-1">({ref.type})</span>
                          )}
                        </div>
                        {ref.url && (
                          <a
                            href={ref.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-400 hover:text-blue-300 shrink-0"
                            title="국가법령정보센터에서 보기"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 검색 정보 */}
              {msg.search_info && (msg.search_info.vector_count > 0 || msg.search_info.api_count > 0) && (
                <div className="mt-2 flex gap-3 text-[11px] text-gray-600">
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
          </div>
        ))}

        {/* 로딩 */}
        {loading && (
          <div className="flex justify-start mb-4">
            <div className="bg-white/[0.06] border border-white/5 rounded-xl px-4 py-3
                            flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
              <span className="text-sm text-gray-400">법령 검색 및 분석 중...</span>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* 입력 영역 */}
      <div className="flex gap-2">
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="법령이나 자치법규에 대해 질문하세요..."
          rows={1}
          className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3
                     text-white placeholder-gray-500 resize-none text-sm
                     focus:outline-none focus:border-blue-500/50 focus:bg-white/[0.07]
                     transition-all"
        />
        <button
          onClick={() => handleSend()}
          disabled={!input.trim() || loading}
          className="px-4 py-3 bg-blue-600 hover:bg-blue-500 
                     disabled:bg-white/5 disabled:text-gray-600
                     disabled:cursor-not-allowed rounded-xl text-white transition-all"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>

      {/* 하단 안내 */}
      <p className="text-center text-[11px] text-gray-600 mt-3">
        ※ AI 답변은 참고용이며, 정확한 법령 해석은 법제팀에 확인하시기 바랍니다
      </p>
    </div>
  );
}