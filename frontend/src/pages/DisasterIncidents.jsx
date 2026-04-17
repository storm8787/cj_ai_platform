import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { disasterApi } from "../services/api";

export default function DisasterIncidents() {
  const navigate = useNavigate();
  const [uploads, setUploads] = useState([]);
  const [selectedUploadId, setSelectedUploadId] = useState(localStorage.getItem("disaster_active_upload_id") || "");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadUploads = async () => {
    try {
      const res = await disasterApi.getUploads();
      const uploadItems = res.data.items || [];
      setUploads(uploadItems);

      if (!selectedUploadId && uploadItems.length > 0) {
        setSelectedUploadId(uploadItems[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadIncidents = async (uploadId) => {
    if (!uploadId) return;
    setLoading(true);
    try {
      const res = await disasterApi.getIncidents({ upload_id: uploadId });
      setItems(res.data.items || []);
      localStorage.setItem("disaster_active_upload_id", uploadId);
    } catch (err) {
      console.error(err);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUploads();
  }, []);

  useEffect(() => {
    if (selectedUploadId) {
      loadIncidents(selectedUploadId);
    }
  }, [selectedUploadId]);

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">사건 목록</h1>
            <p className="text-slate-400 mt-2">
              업로드된 재난상황 카카오톡 데이터를 사건 단위로 정리한 목록입니다.
            </p>
          </div>
          <button
            onClick={() => navigate("/disaster-dashboard")}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg"
          >
            대시보드로
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

        <div className="bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-800 font-semibold">
            사건 목록
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-800 text-slate-300">
                <tr>
                  <th className="p-3 text-left">발생시각</th>
                  <th className="p-3 text-left">읍면동</th>
                  <th className="p-3 text-left">위치</th>
                  <th className="p-3 text-left">유형</th>
                  <th className="p-3 text-left">상태</th>
                  <th className="p-3 text-left">보고자</th>
                  <th className="p-3 text-left">사진수</th>
                  <th className="p-3 text-left">요약</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={8} className="p-6 text-center text-slate-400">
                      불러오는 중...
                    </td>
                  </tr>
                ) : items.length > 0 ? (
                  items.map((item) => (
                    <tr key={item.id} className="border-t border-slate-800">
                      <td className="p-3 whitespace-nowrap">{item.incident_time?.replace("T", " ").slice(0, 16)}</td>
                      <td className="p-3">{item.emd || "-"}</td>
                      <td className="p-3">{item.location_raw || "-"}</td>
                      <td className="p-3">{item.incident_type || "-"}</td>
                      <td className="p-3">{item.status || "-"}</td>
                      <td className="p-3">{item.reporter_name || "-"}</td>
                      <td className="p-3">{item.photo_count || 0}</td>
                      <td className="p-3">{item.summary || "-"}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="p-6 text-center text-slate-400">
                      조회된 사건이 없습니다.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}