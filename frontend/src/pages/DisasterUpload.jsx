import { useState } from "react";
import { disasterApi } from "../services/api";

export default function DisasterUpload() {
  const [file, setFile] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await disasterApi.upload(formData);
      setUploadResult(res.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "업로드 실패");
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!uploadResult?.upload_id) return;
    setAnalyzing(true);
    setError("");
    try {
      await disasterApi.analyze(uploadResult.upload_id);
      alert("분석이 완료되었습니다.");
    } catch (err) {
      setError(err?.response?.data?.detail || "분석 실패");
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="p-6 text-white">
      <h1 className="text-2xl font-bold mb-4">재난상황 카카오톡 업로드</h1>
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 space-y-4">
        <input type="file" accept=".txt" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        <div className="flex gap-3">
          <button onClick={handleUpload} disabled={!file || loading} className="px-4 py-2 bg-cyan-600 rounded-lg">
            {loading ? "업로드 중..." : "업로드"}
          </button>
          <button onClick={handleAnalyze} disabled={!uploadResult?.upload_id || analyzing} className="px-4 py-2 bg-emerald-600 rounded-lg">
            {analyzing ? "분석 중..." : "분석 실행"}
          </button>
        </div>
        {error && <p className="text-red-400">{error}</p>}
        {uploadResult && (
          <div className="text-sm text-gray-300 bg-slate-800 rounded-lg p-4">
            <p>upload_id: {uploadResult.upload_id}</p>
            <p>전체 메시지 수: {uploadResult.message_count}</p>
            <p>일반 메시지 수: {uploadResult.valid_message_count}</p>
          </div>
        )}
      </div>
    </div>
  );
}