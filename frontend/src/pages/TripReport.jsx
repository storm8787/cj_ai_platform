import { useState, useRef } from 'react';
import { Upload, X, FileImage, Loader2, CheckCircle, AlertCircle, Download, Copy, Edit3, RefreshCw } from 'lucide-react';

// API 기본 URL
const API_BASE = import.meta.env.VITE_API_URL || '';

export default function TripReport() {
  // 상태 관리
  const [images, setImages] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [editedInfo, setEditedInfo] = useState({});
  const [editedContent, setEditedContent] = useState([]);
  const [reporterName, setReporterName] = useState('');
  const [reporterDept, setReporterDept] = useState('');
  const [additionalNotes, setAdditionalNotes] = useState('');
  const [generatedReport, setGeneratedReport] = useState('');
  const [error, setError] = useState('');
  const [step, setStep] = useState(1); // 1: 업로드, 2: 분석결과, 3: 보고서
  const [selectedReportType, setSelectedReportType] = useState(''); // 보고서 유형 (변경 가능)
  const [reanalyzing, setReanalyzing] = useState(false); // 재분석 중
  const [originalImages, setOriginalImages] = useState([]); // 원본 이미지 저장 (재분석용)
  
  const fileInputRef = useRef(null);

  // 이미지 업로드 처리
  const handleImageUpload = (e) => {
    const files = Array.from(e.target.files);
    if (files.length + images.length > 10) {
      setError('이미지는 최대 10장까지 업로드 가능합니다.');
      return;
    }

    const newImages = [...images, ...files];
    setImages(newImages);

    // 미리보기 생성
    files.forEach(file => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviews(prev => [...prev, reader.result]);
      };
      reader.readAsDataURL(file);
    });

    setError('');
  };

  // 이미지 제거
  const removeImage = (index) => {
    setImages(prev => prev.filter((_, i) => i !== index));
    setPreviews(prev => prev.filter((_, i) => i !== index));
  };

  // AI 분석 시작
  const handleAnalyze = async () => {
    if (images.length === 0) {
      setError('이미지를 업로드해주세요.');
      return;
    }

    setAnalyzing(true);
    setError('');

    try {
      const formData = new FormData();
      images.forEach(image => {
        formData.append('images', image);
      });
      formData.append('reporter_name', reporterName);
      formData.append('reporter_dept', reporterDept);

      const response = await fetch(`${API_BASE}/api/trip-report/analyze-images`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '분석에 실패했습니다.');
      }

      const data = await response.json();
      setAnalysisResult(data.analysis);
      setEditedInfo(data.analysis.extracted_info || {});
      setEditedContent(data.analysis.main_content || []);
      setSelectedReportType(data.analysis.report_type || '행사참석'); // AI 추천 유형 설정
      setOriginalImages([...images]); // 원본 이미지 저장 (재분석용)
      setStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  // 보고서 생성
  const handleGenerateReport = async () => {
    setGenerating(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE}/api/trip-report/generate-report`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          report_type: selectedReportType, // 사용자가 변경한 유형 사용
          extracted_info: editedInfo,
          main_content: editedContent.filter(c => c.trim()),
          reporter_name: reporterName,
          reporter_dept: reporterDept,
          additional_notes: additionalNotes,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '보고서 생성에 실패했습니다.');
      }

      const data = await response.json();
      setGeneratedReport(data.report_text);
      setStep(3);
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  // 정보 수정 핸들러
  const handleInfoChange = (key, value) => {
    setEditedInfo(prev => ({ ...prev, [key]: value }));
  };

  // 주요 내용 수정 핸들러
  const handleContentChange = (index, value) => {
    setEditedContent(prev => {
      const newContent = [...prev];
      newContent[index] = value;
      return newContent;
    });
  };

  // 주요 내용 추가
  const addContent = () => {
    setEditedContent(prev => [...prev, '']);
  };

  // 주요 내용 삭제
  const removeContent = (index) => {
    setEditedContent(prev => prev.filter((_, i) => i !== index));
  };

  // 유형 변경 시 재분석
  const handleReanalyze = async (newType) => {
    if (originalImages.length === 0) {
      setError('원본 이미지가 없습니다. 처음부터 다시 시작해주세요.');
      return;
    }

    setReanalyzing(true);
    setError('');

    try {
      const formData = new FormData();
      originalImages.forEach(image => {
        formData.append('images', image);
      });
      formData.append('reporter_name', reporterName);
      formData.append('reporter_dept', reporterDept);
      formData.append('force_report_type', newType); // 강제 유형 지정

      const response = await fetch(`${API_BASE}/api/trip-report/analyze-images`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '재분석에 실패했습니다.');
      }

      const data = await response.json();
      setAnalysisResult(data.analysis);
      setEditedInfo(data.analysis.extracted_info || {});
      setEditedContent(data.analysis.main_content || []);
      setSelectedReportType(newType);
    } catch (err) {
      setError(err.message);
    } finally {
      setReanalyzing(false);
    }
  };

  // 유형 변경 핸들러 (재분석 여부 확인)
  const handleReportTypeChange = (newType) => {
    if (newType === selectedReportType) return;
    
    const confirmReanalyze = window.confirm(
      `보고서 유형을 "${newType}"(으)로 변경하면 해당 유형에 맞게 사진을 재분석합니다.\n\n` +
      `⚠️ 현재 수정한 내용은 초기화됩니다.\n` +
      `💰 Vision API 비용이 추가로 발생합니다.\n\n` +
      `계속하시겠습니까?`
    );
    
    if (confirmReanalyze) {
      handleReanalyze(newType);
    }
  };

  // 복사
  const copyToClipboard = () => {
    navigator.clipboard.writeText(generatedReport);
    alert('클립보드에 복사되었습니다.');
  };

  // 다운로드
  const downloadReport = () => {
    const blob = new Blob([generatedReport], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const timestamp = new Date().toISOString().slice(0, 10);
    link.download = `출장보고_${timestamp}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // 처음으로
  const resetAll = () => {
    setImages([]);
    setPreviews([]);
    setAnalysisResult(null);
    setEditedInfo({});
    setEditedContent([]);
    setGeneratedReport('');
    setAdditionalNotes('');
    setSelectedReportType('');
    setOriginalImages([]);
    setError('');
    setStep(1);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 헤더 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">📄 출장보고 생성기</h1>
        <p className="text-slate-400">
          사진만 업로드하면 AI가 자동으로 분석하여 보고서를 생성합니다.
        </p>
      </div>

      {/* 진행 단계 표시 */}
      <div className="flex items-center justify-center mb-8">
        <div className="flex items-center">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
            step >= 1 ? 'bg-cyan-500 text-white' : 'bg-slate-700 text-slate-400'
          }`}>1</div>
          <span className={`ml-2 ${step >= 1 ? 'text-white' : 'text-slate-400'}`}>사진 업로드</span>
        </div>
        <div className={`w-16 h-1 mx-4 ${step >= 2 ? 'bg-cyan-500' : 'bg-slate-700'}`}></div>
        <div className="flex items-center">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
            step >= 2 ? 'bg-cyan-500 text-white' : 'bg-slate-700 text-slate-400'
          }`}>2</div>
          <span className={`ml-2 ${step >= 2 ? 'text-white' : 'text-slate-400'}`}>AI 분석</span>
        </div>
        <div className={`w-16 h-1 mx-4 ${step >= 3 ? 'bg-cyan-500' : 'bg-slate-700'}`}></div>
        <div className="flex items-center">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
            step >= 3 ? 'bg-cyan-500 text-white' : 'bg-slate-700 text-slate-400'
          }`}>3</div>
          <span className={`ml-2 ${step >= 3 ? 'text-white' : 'text-slate-400'}`}>보고서 완성</span>
        </div>
      </div>

      {/* 에러 메시지 */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2 text-red-400">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* Step 1: 사진 업로드 */}
      {step === 1 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 좌측: 업로드 영역 */}
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <FileImage size={20} />
              현장 사진 업로드
            </h2>

            {/* 드래그앤드롭 영역 */}
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-600 rounded-xl p-8 text-center cursor-pointer hover:border-cyan-500 hover:bg-slate-700/50 transition-all"
            >
              <Upload size={48} className="mx-auto text-slate-400 mb-4" />
              <p className="text-slate-300 mb-2">클릭하여 사진 선택</p>
              <p className="text-slate-500 text-sm">또는 파일을 여기에 드래그</p>
              <p className="text-slate-500 text-sm mt-2">최대 10장, JPG/PNG 지원</p>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*"
              onChange={handleImageUpload}
              className="hidden"
            />

            {/* 업로드된 사진 미리보기 */}
            {previews.length > 0 && (
              <div className="mt-4">
                <p className="text-slate-400 text-sm mb-2">업로드된 사진 ({previews.length}/10)</p>
                <div className="grid grid-cols-4 gap-2">
                  {previews.map((preview, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={preview}
                        alt={`미리보기 ${index + 1}`}
                        className="w-full h-20 object-cover rounded-lg"
                      />
                      <button
                        onClick={() => removeImage(index)}
                        className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <X size={14} className="text-white" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 우측: 보고자 정보 */}
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <h2 className="text-lg font-semibold text-white mb-4">👤 보고자 정보</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-slate-400 text-sm mb-1">부서</label>
                <input
                  type="text"
                  value={reporterDept}
                  onChange={(e) => setReporterDept(e.target.value)}
                  placeholder="예: 정보통신과"
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="block text-slate-400 text-sm mb-1">이름</label>
                <input
                  type="text"
                  value={reporterName}
                  onChange={(e) => setReporterName(e.target.value)}
                  placeholder="예: 김태균"
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            {/* AI 분석 시작 버튼 */}
            <button
              onClick={handleAnalyze}
              disabled={images.length === 0 || analyzing}
              className={`w-full mt-6 py-4 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all ${
                images.length === 0 || analyzing
                  ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                  : 'bg-cyan-500 hover:bg-cyan-600 text-white'
              }`}
            >
              {analyzing ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  AI가 사진을 분석 중입니다...
                </>
              ) : (
                <>
                  🤖 AI 분석 시작
                </>
              )}
            </button>

            {analyzing && (
              <div className="mt-4 p-4 bg-cyan-500/10 border border-cyan-500/20 rounded-lg">
                <p className="text-cyan-400 text-sm">
                  ✨ GPT-4 Vision이 사진을 분석하고 있습니다...
                </p>
                <p className="text-slate-400 text-sm mt-1">
                  • 보고서 유형 자동 판단 중
                </p>
                <p className="text-slate-400 text-sm">
                  • 텍스트/간판/현수막 인식 중
                </p>
                <p className="text-slate-400 text-sm">
                  • 현장 상황 파악 중
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Step 2: AI 분석 결과 */}
      {step === 2 && analysisResult && (
        <div className="space-y-6">
          {/* 분석 결과 요약 + 유형 변경 */}
          <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <CheckCircle size={24} className="text-green-400" />
              <div>
                <p className="text-green-400 font-semibold">AI 분석 완료!</p>
                <p className="text-slate-400 text-sm">
                  신뢰도: {Math.round(analysisResult.confidence * 100)}%
                </p>
              </div>
            </div>
            
            {/* 보고서 유형 선택 (변경 가능) */}
            <div className="flex items-center gap-3 mt-3 pt-3 border-t border-green-500/20">
              <span className="text-slate-300 text-sm">보고서 유형:</span>
              <select
                value={selectedReportType}
                onChange={(e) => handleReportTypeChange(e.target.value)}
                disabled={reanalyzing}
                className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-cyan-500 disabled:opacity-50"
              >
                <option value="행사참석">🎤 행사참석</option>
                <option value="출장방문">🏢 출장방문</option>
                <option value="시설점검">🏗️ 시설점검</option>
                <option value="민원현장">🚨 민원현장</option>
                <option value="환경점검">🌳 환경점검</option>
              </select>
              {reanalyzing ? (
                <span className="text-cyan-400 text-xs flex items-center gap-1">
                  <Loader2 size={14} className="animate-spin" />
                  재분석 중...
                </span>
              ) : (
                <span className="text-slate-500 text-xs">(AI 추천: {analysisResult.report_type})</span>
              )}
            </div>
          </div>

          {/* 재분석 중 오버레이 */}
          {reanalyzing && (
            <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-xl p-4 flex items-center gap-3">
              <Loader2 size={24} className="text-cyan-400 animate-spin" />
              <div>
                <p className="text-cyan-400 font-semibold">"{selectedReportType}" 유형으로 재분석 중...</p>
                <p className="text-slate-400 text-sm">해당 유형에 맞는 정보를 다시 추출하고 있습니다.</p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 좌측: 추출된 정보 (수정 가능) */}
            <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Edit3 size={20} />
                추출된 정보 (수정 가능)
              </h2>

              <div className="space-y-4">
                {Object.entries(editedInfo).map(([key, value]) => (
                  <div key={key}>
                    <label className="block text-slate-400 text-sm mb-1">{key}</label>
                    <input
                      type="text"
                      value={value}
                      onChange={(e) => handleInfoChange(key, e.target.value)}
                      className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* 우측: 주요 내용 */}
            <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                📝 주요 내용 (수정 가능)
              </h2>

              <div className="space-y-2">
                {editedContent.map((content, index) => (
                  <div key={index} className="flex gap-2">
                    <input
                      type="text"
                      value={content}
                      onChange={(e) => handleContentChange(index, e.target.value)}
                      className="flex-1 px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-cyan-500"
                    />
                    <button
                      onClick={() => removeContent(index)}
                      className="px-3 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30"
                    >
                      <X size={18} />
                    </button>
                  </div>
                ))}
                <button
                  onClick={addContent}
                  className="w-full py-2 border border-dashed border-slate-600 rounded-lg text-slate-400 hover:border-cyan-500 hover:text-cyan-400"
                >
                  + 항목 추가
                </button>
              </div>

              {/* 추가 요청사항 */}
              <div className="mt-6">
                <label className="block text-slate-400 text-sm mb-1">추가 요청사항 (선택)</label>
                <textarea
                  value={additionalNotes}
                  onChange={(e) => setAdditionalNotes(e.target.value)}
                  placeholder="보고서에 추가할 내용이나 요청사항"
                  rows={3}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
          </div>

          {/* 사진별 분석 결과 */}
          {analysisResult.photos_analysis && analysisResult.photos_analysis.length > 0 && (
            <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
              <h2 className="text-lg font-semibold text-white mb-4">📸 사진별 분석 결과</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {analysisResult.photos_analysis.map((photo, index) => (
                  <div key={index} className="bg-slate-700/50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      {previews[index] && (
                        <img src={previews[index]} alt="" className="w-12 h-12 object-cover rounded" />
                      )}
                      <span className="text-white font-medium">사진 {photo.photo_index}</span>
                    </div>
                    <p className="text-slate-300 text-sm mb-2">{photo.description}</p>
                    {photo.detected_text && (
                      <p className="text-cyan-400 text-sm">📝 "{photo.detected_text}"</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 버튼 영역 */}
          <div className="flex gap-4">
            <button
              onClick={() => setStep(1)}
              className="px-6 py-3 bg-slate-700 text-white rounded-xl hover:bg-slate-600"
            >
              ← 이전 단계
            </button>
            <button
              onClick={handleGenerateReport}
              disabled={generating}
              className={`flex-1 py-3 rounded-xl font-semibold flex items-center justify-center gap-2 ${
                generating
                  ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                  : 'bg-cyan-500 hover:bg-cyan-600 text-white'
              }`}
            >
              {generating ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  보고서 생성 중...
                </>
              ) : (
                <>
                  📄 보고서 생성
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: 생성된 보고서 */}
      {step === 3 && generatedReport && (
        <div className="space-y-6">
          {/* 완료 메시지 */}
          <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4 flex items-center gap-3">
            <CheckCircle size={24} className="text-green-400" />
            <div>
              <p className="text-green-400 font-semibold">보고서 생성 완료!</p>
              <p className="text-slate-400 text-sm">아래 내용을 확인하고 필요시 수정해주세요.</p>
            </div>
          </div>

          {/* 보고서 내용 */}
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-white">📄 생성된 보고서</h2>
              <div className="flex gap-2">
                <button
                  onClick={copyToClipboard}
                  className="px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 flex items-center gap-2"
                >
                  <Copy size={16} />
                  복사
                </button>
                <button
                  onClick={downloadReport}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
                >
                  <Download size={16} />
                  다운로드
                </button>
              </div>
            </div>

            <textarea
              value={generatedReport}
              onChange={(e) => setGeneratedReport(e.target.value)}
              rows={20}
              className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white font-mono text-sm focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* 버튼 영역 */}
          <div className="flex gap-4">
            <button
              onClick={() => setStep(2)}
              className="px-6 py-3 bg-slate-700 text-white rounded-xl hover:bg-slate-600"
            >
              ← 수정하기
            </button>
            <button
              onClick={resetAll}
              className="flex-1 py-3 bg-cyan-500 hover:bg-cyan-600 text-white rounded-xl font-semibold flex items-center justify-center gap-2"
            >
              <RefreshCw size={20} />
              새 보고서 작성
            </button>
          </div>
        </div>
      )}

      {/* 사용 팁 */}
      <div className="mt-8 bg-cyan-500/10 border border-cyan-500/20 rounded-xl p-4">
        <h3 className="font-semibold text-cyan-300 mb-2">💡 사용 팁</h3>
        <ul className="text-sm text-slate-300 space-y-1">
          <li>• 현수막, 간판, 발표자료가 잘 보이는 사진을 업로드하면 더 정확한 분석이 가능합니다</li>
          <li>• AI가 추출한 정보는 직접 수정할 수 있습니다</li>
          <li>• 행사, 출장, 시설점검, 민원현장, 환경점검 등 다양한 유형을 자동으로 판단합니다</li>
          <li>• 사진의 GPS 정보가 있으면 위치가 자동으로 추출됩니다</li>
        </ul>
      </div>
    </div>
  );
}