import { useState, useEffect } from 'react';
import { FileText, ChevronRight, Download, RefreshCw, Sparkles, ClipboardCopy, Check } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function ReportWriter() {
  // 상태 관리
  const [structures, setStructures] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  
  // 입력 상태
  const [title, setTitle] = useState('');
  const [reportType, setReportType] = useState('');
  const [detailType, setDetailType] = useState('');
  const [keywords, setKeywords] = useState('');
  const [length, setLength] = useState('표준');

  // 선택 입력 (비우면 키워드 중심 생성)
  const [department, setDepartment] = useState('');
  const [author, setAuthor] = useState('');
  const [reportDate, setReportDate] = useState('');
  const [facts, setFacts] = useState('');
  const [showOptional, setShowOptional] = useState(false);
  
  // 결과 상태
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');

  // 구조 데이터 로드
  useEffect(() => {
    fetchStructures();
  }, []);

  // 보고서 유형 변경 시 세부 유형 초기화
  useEffect(() => {
    if (structures && reportType) {
      const detailTypes = Object.keys(structures.report_types[reportType] || {});
      if (detailTypes.length > 0) {
        setDetailType(detailTypes[0]);
      }
    }
  }, [reportType, structures]);

  const fetchStructures = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/report-writer/structures`);
      const data = await res.json();
      setStructures(data);
      
      // 초기값 설정
      const types = Object.keys(data.report_types);
      if (types.length > 0) {
        setReportType(types[0]);
        const details = Object.keys(data.report_types[types[0]]);
        if (details.length > 0) {
          setDetailType(details[0]);
        }
      }
    } catch (err) {
      console.error('구조 로드 실패:', err);
    }
  };

  const handleGenerate = async () => {
    if (!title.trim()) {
      setError('보고서 제목을 입력해주세요.');
      return;
    }
    if (!keywords.trim()) {
      setError('키워드를 입력해주세요.');
      return;
    }

    setLoading(true);
    setError('');
    setReport(null);

    try {
      const res = await fetch(`${API_BASE}/api/report-writer/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title.trim(),
          report_type: reportType,
          detail_type: detailType,
          keywords: keywords.trim(),
          length: length,
          department: department.trim(),
          author: author.trim(),
          report_date: reportDate.trim(),
          facts: facts.trim()
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || '생성 실패');
      }

      const data = await res.json();
      setReport(data);
    } catch (err) {
      setError(err.message || '보고서 생성 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setReport(null);
    setError('');
  };

  const handleCopyText = () => {
    if (!report) return;
    
    let text = `${report.title}\n`;
    const metaLine = [report.department, report.report_date, report.author].filter(Boolean).join('  ·  ');
    if (metaLine) text += `${metaLine}\n`;
    text += `\n[요약]\n${report.summary}\n\n`;

    report.sections.forEach(sec => {
      text += `■ ${sec.title}\n`;
      sec.content.forEach(para => {
        text += `  ❍ ${para}\n`;
      });
      text += '\n';
    });

    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadTxt = () => {
    if (!report) return;
    
    let text = `${report.title}\n`;
    const metaLine = [report.department, report.report_date, report.author].filter(Boolean).join('  ·  ');
    if (metaLine) text += `${metaLine}\n`;
    text += `${'='.repeat(50)}\n\n`;
    text += `[요약]\n${report.summary}\n\n`;
    text += `${'─'.repeat(50)}\n\n`;
    
    report.sections.forEach(sec => {
      text += `■ ${sec.title}\n`;
      sec.content.forEach(para => {
        text += `  ❍ ${para}\n`;
      });
      text += '\n';
    });
    
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.title.slice(0, 20).replace(/\s/g, '_')}_보고서.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 현재 선택된 구조 미리보기
  const currentSections = structures?.report_types?.[reportType]?.[detailType] || [];

  return (
    <div className="min-h-screen bg-slate-50">
      {/* 헤더 */}
      <div className="bg-slate-900 text-white py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-3 mb-2">
            <FileText className="text-cyan-400" size={32} />
            <h1 className="text-2xl font-bold">AI 업무보고 생성기</h1>
          </div>
          <p className="text-slate-400">
            공무원 업무보고 스타일에 맞는 보고서를 AI가 자동으로 작성합니다
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* 입력 폼 */}
        {!report && (
          <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
            {/* 제목 */}
            <div className="mb-6">
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                📝 보고서 제목
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="예: 2026년 스마트시티 추진계획"
                className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              />
            </div>

            {/* 유형 선택 (3열) */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  📂 보고서 유형
                </label>
                <select
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value)}
                  className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-cyan-500"
                >
                  {structures && Object.keys(structures.report_types).map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  📋 세부 유형
                </label>
                <select
                  value={detailType}
                  onChange={(e) => setDetailType(e.target.value)}
                  className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-cyan-500"
                >
                  {structures && reportType && 
                    Object.keys(structures.report_types[reportType] || {}).map(detail => (
                      <option key={detail} value={detail}>{detail}</option>
                    ))
                  }
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  📏 보고서 분량
                </label>
                <select
                  value={length}
                  onChange={(e) => setLength(e.target.value)}
                  className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-cyan-500"
                >
                  <option value="간략">간략 (섹션당 3~4항목·항목당 1~2문장)</option>
                  <option value="표준">표준 (섹션당 4~6항목·항목당 2~3문장)</option>
                  <option value="상세">상세 (섹션당 6~8항목·항목당 3~4문장)</option>
                </select>
              </div>
            </div>

            {/* 키워드 */}
            <div className="mb-6">
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                🏷️ 핵심 키워드
              </label>
              <input
                type="text"
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                placeholder="쉼표로 구분 (예: 스마트시티, 데이터 기반, 시민 편의)"
                className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-cyan-500"
              />
            </div>

            {/* 선택 입력 (부서·작성자·보고일자 + 확인된 사실) */}
            <div className="mb-6 border border-slate-200 rounded-xl overflow-hidden">
              <button
                type="button"
                onClick={() => setShowOptional((v) => !v)}
                className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-all text-left"
              >
                <span className="text-sm font-semibold text-slate-700">
                  ⚙️ 선택 입력 (부서·작성자·보고일자·확인된 사실)
                </span>
                <ChevronRight
                  className={`text-slate-400 transition-transform ${showOptional ? 'rotate-90' : ''}`}
                  size={18}
                />
              </button>

              {showOptional && (
                <div className="p-4 space-y-4">
                  <p className="text-xs text-slate-500">
                    비워두면 키워드 중심으로 생성됩니다. 아는 사실을 적을수록 정확도가 올라가며,
                    확인되지 않은 수치는 AI가 지어내지 않고 <span className="font-semibold">○○·□□</span> 자리표시자로 남깁니다.
                  </p>

                  {/* 부서 / 작성자 / 보고일자 (3열) */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 mb-1">부서명</label>
                      <input
                        type="text"
                        value={department}
                        onChange={(e) => setDepartment(e.target.value)}
                        placeholder="예: 자치행정과"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-cyan-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 mb-1">작성자</label>
                      <input
                        type="text"
                        value={author}
                        onChange={(e) => setAuthor(e.target.value)}
                        placeholder="예: 홍길동 주무관"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-cyan-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 mb-1">보고일자</label>
                      <input
                        type="text"
                        value={reportDate}
                        onChange={(e) => setReportDate(e.target.value)}
                        placeholder="예: 2026. 7. 8."
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-cyan-500"
                      />
                    </div>
                  </div>

                  {/* 확인된 사실 */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">
                      확인된 사실 · 배경 · 현황 (자유 서술)
                    </label>
                    <textarea
                      value={facts}
                      onChange={(e) => setFacts(e.target.value)}
                      rows={5}
                      placeholder={'아는 사실을 자유롭게 적어주세요. 예)\n- 관내 CCTV 856대 중 노후장비 274대(32%)\n- 2026년 사업비 3억원 확보\n- 설치 대상지 15개소, 준공목표 6월'}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-cyan-500 resize-y"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* 구조 미리보기 */}
            <div className="mb-6">
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                🔍 보고서 구조 미리보기
              </label>
              <div className="bg-slate-50 rounded-xl p-4 border border-slate-200">
                <div className="flex flex-wrap items-center gap-2">
                  {currentSections.map((section, idx) => (
                    <span key={idx} className="flex items-center">
                      <span className="px-3 py-1.5 bg-white border border-slate-200 rounded-full text-sm font-medium text-slate-700 shadow-sm">
                        {section}
                      </span>
                      {idx < currentSections.length - 1 && (
                        <ChevronRight className="text-slate-300 mx-1" size={16} />
                      )}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* 에러 메시지 */}
            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
                {error}
              </div>
            )}

            {/* 생성 버튼 */}
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="w-full py-4 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-cyan-500/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <RefreshCw className="animate-spin" size={20} />
                  AI가 보고서를 작성 중입니다...
                </>
              ) : (
                <>
                  <Sparkles size={20} />
                  보고서 생성하기
                </>
              )}
            </button>
          </div>
        )}

        {/* 결과 표시 */}
        {report && (
          <div className="space-y-6">
            {/* 보고서 내용 */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              {/* 제목 */}
              <div className="border-2 border-slate-700 rounded-lg p-4 mb-6 text-center">
                <h2 className="text-xl font-bold text-slate-900">{report.title}</h2>
                {(report.department || report.author || report.report_date) && (
                  <p className="mt-2 text-sm text-slate-500">
                    {[report.department, report.report_date, report.author]
                      .filter(Boolean)
                      .join('  ·  ')}
                  </p>
                )}
              </div>

              {/* 요약 */}
              <div className="mb-6 p-4 bg-cyan-50 rounded-xl border border-cyan-200">
                <h3 className="text-sm font-semibold text-cyan-700 mb-2">📌 요약</h3>
                <p className="text-slate-700 leading-relaxed">{report.summary}</p>
              </div>

              {/* 섹션별 내용 */}
              {report.sections.map((section, idx) => (
                <div key={idx} className="mb-6 last:mb-0">
                  <h3 className="flex items-center gap-2 text-lg font-bold text-slate-900 mb-3 pb-2 border-b border-slate-200">
                    <span className="w-2 h-4 bg-slate-800"></span>
                    {section.title}
                  </h3>
                  <div className="space-y-2 pl-4">
                    {section.content.map((para, pIdx) => (
                      <p key={pIdx} className="text-slate-700 leading-relaxed flex">
                        <span className="text-cyan-600 mr-2 flex-shrink-0">❍</span>
                        <span>{para}</span>
                      </p>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* 액션 버튼 */}
            <div className="grid grid-cols-3 gap-4">
              <button
                onClick={handleCopyText}
                className="flex items-center justify-center gap-2 py-3 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-all font-medium text-slate-700"
              >
                {copied ? <Check size={18} className="text-green-500" /> : <ClipboardCopy size={18} />}
                {copied ? '복사됨!' : '텍스트 복사'}
              </button>
              
              <button
                onClick={handleDownloadTxt}
                className="flex items-center justify-center gap-2 py-3 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-all font-medium text-slate-700"
              >
                <Download size={18} />
                TXT 다운로드
              </button>
              
              <button
                onClick={handleReset}
                className="flex items-center justify-center gap-2 py-3 bg-slate-100 border border-slate-200 rounded-xl hover:bg-slate-200 transition-all font-medium text-slate-700"
              >
                <RefreshCw size={18} />
                다시 작성
              </button>
            </div>

            {/* 안내 */}
            <p className="text-center text-sm text-slate-500">
              💡 생성된 보고서는 참고용입니다. 필요에 따라 내용을 수정하여 사용하세요.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}