import { useState, useEffect } from 'react';
import { FileText, ChevronRight, Download, RefreshCw, Sparkles, ClipboardCopy, Check, ChevronUp, ChevronDown, X, Plus, RotateCcw, Pencil } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function ReportWriter() {
  // 상태 관리
  const [structures, setStructures] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [hwpxLoading, setHwpxLoading] = useState(false);
  
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

  // 목차(섹션) 편집 상태
  const [sections, setSections] = useState([]);
  const [sectionsEdited, setSectionsEdited] = useState(false);

  // 결과 상태
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [editMode, setEditMode] = useState(false);

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

  // 유형/세부유형 변경 시 목차를 기본값으로 초기화
  useEffect(() => {
    const def = structures?.report_types?.[reportType]?.[detailType] || [];
    setSections(def);
    setSectionsEdited(false);
  }, [reportType, detailType, structures]);

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
    const cleanSections = sections.map((s) => s.trim()).filter(Boolean);
    if (cleanSections.length === 0) {
      setError('목차 항목을 1개 이상 입력해주세요.');
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
          facts: facts.trim(),
          custom_sections: cleanSections
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || '생성 실패');
      }

      const data = await res.json();
      setReport(data);
      setEditMode(false);
    } catch (err) {
      setError(err.message || '보고서 생성 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setReport(null);
    setError('');
    setEditMode(false);
  };

  // ── 결과 인라인 편집 핸들러 ──
  const updateReportField = (field, value) => {
    setReport((prev) => ({ ...prev, [field]: value }));
  };

  const updateSecTitle = (sIdx, value) => {
    setReport((prev) => ({
      ...prev,
      sections: prev.sections.map((s, i) => (i === sIdx ? { ...s, title: value } : s)),
    }));
  };

  const moveSec = (sIdx, dir) => {
    setReport((prev) => {
      const secs = [...prev.sections];
      const t = sIdx + dir;
      if (t < 0 || t >= secs.length) return prev;
      [secs[sIdx], secs[t]] = [secs[t], secs[sIdx]];
      return { ...prev, sections: secs };
    });
  };

  const removeSec = (sIdx) => {
    setReport((prev) => ({
      ...prev,
      sections: prev.sections.filter((_, i) => i !== sIdx),
    }));
  };

  const addSec = () => {
    setReport((prev) => ({
      ...prev,
      sections: [...prev.sections, { title: '새 항목', order: prev.sections.length + 1, content: [''] }],
    }));
  };

  const updateItem = (sIdx, iIdx, value) => {
    setReport((prev) => ({
      ...prev,
      sections: prev.sections.map((s, i) =>
        i === sIdx ? { ...s, content: s.content.map((c, j) => (j === iIdx ? value : c)) } : s
      ),
    }));
  };

  const moveItem = (sIdx, iIdx, dir) => {
    setReport((prev) => ({
      ...prev,
      sections: prev.sections.map((s, i) => {
        if (i !== sIdx) return s;
        const content = [...s.content];
        const t = iIdx + dir;
        if (t < 0 || t >= content.length) return s;
        [content[iIdx], content[t]] = [content[t], content[iIdx]];
        return { ...s, content };
      }),
    }));
  };

  const removeItem = (sIdx, iIdx) => {
    setReport((prev) => ({
      ...prev,
      sections: prev.sections.map((s, i) =>
        i === sIdx ? { ...s, content: s.content.filter((_, j) => j !== iIdx) } : s
      ),
    }));
  };

  const addItem = (sIdx) => {
    setReport((prev) => ({
      ...prev,
      sections: prev.sections.map((s, i) =>
        i === sIdx ? { ...s, content: [...s.content, ''] } : s
      ),
    }));
  };

  // ── HWPX(한글) 다운로드 ──
  const handleDownloadHwpx = async () => {
    if (!report) return;
    setHwpxLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/report-writer/export-hwpx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: report.title || '',
          summary: report.summary || '',
          department: report.department || '',
          author: report.author || '',
          report_date: report.report_date || '',
          sections: report.sections.map((s) => ({
            title: s.title || '',
            order: s.order || 0,
            content: (s.content || []).filter((c) => c && c.trim()),
          })),
        }),
      });

      if (!res.ok) {
        let msg = 'HWPX 생성 실패';
        try {
          const e = await res.json();
          msg = e.detail || msg;
        } catch (_) { /* ignore */ }
        throw new Error(msg);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(report.title || '업무보고').slice(0, 20).replace(/\s/g, '_')}.hwpx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message || 'HWPX 다운로드 중 오류가 발생했습니다.');
    } finally {
      setHwpxLoading(false);
    }
  };

  // ── 목차(섹션) 편집 핸들러 ──
  const defaultSections = structures?.report_types?.[reportType]?.[detailType] || [];

  const updateSection = (idx, value) => {
    setSections((prev) => prev.map((s, i) => (i === idx ? value : s)));
    setSectionsEdited(true);
  };

  const removeSection = (idx) => {
    setSections((prev) => prev.filter((_, i) => i !== idx));
    setSectionsEdited(true);
  };

  const moveSection = (idx, dir) => {
    setSections((prev) => {
      const next = [...prev];
      const target = idx + dir;
      if (target < 0 || target >= next.length) return prev;
      [next[idx], next[target]] = [next[target], next[idx]];
      return next;
    });
    setSectionsEdited(true);
  };

  const addSection = () => {
    setSections((prev) => [...prev, '']);
    setSectionsEdited(true);
  };

  const resetSections = () => {
    setSections(defaultSections);
    setSectionsEdited(false);
  };

  // 항목 앞의 개조식 번호(가. / 1) / 1. / ①)를 인식해 마커와 본문을 분리
  const parseItem = (text) => {
    const m = (text || '').match(/^((?:[가-힣][.)])|(?:\d{1,2}[.)])|[①-⑳])\s+/);
    if (m) {
      return { marker: m[1], body: text.slice(m[0].length), sub: /^[가-힣]/.test(m[1]) };
    }
    return { marker: null, body: text, sub: false };
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
        if (!para || !para.trim()) return;
        const { marker, body, sub } = parseItem(para);
        text += `${sub ? '    ' : '  '}${marker || '❍'} ${body}\n`;
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
        if (!para || !para.trim()) return;
        const { marker, body, sub } = parseItem(para);
        text += `${sub ? '    ' : '  '}${marker || '❍'} ${body}\n`;
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

            {/* 목차(섹션) 편집 */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-semibold text-slate-700">
                  🔍 보고서 목차 (편집 가능)
                  {sectionsEdited && (
                    <span className="ml-2 text-xs font-normal text-cyan-600">· 사용자 지정</span>
                  )}
                </label>
                {sectionsEdited && defaultSections.length > 0 && (
                  <button
                    type="button"
                    onClick={resetSections}
                    className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700"
                  >
                    <RotateCcw size={14} />
                    기본 목차로 초기화
                  </button>
                )}
              </div>

              <div className="bg-slate-50 rounded-xl p-3 border border-slate-200 space-y-2">
                {sections.map((section, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className="w-6 text-right text-sm text-slate-400 flex-shrink-0">
                      {idx + 1}.
                    </span>
                    <input
                      type="text"
                      value={section}
                      onChange={(e) => updateSection(idx, e.target.value)}
                      placeholder="목차 항목명 (예: 추진배경)"
                      className="flex-1 px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                    />
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button
                        type="button"
                        onClick={() => moveSection(idx, -1)}
                        disabled={idx === 0}
                        title="위로"
                        className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-white rounded-md disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        <ChevronUp size={16} />
                      </button>
                      <button
                        type="button"
                        onClick={() => moveSection(idx, 1)}
                        disabled={idx === sections.length - 1}
                        title="아래로"
                        className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-white rounded-md disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        <ChevronDown size={16} />
                      </button>
                      <button
                        type="button"
                        onClick={() => removeSection(idx)}
                        title="삭제"
                        className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-white rounded-md"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  </div>
                ))}

                <button
                  type="button"
                  onClick={addSection}
                  className="w-full flex items-center justify-center gap-1 py-2 mt-1 border border-dashed border-slate-300 rounded-lg text-sm text-slate-500 hover:text-cyan-600 hover:border-cyan-400 transition-all"
                >
                  <Plus size={16} />
                  목차 항목 추가
                </button>
              </div>
              <p className="mt-1.5 text-xs text-slate-400">
                💡 표준 목차 항목명(추진배경·기대효과 등)을 사용하면 항목별 작성 스타일이 자동 적용됩니다.
              </p>
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
              {/* 편집 토글 */}
              <div className="flex justify-end mb-4">
                <button
                  onClick={() => setEditMode((v) => !v)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    editMode
                      ? 'bg-cyan-600 text-white hover:bg-cyan-700'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {editMode ? <><Check size={16} /> 편집 완료</> : <><Pencil size={16} /> 내용 편집</>}
                </button>
              </div>

              {/* 제목 */}
              <div className="border-2 border-slate-700 rounded-lg p-4 mb-6 text-center">
                {editMode ? (
                  <input
                    type="text"
                    value={report.title}
                    onChange={(e) => updateReportField('title', e.target.value)}
                    className="w-full text-xl font-bold text-slate-900 text-center bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                  />
                ) : (
                  <h2 className="text-xl font-bold text-slate-900">{report.title}</h2>
                )}
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
                {editMode ? (
                  <textarea
                    value={report.summary}
                    onChange={(e) => updateReportField('summary', e.target.value)}
                    rows={4}
                    className="w-full bg-white border border-cyan-200 rounded-lg px-3 py-2 text-slate-700 leading-relaxed focus:ring-2 focus:ring-cyan-500 focus:border-transparent resize-y"
                  />
                ) : (
                  <p className="text-slate-700 leading-relaxed">{report.summary}</p>
                )}
              </div>

              {/* 섹션별 내용 */}
              {report.sections.map((section, idx) => (
                <div key={idx} className="mb-6 last:mb-0">
                  {editMode ? (
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-200">
                      <span className="w-2 h-4 bg-slate-800 flex-shrink-0"></span>
                      <input
                        type="text"
                        value={section.title}
                        onChange={(e) => updateSecTitle(idx, e.target.value)}
                        placeholder="섹션 제목"
                        className="flex-1 text-lg font-bold text-slate-900 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                      />
                      <button type="button" onClick={() => moveSec(idx, -1)} disabled={idx === 0} title="위로"
                        className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md disabled:opacity-30 disabled:cursor-not-allowed">
                        <ChevronUp size={16} />
                      </button>
                      <button type="button" onClick={() => moveSec(idx, 1)} disabled={idx === report.sections.length - 1} title="아래로"
                        className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md disabled:opacity-30 disabled:cursor-not-allowed">
                        <ChevronDown size={16} />
                      </button>
                      <button type="button" onClick={() => removeSec(idx)} title="섹션 삭제"
                        className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-slate-100 rounded-md">
                        <X size={16} />
                      </button>
                    </div>
                  ) : (
                    <h3 className="flex items-center gap-2 text-lg font-bold text-slate-900 mb-3 pb-2 border-b border-slate-200">
                      <span className="w-2 h-4 bg-slate-800"></span>
                      {section.title}
                    </h3>
                  )}

                  <div className="space-y-2 pl-4">
                    {section.content.map((para, pIdx) =>
                      editMode ? (
                        <div key={pIdx} className="flex items-start gap-2">
                          <textarea
                            value={para}
                            onChange={(e) => updateItem(idx, pIdx, e.target.value)}
                            rows={2}
                            placeholder="항목 내용 (개조식 번호 가./1) 사용 가능)"
                            className="flex-1 text-sm text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:ring-2 focus:ring-cyan-500 focus:border-transparent resize-y"
                          />
                          <div className="flex flex-col gap-1 flex-shrink-0">
                            <button type="button" onClick={() => moveItem(idx, pIdx, -1)} disabled={pIdx === 0} title="위로"
                              className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded disabled:opacity-30 disabled:cursor-not-allowed">
                              <ChevronUp size={15} />
                            </button>
                            <button type="button" onClick={() => moveItem(idx, pIdx, 1)} disabled={pIdx === section.content.length - 1} title="아래로"
                              className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded disabled:opacity-30 disabled:cursor-not-allowed">
                              <ChevronDown size={15} />
                            </button>
                            <button type="button" onClick={() => removeItem(idx, pIdx)} title="삭제"
                              className="p-1 text-slate-400 hover:text-red-600 hover:bg-slate-100 rounded">
                              <X size={15} />
                            </button>
                          </div>
                        </div>
                      ) : (
                        (() => {
                          const { marker, body, sub } = parseItem(para);
                          return (
                            <p
                              key={pIdx}
                              className={`text-slate-700 leading-relaxed flex ${sub ? 'pl-5' : ''}`}
                            >
                              <span className={`mr-2 flex-shrink-0 ${marker ? 'text-slate-500 font-medium' : 'text-cyan-600'}`}>
                                {marker || '❍'}
                              </span>
                              <span>{body}</span>
                            </p>
                          );
                        })()
                      )
                    )}

                    {editMode && (
                      <button
                        type="button"
                        onClick={() => addItem(idx)}
                        className="w-full flex items-center justify-center gap-1 py-1.5 border border-dashed border-slate-300 rounded-lg text-xs text-slate-500 hover:text-cyan-600 hover:border-cyan-400 transition-all"
                      >
                        <Plus size={14} />
                        항목 추가
                      </button>
                    )}
                  </div>
                </div>
              ))}

              {editMode && (
                <button
                  type="button"
                  onClick={addSec}
                  className="w-full flex items-center justify-center gap-1 py-2 border border-dashed border-slate-300 rounded-lg text-sm text-slate-500 hover:text-cyan-600 hover:border-cyan-400 transition-all"
                >
                  <Plus size={16} />
                  섹션 추가
                </button>
              )}
            </div>

            {/* 결과 오류 메시지 */}
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm text-center">
                {error}
              </div>
            )}

            {/* 액션 버튼 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
                onClick={handleDownloadHwpx}
                disabled={hwpxLoading}
                className="flex items-center justify-center gap-2 py-3 bg-cyan-600 text-white rounded-xl hover:bg-cyan-700 transition-all font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {hwpxLoading ? <RefreshCw size={18} className="animate-spin" /> : <FileText size={18} />}
                {hwpxLoading ? '생성 중...' : 'HWPX 다운로드'}
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
              💡 '내용 편집'으로 직접 수정한 결과가 복사·TXT·HWPX에 모두 반영됩니다. HWPX는 한글(HWP)에서 열어 확인하세요.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}