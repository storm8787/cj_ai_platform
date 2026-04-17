import { useEffect, useState } from "react";
import { disasterApi } from "../services/api";

function Card({ title, value }) {
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
      <div className="text-gray-400 text-sm">{title}</div>
      <div className="text-2xl font-bold text-white mt-1">{value}</div>
    </div>
  );
}

export default function DisasterDashboard() {
  const [uploadId, setUploadId] = useState("");
  const [data, setData] = useState(null);

  const loadData = async () => {
    if (!uploadId) return;
    const res = await disasterApi.getOverview(uploadId);
    setData(res.data);
  };

  return (
    <div className="p-6 text-white space-y-6">
      <h1 className="text-2xl font-bold">재난상황 대시보드</h1>
      <div className="flex gap-3">
        <input
          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 w-96"
          placeholder="upload_id 입력"
          value={uploadId}
          onChange={(e) => setUploadId(e.target.value)}
        />
        <button onClick={loadData} className="px-4 py-2 bg-cyan-600 rounded-lg">조회</button>
      </div>

      {data && (
        <>
          <div className="grid grid-cols-4 gap-4">
            <Card title="총 사건 수" value={data.total || 0} />
            <Card title="유형 수" value={Object.keys(data.by_type || {}).length} />
            <Card title="상태 수" value={Object.keys(data.by_status || {}).length} />
            <Card title="읍면동 수" value={Object.keys(data.by_emd || {}).length} />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
              <h2 className="font-semibold mb-3">유형별 건수</h2>
              <pre className="text-sm text-gray-300 whitespace-pre-wrap">{JSON.stringify(data.by_type, null, 2)}</pre>
            </div>
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
              <h2 className="font-semibold mb-3">상태별 건수</h2>
              <pre className="text-sm text-gray-300 whitespace-pre-wrap">{JSON.stringify(data.by_status, null, 2)}</pre>
            </div>
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
              <h2 className="font-semibold mb-3">읍면동별 건수</h2>
              <pre className="text-sm text-gray-300 whitespace-pre-wrap">{JSON.stringify(data.by_emd, null, 2)}</pre>
            </div>
          </div>
        </>
      )}
    </div>
  );
}