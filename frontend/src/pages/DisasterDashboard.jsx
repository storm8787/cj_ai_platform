import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { disasterApi } from "../services/api";
import { INCIDENT_TYPE_LABELS, STATUS_LABELS } from "../constants/disaster";
import { useDisasterSession } from "../hooks/useDisasterSession";

// ── 유형 색상 ──────────────────────────────────────────
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

const STATUS_DOT = {
  reported: "bg-red-500",
  in_progress: "bg-amber-400",
  completed: "bg-green-500",
  monitoring: "bg-blue-400",
  no_issue: "bg-slate-400",
  closed: "bg-slate-600",
};

// ── 공통 컴포넌트 ────────────────────────────────────────

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
        <span className="text-slate-300 truncate max-w-[70%]">{label}</span>
        <span className="text-slate-400 shrink-0 ml-1">{value}건</span>
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

// ── 진행중 사건 패널 ─────────────────────────────────────

function ActiveIncidentRow({ incident }) {
  const typeBg = TYPE_BG[incident.incident_type] || "bg-slate-500/20 text-slate-400";
  const statusBg = STATUS_BG[incident.status] || "bg-slate-500/20 text-slate-400";
  const dot = STATUS_DOT[incident.status] || "bg-slate-500";

  const timeStr = (incident.last_update_time || incident.incident_time || "").slice(0, 16).replace("T", " ");

  return (
    <div className="flex items-start gap-3 py-3 border-b border-slate-800 last:border-0">
      {/* 상태 점 */}
      <div className="mt-1.5 shrink-0">
        <span className={`block w-2 h-2 rounded-full ${dot}`} />
      </div>
      <div className="flex-1 min-w-0">
        {/* 배지 */}
        <div className="flex items-center gap-1 flex-wrap mb-1">
          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${statusBg}`}>
            {incident.status_label || STATUS_LABELS[incident.status] || incident.status}
          </span>
          <span className={`text-xs px-1.5 py-0.5 rounded ${typeBg}`}>
            {incident.incident_type_label || INCIDENT_TYPE_LABELS[incident.incident_type] || incident.incident_type}
          </span>
          {incident.emd && (
            <span className="text-xs text-slate-500">{incident.emd}</span>
          )}
        </div>
        {/* 위치·요약 */}
        <p className="text-sm text-white truncate">
          {incident.location_raw || incident.emd || "위치 불명"}
        </p>
        {incident.summary && (
          <p className="text-xs text-slate-500 truncate mt-0.5">{incident.summary}</p>
        )}
      </div>
      {/* 시간 */}
      <div className="shrink-0 text-right">
        <p className="text-xs text-slate-600 whitespace-nowrap">{timeStr}</p>
        {incident.message_count > 0 && (
          <p className="text-xs text-slate-700 mt-0.5">{incident.message_count}건 보고</p>
        )}
      </div>
    </div>
  );
}

function ActiveIncidentPanel({ incidents }) {
  const [expanded, setExpanded] = useState(false);
  const SHOW_LIMIT = 6;
  const visible = expanded ? incidents : incidents.slice(0, SHOW_LIMIT);
  const hasMore = incidents.length > SHOW_LIMIT;

  if (incidents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-40 gap-2">
        <div className="w-10 h-10 rounded-full bg-green-900/40 flex items-center justify-center">
          <span className="text-green-400 text-xl">✓</span>
        </div>
        <p className="text-green-400 text-sm font-medium">현재 진행중 사건 없음</p>
        <p className="text-slate-600 text-xs">모든 사건이 완료 또는 종결되었습니다</p>
      </div>
    );
  }

  return (
    <div>
      <div className={`${expanded ? "max-h-[600px]" : ""} overflow-y-auto`}>
        {visible.map((inc, i) => (
          <ActiveIncidentRow key={inc.id || i} incident={inc} />
        ))}
      </div>
      {hasMore && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-2 w-full text-xs text-slate-500 hover:text-slate-300 py-1.5 border border-slate-800 rounded-lg transition-colors"
        >
          {expanded
            ? "접기"
            : `나머지 ${incidents.length - SHOW_LIMIT}건 더 보기`}
        </button>
      )}
    </div>
  );
}

// ── 읍면동 랭킹 테이블 ────────────────────────────────────

function EmdRankTable({ emdMapData }) {
  const withIncidents = (emdMapData || [])
    .filter((d) => d.count > 0)
    .sort((a, b) => b.count - a.count);

  if (withIncidents.length === 0) {
    return (
      <p className="text-slate-600 text-sm text-center py-8">사건 데이터 없음</p>
    );
  }

  const maxCount = withIncidents[0]?.count || 1;

  return (
    <div className="overflow-y-auto max-h-72">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-slate-900">
          <tr className="text-slate-500 border-b border-slate-800">
            <th className="text-left py-1.5 font-medium">읍면동</th>
            <th className="text-right py-1.5 font-medium pr-2">전체</th>
            <th className="text-right py-1.5 font-medium">진행중</th>
          </tr>
        </thead>
        <tbody>
          {withIncidents.map((d) => {
            const pct = Math.round((d.count / maxCount) * 100);
            const hasActive = d.active_count > 0;
            return (
              <tr
                key={d.emd}
                className={`border-b border-slate-800/50 last:border-0 ${
                  hasActive ? "bg-red-950/20" : ""
                }`}
              >
                <td className="py-2">
                  <div className="flex items-center gap-2">
                    {hasActive && (
                      <span className="block w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
                    )}
                    <span className={hasActive ? "text-white" : "text-slate-400"}>
                      {d.emd}
                    </span>
                  </div>
                  <div className="mt-1 h-1 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: hasActive ? "#ef4444" : "#16a34a",
                      }}
                    />
                  </div>
                </td>
                <td className="text-right pr-2 text-slate-300 font-medium">
                  {d.count}
                </td>
                <td className="text-right">
                  <span
                    className={
                      hasActive
                        ? "text-red-400 font-semibold"
                        : "text-slate-600"
                    }
                  >
                    {d.active_count}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── 완료 사건 간략 목록 ───────────────────────────────────

function DoneIncidentList({ incidents }) {
  if (!incidents || incidents.length === 0) {
    return (
      <p className="text-slate-600 text-sm text-center py-6">완료 사건 없음</p>
    );
  }
  return (
    <div className="space-y-2">
      {incidents.map((inc, i) => (
        <div
          key={inc.id || i}
          className="flex items-start gap-2 py-2 border-b border-slate-800 last:border-0"
        >
          <span
            className={`mt-0.5 text-xs px-1.5 py-0.5 rounded shrink-0 ${
              STATUS_BG[inc.status] || "bg-slate-500/20 text-slate-400"
            }`}
          >
            {inc.status_label || STATUS_LABELS[inc.status]}
          </span>
          <div className="min-w-0">
            <p className="text-xs text-slate-300 truncate">
              {inc.location_raw || inc.emd || "위치 불명"}
            </p>
            <p className="text-xs text-slate-600 mt-0.5">
              {(inc.incident_type_label || inc.incident_type || "")}
              {inc.emd ? ` · ${inc.emd}` : ""}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── 메인 페이지 ──────────────────────────────────────────

export default function DisasterDashboard() {
  const navigate = useNavigate();
  const { uploadId: activeUploadId, fileName: activeFileName } =
    useDisasterSession();

  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!activeUploadId) {
      setOverview(null);
      return;
    }
    setLoading(true);
    disasterApi
      .getOverview(activeUploadId)
      .then((res) => setOverview(res.data))
      .catch(() => setOverview(null))
      .finally(() => setLoading(false));
  }, [activeUploadId]);

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
  const maxStatusVal = Math.max(...Object.values(overview?.by_status || {}), 1);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* 상단 헤더 */}
      <div className="bg-slate-900 border-b border-slate-800 px-6 py-3.5">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold tracking-tight">재난상황 대시보드</h1>
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
            {/* ── Row 1: 요약 카드 5개 ── */}
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

            {/* ── Row 2: 진행중 사건 패널 + 읍면동 현황 ── */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* 진행중·발생 사건 패널 (2/3) */}
              <div className="lg:col-span-2 bg-slate-900 border border-slate-700 rounded-2xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-semibold text-slate-200">
                      진행중·발생 사건
                    </h2>
                    {(overview.active_incidents?.length ?? 0) > 0 && (
                      <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full font-medium">
                        {overview.active_incidents.length}건
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
                      발생
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" />
                      조치중
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-blue-400 inline-block" />
                      모니터링
                    </span>
                  </div>
                </div>
                <ActiveIncidentPanel incidents={overview.active_incidents || []} />
              </div>

              {/* 읍면동별 현황 (1/3) */}
              <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4 flex flex-col">
                <h2 className="text-sm font-semibold text-slate-200 mb-3">
                  읍면동별 현황
                </h2>
                <EmdRankTable emdMapData={overview.emd_map_data || []} />
              </div>
            </div>

            {/* ── Row 3: 유형별 + 상태별 차트 + 완료 사건 ── */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* 유형별 */}
              <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4">
                <h2 className="text-sm font-semibold text-slate-200 mb-4">
                  유형별 사건 수
                </h2>
                <div className="space-y-3">
                  {Object.entries(overview.by_type || {})
                    .sort((a, b) => b[1] - a[1])
                    .map(([type, count]) => (
                      <HBar
                        key={type}
                        label={INCIDENT_TYPE_LABELS[type] || type}
                        value={count}
                        max={maxTypeVal}
                        color={TYPE_COLORS[type]}
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
                    .map(([status, count]) => (
                      <HBar
                        key={status}
                        label={STATUS_LABELS[status] || status}
                        value={count}
                        max={maxStatusVal}
                        color={
                          status === "in_progress"
                            ? "#f59e0b"
                            : status === "reported"
                            ? "#ef4444"
                            : status === "completed"
                            ? "#22c55e"
                            : status === "closed"
                            ? "#64748b"
                            : "#3b82f6"
                        }
                      />
                    ))}
                </div>
              </div>

              {/* 최근 완료·종결 사건 */}
              <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4">
                <h2 className="text-sm font-semibold text-slate-200 mb-3">
                  최근 완료·종결
                </h2>
                <DoneIncidentList incidents={overview.done_incidents || []} />
              </div>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-64">
            <p className="text-slate-500 text-sm">데이터를 불러올 수 없습니다.</p>
          </div>
        )}
      </div>
    </div>
  );
}
