import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { disasterApi } from "../services/api";
import { INCIDENT_TYPE_LABELS, STATUS_LABELS } from "../constants/disaster";
import { useDisasterSession } from "../hooks/useDisasterSession";

const TYPE_COLORS = {
  flood: "#3b82f6",
  drainage: "#06b6d4",
  landslide: "#d97706",
  tree_fall: "#16a34a",
  road_control: "#f97316",
  sinkhole: "#ef4444",
  rescue: "#a855f7",
  facility: "#6366f1",
  heavy_snow: "#93c5fd",
  icing: "#67e8f9",
  cold_wave: "#818cf8",
  inspection: "#64748b",
};

const TYPE_BG = {
  flood: "bg-blue-500/20 text-blue-300",
  drainage: "bg-cyan-500/20 text-cyan-300",
  landslide: "bg-amber-500/20 text-amber-300",
  tree_fall: "bg-green-500/20 text-green-300",
  road_control: "bg-orange-500/20 text-orange-300",
  sinkhole: "bg-red-500/20 text-red-300",
  rescue: "bg-purple-500/20 text-purple-300",
  facility: "bg-indigo-500/20 text-indigo-300",
  heavy_snow: "bg-blue-300/20 text-blue-200",
  icing: "bg-cyan-300/20 text-cyan-200",
  cold_wave: "bg-indigo-400/20 text-indigo-300",
  inspection: "bg-slate-500/20 text-slate-400",
};

const STATUS_BG = {
  reported: "bg-red-500/20 text-red-300",
  in_progress: "bg-amber-500/20 text-amber-300",
  completed: "bg-green-500/20 text-green-300",
  monitoring: "bg-blue-500/20 text-blue-300",
  no_issue: "bg-slate-400/20 text-slate-400",
  closed: "bg-slate-500/20 text-slate-500",
};

const STATUS_COLORS = {
  reported: "#ef4444",
  in_progress: "#f59e0b",
  completed: "#22c55e",
  monitoring: "#3b82f6",
  no_issue: "#94a3b8",
  closed: "#64748b",
};

function StatCard({ title, value, sub, highlight }) {
  return (
    <div
      className={`rounded-2xl p-4 border ${
        highlight
          ? "bg-red-950/60 border-red-700"
          : "bg-slate-900 border-slate-700"
      }`}
    >
      <p className="text-xs text-slate-400 tracking-widest uppercase">{title}</p>
      <p
        className={`text-3xl font-bold mt-1 ${
          highlight ? "text-red-300" : "text-white"
        }`}
      >
        {value ?? "—"}
      </p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}

function HBar({ label, value, max, color }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-300">{label}</span>
        <span className="text-slate-400">{value}건</span>
      </div>
      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color || "#06b6d4" }}
        />
      </div>
    </div>
  );
}

