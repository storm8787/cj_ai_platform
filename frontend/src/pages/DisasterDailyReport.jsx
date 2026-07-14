import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { disasterApi } from "../services/api";
import { useDisasterSession } from "../hooks/useDisasterSession";

// ── 표 구분선 판별 ───────────────────────────────────────────────
// 공백 제거 후 |, -, : 만 남으면 구분선으로 판단
// 예: "| --- | --- |", "|:--|:--|", "|---------|------|" 모두 처리
function isTableSep(line) {
  const s = line.replace(/\s/g, "");
  return s.length > 2 && /^[|:\-]+$/.test(s) && s.includes("|") && s.includes("-");
}

function parseRow(line) {
  return line.split("|").slice(1, -1).map((c) => c.trim());
}

/** 굵게(**text**), 인라인 코드(`code`) 인라인 처리 */
function renderInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**"))
      return (
        <strong key={i} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    if (part.startsWith("`") && part.endsWith("`"))
      return (
        <code
          key={i}
          className="bg-slate-700 text-cyan-300 px-1 py-0.5 rounded text-xs font-mono"
        >
          {part.slice(1, -1)}
        </code>
      );
    return part;
  });
}

// ── 완전 재작성된 Markdown 렌더러 ─────────────────────────────────
// - 블록 단위 파싱 (표 사이 빈 줄 허용)
// - isTableSep으로 견고한 구분선 판별
// - 코드 펜스(```) 지원
// - 순서 없는/있는 리스트, 인라인 코드, 굵게 지원
function MdRenderer({ content }) {
  if (!content) return null;

  const rawLines = content.split("\n").map((l) => l.trimEnd());
  const elements = [];
  let i = 0;

  while (i < rawLines.length) {
    const line = rawLines[i];

    // 빈 줄 → 건너뜀
    if (!line.trim()) {
      i++;
      continue;
    }

    // ── 제목 ──────────────────────────────────────────
    const hMatch = line.match(/^(#{1,3})\s+(.+)/);
    if (hMatch) {
      const level = hMatch[1].length;
      const text = hMatch[2];
      if (level === 1) {
        elements.push(
          <h1 key={i} className="text-2xl font-bold text-white mt-6 mb-3 pb-2 border-b border-slate-700">
            {renderInline(text)}
          </h1>
        );
      } else if (level === 2) {
        elements.push(
          <h2 key={i} className="text-lg font-semibold text-slate-200 mt-5 mb-2">
            {renderInline(text)}
          </h2>
        );
      } else {
        elements.push(
          <h3 key={i} className="text-base font-semibold text-slate-300 mt-4 mb-1">
            {renderInline(text)}
          </h3>
        );
      }
      i++;
      continue;
    }

    // ── 코드 펜스 ─────────────────────────────────────
    if (line.startsWith("```")) {
      i++;
      const codeLines = [];
      while (i < rawLines.length && !rawLines[i].startsWith("```")) {
        codeLines.push(rawLines[i]);
        i++;
      }
      if (i < rawLines.length) i++; // 닫는 ``` 건너뜀
      elements.push(
        <pre
          key={`cf-${i}`}
          className="bg-slate-800 rounded-xl p-4 text-sm text-cyan-300 font-mono overflow-x-auto my-3 border border-slate-700"
        >
          {codeLines.join("\n")}
        </pre>
      );
      continue;
    }

    // ── 구분선 ───────────────────────────────────────
    if (/^[-*_]{3,}$/.test(line.trim())) {
      elements.push(<hr key={i} className="border-slate-700 my-5" />);
      i++;
      continue;
    }

    // ── 표 ──────────────────────────────────────────
    // | 로 시작하는 연속 줄 수집. 표 내 빈 줄 1개는 허용 (다음 줄이 |로 시작할 때)
    if (line.startsWith("|")) {
      const tableLines = [line];
      i++;
      while (i < rawLines.length) {
        const cur = rawLines[i].trimEnd();
        if (cur.startsWith("|")) {
          tableLines.push(cur);
          i++;
        } else if (
          !cur.trim() &&
          i + 1 < rawLines.length &&
          rawLines[i + 1].trimEnd().startsWith("|")
        ) {
          i++; // 표 내 빈 줄 한 개 허용
        } else {
          break;
        }
      }

      // 구분선 제거
      const dataLines = tableLines.filter((l) => !isTableSep(l));
      if (dataLines.length > 0) {
        const [headerLine, ...bodyLines] = dataLines;
        const headers = parseRow(headerLine);
        const rows = bodyLines.map(parseRow);

        elements.push(
          <div key={`tbl-${i}`} className="overflow-x-auto my-4">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr>
                  {headers.map((h, ci) => (
                    <th
                      key={ci}
                      className="px-3 py-2.5 text-left text-slate-200 font-semibold bg-slate-800 border border-slate-600 first:rounded-tl-lg last:rounded-tr-lg"
                    >
                      {renderInline(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, ri) => (
                  <tr
                    key={ri}
                    className={
                      ri % 2 === 0
                        ? "bg-slate-900 hover:bg-slate-800/60"
                        : "bg-slate-950 hover:bg-slate-800/60"
                    }
                  >
                    {row.map((cell, ci) => (
                      <td
                        key={ci}
                        className="px-3 py-2 text-slate-300 border border-slate-700"
                      >
                        {renderInline(cell)}
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

    // ── 순서 없는 리스트 ─────────────────────────────
    if (/^[-*+•◦]\s/.test(line)) {
      const items = [];
      while (i < rawLines.length && /^[-*+•◦]\s/.test(rawLines[i])) {
        items.push(rawLines[i].replace(/^[-*+•◦]\s+/, ""));
        i++;
      }
      elements.push(
        <ul
          key={`ul-${i}`}
          className="list-disc list-inside space-y-1 my-2 text-slate-300 text-sm ml-1"
        >
          {items.map((item, li) => (
            <li key={li} className="leading-relaxed">
              {renderInline(item)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // ── 순서 있는 리스트 ─────────────────────────────
    if (/^\d+[.)]\s/.test(line)) {
      const items = [];
      while (i < rawLines.length && /^\d+[.)]\s/.test(rawLines[i])) {
        items.push(rawLines[i].replace(/^\d+[.)]\s+/, ""));
        i++;
      }
      elements.push(
        <ol
          key={`ol-${i}`}
          className="list-decimal list-inside space-y-1 my-2 text-slate-300 text-sm ml-1"
        >
          {items.map((item, li) => (
            <li key={li} className="leading-relaxed">
              {renderInline(item)}
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // ── 일반 문단 ────────────────────────────────────
    elements.push(
      <p key={`p-${i}`} className="text-sm text-slate-300 leading-relaxed my-1">
        {renderInline(line)}
      </p>
    );
    i++;
  }

  return <div className="space-y-0.5">{elements}</div>;
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
  const [exporting, setExporting] = useState(false);
  const [viewMode, setViewMode] = useState("render");

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
    const blob = new Blob([report.report_text], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `재난일일보고_${reportDate}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadHwpx = async () => {
    if (!report?.report_text) return;
    setExporting(true);
    try {
      const res = await disasterApi.exportDailyReportHwpx({
        title: report.title,
        report_text: report.report_text,
        summary_text: report.summary_text,
        report_date: reportDate,
      });
      const blob = new Blob([res.data], { type: "application/octet-stream" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `재난일일보고_${reportDate}.hwpx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert("한글(HWPX) 내보내기에 실패했습니다.");
    } finally {
      setExporting(false);
    }
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
                  onClick={handleDownloadHwpx}
                  disabled={exporting}
                  className="px-4 py-2 bg-indigo-700 hover:bg-indigo-600 rounded-lg text-sm disabled:opacity-50"
                >
                  {exporting ? "내보내는 중..." : "한글(hwpx) 다운로드"}
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
