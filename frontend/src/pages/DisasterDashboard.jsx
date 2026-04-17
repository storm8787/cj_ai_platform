import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { disasterApi } from "../services/api";

function StatCard({ title, value }) {
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4">
      <p className="text-sm text-slate-400">{title}</p>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
    </div>
  );
}

export default function DisasterDashboard() {
  const navigate = useNavigate();
  const [uploads, setUploads] = useState([]);
  const [selectedUploadId, setSelectedUploadId] = useState(localStorage.getItem("disaster_active_upload_id") || "");
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadUploads = async () => {
    try {
      const res = await disasterApi.getUploads();
      const items = res.data.items || [];
      setUploads(items);

      if (!selectedUploadId && items.length > 0) {
        setSelectedUploadId(items[0].id);
        localStorage.setItem("disaster_active_upload_id", items[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadOverview = async (uploadId) => {
    if (!uploadId) return;
    setLoading(true);
    try {
      const res = await disasterApi.getOverview(uploadId);
      setOverview(res.data);
      localStorage.setItem("disaster_active_upload_id", uploadId);
    } catch (err) {
      console.error(err);
      setOverview(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUploads();
  }, []);

  useEffect(() => {
    if (selectedUploadId) {
      loadOverview(selectedUploadId);
    }
  }, [selectedUploadId]);

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">재난상황 대시보드</h1>
            <p className="text-slate-400 mt-2">
              업로드된 카카오톡 재난상황 데이터를 기준으로 사건 통계를 확인합니다.
            </p>
          </div>
          <button
            onClick={() => navigate("/disaster-upload")}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg"
          >
            새 파일 업로드
          </button>
        </div>

        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4">
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

        {loading ? (
          <div className="text-slate-400">불러오는 중...</div>
        ) : overview ? (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard title="총 사건 수" value={overview.total || 0} />
              <StatCard title="유형 수" value={Object.keys(overview.by_type || {}).length} />
              <StatCard title="상태 수" value={Object.keys(overview.by_status || {}).length} />
              <StatCard title="읍면동 수" value={Object.keys(overview.by_emd || {}).length} />
            </div>

            <div className="grid md:grid-cols-3 gap-4">
              <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4">
                <h2 className="font-semibold mb-3">유형별 건수</h2>
                <div className="space-y-2 text-sm">
                  {Object.entries(overview.by_type || {}).map(([key, value]) => (
                    <div key={key} className="flex justify-between border-b border-slate-800 pb-2">
                      <span>{key}</span>
                      <span>{value}건</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4">
                <h2 className="font-semibold mb-3">상태별 건수</h2>
                <div className="space-y-2 text-sm">
                  {Object.entries(overview.by_status || {}).map(([key, value]) => (
                    <div key={key} className="flex justify-between border-b border-slate-800 pb-2">
                      <span>{key}</span>
                      <span>{value}건</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4">
                <h2 className="font-semibold mb-3">읍면동별 건수</h2>
                <div className="space-y-2 text-sm max-h-80 overflow-y-auto">
                  {Object.entries(overview.by_emd || {}).map(([key, value]) => (
                    <div key={key} className="flex justify-between border-b border-slate-800 pb-2">
                      <span>{key}</span>
                      <span>{value}건</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => navigate("/disaster-incidents")}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg"
              >
                사건목록 보기
              </button>
              <button
                onClick={() => navigate("/disaster-report")}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg"
              >
                일일보고서 생성
              </button>
            </div>
          </>
        ) : (
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 text-slate-400">
            분석된 데이터가 없습니다. 먼저 업로드 후 분석을 실행해주세요.
          </div>
        )}
      </div>
    </div>
  );
}