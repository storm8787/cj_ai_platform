import { useState, useRef, useEffect } from 'react';
import { Scale, Send, User, Bot, Loader2, ChevronDown } from 'lucide-react';
import { electionLawApi } from '../services/api';

const SEARCH_TARGETS = [
  { value: 'all', label: '전체 검색' },
  { value: 'law', label: '법령' },
  { value: 'panli', label: '판례' },
  { value: 'written', label: '서면질의' },
  { value: 'internet', label: '인터넷질의' },
  { value: 'guidance', label: '지도기준' },
];

const QUICK_QUESTIONS = [
  '선거운동 기간은 언제부터인가요?',
  '공무원의 선거운동 제한은?',
  '사전선거운동의 정의는?',
  '기부행위 제한 규정은?',
];

function ElectionLaw() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '안녕하세요! 선거법 관련 질문에 답변드리는 AI 챗봇입니다. 궁금한 점을 물어보세요.',
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchTarget, setSearchTarget] = useState('all');
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
      const response = await electionLawApi.askQuestion({
        question: question,
        target: searchTarget,
      });

      const data = response.data;
      const assistantMessage = {
        role: 'assistant',
        content: data.answer || '답변을 생성할 수 없습니다.',
        references: data.references || [],
        questionType: data.question_type,
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
    <div className="h-[calc(100vh-8rem)] flex flex-col animate-fadeIn">
      {/* 상단 컨트롤 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Scale className="text-purple-600" size={24} />
          <h2 className="text-xl font-semibold text-gray-900">선거법 챗봇</h2>
        </div>
        
        {/* 검색 대상 선택 */}
        <select
          className="input-field w-auto"
          value={searchTarget}
          onChange={(e) => setSearchTarget(e.target.value)}
        >
          {SEARCH_TARGETS.map(({ value, label }) => (
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
            className="px-3 py-1.5 text-sm bg-purple-50 text-purple-700 rounded-full
                     hover:bg-purple-100 transition-colors disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>

      {/* 채팅 영역 */}
      <div className="flex-1 overflow-y-auto bg-white rounded-xl border border-gray-200 p-4 space-y-4">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
                <Bot size={18} className="text-purple-600" />
              </div>
            )}
            
            <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-first' : ''}`}>
              <div className={`
                px-4 py-3 rounded-2xl
                ${msg.role === 'user' 
                  ? 'bg-purple-600 text-white rounded-tr-sm' 
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
                    className="flex items-center gap-1 text-sm text-purple-600 hover:text-purple-700"
                  >
                    <ChevronDown 
                      size={16} 
                      className={`transition-transform ${showReferences[index] ? 'rotate-180' : ''}`}
                    />
                    참고자료 {msg.references.length}건
                  </button>
                  
                  {showReferences[index] && (
                    <div className="mt-2 space-y-2">
                      {msg.references.map((ref, refIndex) => (
                        <div key={refIndex} className="p-3 bg-gray-50 rounded-lg text-sm">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">
                              {ref.type || '문서'}
                            </span>
                            <span className="text-gray-500">
                              유사도: {(ref.similarity * 100).toFixed(1)}%
                            </span>
                          </div>
                          <p className="text-gray-600 line-clamp-3">{ref.content}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                <User size={18} className="text-gray-600" />
              </div>
            )}
          </div>
        ))}

        {/* 로딩 표시 */}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center">
              <Bot size={18} className="text-purple-600" />
            </div>
            <div className="px-4 py-3 bg-gray-100 rounded-2xl rounded-tl-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full loading-dot" />
                <span className="w-2 h-2 bg-gray-400 rounded-full loading-dot" />
                <span className="w-2 h-2 bg-gray-400 rounded-full loading-dot" />
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
            className="input-field flex-1"
            placeholder="선거법 관련 질문을 입력하세요..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="btn-primary flex items-center gap-2"
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
  );
}

export default ElectionLaw;
