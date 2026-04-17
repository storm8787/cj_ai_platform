import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { disasterApi } from "../services/api";

export default function DisasterUpload() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [uploadResult, setUploadResult] = useState(null);
  const [uploads, setUploads] = useState([]);

  const loadUploads = async () => {
    try {
      const res = await disasterApi.getUploads();
      setUploads(res.data.items || []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadUploads();
  }, []);

  const saveActiveUpload = (upload) => {
    localStorage.setItem("disaster_active_upload_id", upload.id || upload.upload_id);
    localStorage.setItem("disaster_active_upload_name", upload.file_name || "");
  };

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

      localStorage.setItem("disaster_active_upload_id", res.data.upload_id);
      localStorage.setItem("disaster_active_upload_name", res.data.file_name || file.name);

      await loadUploads();
    } catch (err) {
      setError(err?.response?.data?.detail || "업로드 중 오류가 발생했습니다.");
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyze = async (uploadId) => {
    if (!uploadId) return;
    setAnalyzing(true);
    setError("");

    try {
      await disasterApi.analyze(uploadId);
      localStorage.setItem("disaster_active_upload_id", uploadId);
      alert("분석이 완료되었습니다.");
      navigate("/disaster-dashboard");
    } catch (err) {
      setError(err?.response?.data?.detail || "분석 중 오류가 발생했습니다.");
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">재난상황 카카오톡 업로드</h1>
          <p className="text-slate-400 mt-2">
            카카오톡 대화 txt 파일을 업로드하면 사건 목록, 대시보드, 일일보고서를 생성합니다.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 space-y-4">
          <h2 className="text-lg font-semibold">새 파일 업로드</h2>

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

            {uploadResult?.upload_id && (
              <button
                onClick={() => handleAnalyze(uploadResult.upload_id)}
                disabled={analyzing}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg disabled:opacity-50"
              >
                {analyzing ? "분석 중..." : "업로드한 파일 분석"}
              </button>
            )}
          </div>

          {error && (
            <div className="text-red-400 text-sm">{error}</div>
          )}

          {uploadResult && (
            <div className="bg-slate-800 rounded-lg p-4 text-sm text-slate-300">
              <p>파일명: {uploadResult.file_name}</p>
              <p>전체 메시지 수: {uploadResult.message_count}</p>
              <p>일반 메시지 수: {uploadResult.valid_message_count}</p>
            </div>
          )}
        </div>

        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6">
          <h2 className="text-lg font-semibold mb-4">최근 업로드</h2>

          {!uploads.length ? (
            <p className="text-slate-400">업로드된 파일이 없습니다.</p>
          ) : (
            <div className="space-y-3">
              {uploads.map((item) => (
                <div
                  key={item.id}
                  className="bg-slate-800 rounded-xl p-4 flex items-center justify-between"
                >
                  <div>
                    <p className="font-medium">{item.file_name}</p>
                    <p className="text-sm text-slate-400">
                      업로드: {item.uploaded_at?.replace("T", " ").slice(0, 16)} / 상태: {item.analysis_status}
                    </p>
                    <p className="text-sm text-slate-500">
                      메시지 {item.message_count || 0}건 / 사건 {item.incident_count || 0}건
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        saveActiveUpload(item);
                        navigate("/disaster-dashboard");
                      }}
                      className="px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm"
                    >
                      대시보드
                    </button>

                    <button
                      onClick={() => {
                        saveActiveUpload(item);
                        navigate("/disaster-incidents");
                      }}
                      className="px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm"
                    >
                      사건목록
                    </button>

                    <button
                      onClick={() => {
                        saveActiveUpload(item);
                        navigate("/disaster-report");
                      }}
                      className="px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm"
                    >
                      보고서
                    </button>

                    {item.analysis_status !== "analyzed" && (
                      <button
                        onClick={() => handleAnalyze(item.id)}
                        disabled={analyzing}
                        className="px-3 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm disabled:opacity-50"
                      >
                        분석
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}