import { useState } from "react";
import { disasterApi } from "../services/api";

export default function DisasterIncidents() {
  const [uploadId, setUploadId] = useState("");
  const [items, setItems] = useState([]);

  const handleSearch = async () => {
    const res = await disasterApi.getIncidents({ upload_id: uploadId });
    setItems(res.data.items || []);
  };

  return (
    <div className="p-6 text-white space-y-6">
      <h1 className="text-2xl font-bold">사건 목록</h1>
      <div className="flex gap-3">
        <input
          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 w-96"
          placeholder="upload_id 입력"
          value={uploadId}
          onChange={(e) => setUploadId(e.target.value)}
        />
        <button onClick={handleSearch} className="px-4 py-2 bg-cyan-600 rounded-lg">조회</button>
      </div>

      <div className="overflow-auto bg-slate-900 border border-slate-700 rounded-xl">
        <table className="w-full text-sm">
          <thead className="bg-slate-800 text-gray-300">
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
            {items.map((item) => (
              <tr key={item.id} className="border-t border-slate-800">
                <td className="p-3">{item.incident_time}</td>
                <td className="p-3">{item.emd}</td>
                <td className="p-3">{item.location_raw}</td>
                <td className="p-3">{item.incident_type}</td>
                <td className="p-3">{item.status}</td>
                <td className="p-3">{item.reporter_name}</td>
                <td className="p-3">{item.photo_count}</td>
                <td className="p-3">{item.summary}</td>
              </tr>
            ))}
            {!items.length && (
              <tr>
                <td className="p-4 text-center text-gray-400" colSpan={8}>조회된 사건이 없습니다.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}