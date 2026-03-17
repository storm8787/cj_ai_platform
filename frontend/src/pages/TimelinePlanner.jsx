import { useState, useCallback, useRef } from "react";
import {
  Sparkles,
  Plus,
  Trash2,
  Download,
  FileImage,
  FileSpreadsheet,
  Presentation,
  GripVertical,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertCircle,
  CheckCircle,
  Edit3,
  RotateCcw,
  Info,
} from "lucide-react";
import api from "../services/api";

// ──────────────────────────────────────────────
// 카테고리 색상 맵
// ──────────────────────────────────────────────
const CATEGORY_STYLES = {
  준비: {
    bg: "bg-purple-50",
    bar: "bg-purple-400",
    border: "border-purple-300",
    text: "text-purple-700",
    badge: "bg-purple-100 text-purple-700",
  },
  시행: {
    bg: "bg-emerald-50",
    bar: "bg-emerald-500",
    border: "border-emerald-300",
    text: "text-emerald-700",
    badge: "bg-emerald-100 text-emerald-700",
  },
  마무리: {
    bg: "bg-orange-50",
    bar: "bg-orange-400",
    border: "border-orange-300",
    text: "text-orange-700",
    badge: "bg-orange-100 text-orange-700",
  },
};

const DEFAULT_STYLE = {
  bg: "bg-blue-50",
  bar: "bg-blue-400",
  border: "border-blue-300",
  text: "text-blue-700",
  badge: "bg-blue-100 text-blue-700",
};

const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1);

// ──────────────────────────────────────────────
// 유틸리티
// ──────────────────────────────────────────────
const getMonthRange = (tasks, baseYear) => {
  if (!tasks.length) {
    return MONTHS.map((m) => ({ year: baseYear, month: m }));
  }
  let minY = Infinity, minM = 13, maxY = -Infinity, maxM = 0;
  tasks.forEach((t) => {
    if (t.start_year < minY || (t.start_year === minY && t.start_month < minM)) {
      minY = t.start_year; minM = t.start_month;
    }
    if (t.end_year > maxY || (t.end_year === maxY && t.end_month > maxM)) {
      maxY = t.end_year; maxM = t.end_month;
    }
  });
  const result = [];
  let y = minY, m = minM;
  while (y < maxY || (y === maxY && m <= maxM)) {
    result.push({ year: y, month: m });
    m++;
    if (m > 12) { m = 1; y++; }
  }
  return result;
};

const downloadBase64 = (base64, filename, mime) => {
  const byteChars = atob(base64);
  const byteNums = new Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) byteNums[i] = byteChars.charCodeAt(i);
  const blob = new Blob([new Uint8Array(byteNums)], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};


