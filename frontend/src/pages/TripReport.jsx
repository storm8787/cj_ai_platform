import { useMemo, useRef, useState } from "react";
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

const API_BASE = import.meta.env.VITE_API_URL || "";

function coerceMainContent(v) {
  // backend에서 이미 고쳤지만, 프론트에서도 한 번 더 방어
  if (!v) return [];
  if (Array.isArray(v)) {
    // 글자단위 배열이면 join 후 줄/구분자로 재분리
    const isCharArray = v.length > 0 && v.every((x) => typeof x === "string" && x.length <= 1);
    if (isCharArray) {
      const joined = v.join("").trim();
      return splitToLines(joined);
    }
    return v.map((x) => String(x).trim()).filter(Boolean);
  }
  if (typeof v === "string") return splitToLines(v);
  return [String(v).trim()].filter(Boolean);
}

function splitToLines(s) {
  const text = (s || "").trim();
  if (!text) return [];
  // 줄바꿈/블릿/중점 등으로 분리
  let parts = text.split(/\r?\n+/).map((x) => x.trim()).filter(Boolean);
  if (parts.length <= 1) {
    parts = text
      .split(/•|\u2022|·| - |\s-\s/)
      .map((x) => x.trim())
      .filter(Boolean);
  }
  // 너무 짧은 토큰만 잔뜩이면 문장 단위로 재시도
  const shortRatio = parts.length ? parts.filter((x) => x.length <= 1).length / parts.length : 0;
  if (shortRatio > 0.6) {
    parts = text.split(/[。\.]|;|,/).map((x) => x.trim()).filter(Boolean);
  }
  return parts.slice(0, 50);
}

