import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { disasterApi } from "../services/api";

export default function DisasterIncidents() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  const activeUploadId = sessionStorage.getItem("disaster_active_upload_id");
  const activeFileName = sessionStorage.getItem("disaster_active_upload_name");

  const loadIncidents = async () => {
    if (!activeUploadId) return;

    setLoading(true);
    try {
      const res = await disasterApi.getIncidents({ upload_id: activeUploadId });
      setItems(res.data.items || []);
    } catch (err) {
      console.error(err);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, []);

  if (!activeUploadId) {
    return (
      <div className="min-h-screen bg-slate-950 text-white p-6">
        <div className="max-w-4xl mx-auto bg-slate-900 border border-slate-700 rounded-2xl p-6">
          <h1 className="text-2xl font-bold mb-3">사건 목록</h1>
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
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">사건 목록</h1>
            <p className="text-slate-400 mt-2">
              현재 세션 파일 기준 사건 목록입니다.
            </p>
            <p className="text-sm text-slate-500 mt-1">
              파일명: {activeFileName || "현재 세션 파일"}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => navigate("/disaster-dashboard")}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg"
            >
              대시보드로
            </button>
            <button
              onClick={() => navigate("/disaster-upload")}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg"
            >
              다른 파일 업로드
            </button>
          </div>
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