function EmdDotMap({ emdMapData }) {
  // 좌표 있는 항목만 렌더링. 백엔드가 25개 전체 EMD를 항상 전달하므로 항상 지도 표시됨.
  const withCoords = (emdMapData || []).filter((d) => d.lat && d.lng);

  if (withCoords.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500 text-sm">
        데이터 불러오는 중...
      </div>
    );
  }

  const lats = withCoords.map((d) => d.lat);
  const lngs = withCoords.map((d) => d.lng);
  const minLat = Math.min(...lats) - 0.025;
  const maxLat = Math.max(...lats) + 0.025;
  const minLng = Math.min(...lngs) - 0.025;
  const maxLng = Math.max(...lngs) + 0.025;
  const maxCount = Math.max(...withCoords.map((d) => d.count), 1);

  return (
    <div className="relative w-full h-full bg-slate-800/50 rounded-xl overflow-hidden border border-slate-700/50">
      <div
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage:
            "linear-gradient(rgba(148,163,184,0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.4) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />
      <div className="absolute top-2 left-3 text-xs text-slate-500 pointer-events-none">
        충주시 읍면동 현황
      </div>

      {withCoords.map((d) => {
        const x = ((d.lng - minLng) / (maxLng - minLng)) * 100;
        const y = ((maxLat - d.lat) / (maxLat - minLat)) * 100;
        const r = 7 + Math.min(d.count / maxCount, 1) * 14;
        const hasActive = d.active_count > 0;
        const hasAny = d.count > 0;

        return (
          <div
            key={d.emd}
            className="absolute group cursor-default"
            style={{
              left: `${x}%`,
              top: `${y}%`,
              transform: "translate(-50%, -50%)",
              zIndex: hasActive ? 10 : hasAny ? 5 : 1,
            }}
          >
            {hasActive && (
              <div
                className="absolute rounded-full animate-ping opacity-30"
                style={{
                  width: r * 2 + 8 + "px",
                  height: r * 2 + 8 + "px",
                  top: -(r + 4) + "px",
                  left: -(r + 4) + "px",
                  backgroundColor: "#ef4444",
                }}
              />
            )}
            <div
              className="relative rounded-full flex items-center justify-center text-white font-bold shadow-lg border border-white/10"
              style={{
                width: r * 2 + "px",
                height: r * 2 + "px",
                backgroundColor: hasActive
                  ? "#dc2626"
                  : hasAny
                  ? "#16a34a"
                  : "#1e293b",
                fontSize: r < 11 ? "8px" : "10px",
              }}
            >
              {hasAny ? d.count : ""}
            </div>
            <div className="absolute z-20 bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-slate-800 border border-slate-600 rounded-lg px-2.5 py-1.5 text-xs whitespace-nowrap shadow-xl pointer-events-none">
              <div className="font-semibold text-white">{d.emd}</div>
              <div className="text-slate-400">
                전체 {d.count}건 | 진행중{" "}
                <span className={d.active_count > 0 ? "text-red-400" : ""}>
                  {d.active_count}건
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function KakaoMapView({ emdMapData }) {
  const mapRef = useRef(null);
  const [kakaoLoaded, setKakaoLoaded] = useState(false);
  const KAKAO_KEY = import.meta.env.VITE_KAKAO_MAP_KEY;

  useEffect(() => {
    if (!KAKAO_KEY || !mapRef.current) return;
    let scriptEl = null;

    const init = () => {
      try {
        window.kakao.maps.load(() => {
          try {
            const center = new window.kakao.maps.LatLng(36.9911, 127.8636);
            const map = new window.kakao.maps.Map(mapRef.current, {
              center,
              level: 9,
            });
            (emdMapData || []).forEach((d) => {
              if (!d.lat || !d.lng || d.count === 0) return;
              const pos = new window.kakao.maps.LatLng(d.lat, d.lng);
              new window.kakao.maps.Circle({
                map,
                center: pos,
                radius: 300 + d.count * 200,
                strokeWeight: 2,
                strokeColor: d.active_count > 0 ? "#ef4444" : "#16a34a",
                strokeOpacity: 0.9,
                fillColor: d.active_count > 0 ? "#ef4444" : "#16a34a",
                fillOpacity: 0.35,
              });
              new window.kakao.maps.CustomOverlay({
                map,
                position: pos,
                content: `<div style="background:rgba(0,0,0,0.75);color:#fff;border-radius:4px;padding:2px 6px;font-size:11px;white-space:nowrap">${d.emd} ${d.count}건</div>`,
                yAnchor: 2.6,
              });
            });
            setKakaoLoaded(true);
          } catch {
            // 카카오맵 초기화 실패 → EmdDotMap으로 fallback (아무것도 안 해도 됨)
          }
        });
      } catch {
        // 무시 — EmdDotMap이 항상 기본 표시됨
      }
    };

    if (window.kakao?.maps) {
      init();
    } else {
      scriptEl = document.createElement("script");
      scriptEl.src = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_KEY}&autoload=false`;
      scriptEl.async = true;
      scriptEl.onload = init;
      scriptEl.onerror = () => {}; // EmdDotMap이 기본 표시됨
      document.head.appendChild(scriptEl);
    }

    return () => {
      if (scriptEl && document.head.contains(scriptEl))
        document.head.removeChild(scriptEl);
    };
  }, [KAKAO_KEY, emdMapData]);

  return (
    <div className="relative w-full h-full">
      {/* EmdDotMap은 항상 기본 표시 */}
      <EmdDotMap emdMapData={emdMapData} />
      {/* 카카오맵 성공 시 위에 오버레이 */}
      {KAKAO_KEY && (
        <div
          ref={mapRef}
          className="absolute inset-0 rounded-xl"
          style={{ display: kakaoLoaded ? "block" : "none" }}
        />
      )}
    </div>
  );
}

function RecentIncidentCard({ incident }) {
  const typeBg =
    TYPE_BG[incident.incident_type] || "bg-slate-500/20 text-slate-400";
  const statusBg =
    STATUS_BG[incident.status] || "bg-slate-500/20 text-slate-400";

  return (
    <div className="border-b border-slate-800 py-2.5 last:border-0">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1 flex-wrap mb-1">
            <span className={`text-xs px-1.5 py-0.5 rounded ${typeBg}`}>
              {incident.incident_type_label ||
                INCIDENT_TYPE_LABELS[incident.incident_type] ||
                incident.incident_type}
            </span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${statusBg}`}>
              {incident.status_label ||
                STATUS_LABELS[incident.status] ||
                incident.status}
            </span>
          </div>
          <p className="text-sm text-white truncate">
            {incident.location_raw || incident.emd || "위치 불명"}
          </p>
          {incident.summary && (
            <p className="text-xs text-slate-500 truncate mt-0.5">
              {incident.summary}
            </p>
          )}
        </div>
        <div className="text-right shrink-0">
          <p className="text-xs text-slate-500">{incident.emd}</p>
          <p className="text-xs text-slate-600">
            {(incident.last_update_time || "").slice(0, 16)}
          </p>
        </div>
      </div>
    </div>
  );
}

export default function DisasterDashboard() {
  const navigate = useNavigate();
  const { uploadId: activeUploadId, fileName: activeFileName } =
    useDisasterSession();

  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");

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

  const filteredRecent = (overview?.recent_incidents || []).filter((inc) => {
    if (filterType !== "all" && inc.incident_type !== filterType) return false;
    if (filterStatus !== "all" && inc.status !== filterStatus) return false;
    return true;
  });

  if (!activeUploadId) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-8 text-center">
          <div className="text-5xl mb-4">🚨</div>
          <h1 className="text-2xl font-bold mb-3">재난상황 대시보드</h1>
          <p className="text-slate-400 mb-6 text-sm">
            선택된 파일이 없습니다. 카카오톡 TXT 파일을 업로드하고 분석을
            실행해주세요.
          </p>
          <button
            onClick={() => navigate("/disaster-upload")}
            className="px-6 py-3 bg-cyan-600 hover:bg-cyan-500 rounded-xl font-semibold"
          >
            파일 업로드하기
          </button>
        </div>
      </div>
    );
  }

  const maxTypeVal = Math.max(...Object.values(overview?.by_type || {}), 1);
  const maxStatusVal = Math.max(
    ...Object.values(overview?.by_status || {}),
    1
  );
  const maxEmdVal = Math.max(...Object.values(overview?.by_emd || {}), 1);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* 상단 헤더 */}
      <div className="bg-slate-900 border-b border-slate-800 px-6 py-3.5">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold tracking-tight">
              재난상황 대시보드
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              {activeFileName || "현재 세션 파일"}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => navigate("/disaster-upload")}
              className="px-3 py-1.5 text-sm bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700"
            >
              업로드
            </button>
            <button
              onClick={() => navigate("/disaster-incidents")}
              className="px-3 py-1.5 text-sm bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700"
            >
              사건 목록
            </button>
            <button
              onClick={() => navigate("/disaster-report")}
              className="px-3 py-1.5 text-sm bg-emerald-700 hover:bg-emerald-600 rounded-lg"
            >
              보고서 생성
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-5 space-y-5">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-slate-400 text-sm animate-pulse">
              데이터 불러오는 중...
            </div>
          </div>
        ) : overview ? (
          <>
            {/* 요약 카드 5개 */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              <StatCard title="총 사건" value={overview.total ?? 0} />
              <StatCard
                title="진행중"
                value={overview.active_count ?? 0}
                highlight={(overview.active_count ?? 0) > 0}
                sub="즉시 조치 필요"
              />
              <StatCard
                title="완료·종결"
                value={overview.done_count ?? 0}
                sub="건"
              />
              <StatCard
                title="발생 읍면동"
                value={
                  overview.affected_emd_count ??
                  Object.keys(overview.by_emd || {}).length
                }
                sub="개 지역"
              />
              <StatCard
                title="최다 유형"
                value={overview.top_type_label || "—"}
                sub={
                  overview.top_type
                    ? `${overview.by_type?.[overview.top_type] ?? ""}건`
                    : ""
                }
              />
            </div>

            {/* 지도 + 최근 사건 */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* 지도 영역 */}
              <div className="lg:col-span-2 bg-slate-900 border border-slate-700 rounded-2xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-slate-200">
                    읍면동별 사건 현황
                  </h2>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
                      진행중
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
                      완료
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-slate-600 inline-block" />
                      없음
                    </span>
                  </div>
                </div>
                <div className="h-72 relative">
                  <KakaoMapView emdMapData={overview.emd_map_data || []} />
                </div>
              </div>

              {/* 최근 사건 카드 */}
              <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4 flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-sm font-semibold text-slate-200">
                    최근 사건
                  </h2>
                  <span className="text-xs text-slate-500">최근 업데이트순</span>
                </div>
                <div className="flex gap-1.5 mb-3 flex-wrap">
                  <select
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value)}
                    className="text-xs bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-300 flex-1 min-w-0"
                  >
                    <option value="all">전체 유형</option>
                    {Object.entries(INCIDENT_TYPE_LABELS).map(([k, v]) => (
                      <option key={k} value={k}>
                        {v}
                      </option>
                    ))}
                  </select>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="text-xs bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-300 flex-1 min-w-0"
                  >
                    <option value="all">전체 상태</option>
                    {Object.entries(STATUS_LABELS).map(([k, v]) => (
                      <option key={k} value={k}>
                        {v}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="overflow-y-auto flex-1">
                  {filteredRecent.length > 0 ? (
                    filteredRecent.map((inc, i) => (
                      <RecentIncidentCard key={i} incident={inc} />
                    ))
                  ) : (
                    <div className="flex items-center justify-center h-full min-h-[80px]">
                      <p className="text-slate-500 text-sm">
                        해당 조건의 사건 없음
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* 차트 3열 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* 유형별 */}
              <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4">
                <h2 className="text-sm font-semibold text-slate-200 mb-4">
                  유형별 사건 수
                </h2>
                <div className="space-y-3">
                  {Object.entries(overview.by_type || {})
                    .sort((a, b) => b[1] - a[1])
                    .map(([key, val]) => (
                      <HBar
                        key={key}
                        label={INCIDENT_TYPE_LABELS[key] || key}
                        value={val}
                        max={maxTypeVal}
                        color={TYPE_COLORS[key] || "#64748b"}
                      />
                    ))}
                </div>
              </div>

              {/* 상태별 */}
              <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4">
                <h2 className="text-sm font-semibold text-slate-200 mb-4">
                  상태별 사건 수
                </h2>
                <div className="space-y-3">
                  {Object.entries(overview.by_status || {})
                    .sort((a, b) => b[1] - a[1])
                    .map(([key, val]) => (
                      <HBar
                        key={key}
                        label={STATUS_LABELS[key] || key}
                        value={val}
                        max={maxStatusVal}
                        color={STATUS_COLORS[key] || "#94a3b8"}
                      />
                    ))}
                </div>
              </div>

              {/* 읍면동별 */}
              <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4">
                <h2 className="text-sm font-semibold text-slate-200 mb-4">
                  읍면동별 사건 수
                </h2>
                <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                  {Object.entries(overview.by_emd || {})
                    .sort((a, b) => b[1] - a[1])
                    .map(([key, val]) => (
                      <HBar
                        key={key}
                        label={key}
                        value={val}
                        max={maxEmdVal}
                        color="#06b6d4"
                      />
                    ))}
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-8 text-center">
            <p className="text-slate-400 mb-4">분석된 데이터가 없습니다.</p>
            <p className="text-sm text-slate-500 mb-6">
              업로드 페이지에서 파일을 분석해주세요.
            </p>
            <button
              onClick={() => navigate("/disaster-upload")}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg text-sm"
            >
              업로드 페이지로 이동
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