export default function TripReport() {
  const fileInputRef = useRef(null);

  const [images, setImages] = useState([]); // File[]
  const [previews, setPreviews] = useState([]); // objectURL[]
  const [dragActive, setDragActive] = useState(false);

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

  const [step, setStep] = useState(1);
  const [selectedReportType, setSelectedReportType] = useState("");

  const [originalImages, setOriginalImages] = useState([]); // 분석 후 재분석용

  const reportTypes = useMemo(
    () => [
      { id: "행사참석", name: "행사참석", icon: "🎤" },
      { id: "출장방문", name: "출장방문", icon: "🏢" },
      { id: "시설점검", name: "시설점검", icon: "🏗️" },
      { id: "민원현장", name: "민원현장", icon: "🚨" },
      { id: "환경점검", name: "환경점검", icon: "🌳" },
    ],
    []
  );

  const clearAll = () => {
    previews.forEach((u) => URL.revokeObjectURL(u));
    setImages([]);
    setPreviews([]);
    setAnalysisResult(null);
    setEditedInfo({});
    setEditedContent([]);
    setAdditionalNotes("");
    setGeneratedReport("");
    setError("");
    setSelectedReportType("");
    setOriginalImages([]);
    setStep(1);
  };

  const addFiles = (files) => {
    const list = Array.from(files || []).filter((f) => f.type?.startsWith("image/"));
    if (list.length === 0) return;

    const currentCount = images.length;
    const remain = Math.max(0, 10 - currentCount);
    const toAdd = list.slice(0, remain);

    const nextImages = [...images, ...toAdd];
    const nextPreviews = [...previews, ...toAdd.map((f) => URL.createObjectURL(f))];

    setImages(nextImages);
    setPreviews(nextPreviews);
  };

  const handleImageUpload = (e) => {
    setError("");
    addFiles(e.target.files);
    // 같은 파일 재선택 가능하게
    e.target.value = "";
  };

  // ===== Drag & Drop (핵심) =====
  const onDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const onDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const onDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    setError("");

    const dt = e.dataTransfer;
    if (!dt?.files || dt.files.length === 0) return;
    addFiles(dt.files);
  };

  const removeImage = (index) => {
    const nextImages = images.filter((_, i) => i !== index);
    const nextPreviews = previews.filter((_, i) => i !== index);

    // revoke removed preview
    const removed = previews[index];
    if (removed) URL.revokeObjectURL(removed);

    setImages(nextImages);
    setPreviews(nextPreviews);
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

      const analysis = payload.analysis || {};
      setAnalysisResult(analysis);
      setSelectedReportType(analysis.report_type || "행사참석");
      setEditedInfo(analysis.extracted_info || {});
      setEditedContent(coerceMainContent(analysis.main_content));
      setOriginalImages([...images]);
      setStep(2);
    } catch (err) {
      setError(err?.message || "분석 오류");
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

      const analysis = payload.analysis || {};
      setAnalysisResult(analysis);
      setSelectedReportType(newType);
      setEditedInfo(analysis.extracted_info || {});
      setEditedContent(coerceMainContent(analysis.main_content));
    } catch (err) {
      setError(err?.message || "재분석 오류");
    } finally {
      setReanalyzing(false);
    }
  };

  // ========== 보고서 생성 ==========
  const handleGenerate = async () => {
    if (!analysisResult) {
      setError("분석 결과가 없습니다.");
      return;
    }

    setGenerating(true);
    setError("");

    try {
      const payload = {
        report_type: selectedReportType || analysisResult.report_type || "행사참석",
        extracted_info: editedInfo || {},
        main_content: coerceMainContent(editedContent),
        photos_analysis: analysisResult.photos_analysis || [],
        reporter_name: reporterName,
        reporter_dept: reporterDept,
        additional_notes: additionalNotes,
      };

      const response = await fetch(`${API_BASE}/api/trip-report/generate-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "보고서 생성 실패");

      setGeneratedReport(data.report_text || "");
      setStep(3);
    } catch (err) {
      setError(err?.message || "생성 오류");
    } finally {
      setGenerating(false);
    }
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(generatedReport || "");
    } catch {
      setError("클립보드 복사 실패");
    }
  };

  const downloadText = () => {
    const blob = new Blob([generatedReport || ""], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `출장보고서_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const addContentItem = () => setEditedContent((prev) => [...coerceMainContent(prev), ""]);
  const removeContentItem = (idx) =>
    setEditedContent((prev) => coerceMainContent(prev).filter((_, i) => i !== idx));

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">출장보고 생성기</h1>
            <p className="text-slate-400 mt-1">사진 기반 유형 추론 → 정보 추출 → 공문서 문체 보고서 생성</p>
          </div>
          <button onClick={clearAll} className="btn-secondary flex items-center gap-2">
            <RefreshCw className="w-4 h-4" /> 초기화
          </button>
        </div>

        {error && (
          <div className="mb-4 p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-300 mt-0.5" />
            <div className="text-red-200 text-sm whitespace-pre-wrap">{error}</div>
          </div>
        )}

        {/* Step Indicator */}
        <div className="mb-6 flex items-center gap-3 text-sm">
          <div className={`flex items-center gap-2 ${step >= 1 ? "text-cyan-300" : "text-slate-500"}`}>
            <CheckCircle className="w-4 h-4" /> 1) 업로드
          </div>
          <div className="text-slate-600">→</div>
          <div className={`flex items-center gap-2 ${step >= 2 ? "text-cyan-300" : "text-slate-500"}`}>
            <CheckCircle className="w-4 h-4" /> 2) 추출/편집
          </div>
          <div className="text-slate-600">→</div>
          <div className={`flex items-center gap-2 ${step >= 3 ? "text-cyan-300" : "text-slate-500"}`}>
            <CheckCircle className="w-4 h-4" /> 3) 보고서
          </div>
        </div>

        {step === 1 && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: uploader */}
            <div className="lg:col-span-2">
              <div
                className={`border-2 border-dashed rounded-xl p-8 cursor-pointer transition-all
                  ${dragActive ? "border-cyan-400 bg-cyan-500/10" : "border-slate-700 hover:border-slate-500"}
                `}
                onClick={() => fileInputRef.current?.click()}
                onDragEnter={onDragEnter}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
                role="button"
                tabIndex={0}
              >
                <div className="flex flex-col items-center text-center">
                  <div className="w-14 h-14 rounded-full bg-slate-800 flex items-center justify-center mb-4">
                    <Upload className="w-7 h-7 text-cyan-300" />
                  </div>
                  <p className="text-slate-200 mb-2">클릭하여 사진 선택</p>
                  <p className="text-slate-400 text-sm">또는 파일을 여기에 드래그하여 업로드</p>
                  <p className="text-slate-500 text-sm mt-2">최대 10장, 이미지 파일만</p>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={handleImageUpload}
                  className="hidden"
                />
              </div>

              {previews.length > 0 && (
                <div className="mt-4">
                  <p className="text-slate-400 text-sm mb-2">업로드된 사진 ({previews.length}/10)</p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {previews.map((preview, index) => (
                      <div key={preview} className="relative rounded-lg overflow-hidden border border-slate-800">
                        <img src={preview} alt={`preview-${index}`} className="w-full h-32 object-cover" />
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            removeImage(index);
                          }}
                          className="absolute top-2 right-2 bg-black/60 hover:bg-black/80 p-1 rounded"
                        >
                          <X className="w-4 h-4 text-white" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Right: meta + analyze */}
            <div className="card text-gray-900">
              <h2 className="text-lg font-bold flex items-center gap-2 mb-4">
                <FileImage className="w-5 h-5" /> 보고자 정보
              </h2>

              <div className="space-y-3">
                <div>
                  <label className="text-sm text-gray-700 font-semibold">부서</label>
                  <input
                    className="input-field w-full mt-1"
                    value={reporterDept}
                    onChange={(e) => setReporterDept(e.target.value)}
                    placeholder="예: 정보통신과"
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-700 font-semibold">성명</label>
                  <input
                    className="input-field w-full mt-1"
                    value={reporterName}
                    onChange={(e) => setReporterName(e.target.value)}
                    placeholder="예: 이호진"
                  />
                </div>

                <button
                  className="btn-primary w-full flex items-center justify-center gap-2"
                  onClick={handleAnalyze}
                  disabled={analyzing}
                >
                  {analyzing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" /> 분석 중...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" /> AI 분석 시작
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {step === 2 && analysisResult && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Extracted info */}
            <div className="card text-gray-900">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold flex items-center gap-2">
                  <Edit3 className="w-5 h-5" /> 추출된 정보 (수정 가능)
                </h2>
                <div className="flex items-center gap-2">
                  <select
                    className="input-field"
                    value={selectedReportType}
                    onChange={(e) => {
                      const t = e.target.value;
                      setSelectedReportType(t);
                      handleReanalyze(t);
                    }}
                    disabled={reanalyzing}
                  >
                    {reportTypes.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.icon} {t.name}
                      </option>
                    ))}
                  </select>
                  {reanalyzing && <Loader2 className="w-4 h-4 animate-spin text-cyan-600" />}
                </div>
              </div>

              <div className="space-y-3">
                {Object.entries(editedInfo || {}).map(([k, v]) => (
                  <div key={k}>
                    <label className="text-sm text-gray-700 font-semibold">{k}</label>
                    <input
                      className="input-field w-full mt-1"
                      value={v || ""}
                      onChange={(e) => setEditedInfo((prev) => ({ ...prev, [k]: e.target.value }))}
                      placeholder="(미입력)"
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Main content */}
            <div className="card text-gray-900">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold flex items-center gap-2">
                  <Edit3 className="w-5 h-5" /> 주요 내용 (수정 가능)
                </h2>
                <button className="btn-secondary flex items-center gap-2" onClick={addContentItem}>
                  + 항목 추가
                </button>
              </div>

              <div className="space-y-2">
                {coerceMainContent(editedContent).map((item, idx) => (
                  <div key={idx} className="flex gap-2">
                    <input
                      className="input-field flex-1"
                      value={item}
                      onChange={(e) =>
                        setEditedContent((prev) => {
                          const arr = coerceMainContent(prev);
                          arr[idx] = e.target.value;
                          return arr;
                        })
                      }
                      placeholder="예: 절차 1: ..."
                    />
                    <button className="px-3 py-2 rounded-lg bg-red-500/10 hover:bg-red-500/20" onClick={() => removeContentItem(idx)}>
                      <X className="w-4 h-4 text-red-600" />
                    </button>
                  </div>
                ))}
                {coerceMainContent(editedContent).length === 0 && (
                  <div className="text-sm text-gray-500">추출된 주요 내용이 없으면 “항목 추가”로 직접 입력 가능함</div>
                )}
              </div>

              <div className="mt-5">
                <label className="text-sm text-gray-700 font-semibold">추가 요청사항(선택)</label>
                <textarea
                  className="input-field w-full mt-1 h-24"
                  value={additionalNotes}
                  onChange={(e) => setAdditionalNotes(e.target.value)}
                  placeholder="예: 보고서에 예산/담당/일정을 명확히 반영, 시사점은 정책적 관점으로 강화 등"
                />
              </div>

              <button
                className="btn-primary w-full mt-4 flex items-center justify-center gap-2"
                onClick={handleGenerate}
                disabled={generating}
              >
                {generating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> 보고서 생성 중...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4" /> 보고서 생성
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="card text-gray-900">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold">생성된 보고서</h2>
              <div className="flex items-center gap-2">
                <button className="btn-secondary flex items-center gap-2" onClick={copyToClipboard}>
                  <Copy className="w-4 h-4" /> 복사
                </button>
                <button className="btn-secondary flex items-center gap-2" onClick={downloadText}>
                  <Download className="w-4 h-4" /> 다운로드
                </button>
              </div>
            </div>

            <pre className="whitespace-pre-wrap text-sm leading-6 bg-white border border-gray-200 rounded-lg p-4 text-gray-900">
              {generatedReport || "(결과 없음)"}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}