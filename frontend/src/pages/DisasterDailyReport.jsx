import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { disasterApi } from "../services/api";

export default function DisasterDailyReport() {
  const navigate = useNavigate();
  const [reportDate, setReportDate] = useState(new Date().toISOString().slice(0, 10));
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const activeUploadId = sessionStorage.getItem("disaster_active_upload_id");
  const activeFileName = sessionStorage.getItem("disaster_active_upload_name");

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
      alert("보고서가 복사되었습니다.");
    } catch (err) {
      console.error(err);
      alert("복사에 실패했습니다.");
    }
  };

  if (!activeUploadId) {
    return (
      <div className="min-h-screen bg-slate-950 text-white p-6">
        <div className="max-w-4xl mx-auto bg-slate-900 border border-slate-700 rounded-2xl p-6">
          <h1 className="text-2xl font-bold mb-3">일일보고서 생성</h1>
          <p className="text-slate-400 mb-4">현재 세션에 선택된 파일이 없습니다. 먼저 txt 파일을 업로드하고 분석해주세요.</p>
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
        <div>
          <h1 className="text-2xl font-bold">일일보고서 생성</h1>
          <p className="text-slate-400 mt-2">
            현재 세션 파일 기준 재난상황 일일보고서를 자동 생성합니다.
          </p>
          <p className="text-sm text-slate-500 mt-1">
            파일명: {activeFileName || "현재 세션 파일"}
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-2">보고일자</label>
            <input
              type="date"
              value={reportDate}
              onChange={(e) => setReportDate(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
            />
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg disabled:opacity-50"
            >
              {loading ? "생성 중..." : "보고서 생성"}
            </button>

            {report && (
              <button
                onClick={handleCopy}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg"
              >
                복사
              </button>
            )}

            <button
              onClick={() => navigate("/disaster-upload")}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg"
            >
              다른 파일 업로드
            </button>
          </div>
        </div>

        {report && (
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 space-y-4">
            <h2 className="text-xl font-bold">{report.title}</h2>
            <p className="text-slate-300">{report.summary_text}</p>

            <pre className="whitespace-pre-wrap text-sm leading-relaxed text-slate-200 bg-slate-950 rounded-xl p-4 border border-slate-800">
              {report.report_text}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}