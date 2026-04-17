import { useEffect, useState } from "react";
import { disasterApi } from "../services/api";

export default function DisasterDailyReport() {
  const [uploads, setUploads] = useState([]);
  const [selectedUploadId, setSelectedUploadId] = useState(localStorage.getItem("disaster_active_upload_id") || "");
  const [reportDate, setReportDate] = useState(new Date().toISOString().slice(0, 10));
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadUploads = async () => {
    try {
      const res = await disasterApi.getUploads();
      const items = res.data.items || [];
      setUploads(items);

      if (!selectedUploadId && items.length > 0) {
        setSelectedUploadId(items[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadUploads();
  }, []);

  const handleGenerate = async () => {
    if (!selectedUploadId || !reportDate) return;
    setLoading(true);
    try {
      const res = await disasterApi.generateDailyReport({
        upload_id: selectedUploadId,
        report_date: reportDate,
        created_by: "admin",
      });
      setReport(res.data.report);
      localStorage.setItem("disaster_active_upload_id", selectedUploadId);
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

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">일일보고서 생성</h1>
          <p className="text-slate-400 mt-2">
            업로드된 사건 데이터를 기반으로 재난상황 일일보고서를 자동 생성합니다.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-2">분석 파일 선택</label>
            <select
              value={selectedUploadId}
              onChange={(e) => setSelectedUploadId(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
            >
              <option value="">선택하세요</option>
              {uploads.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.file_name} ({item.analysis_status})
                </option>
              ))}
            </select>
          </div>

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