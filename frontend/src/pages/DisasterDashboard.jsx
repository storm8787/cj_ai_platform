import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { disasterApi } from "../services/api";
import {
  INCIDENT_TYPE_LABELS,
  STATUS_LABELS,
} from "../constants/disaster";
import { useDisasterSession } from "../hooks/useDisasterSession";

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
  const { uploadId: activeUploadId, fileName: activeFileName } = useDisasterSession();

  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadOverview = async () => {
      if (!activeUploadId) {
        setOverview(null);
        return;
      }

      setLoading(true);
      try {
        const res = await disasterApi.getOverview(activeUploadId);
        setOverview(res.data);
      } catch (err) {
        console.error(err);
        setOverview(null);
      } finally {
        setLoading(false);
      }
    };

    loadOverview();
  }, [activeUploadId]);

  if (!activeUploadId) {
    return (
      <div className="min-h-screen bg-slate-950 text-white p-6">
        <div className="max-w-4xl mx-auto bg-slate-900 border border-slate-700 rounded-2xl p-6">
          <h1 className="text-2xl font-bold mb-3">재난상황 대시보드</h1>
          <p className="text-slate-400 mb-4">
            현재 세션에 선택된 파일이 없습니다. 먼저 txt 파일을 업로드하고 분석해주세요.
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
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">재난상황 대시보드</h1>
            <p className="text-slate-400 mt-2">현재 세션 파일 기준 통계입니다.</p>
            <p className="text-sm text-slate-500 mt-1">
              파일명: {activeFileName || "현재 세션 파일"}
            </p>
          </div>
          <button
            onClick={() => navigate("/disaster-upload")}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg"
          >
            다른 파일 업로드
          </button>
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
                      <span>{INCIDENT_TYPE_LABELS[key] || key}</span>
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
                      <span>{STATUS_LABELS[key] || key}</span>
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
            분석된 데이터가 없습니다. 업로드 후 분석을 먼저 실행해주세요.
          </div>
        )}
      </div>
    </div>
  );
}