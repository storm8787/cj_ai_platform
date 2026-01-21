import { useState, useRef, useCallback, useEffect } from 'react';
import { 
  Mic, Upload, Loader2, FileText, Download, Copy, Check,
  Users, FileQuestion, Clock, Sparkles, ChevronDown, ChevronUp
} from 'lucide-react';
import { meetingSummarizerApi } from '../services/api';

function MeetingSummarizer() {
  // 입력 상태
  const [inputMethod, setInputMethod] = useState('text'); // 'text' | 'file'
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  
  // 옵션 상태
  const [summaryMode, setSummaryMode] = useState('표준');
  const [focusPattern, setFocusPattern] = useState('');
  const [extractActions, setExtractActions] = useState(true);
  const [directiveMode, setDirectiveMode] = useState(false);
  const [autoAdjustMode, setAutoAdjustMode] = useState(true);
  const [extractFormat, setExtractFormat] = useState('요약'); // '요약' | '지시사항'
  
  // 결과 상태
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  
  // UI 상태
  const [showOptions, setShowOptions] = useState(false);
  const [showSystemInfo, setShowSystemInfo] = useState(false);
  const [systemInfo, setSystemInfo] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');
  
  const fileInputRef = useRef(null);
  const dropZoneRef = useRef(null);

  // 시스템 정보 로드
  useEffect(() => {
    loadSystemInfo();
  }, []);

  const loadSystemInfo = async () => {
    try {
      const response = await meetingSummarizerApi.getSystemInfo();
      setSystemInfo(response.data);
    } catch (err) {
      console.error('시스템 정보 로드 실패:', err);
    }
  };

  // 드래그 이벤트 핸들러
  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (dropZoneRef.current && !dropZoneRef.current.contains(e.relatedTarget)) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      validateAndSetFile(droppedFile);
    }
  }, []);

  const validateAndSetFile = (selectedFile) => {
    if (!selectedFile.name.endsWith('.txt')) {
      setError('txt 파일만 지원합니다.');
      return;
    }
    
    if (selectedFile.size > 5 * 1024 * 1024) {
      setError('파일 크기는 5MB 이하만 가능합니다.');
      return;
    }
    
    setFile(selectedFile);
    setError('');
    
    // 파일 내용 미리보기
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target.result;
      setText(content.substring(0, 500) + (content.length > 500 ? '...' : ''));
    };
    reader.readAsText(selectedFile);
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      validateAndSetFile(selectedFile);
    }
  };

  // 요약 실행
  const handleSummarize = async () => {
    const inputText = inputMethod === 'file' && file ? null : text;
    
    if (!inputText && !file) {
      setError('회의록 텍스트를 입력하거나 파일을 업로드해주세요.');
      return;
    }
    
    setLoading(true);
    setError('');
    setResult(null);
    
    try {
      let response;
      
      const isDirective = summaryMode === '표준' && extractFormat === '지시사항';
      
      if (inputMethod === 'file' && file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('summary_mode', summaryMode);
        formData.append('focus_pattern', focusPattern);
        formData.append('extract_actions', extractActions.toString());
        formData.append('directive_mode', isDirective.toString());
        formData.append('auto_adjust_mode', autoAdjustMode.toString());
        
        response = await meetingSummarizerApi.summarizeFile(formData);
      } else {
        response = await meetingSummarizerApi.summarize({
          text: text,
          summary_mode: summaryMode,
          focus_pattern: focusPattern || null,
          extract_actions: extractActions,
          directive_mode: isDirective,
          auto_adjust_mode: autoAdjustMode
        });
      }
      
      setResult(response.data);
      setActiveTab('summary');
      
    } catch (err) {
      setError(err.response?.data?.detail || '요약 처리 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 복사 기능
  const handleCopy = async () => {
    if (!result?.summary) return;
    
    try {
      await navigator.clipboard.writeText(result.summary.replace(/  \n/g, '\n'));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      setError('복사에 실패했습니다.');
    }
  };

  // 다운로드 기능
  const handleDownload = () => {
    if (!result?.summary) return;
    
    const content = result.summary.replace(/  \n/g, '\n');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `meeting_summary_${new Date().toISOString().slice(0, 10)}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const resetFile = () => {
    setFile(null);
    setText('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 헤더 */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Mic className="text-cyan-400" size={28} />
          <h1 className="text-2xl font-bold text-white">AI 스마트 회의록 요약기</h1>
        </div>
        <p className="text-slate-400">
          충주시 특화 AI가 회의록을 분석하여 체계적으로 요약해드립니다
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 입력 영역 */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">📄 회의록 입력</h2>
          
          {/* 입력 방식 선택 */}
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setInputMethod('text')}
              className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                inputMethod === 'text'
                  ? 'bg-cyan-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              직접 입력
            </button>
            <button
              onClick={() => setInputMethod('file')}
              className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                inputMethod === 'file'
                  ? 'bg-cyan-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              파일 업로드
            </button>
          </div>

          {/* 텍스트 입력 */}
          {inputMethod === 'text' && (
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="회의록을 붙여넣어주세요...

예시:
시장: 올해 관광 활성화 방안에 대해 논의합니다.
과장: 사계절 관광 프로그램 확대를 제안드립니다.
..."
              rows={12}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 resize-none"
            />
          )}

          {/* 파일 업로드 */}
          {inputMethod === 'file' && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt"
                onChange={handleFileChange}
                className="hidden"
              />
              
              <div
                ref={dropZoneRef}
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onClick={() => !file && fileInputRef.current?.click()}
                className={`
                  border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
                  transition-all duration-200
                  ${file 
                    ? 'border-cyan-400 bg-cyan-50' 
                    : isDragging
                      ? 'border-cyan-500 bg-cyan-100 scale-[1.02]'
                      : 'border-gray-300 hover:border-cyan-400 hover:bg-cyan-50'}
                `}
              >
                {file ? (
                  <div>
                    <FileText size={32} className="mx-auto text-cyan-600 mb-2" />
                    <p className="font-medium text-gray-900">{file.name}</p>
                    <p className="text-sm text-gray-500 mb-2">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                    <button
                      onClick={(e) => { e.stopPropagation(); resetFile(); }}
                      className="px-3 py-1 bg-gray-200 hover:bg-gray-300 rounded text-sm"
                    >
                      파일 변경
                    </button>
                  </div>
                ) : isDragging ? (
                  <div>
                    <Upload size={32} className="mx-auto text-cyan-600 mb-2 animate-bounce" />
                    <p className="text-cyan-700 font-medium">여기에 파일을 놓으세요!</p>
                  </div>
                ) : (
                  <div>
                    <Upload size={32} className="mx-auto text-gray-400 mb-2" />
                    <p className="text-gray-600 font-medium">텍스트 파일을 드래그하거나 클릭</p>
                    <p className="text-sm text-gray-400 mt-1">txt 파일 (최대 5MB)</p>
                  </div>
                )}
              </div>

              {/* 파일 미리보기 */}
              {file && text && (
                <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                  <p className="text-xs font-medium text-gray-500 mb-1">📄 미리보기</p>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">{text}</p>
                </div>
              )}
            </>
          )}

          {/* 옵션 영역 */}
          <div className="mt-4">
            <button
              onClick={() => setShowOptions(!showOptions)}
              className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-900"
            >
              {showOptions ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              요약 옵션 설정
            </button>
            
            {showOptions && (
              <div className="mt-3 p-4 bg-gray-50 rounded-lg space-y-4">
                {/* 요약 상세도 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    📊 요약 상세도
                  </label>
                  <div className="flex gap-2">
                    {['최소', '간략', '표준'].map((mode) => (
                      <button
                        key={mode}
                        onClick={() => setSummaryMode(mode)}
                        className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                          summaryMode === mode
                            ? 'bg-cyan-600 text-white'
                            : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        {mode}
                      </button>
                    ))}
                  </div>
                  <p className="mt-1 text-xs text-gray-500">
                    {summaryMode === '최소' && '핵심 키워드만 간단히 서술'}
                    {summaryMode === '간략' && '요점과 간단한 배경을 포함하여 요약'}
                    {summaryMode === '표준' && '배경→현황→문제점→대응→향후 계획까지 종합적으로 기술'}
                  </p>
                </div>

                {/* 출력 형식 (표준 모드일 때만) */}
                {summaryMode === '표준' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      📝 출력 형식
                    </label>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setExtractFormat('요약')}
                        className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                          extractFormat === '요약'
                            ? 'bg-cyan-600 text-white'
                            : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        요약
                      </button>
                      <button
                        onClick={() => setExtractFormat('지시사항')}
                        className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                          extractFormat === '지시사항'
                            ? 'bg-cyan-600 text-white'
                            : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        지시사항
                      </button>
                    </div>
                  </div>
                )}

                {/* 발화자 지정 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    🎙️ 요약 발화자 지정 (선택)
                  </label>
                  <input
                    type="text"
                    value={focusPattern}
                    onChange={(e) => setFocusPattern(e.target.value)}
                    placeholder="예: 시장, 과장 (비워두면 전체 요약)"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  />
                </div>

                {/* 체크박스 옵션 */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={extractActions}
                      onChange={(e) => setExtractActions(e.target.checked)}
                      className="rounded border-gray-300 text-cyan-600 focus:ring-cyan-500"
                    />
                    <span className="text-sm text-gray-700">액션 아이템 추출</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoAdjustMode}
                      onChange={(e) => setAutoAdjustMode(e.target.checked)}
                      className="rounded border-gray-300 text-cyan-600 focus:ring-cyan-500"
                    />
                    <span className="text-sm text-gray-700">입력 길이에 따라 모드 자동 조정</span>
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* AI 시스템 정보 */}
          <div className="mt-4">
            <button
              onClick={() => setShowSystemInfo(!showSystemInfo)}
              className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-900"
            >
              {showSystemInfo ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              AI 시스템 정보
            </button>
            
            {showSystemInfo && systemInfo && (
              <div className="mt-3 p-4 bg-cyan-50 rounded-lg">
                <p className="text-sm font-medium text-cyan-800 mb-2">✅ 충주시 특화 AI 활성화</p>
                <div className="grid grid-cols-2 gap-2 text-sm text-cyan-700">
                  <p>🏢 부서명 인식: {systemInfo.departments_count}개</p>
                  <p>🗺️ 지역명 인식: {systemInfo.locations_count}개</p>
                </div>
                <div className="mt-2 text-xs text-cyan-600">
                  {systemInfo.features?.map((f, i) => (
                    <span key={i} className="mr-2">• {f}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 에러 메시지 */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
              ❌ {error}
            </div>
          )}

          {/* 요약 버튼 */}
          <button
            onClick={handleSummarize}
            disabled={loading || (!text && !file)}
            className={`
              w-full mt-4 py-4 px-6 rounded-xl text-white font-semibold text-lg
              flex items-center justify-center gap-3 transition-colors
              ${loading || (!text && !file)
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-cyan-600 hover:bg-cyan-700'}
            `}
          >
            {loading ? (
              <>
                <Loader2 size={24} className="animate-spin" />
                AI 요약 중...
              </>
            ) : (
              <>
                <Sparkles size={24} />
                AI 요약 시작
              </>
            )}
          </button>
        </div>

        {/* 결과 영역 */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">✨ 요약 결과</h2>
            {result && (
              <div className="flex gap-2">
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 px-3 py-1.5 bg-cyan-100 hover:bg-cyan-200 text-cyan-700 rounded-lg text-sm transition-colors"
                >
                  {copied ? <Check size={16} /> : <Copy size={16} />}
                  {copied ? '복사됨!' : '복사'}
                </button>
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm transition-colors"
                >
                  <Download size={16} />
                  다운로드
                </button>
              </div>
            )}
          </div>

          {result ? (
            <>
              {/* 탭 */}
              <div className="flex gap-2 mb-4 border-b border-gray-200">
                <button
                  onClick={() => setActiveTab('summary')}
                  className={`pb-2 px-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'summary'
                      ? 'border-cyan-600 text-cyan-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  📄 요약 결과
                </button>
                {result.actions?.length > 0 && (
                  <button
                    onClick={() => setActiveTab('actions')}
                    className={`pb-2 px-3 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'actions'
                        ? 'border-cyan-600 text-cyan-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    📋 액션 아이템 ({result.actions.length})
                  </button>
                )}
                <button
                  onClick={() => setActiveTab('stats')}
                  className={`pb-2 px-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'stats'
                      ? 'border-cyan-600 text-cyan-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  📊 분석 상세
                </button>
              </div>

              {/* 탭 내용 */}
              <div className="min-h-[400px]">
                {activeTab === 'summary' && (
                  <div className="prose prose-sm max-w-none">
                    <div className="whitespace-pre-wrap text-gray-800 leading-relaxed">
                      {result.summary.replace(/  \n/g, '\n')}
                    </div>
                  </div>
                )}

                {activeTab === 'actions' && result.actions?.length > 0 && (
                  <div className="space-y-4">
                    {result.actions.map((action, i) => (
                      <div key={i} className="p-4 bg-gray-50 rounded-lg">
                        <p className="font-semibold text-gray-900 mb-2">
                          {i + 1}. {action.task}
                        </p>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <p className="text-gray-600">
                            👤 담당: <span className="font-medium">{action.assignee}</span>
                          </p>
                          <p className="text-gray-600">
                            📅 기한: <span className="font-medium">{action.deadline}</span>
                          </p>
                        </div>
                        {action.details && action.details !== action.task && (
                          <p className="mt-2 text-sm text-gray-500">
                            📝 {action.details}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'stats' && result.analysis_stats && (
                  <div className="space-y-4">
                    {/* 통계 카드 */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <div className="bg-cyan-50 rounded-lg p-3 text-center">
                        <Users className="mx-auto text-cyan-600 mb-1" size={20} />
                        <p className="text-2xl font-bold text-cyan-700">
                          {result.analysis_stats.speaker_count}
                        </p>
                        <p className="text-xs text-cyan-600">발화자 수</p>
                      </div>
                      <div className="bg-blue-50 rounded-lg p-3 text-center">
                        <FileQuestion className="mx-auto text-blue-600 mb-1" size={20} />
                        <p className="text-2xl font-bold text-blue-700">
                          {result.analysis_stats.topic_count}
                        </p>
                        <p className="text-xs text-blue-600">주요 주제</p>
                      </div>
                      <div className="bg-purple-50 rounded-lg p-3 text-center">
                        <Sparkles className="mx-auto text-purple-600 mb-1" size={20} />
                        <p className="text-2xl font-bold text-purple-700">
                          {result.analysis_stats.keyword_count}
                        </p>
                        <p className="text-xs text-purple-600">용어 보정</p>
                      </div>
                      <div className="bg-orange-50 rounded-lg p-3 text-center">
                        <Clock className="mx-auto text-orange-600 mb-1" size={20} />
                        <p className="text-2xl font-bold text-orange-700">
                          {result.analysis_stats.processing_time}초
                        </p>
                        <p className="text-xs text-orange-600">처리 시간</p>
                      </div>
                    </div>

                    {/* 검증 상태 */}
                    <div className={`p-3 rounded-lg ${
                      result.analysis_stats.validation_status?.includes('통과')
                        ? 'bg-green-50 text-green-700'
                        : 'bg-yellow-50 text-yellow-700'
                    }`}>
                      <p className="text-sm">
                        {result.analysis_stats.validation_status?.includes('통과') ? '✅' : 'ℹ️'} 
                        {' '}검증 상태: {result.analysis_stats.validation_status}
                      </p>
                    </div>

                    {/* 용어 보정 내역 */}
                    {result.analysis_stats.corrections?.length > 0 && (
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-sm font-medium text-gray-700 mb-2">🔧 용어 보정 내역</p>
                        <div className="flex flex-wrap gap-2">
                          {result.analysis_stats.corrections.map((c, i) => (
                            <span key={i} className="px-2 py-1 bg-white rounded text-xs text-gray-600 border">
                              {c}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 모드 조정 */}
                    {result.analysis_stats.mode_adjustment && (
                      <div className="p-3 bg-yellow-50 rounded-lg">
                        <p className="text-sm text-yellow-700">
                          ⚠️ {result.analysis_stats.mode_adjustment}
                        </p>
                      </div>
                    )}

                    {/* 요약 설정 정보 */}
                    <div className="p-3 bg-gray-50 rounded-lg text-sm text-gray-600">
                      <p className="font-medium text-gray-700 mb-2">📊 요약 설정 정보</p>
                      <p>• 선택 모드: <strong>{result.analysis_stats.original_mode}</strong></p>
                      <p>• 적용 모드: <strong>{result.analysis_stats.effective_mode}</strong></p>
                      <p>• 요약 타입: <strong>{result.analysis_stats.summary_type}</strong></p>
                      <p>• 입력 길이: {result.analysis_stats.input_length}자 ({result.analysis_stats.input_category})</p>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="h-[400px] flex items-center justify-center text-gray-400">
              <div className="text-center">
                <Mic size={48} className="mx-auto mb-2 opacity-50" />
                <p>회의록을 입력하고</p>
                <p>AI 요약을 시작해보세요!</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 안내 */}
      <div className="mt-6 bg-cyan-500/10 border border-cyan-500/20 rounded-xl p-4">
        <h3 className="font-semibold text-cyan-300 mb-2">💡 사용 안내</h3>
        <ul className="text-sm text-slate-300 space-y-1">
          <li>• 발화자 형식: "시장:", "과장:", "참석자1:" 등으로 구분하면 더 정확한 요약이 가능합니다</li>
          <li>• 특정 발화자만 요약하려면 발화자 지정 옵션을 사용하세요</li>
          <li>• 충주시 부서명과 지역명은 자동으로 인식하고 보정합니다</li>
          <li>• 표준 모드에서 "지시사항" 형식을 선택하면 ~할 것 스타일로 출력됩니다</li>
        </ul>
      </div>
    </div>
  );
}

export default MeetingSummarizer;
