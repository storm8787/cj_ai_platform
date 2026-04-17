import { useState } from "react";
import { disasterApi } from "../services/api";

export default function DisasterDailyReport() {
  const [uploadId, setUploadId] = useState("");
  const [reportDate, setReportDate] = useState("");
  const [report, setReport] = useState(null);

  const handleGenerate = async () => {
    const res = await disasterApi.generateDailyReport({
      upload_id: uploadId,
      report_date: reportDate,
      created_by: "admin",
    });
    setReport(res.data.report);
  };

  return (
    <div className="p-6 text-white space-y-6">
      <h1 className="text-2xl font-bold">일일보고서 생성</h1>
      <div className="flex gap-3">
        <input
          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 w-80"
          placeholder="upload_id 입력"
          value={uploadId}
          onChange={(e) => setUploadId(e.target.value)}
        />
        <input
          type="date"
          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2"
          value={reportDate}
          onChange={(e) => setReportDate(e.target.value)}
        />
        <button onClick={handleGenerate} className="px-4 py-2 bg-emerald-600 rounded-lg">생성</button>
      </div>

      {report && (
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 space-y-4">
          <h2 className="text-xl font-bold">{report.title}</h2>
          <p className="text-gray-300">{report.summary_text}</p>
          <pre className="whitespace-pre-wrap text-sm text-gray-200 bg-slate-950 rounded-lg p-4">
            {report.report_text}
          </pre>
        </div>
      )}
    </div>
  );
}