// ──────────────────────────────────────────────
// 메인 컴포넌트
// ──────────────────────────────────────────────
export default function TimelinePlanner() {
  const currentYear = new Date().getFullYear();

  // 상태
  const [title, setTitle] = useState("");
  const [tasks, setTasks] = useState([]);
  const [baseYear, setBaseYear] = useState(currentYear);
  const [aiSummary, setAiSummary] = useState("");

  // AI 추천 입력
  const [projectName, setProjectName] = useState("");
  const [projectDesc, setProjectDesc] = useState("");
  const [budget, setBudget] = useState("");
  const [deadline, setDeadline] = useState("");
  const [projectType, setProjectType] = useState("");
  const [projectTypes, setProjectTypes] = useState([]);

  // UI 상태
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [activeTab, setActiveTab] = useState("ai"); // "ai" | "manual"
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [editingIdx, setEditingIdx] = useState(null);

  const exportRef = useRef(null);

  // 사업유형 로드
  useState(() => {
    api.get("/api/timeline/project-types")
      .then((res) => setProjectTypes(res.data.types || []))
      .catch(() => {});
  }, []);

  // ─── AI 자동 추천 ───
  const handleAiSuggest = useCallback(async () => {
    if (!projectName.trim()) {
      setError("사업명을 입력해 주세요.");
      return;
    }
    setLoading(true);
    setError("");
    setSuccess("");
    setAiSummary("");

    try {
      const res = await api.post("/api/timeline/suggest", {
        project_name: projectName.trim(),
        project_description: projectDesc.trim() || null,
        budget: budget.trim() || null,
        deadline: deadline.trim() || null,
        project_type: projectType || null,
      });

      if (res.data.success) {
        const suggested = res.data.tasks.map((t, i) => ({
          id: Date.now() + i,
          ...t,
        }));
        setTasks(suggested);
        setTitle(projectName.trim());
        setBaseYear(suggested[0]?.start_year || currentYear);
        setAiSummary(res.data.summary || "");
        setSuccess("AI가 일정을 추천했습니다. 수정 후 내보내기 하세요.");
      }
    } catch (err) {
      setError(err.response?.data?.detail || "AI 일정 추천에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }, [projectName, projectDesc, budget, deadline, projectType, currentYear]);

  // ─── 수동 일정 추가 ───
  const addTask = useCallback(() => {
    setTasks((prev) => [
      ...prev,
      {
        id: Date.now(),
        name: "",
        start_month: new Date().getMonth() + 1,
        end_month: Math.min(new Date().getMonth() + 2, 12),
        start_year: baseYear,
        end_year: baseYear,
        category: "시행",
        is_milestone: false,
      },
    ]);
    setEditingIdx(tasks.length);
  }, [baseYear, tasks.length]);

  const updateTask = useCallback((idx, field, value) => {
    setTasks((prev) => {
      const updated = [...prev];
      updated[idx] = { ...updated[idx], [field]: value };
      // 시작 > 종료 자동 보정
      const t = updated[idx];
      if (field === "start_month" || field === "start_year") {
        if (t.start_year > t.end_year || (t.start_year === t.end_year && t.start_month > t.end_month)) {
          updated[idx].end_month = t.start_month;
          updated[idx].end_year = t.start_year;
        }
      }
      return updated;
    });
  }, []);

  const removeTask = useCallback((idx) => {
    setTasks((prev) => prev.filter((_, i) => i !== idx));
    if (editingIdx === idx) setEditingIdx(null);
  }, [editingIdx]);

  const moveTask = useCallback((idx, dir) => {
    setTasks((prev) => {
      const arr = [...prev];
      const newIdx = idx + dir;
      if (newIdx < 0 || newIdx >= arr.length) return arr;
      [arr[idx], arr[newIdx]] = [arr[newIdx], arr[idx]];
      return arr;
    });
  }, []);

  // ─── 내보내기 ───
  const handleExport = useCallback(async (format) => {
    if (!tasks.length) {
      setError("내보낼 일정이 없습니다.");
      return;
    }
    if (!title.trim()) {
      setError("사업명을 입력해 주세요.");
      return;
    }

    setExporting(true);
    setExportFormat(format);
    setShowExportMenu(false);
    setError("");

    try {
      const payload = {
        timeline: {
          title: title.trim(),
          tasks: tasks.map(({ id, ...rest }) => rest),
          base_year: baseYear,
        },
        format,
      };

      const res = await api.post("/api/timeline/export", payload);

      if (res.data.success) {
        downloadBase64(res.data.data, res.data.filename, res.data.mime_type);
        setSuccess(`${format.toUpperCase()} 파일이 다운로드되었습니다.`);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "내보내기에 실패했습니다.");
    } finally {
      setExporting(false);
      setExportFormat(null);
    }
  }, [tasks, title, baseYear]);

  // ─── 초기화 ───
  const handleReset = () => {
    setTasks([]);
    setTitle("");
    setAiSummary("");
    setError("");
    setSuccess("");
    setProjectName("");
    setProjectDesc("");
    setBudget("");
    setDeadline("");
    setProjectType("");
  };

  // ─── 간트 차트 미리보기 데이터 ───
  const monthRange = getMonthRange(tasks, baseYear);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <div className="p-2.5 rounded-xl bg-gradient-to-br from-orange-100 to-amber-50">
          <CalendarRange className="w-6 h-6 text-orange-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">사업 타임라인 생성기</h1>
          <p className="text-sm text-gray-500">AI가 추천하는 사업 일정, 간트차트로 시각화</p>
        </div>
      </div>

      {/* 알림 */}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 text-red-700 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 text-green-700 text-sm">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* 탭 전환 */}
      <div className="flex gap-1 p-1 bg-gray-100 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab("ai")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
            activeTab === "ai" ? "bg-white shadow text-gray-900" : "text-gray-500 hover:text-gray-700"
          }`}
        >
          <Sparkles className="w-4 h-4 inline mr-1.5" />
          AI 자동 추천
        </button>
        <button
          onClick={() => setActiveTab("manual")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
            activeTab === "manual" ? "bg-white shadow text-gray-900" : "text-gray-500 hover:text-gray-700"
          }`}
        >
          <Edit3 className="w-4 h-4 inline mr-1.5" />
          수동 입력
        </button>
      </div>

      {/* AI 추천 탭 */}
      {activeTab === "ai" && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">사업명 *</label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="예: 충주시 스마트시티 통합플랫폼 구축"
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-200 focus:border-orange-400 outline-none"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">사업 설명 (선택)</label>
              <textarea
                value={projectDesc}
                onChange={(e) => setProjectDesc(e.target.value)}
                placeholder="사업의 주요 내용, 범위, 목적 등"
                rows={2}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-200 focus:border-orange-400 outline-none resize-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">사업 유형 (선택)</label>
              <select
                value={projectType}
                onChange={(e) => setProjectType(e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-200 focus:border-orange-400 outline-none bg-white"
              >
                <option value="">유형 선택...</option>
                {projectTypes.map((pt) => (
                  <option key={pt.value} value={pt.value}>
                    {pt.icon} {pt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">예산 규모 (선택)</label>
              <input
                type="text"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                placeholder="예: 5억원"
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-200 focus:border-orange-400 outline-none"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">완료 목표 (선택)</label>
              <input
                type="text"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                placeholder="예: 2026년 12월, 연내 완료, 상반기 등"
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-200 focus:border-orange-400 outline-none"
              />
            </div>
          </div>

          <button
            onClick={handleAiSuggest}
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-orange-500 to-amber-500 text-white font-medium rounded-lg hover:from-orange-600 hover:to-amber-600 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                AI가 일정을 분석하고 있습니다...
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                AI 일정 추천받기
              </>
            )}
          </button>

          {aiSummary && (
            <div className="flex gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200 text-sm text-amber-800">
              <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{aiSummary}</span>
            </div>
          )}
        </div>
      )}

      {/* 수동 입력 탭 */}
      {activeTab === "manual" && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">사업명</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="사업명을 입력하세요"
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-200 focus:border-orange-400 outline-none"
            />
          </div>
          <button
            onClick={addTask}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-orange-600 bg-orange-50 rounded-lg hover:bg-orange-100 transition-colors"
          >
            <Plus className="w-4 h-4" />
            일정 추가
          </button>
        </div>
      )}

      {/* 일정 편집 목록 */}
      {tasks.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">
              일정 목록 ({tasks.length}개)
            </h2>
            <div className="flex gap-2">
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                초기화
              </button>
              <button
                onClick={addTask}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-orange-600 hover:bg-orange-50 rounded-md transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                추가
              </button>
            </div>
          </div>

          <div className="divide-y divide-gray-100">
            {tasks.map((task, idx) => {
              const style = CATEGORY_STYLES[task.category] || DEFAULT_STYLE;
              const isEditing = editingIdx === idx;

              return (
                <div
                  key={task.id}
                  className={`px-6 py-3 flex items-center gap-3 ${
                    isEditing ? "bg-orange-50/50" : "hover:bg-gray-50"
                  } transition-colors`}
                >
                  {/* 순서 이동 */}
                  <div className="flex flex-col gap-0.5">
                    <button
                      onClick={() => moveTask(idx, -1)}
                      disabled={idx === 0}
                      className="p-0.5 text-gray-300 hover:text-gray-500 disabled:opacity-30"
                    >
                      <ChevronUp className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => moveTask(idx, 1)}
                      disabled={idx === tasks.length - 1}
                      className="p-0.5 text-gray-300 hover:text-gray-500 disabled:opacity-30"
                    >
                      <ChevronDown className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* 카테고리 뱃지 */}
                  <select
                    value={task.category || "시행"}
                    onChange={(e) => updateTask(idx, "category", e.target.value)}
                    className={`text-xs font-medium px-2 py-1 rounded-md border-0 ${style.badge} cursor-pointer`}
                  >
                    <option value="준비">준비</option>
                    <option value="시행">시행</option>
                    <option value="마무리">마무리</option>
                  </select>

                  {/* 단계명 */}
                  <input
                    type="text"
                    value={task.name}
                    onChange={(e) => updateTask(idx, "name", e.target.value)}
                    onClick={() => setEditingIdx(idx)}
                    placeholder="단계명 입력"
                    className="flex-1 px-2 py-1.5 text-sm border border-transparent hover:border-gray-200 focus:border-orange-300 rounded-md outline-none transition-colors bg-transparent"
                  />

                  {/* 기간 */}
                  <div className="flex items-center gap-1 text-sm text-gray-500">
                    <select
                      value={task.start_year}
                      onChange={(e) => updateTask(idx, "start_year", Number(e.target.value))}
                      className="w-20 px-1 py-1 border border-gray-200 rounded text-xs bg-white"
                    >
                      {[currentYear - 1, currentYear, currentYear + 1, currentYear + 2].map((y) => (
                        <option key={y} value={y}>{y}년</option>
                      ))}
                    </select>
                    <select
                      value={task.start_month}
                      onChange={(e) => updateTask(idx, "start_month", Number(e.target.value))}
                      className="w-16 px-1 py-1 border border-gray-200 rounded text-xs bg-white"
                    >
                      {MONTHS.map((m) => (
                        <option key={m} value={m}>{m}월</option>
                      ))}
                    </select>
                    <span className="text-gray-300">~</span>
                    <select
                      value={task.end_year}
                      onChange={(e) => updateTask(idx, "end_year", Number(e.target.value))}
                      className="w-20 px-1 py-1 border border-gray-200 rounded text-xs bg-white"
                    >
                      {[currentYear - 1, currentYear, currentYear + 1, currentYear + 2].map((y) => (
                        <option key={y} value={y}>{y}년</option>
                      ))}
                    </select>
                    <select
                      value={task.end_month}
                      onChange={(e) => updateTask(idx, "end_month", Number(e.target.value))}
                      className="w-16 px-1 py-1 border border-gray-200 rounded text-xs bg-white"
                    >
                      {MONTHS.map((m) => (
                        <option key={m} value={m}>{m}월</option>
                      ))}
                    </select>
                  </div>

                  {/* 삭제 */}
                  <button
                    onClick={() => removeTask(idx)}
                    className="p-1.5 text-gray-300 hover:text-red-500 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 간트 차트 미리보기 */}
      {tasks.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">미리보기</h2>

            {/* 내보내기 버튼 */}
            <div className="relative" ref={exportRef}>
              <button
                onClick={() => setShowExportMenu(!showExportMenu)}
                disabled={exporting}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-gray-800 rounded-lg hover:bg-gray-900 transition-colors disabled:opacity-50"
              >
                {exporting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {exportFormat?.toUpperCase()} 생성 중...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" />
                    내보내기
                    <ChevronDown className="w-3.5 h-3.5" />
                  </>
                )}
              </button>

              {showExportMenu && !exporting && (
                <div className="absolute right-0 top-full mt-1 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-10 overflow-hidden">
                  <button
                    onClick={() => handleExport("png")}
                    className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <FileImage className="w-4 h-4 text-orange-500" />
                    <div className="text-left">
                      <div className="font-medium">PNG 이미지</div>
                      <div className="text-xs text-gray-400">보고서 삽입용</div>
                    </div>
                  </button>
                  <button
                    onClick={() => handleExport("xlsx")}
                    className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <FileSpreadsheet className="w-4 h-4 text-emerald-500" />
                    <div className="text-left">
                      <div className="font-medium">Excel 스프레드시트</div>
                      <div className="text-xs text-gray-400">수정·편집 가능</div>
                    </div>
                  </button>
                  <button
                    onClick={() => handleExport("pptx")}
                    className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <Presentation className="w-4 h-4 text-red-500" />
                    <div className="text-left">
                      <div className="font-medium">PowerPoint 슬라이드</div>
                      <div className="text-xs text-gray-400">발표자료용</div>
                    </div>
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* 간트 차트 */}
          <div className="overflow-x-auto">
            <div className="min-w-[800px] p-6">
              {/* 사업명 */}
              <h3 className="text-lg font-bold text-gray-800 mb-4">{title || "사업명 미입력"}</h3>

              {/* 월 헤더 */}
              <div className="flex">
                <div className="w-56 flex-shrink-0" />
                <div className="flex-1 flex">
                  {monthRange.map(({ year, month }, i) => (
                    <div
                      key={`${year}-${month}`}
                      className="flex-1 text-center text-xs text-gray-500 py-2 border-b border-gray-200"
                      style={{ minWidth: 60 }}
                    >
                      {(month === 1 || i === 0) && (
                        <div className="text-[10px] text-gray-400">{year}</div>
                      )}
                      {month}월
                    </div>
                  ))}
                </div>
              </div>

              {/* 행 */}
              {tasks.map((task, idx) => {
                const style = CATEGORY_STYLES[task.category] || DEFAULT_STYLE;

                // 바 위치 계산
                const startIdx = monthRange.findIndex(
                  (m) => m.year === task.start_year && m.month === task.start_month
                );
                const endIdx = monthRange.findIndex(
                  (m) => m.year === task.end_year && m.month === task.end_month
                );
                const totalCols = monthRange.length;

                const leftPct = startIdx >= 0 ? (startIdx / totalCols) * 100 : 0;
                const widthPct =
                  startIdx >= 0 && endIdx >= 0
                    ? ((endIdx - startIdx + 1) / totalCols) * 100
                    : 0;

                return (
                  <div
                    key={task.id}
                    className={`flex items-center border-b border-gray-100 ${
                      idx % 2 === 0 ? "bg-gray-50/50" : ""
                    }`}
                    style={{ minHeight: 44 }}
                  >
                    {/* 레이블 */}
                    <div className="w-56 flex-shrink-0 px-3 py-2 flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${style.bar}`} />
                      <span className="text-sm text-gray-700 truncate">{task.name || "미입력"}</span>
                    </div>

                    {/* 바 */}
                    <div className="flex-1 relative" style={{ minHeight: 32 }}>
                      {/* 세로 그리드 */}
                      {monthRange.map((_, i) => (
                        <div
                          key={i}
                          className="absolute top-0 bottom-0 border-l border-gray-100"
                          style={{ left: `${(i / totalCols) * 100}%` }}
                        />
                      ))}

                      {widthPct > 0 && (
                        <div
                          className={`absolute top-1 bottom-1 ${style.bar} rounded-md opacity-80`}
                          style={{
                            left: `${leftPct}%`,
                            width: `${widthPct}%`,
                            minWidth: 20,
                          }}
                        >
                          {widthPct > 8 && (
                            <span className="absolute inset-0 flex items-center justify-center text-white text-[10px] font-medium">
                              {endIdx - startIdx + 1}개월
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* 범례 */}
              <div className="flex gap-5 mt-4 pt-3 border-t border-gray-100">
                {Object.entries(CATEGORY_STYLES).map(([cat, style]) => (
                  <div key={cat} className="flex items-center gap-1.5 text-xs text-gray-500">
                    <div className={`w-3 h-3 rounded-sm ${style.bar}`} />
                    {cat}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 빈 상태 */}
      {tasks.length === 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <CalendarRange className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 mb-1">아직 일정이 없습니다</p>
          <p className="text-sm text-gray-400">
            {activeTab === "ai"
              ? "사업 정보를 입력하고 AI 추천을 받아보세요"
              : "일정 추가 버튼을 눌러 직접 입력하세요"}
          </p>
        </div>
      )}
    </div>
  );
}