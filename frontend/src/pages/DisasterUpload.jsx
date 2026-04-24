import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { disasterApi } from "../services/api";
import { setDisasterSession } from "../constants/disaster";
import { useDisasterSession } from "../hooks/useDisasterSession";

export default function DisasterUpload() {
  const navigate = useNavigate();
  const { uploadId: activeUploadId, fileName: activeFileName } = useDisasterSession();

  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [uploadResult, setUploadResult] = useState(null);

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError("");
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await disasterApi.upload(formData);
      setUploadResult(res.data);

      setDisasterSession(res.data.upload_id, res.data.file_name || file.name);
    } catch (err) {
      setError(err?.response?.data?.detail || "업로드 중 오류가 발생했습니다.");
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyze = async () => {
    const targetUploadId = uploadResult?.upload_id || activeUploadId;
    if (!targetUploadId) return;

    setAnalyzing(true);
    setError("");

    try {
      await disasterApi.analyze(targetUploadId);
      alert("분석이 완료되었습니다.");
      navigate("/disaster-dashboard");
    } catch (err) {
      // 409 Conflict (이미 분석 중) 특별 처리
      if (err?.response?.status === 409) {
        setError("이미 분석 중입니다. 잠시 후 다시 시도해주세요.");
      } else {
        setError(err?.response?.data?.detail || "분석 중 오류가 발생했습니다.");
      }
    } finally {
      setAnalyzing(false);
    }
  };

  const canAnalyze = !!(uploadResult?.upload_id || activeUploadId);

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">재난상황 카카오톡 업로드</h1>
          <p className="text-slate-400 mt-2">
            카카오톡 대화 txt 파일을 업로드하면 사건 목록, 대시보드, 일일보고서를 생성합니다.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 space-y-4">
          <h2 className="text-lg font-semibold">파일 업로드</h2>

          <input
            type="file"
            accept=".txt"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-slate-300"
          />

          <div className="flex gap-3">
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg disabled:opacity-50"
            >
              {uploading ? "업로드 중..." : "업로드"}
            </button>

            {canAnalyze && (
              <button
                onClick={handleAnalyze}
                disabled={analyzing}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg disabled:opacity-50"
              >
                {analyzing ? "분석 중..." : "분석 실행"}
              </button>
            )}
          </div>

          {error && <div className="text-red-400 text-sm">{error}</div>}

          {uploadResult && (
            <div className="bg-slate-800 rounded-lg p-4 text-sm text-slate-300">
              <p>파일명: {uploadResult.file_name}</p>
              <p>전체 메시지 수: {uploadResult.message_count}</p>
              <p>일반 메시지 수: {uploadResult.valid_message_count}</p>
            </div>
          )}
        </div>

        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6">
          <h2 className="text-lg font-semibold mb-3">현재 작업 파일</h2>
          {activeUploadId ? (
            <div className="text-sm text-slate-300 space-y-1">
              <p>파일명: {activeFileName || "현재 세션 파일"}</p>
              <p className="text-slate-500">
                현재 세션에서만 유지됩니다. 브라우저를 닫으면 목록은 사라집니다.
              </p>
            </div>
          ) : (
            <p className="text-slate-400">현재 세션에 선택된 파일이 없습니다.</p>
          )}
        </div>
      </div>
    </div>
  );
}