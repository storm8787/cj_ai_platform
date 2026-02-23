import { useEffect, useMemo, useRef, useState } from "react";
import {
  Upload,
  X,
  FileImage,
  Loader2,
  CheckCircle,
  AlertCircle,
  Download,
  Copy,
  Edit3,
  RefreshCw,
} from "lucide-react";

// API 기본 URL
const API_BASE = import.meta.env.VITE_API_URL || "";

// 보고서 유형 기본값 (서버에서 로드 실패 시 사용)
const FALLBACK_TYPES = [
  { id: "회의참석",   name: "회의 참석",       icon: "🤝", fields: ["회의명", "일시", "장소", "주최기관", "참석자"] },
  { id: "벤치마킹",   name: "벤치마킹",        icon: "🏢", fields: ["방문목적", "일시", "방문기관", "담당자"] },
  { id: "교육연수",   name: "교육·연수",       icon: "📚", fields: ["교육명", "일시", "장소", "주관기관", "교육내용"] },
  { id: "설명회참석", name: "설명회·행사 참석", icon: "🎤", fields: ["행사명", "일시", "장소", "주최", "참석인원"] },
  { id: "조사연구",   name: "조사·연구",       icon: "🔍", fields: ["조사목적", "일시", "조사지역", "조사항목"] },
  { id: "시설점검",   name: "시설점검",        icon: "🏗️", fields: ["점검위치", "점검대상", "발견사항", "위험도"] },
  { id: "민원현장",   name: "민원현장",        icon: "🚨", fields: ["민원위치", "민원유형", "현장상황", "조치결과"] },
  { id: "환경점검",   name: "환경점검",        icon: "🌳", fields: ["점검위치", "점검항목", "측정결과", "적합여부"] },
];

