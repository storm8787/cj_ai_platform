import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { disasterApi } from "../services/api";
import { useDisasterSession } from "../hooks/useDisasterSession";

// ── 간단한 Markdown 렌더러 (외부 라이브러리 미사용) ──────────────
// h1/h2/h3, 표(|col|col|), 리스트(-/•), 굵게(**), 일반 텍스트 지원
function MdRenderer({ content }) {
  if (!content) return null;

  const lines = content.split("\n");
  const elements = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // 제목
    if (line.startsWith("# ")) {
      elements.push(
        <h1 key={i} className="text-2xl font-bold text-white mt-6 mb-3 pb-2 border-b border-slate-700">
          {line.slice(2)}
        </h1>
      );
      i++;
      continue;
    }
    if (line.startsWith("## ")) {
      elements.push(
        <h2 key={i} className="text-lg font-semibold text-slate-200 mt-5 mb-2">
          {line.slice(3)}
        </h2>
      );
      i++;
      continue;
    }
    if (line.startsWith("### ")) {
      elements.push(
        <h3 key={i} className="text-base font-semibold text-slate-300 mt-4 mb-1">
          {line.slice(4)}
        </h3>
      );
      i++;
      continue;
    }

    // 구분선
    if (/^-{3,}$/.test(line.trim())) {
      elements.push(<hr key={i} className="border-slate-700 my-4" />);
      i++;
      continue;
    }

    // 표: |로 시작하는 연속 행 묶기
    if (line.startsWith("|")) {
      const tableLines = [];
      while (i < lines.length && lines[i].startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }
      // 구분선(|---|) 제거
      const dataLines = tableLines.filter((l) => !/^\|[-:\s|]+\|$/.test(l));
      if (dataLines.length > 0) {
        const parseRow = (l) =>
          l.split("|").slice(1, -1).map((c) => c.trim());
        const [header, ...body] = dataLines;
        elements.push(
          <div key={`tbl-${i}`} className="overflow-x-auto my-3">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-slate-800">
                  {parseRow(header).map((cell, ci) => (
                    <th
                      key={ci}
                      className="px-3 py-2 text-left text-slate-300 font-semibold border border-slate-700"
                    >
                      {cell}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {body.map((row, ri) => (
                  <tr
                    key={ri}
                    className={ri % 2 === 0 ? "bg-slate-900" : "bg-slate-950"}
                  >
                    {parseRow(row).map((cell, ci) => (
                      <td
                        key={ci}
                        className="px-3 py-1.5 text-slate-300 border border-slate-800"
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      continue;
    }

    // 리스트 항목
    if (/^[-•◦]\s/.test(line)) {
      const listLines = [];
      while (i < lines.length && /^[-•◦]\s/.test(lines[i])) {
        listLines.push(lines[i].replace(/^[-•◦]\s/, ""));
        i++;
      }
      elements.push(
        <ul key={`ul-${i}`} className="list-disc list-inside space-y-0.5 my-2 text-slate-300 text-sm">
          {listLines.map((item, li) => (
            <li key={li}>{renderInline(item)}</li>
          ))}
        </ul>
      );
      continue;
    }

    // 빈 줄
    if (line.trim() === "") {
      elements.push(<div key={i} className="h-2" />);
      i++;
      continue;
    }

    // 일반 텍스트
    elements.push(
      <p key={i} className="text-sm text-slate-300 leading-relaxed my-0.5">
        {renderInline(line)}
      </p>
    );
    i++;
  }

  return <div className="space-y-0.5">{elements}</div>;
}

/** 굵게(**text**) 인라인 처리 */
function renderInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i} className="text-white font-semibold">{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

// ── 메인 페이지 ──────────────────────────────────────────
export default function DisasterDailyReport() {
  const navigate = useNavigate();
  const { uploadId: activeUploadId, fileName: activeFileName } =
    useDisasterSession();

  const [reportDate, setReportDate] = useState(
    new Date().toISOString().slice(0, 10)
  );
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState("render"); // "render" | "raw"

  const handleGenerate = async () => {
    if (!activeUploadId || !reportDate) return;
    setLoading(true);
    try {
      const res = await disasterApi.generateDailyReport({
        upload_id: activeUploadId,
        report_date: reportDate,
        created_by: "admin",
      });
      setReport(res.data.report);
      setViewMode("render");
    } catch (err) {
      console.error(err);
      alert(err?.response?.data?.detail || "보고서 생성 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!report?.report_text) return;
    try {
      await navigator.clipboard.writeText(report.report_text);
      alert("복사되었습니다.");
    } catch {
      alert("복사에 실패했습니다.");
    }
  };

  const handleDownload = () => {
    if (!report?.report_text) return;
    const blob = new Blob([report.report_text], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `재난일일보고_${reportDate}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!activeUploadId) {
    return (
      <div className="min-h-screen bg-slate-950 text-white p-6">
        <div className="max-w-4xl mx-auto bg-slate-900 border border-slate-700 rounded-2xl p-6">
          <h1 className="text-2xl font-bold mb-3">일일보고서 생성</h1>
          <p className="text-slate-400 mb-4">
            현재 세션에 선택된 파일이 없습니다. 먼저 txt 파일을 업로드하고
            분석해주세요.
          </p>
          <button
            onClick={() => navigate("/disaster-upload")}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg"
          >
            업로드 페이지로 이동
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* 헤더 */}
        <div>
          <h1 className="text-2xl font-bold">일일보고서 생성</h1>
          <p className="text-slate-400 mt-1 text-sm">
            파일명: {activeFileName || "현재 세션 파일"}
          </p>
        </div>

        {/* 생성 컨트롤 */}
        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-5 space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-2">보고일자</label>
            <input
              type="date"
              value={reportDate}
              onChange={(e) => setReportDate(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg disabled:opacity-50"
            >
              {loading ? "생성 중..." : "보고서 생성"}
            </button>
            {report && (
              <>
                <button
                  onClick={handleDownload}
                  className="px-4 py-2 bg-cyan-700 hover:bg-cyan-600 rounded-lg text-sm"
                >
                  .md 다운로드
                </button>
                <button
                  onClick={handleCopy}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm"
                >
                  복사
                </button>
              </>
            )}
            <button
              onClick={() => navigate("/disaster-upload")}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm border border-slate-700"
            >
              다른 파일 업로드
            </button>
          </div>
        </div>

        {/* 보고서 출력 */}
        {report && (
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 space-y-4">
            {/* 요약 */}
            {report.summary_text && (
              <div className="bg-slate-800/60 rounded-xl px-4 py-3 border border-slate-700 text-slate-300 text-sm">
                {report.summary_text}
              </div>
            )}

            {/* 렌더/RAW 탭 */}
            <div className="flex gap-1 border-b border-slate-800 pb-0">
              <button
                onClick={() => setViewMode("render")}
                className={`px-3 py-1.5 text-sm rounded-t-lg transition-colors ${
                  viewMode === "render"
                    ? "bg-slate-800 text-white"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                미리보기
              </button>
              <button
                onClick={() => setViewMode("raw")}
                className={`px-3 py-1.5 text-sm rounded-t-lg transition-colors ${
                  viewMode === "raw"
                    ? "bg-slate-800 text-white"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                Markdown 원문
              </button>
            </div>

            {viewMode === "render" ? (
              <div className="bg-slate-950 rounded-xl p-5 border border-slate-800 min-h-[200px]">
                <MdRenderer content={report.report_text} />
              </div>
            ) : (
              <pre className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300 bg-slate-950 rounded-xl p-5 border border-slate-800 font-mono">
                {report.report_text}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