export default function TripReport() {
  // ========== 상태 관리 ==========
  const [images, setImages] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [isDragging, setIsDragging] = useState(false);

  const [analyzing, setAnalyzing] = useState(false);
  const [reanalyzing, setReanalyzing] = useState(false);
  const [generating, setGenerating] = useState(false);

  const [analysisResult, setAnalysisResult] = useState(null);

  const [editedInfo, setEditedInfo] = useState({});
  const [editedContent, setEditedContent] = useState([]);

  const [reporterName, setReporterName] = useState("");
  const [reporterDept, setReporterDept] = useState("");
  const [additionalNotes, setAdditionalNotes] = useState("");
  const [generatedReport, setGeneratedReport] = useState("");

  const [error, setError] = useState("");
  const [step, setStep] = useState(1); // 1: 업로드, 2: 분석결과, 3: 보고서
  const [selectedReportType, setSelectedReportType] = useState("");

  const [originalImages, setOriginalImages] = useState([]);
  const [reportTypes, setReportTypes] = useState(FALLBACK_TYPES);

  const fileInputRef = useRef(null);

  // ========== 서버에서 보고서 유형 로드 ==========
  useEffect(() => {
    let ignore = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/trip-report/report-types`);
        if (!res.ok) return;
        const data = await res.json();
        if (!ignore && data?.types?.length) setReportTypes(data.types);
      } catch {
        // fallback 유지
      }
    })();
    return () => { ignore = true; };
  }, []);

  const reportTypeMap = useMemo(() => {
    const m = new Map();
    for (const t of reportTypes) m.set(t.id, t);
    return m;
  }, [reportTypes]);

  // ========== 파일 업로드 ==========
  const readFileAsDataURL = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

  const addFiles = async (fileList) => {
    const incoming = Array.from(fileList || []).filter((f) => f.type?.startsWith("image/"));
    if (incoming.length === 0) {
      setError("이미지 파일만 업로드 가능합니다.");
      return;
    }
    if (incoming.length + images.length > 10) {
      setError("이미지는 최대 10장까지 업로드 가능합니다.");
      return;
    }

    try {
      const nextPreviews = await Promise.all(incoming.map(readFileAsDataURL));
      setImages((prev) => [...prev, ...incoming]);
      setPreviews((prev) => [...prev, ...nextPreviews]);
      setError("");
    } catch {
      setError("미리보기 생성 중 오류가 발생했습니다.");
    }
  };

  const handleImageUpload = async (e) => {
    await addFiles(e.target.files);
    e.target.value = "";
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    await addFiles(e.dataTransfer.files);
  };

  const removeImage = (index) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
    setPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  // ========== AI 분석 ==========
  const handleAnalyze = async () => {
    if (images.length === 0) {
      setError("이미지를 업로드해주세요.");
      return;
    }

    setAnalyzing(true);
    setError("");

    try {
      const formData = new FormData();
      images.forEach((image) => formData.append("images", image));
      formData.append("reporter_name", reporterName);
      formData.append("reporter_dept", reporterDept);

      const response = await fetch(`${API_BASE}/api/trip-report/analyze-images`, {
        method: "POST",
        body: formData,
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "분석에 실패했습니다.");

      const analysis = payload.analysis;
      setAnalysisResult(analysis);
      setSelectedReportType(analysis.report_type || "회의참석");
      setEditedInfo(analysis.extracted_info || {});
      setEditedContent(analysis.main_content || []);
      setOriginalImages([...images]);
      setStep(2);
    } catch (err) {
      setError(err.message || "분석 오류");
    } finally {
      setAnalyzing(false);
    }
  };

  // ========== 유형 변경 시 재분석 ==========
  const handleReanalyze = async (newType) => {
    if (originalImages.length === 0) {
      setError("원본 이미지가 없습니다. 처음부터 다시 시작해주세요.");
      return;
    }

    setReanalyzing(true);
    setError("");

    try {
      const formData = new FormData();
      originalImages.forEach((image) => formData.append("images", image));
      formData.append("reporter_name", reporterName);
      formData.append("reporter_dept", reporterDept);
      formData.append("force_report_type", newType);

      const response = await fetch(`${API_BASE}/api/trip-report/analyze-images`, {
        method: "POST",
        body: formData,
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "재분석에 실패했습니다.");

      const analysis = payload.analysis;
      setAnalysisResult(analysis);
      setSelectedReportType(newType);
      setEditedInfo(analysis.extracted_info || {});
      setEditedContent(analysis.main_content || []);
    } catch (err) {
      setError(err.message || "재분석 오류");
    } finally {
      setReanalyzing(false);
    }
  };

  const handleReportTypeChange = (newType) => {
    if (newType === selectedReportType) return;

    const confirmReanalyze = window.confirm(
      `보고서 유형을 "${newType}"(으)로 변경하시겠습니까?\n\n` +
      `⚠️ 해당 유형에 맞게 사진을 재분석합니다.\n` +
      `⚠️ 현재 수정한 내용은 초기화됩니다.\n` +
      `💰 Vision API 비용이 추가로 발생합니다.`
    );

    if (confirmReanalyze) handleReanalyze(newType);
  };

  // ========== 보고서 생성 ==========
  const handleGenerateReport = async () => {
    setGenerating(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/api/trip-report/generate-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          report_type: selectedReportType,
          extracted_info: editedInfo,
          main_content: editedContent.filter((c) => c.trim()),
          photos_analysis: analysisResult?.photos_analysis || [],
          reporter_name: reporterName,
          reporter_dept: reporterDept,
          additional_notes: additionalNotes,
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "보고서 생성에 실패했습니다.");

      setGeneratedReport(payload.report_text || "");
      setStep(3);
    } catch (err) {
      setError(err.message || "보고서 생성 오류");
    } finally {
      setGenerating(false);
    }
  };

  // ========== 편집 핸들러 ==========
  const handleInfoChange = (key, value) => {
    setEditedInfo((prev) => ({ ...prev, [key]: value }));
  };

  const handleContentChange = (index, value) => {
    setEditedContent((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  };

  const addContent = () => setEditedContent((prev) => [...prev, ""]);
  const removeContent = (index) => setEditedContent((prev) => prev.filter((_, i) => i !== index));

  // ========== 복사/다운로드 ==========
  const copyToClipboard = () => {
    navigator.clipboard.writeText(generatedReport);
    alert("클립보드에 복사되었습니다.");
  };

  const downloadReport = () => {
    const blob = new Blob([generatedReport], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    const timestamp = new Date().toISOString().slice(0, 10);
    link.download = `출장보고_${timestamp}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // ========== 리셋 ==========
  const resetAll = () => {
    setImages([]);
    setPreviews([]);
    setAnalysisResult(null);
    setEditedInfo({});
    setEditedContent([]);
    setGeneratedReport("");
    setAdditionalNotes("");
    setSelectedReportType("");
    setOriginalImages([]);
    setError("");
    setStep(1);
  };

  // ========== 유형별 필드 ==========
  const selectedType = reportTypeMap.get(selectedReportType);
  const typeFields = selectedType?.fields || [];
  const extraKeys = Object.keys(editedInfo || {}).filter((k) => !typeFields.includes(k));

  // ========== 렌더링 ==========
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 헤더 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">📄 출장보고 생성기</h1>
        <p className="text-slate-400">
          사진만 업로드하면 AI가 자동으로 분석하여 공문서 형식의 보고서를 생성합니다.
        </p>
      </div>

      {/* 진행 단계 */}
      <div className="flex items-center justify-center mb-8">
        {[
          { num: 1, label: "사진 업로드" },
          { num: 2, label: "AI 분석" },
          { num: 3, label: "보고서 완성" },
        ].map((s, i) => (
          <div key={s.num} className="flex items-center">
            {i > 0 && <div className={`w-16 h-1 mx-4 ${step >= s.num ? "bg-cyan-500" : "bg-slate-700"}`} />}
            <div className="flex items-center">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                step >= s.num ? "bg-cyan-500 text-white" : "bg-slate-700 text-slate-400"
              }`}>{s.num}</div>
              <span className={`ml-2 ${step >= s.num ? "text-white" : "text-slate-400"}`}>{s.label}</span>
            </div>
          </div>
        ))}
      </div>

      {/* 에러 메시지 */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2 text-red-400">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* ========== Step 1: 사진 업로드 ========== */}
      {step === 1 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 업로드 영역 */}
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <FileImage size={20} />
              현장 사진 업로드
            </h2>

            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={handleDragOver}
              onDragEnter={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                isDragging
                  ? "border-cyan-500 bg-slate-700/60"
                  : "border-slate-600 hover:border-cyan-500 hover:bg-slate-700/50"
              }`}
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

            {previews.length > 0 && (
              <div className="mt-4">
                <p className="text-slate-400 text-sm mb-2">업로드된 사진 ({previews.length}/10)</p>
                <div className="grid grid-cols-4 gap-2">
                  {previews.map((preview, index) => (
                    <div key={index} className="relative group">
                      <img src={preview} alt={`미리보기 ${index + 1}`} className="w-full h-20 object-cover rounded-lg" />
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

          {/* 보고자 정보 */}
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
                  placeholder="예: 홍길동"
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <button
              onClick={handleAnalyze}
              disabled={images.length === 0 || analyzing}
              className={`w-full mt-6 py-4 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all ${
                images.length === 0 || analyzing
                  ? "bg-slate-700 text-slate-500 cursor-not-allowed"
                  : "bg-cyan-500 hover:bg-cyan-600 text-white"
              }`}
            >
              {analyzing ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  AI가 사진을 분석 중입니다...
                </>
              ) : (
                <>🤖 AI 분석 시작</>
              )}
            </button>

            {analyzing && (
              <div className="mt-4 p-4 bg-cyan-500/10 border border-cyan-500/20 rounded-lg">
                <p className="text-cyan-400 text-sm">✨ GPT Vision이 사진을 분석하고 있습니다...</p>
                <p className="text-slate-400 text-sm mt-1">• 1단계: 보고서 유형 분류</p>
                <p className="text-slate-400 text-sm">• 2단계: 상세 정보 추출</p>
                <p className="text-slate-400 text-sm">• 텍스트/현수막/표 인식</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========== Step 2: AI 분석 결과 ========== */}
      {step === 2 && analysisResult && (
        <div className="space-y-6">
          {/* 분석 완료 */}
          <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <CheckCircle size={24} className="text-green-400" />
              <div>
                <p className="text-green-400 font-semibold">AI 분석 완료!</p>
                <p className="text-slate-400 text-sm">신뢰도: {Math.round((analysisResult.confidence || 0) * 100)}%</p>
              </div>
            </div>

            <div className="flex items-center gap-3 mt-3 pt-3 border-t border-green-500/20">
              <span className="text-slate-300 text-sm">보고서 유형:</span>
              <select
                value={selectedReportType}
                onChange={(e) => handleReportTypeChange(e.target.value)}
                disabled={reanalyzing}
                className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-cyan-500 disabled:opacity-50"
              >
                {reportTypes.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.icon} {t.name}
                  </option>
                ))}
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

          {/* 재분석 중 */}
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
            {/* 추출된 정보 */}
            <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Edit3 size={20} />
                추출된 정보 (수정 가능)
              </h2>

              <div className="space-y-4">
                {typeFields.map((key) => (
                  <div key={key}>
                    <label className="block text-slate-400 text-sm mb-1">{key}</label>
                    <input
                      type="text"
                      value={editedInfo?.[key] ?? ""}
                      onChange={(e) => handleInfoChange(key, e.target.value)}
                      className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                ))}

                {extraKeys.length > 0 && (
                  <div className="pt-3 mt-2 border-t border-slate-700">
                    <p className="text-slate-500 text-xs mb-2">추가 인식 항목</p>
                    {extraKeys.map((key) => (
                      <div key={key} className="mb-3">
                        <label className="block text-slate-400 text-sm mb-1">{key}</label>
                        <input
                          type="text"
                          value={editedInfo?.[key] ?? ""}
                          onChange={(e) => handleInfoChange(key, e.target.value)}
                          className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* 주요 내용 */}
            <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
              <h2 className="text-lg font-semibold text-white mb-4">📝 주요 내용 (수정 가능)</h2>

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

          {/* 사진별 분석 */}
          {analysisResult.photos_analysis?.length > 0 && (
            <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
              <h2 className="text-lg font-semibold text-white mb-4">📸 사진별 분석 결과</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {analysisResult.photos_analysis.map((photo, idx) => {
                  const pIndex = (photo?.photo_index ? Number(photo.photo_index) : idx + 1) - 1;
                  return (
                    <div key={idx} className="bg-slate-700/50 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        {previews[pIndex] && (
                          <img src={previews[pIndex]} alt="" className="w-12 h-12 object-cover rounded" />
                        )}
                        <span className="text-white font-medium">사진 {photo.photo_index ?? idx + 1}</span>
                      </div>
                      <p className="text-slate-300 text-sm mb-2">{photo.description}</p>
                      {photo.detected_text && (
                        <p className="text-cyan-400 text-sm">📝 "{photo.detected_text}"</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 버튼 */}
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
                  ? "bg-slate-700 text-slate-500 cursor-not-allowed"
                  : "bg-cyan-500 hover:bg-cyan-600 text-white"
              }`}
            >
              {generating ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  보고서 생성 중...
                </>
              ) : (
                <>📄 보고서 생성</>
              )}
            </button>
          </div>
        </div>
      )}

      {/* ========== Step 3: 생성된 보고서 ========== */}
      {step === 3 && generatedReport && (
        <div className="space-y-6">
          <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4 flex items-center gap-3">
            <CheckCircle size={24} className="text-green-400" />
            <div>
              <p className="text-green-400 font-semibold">보고서 생성 완료!</p>
              <p className="text-slate-400 text-sm">공문서 문체(단어형 종결)로 작성되었습니다. 필요시 수정해주세요.</p>
            </div>
          </div>

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

      <div className="mt-8 bg-cyan-500/10 border border-cyan-500/20 rounded-xl p-4">
        <h3 className="font-semibold text-cyan-300 mb-2">💡 사용 팁</h3>
        <ul className="text-sm text-slate-300 space-y-1">
          <li>• 현수막/간판/PPT/표가 잘 보이는 사진을 올리면 추출 정확도가 올라갑니다</li>
          <li>• 유형 변경 시 해당 유형에 맞게 재분석되어 서식이 자동 변경됩니다</li>
          <li>• 보고서는 공문서 문체(단어형 종결: ~논의 예정, ~검토 완료)로 자동 생성됩니다</li>
          <li>• 생성된 보고서는 직접 수정 후 복사/다운로드할 수 있습니다</li>
        </ul>
      </div>
    </div>
  );
}