import { useState, useEffect, useCallback } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "";

function getToken() {
  try {
    const raw = localStorage.getItem("auth_token");
    if (!raw) return "";
    const parsed = JSON.parse(raw);
    return parsed?.access_token || raw;
  } catch {
    return localStorage.getItem("auth_token") || "";
  }
}

async function api(path, options = {}) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Error ${res.status}`);
  }
  return res.json();
}

// ─── 메인 컴포넌트 ───
export default function PromptManager() {
  const [features, setFeatures] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [editingPrompt, setEditingPrompt] = useState(null);
  const [editContent, setEditContent] = useState("");
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  const showToast = (message, type = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  // 데이터 로드
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [featRes, promptRes] = await Promise.all([
        api("/api/prompts/features"),
        api("/api/prompts/list"),
      ]);
      setFeatures(featRes.features || []);
      setPrompts(promptRes.prompts || []);
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // 필터링된 프롬프트
  const filteredPrompts = prompts.filter((p) => {
    const matchFeature = !selectedFeature || p.feature === selectedFeature;
    const matchSearch = !searchQuery || 
      p.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.prompt_key.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.feature_name || "").includes(searchQuery);
    return matchFeature && matchSearch;
  });

  // 기능별 그룹핑
  const grouped = {};
  filteredPrompts.forEach((p) => {
    if (!grouped[p.feature]) grouped[p.feature] = [];
    grouped[p.feature].push(p);
  });

  // 편집 시작
  const startEdit = (prompt) => {
    setEditingPrompt(prompt);
    setEditContent(prompt.content);
    setShowHistory(false);
    setHistory([]);
  };

  // 저장
  const savePrompt = async () => {
    if (!editingPrompt) return;
    setSaving(true);
    try {
      await api("/api/prompts/update", {
        method: "PUT",
        body: JSON.stringify({
          feature: editingPrompt.feature,
          prompt_key: editingPrompt.prompt_key,
          content: editContent,
        }),
      });
      showToast("프롬프트가 저장되었습니다");
      setEditingPrompt(null);
      await loadData();
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      setSaving(false);
    }
  };

  // 이력 조회
  const loadHistory = async () => {
    if (!editingPrompt) return;
    try {
      const res = await api("/api/prompts/history", {
        method: "POST",
        body: JSON.stringify({
          feature: editingPrompt.feature,
          prompt_key: editingPrompt.prompt_key,
          limit: 10,
        }),
      });
      setHistory(res.history || []);
      setShowHistory(true);
    } catch (e) {
      showToast(e.message, "error");
    }
  };

  // 캐시 갱신
  const refreshCache = async () => {
    try {
      await api("/api/prompts/refresh-cache", { method: "POST" });
      showToast("서버 캐시가 갱신되었습니다");
    } catch (e) {
      showToast(e.message, "error");
    }
  };

  if (loading) {
    return (
      <div style={styles.loadingWrap}>
        <div style={styles.spinner} />
        <p style={styles.loadingText}>프롬프트 로딩 중...</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* 토스트 */}
      {toast && (
        <div style={{
          ...styles.toast,
          background: toast.type === "error" ? "#ef4444" : "#10b981",
        }}>
          {toast.message}
        </div>
      )}

      {/* 헤더 */}
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>프롬프트 관리</h1>
          <p style={styles.subtitle}>
            {prompts.length}개 프롬프트 · {features.length}개 기능
          </p>
        </div>
        <button onClick={refreshCache} style={styles.refreshBtn}>
          캐시 갱신
        </button>
      </div>

      {/* 검색 + 필터 */}
      <div style={styles.filterBar}>
        <input
          type="text"
          placeholder="프롬프트 검색..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={styles.searchInput}
        />
        <div style={styles.featureTabs}>
          <button
            onClick={() => setSelectedFeature(null)}
            style={selectedFeature === null ? styles.tabActive : styles.tab}
          >
            전체
          </button>
          {features.map((f) => (
            <button
              key={f.id}
              onClick={() => setSelectedFeature(f.id)}
              style={selectedFeature === f.id ? styles.tabActive : styles.tab}
            >
              {f.icon} {f.name}
            </button>
          ))}
        </div>
      </div>

      {/* 메인 영역 */}
      <div style={styles.mainArea}>
        {/* 왼쪽: 프롬프트 목록 */}
        <div style={styles.listPanel}>
          {Object.entries(grouped).map(([feature, items]) => {
            const meta = features.find((f) => f.id === feature) || {};
            return (
              <div key={feature} style={styles.featureGroup}>
                <h3 style={styles.groupTitle}>
                  {meta.icon || "📄"} {meta.name || feature}
                  <span style={styles.badge}>{items.length}</span>
                </h3>
                {items.map((p) => (
                  <div
                    key={`${p.feature}-${p.prompt_key}`}
                    onClick={() => startEdit(p)}
                    style={{
                      ...styles.promptCard,
                      ...(editingPrompt?.id === p.id ? styles.promptCardActive : {}),
                    }}
                  >
                    <div style={styles.promptKey}>{p.prompt_key}</div>
                    <div style={styles.promptPreview}>
                      {p.content.slice(0, 80)}...
                    </div>
                    <div style={styles.promptMeta}>
                      {p.content.length.toLocaleString()}자 · {new Date(p.updated_at).toLocaleDateString("ko-KR")}
                    </div>
                  </div>
                ))}
              </div>
            );
          })}
          {filteredPrompts.length === 0 && (
            <p style={styles.emptyText}>일치하는 프롬프트가 없습니다</p>
          )}
        </div>

        {/* 오른쪽: 편집 패널 */}
        <div style={styles.editPanel}>
          {editingPrompt ? (
            <>
              <div style={styles.editHeader}>
                <div>
                  <span style={styles.editFeature}>
                    {editingPrompt.feature_icon} {editingPrompt.feature_name}
                  </span>
                  <h2 style={styles.editTitle}>{editingPrompt.prompt_key}</h2>
                </div>
                <div style={styles.editActions}>
                  <button onClick={loadHistory} style={styles.historyBtn}>
                    변경 이력
                  </button>
                  <button onClick={() => setEditingPrompt(null)} style={styles.cancelBtn}>
                    취소
                  </button>
                  <button
                    onClick={savePrompt}
                    disabled={saving || editContent === editingPrompt.content}
                    style={{
                      ...styles.saveBtn,
                      opacity: saving || editContent === editingPrompt.content ? 0.5 : 1,
                    }}
                  >
                    {saving ? "저장 중..." : "저장"}
                  </button>
                </div>
              </div>

              <div style={styles.editorInfo}>
                <span>{editContent.length.toLocaleString()}자</span>
                {editContent !== editingPrompt.content && (
                  <span style={styles.changedBadge}>수정됨</span>
                )}
              </div>

              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                style={styles.textarea}
                spellCheck={false}
              />

              {/* 변경 이력 */}
              {showHistory && history.length > 0 && (
                <div style={styles.historyPanel}>
                  <h3 style={styles.historyTitle}>변경 이력</h3>
                  {history.map((h, i) => (
                    <div key={i} style={styles.historyItem}>
                      <div style={styles.historyMeta}>
                        {new Date(h.changed_at).toLocaleString("ko-KR")}
                        {h.changed_by && ` · ${h.changed_by}`}
                      </div>
                      <button
                        onClick={() => setEditContent(h.old_content)}
                        style={styles.restoreBtn}
                      >
                        이 버전으로 복원
                      </button>
                    </div>
                  ))}
                </div>
              )}
              {showHistory && history.length === 0 && (
                <p style={styles.emptyText}>변경 이력이 없습니다</p>
              )}
            </>
          ) : (
            <div style={styles.emptyEdit}>
              <p style={{ fontSize: 48 }}>📝</p>
              <p style={styles.emptyEditText}>
                왼쪽에서 프롬프트를 선택하세요
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── 스타일 ───
const styles = {
  container: {
    maxWidth: 1400,
    margin: "0 auto",
    padding: "24px",
    fontFamily: "'Pretendard', -apple-system, sans-serif",
  },
  loadingWrap: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "60vh" },
  spinner: { width: 40, height: 40, border: "3px solid #e5e7eb", borderTop: "3px solid #3b82f6", borderRadius: "50%", animation: "spin 0.8s linear infinite" },
  loadingText: { marginTop: 16, color: "#6b7280" },
  toast: { position: "fixed", top: 24, right: 24, padding: "12px 24px", borderRadius: 8, color: "#fff", fontSize: 14, fontWeight: 500, zIndex: 9999, boxShadow: "0 4px 12px rgba(0,0,0,0.15)" },

  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 },
  title: { fontSize: 24, fontWeight: 700, color: "#111827", margin: 0 },
  subtitle: { fontSize: 14, color: "#6b7280", marginTop: 4 },
  refreshBtn: { padding: "8px 16px", background: "#f3f4f6", border: "1px solid #d1d5db", borderRadius: 8, cursor: "pointer", fontSize: 13, fontWeight: 500 },

  filterBar: { marginBottom: 20 },
  searchInput: { width: "100%", padding: "10px 14px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 14, marginBottom: 12, boxSizing: "border-box", outline: "none" },
  featureTabs: { display: "flex", gap: 6, flexWrap: "wrap" },
  tab: { padding: "6px 12px", background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 6, cursor: "pointer", fontSize: 12, fontWeight: 500, color: "#374151" },
  tabActive: { padding: "6px 12px", background: "#3b82f6", border: "1px solid #3b82f6", borderRadius: 6, cursor: "pointer", fontSize: 12, fontWeight: 600, color: "#fff" },

  mainArea: { display: "flex", gap: 20, minHeight: "65vh" },

  listPanel: { width: 360, minWidth: 360, overflowY: "auto", maxHeight: "70vh", paddingRight: 8 },
  featureGroup: { marginBottom: 20 },
  groupTitle: { fontSize: 14, fontWeight: 600, color: "#374151", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 },
  badge: { background: "#e5e7eb", color: "#6b7280", fontSize: 11, fontWeight: 600, padding: "2px 7px", borderRadius: 10 },
  promptCard: { padding: "10px 12px", background: "#fff", border: "1px solid #e5e7eb", borderRadius: 8, marginBottom: 6, cursor: "pointer", transition: "all 0.15s" },
  promptCardActive: { borderColor: "#3b82f6", background: "#eff6ff", boxShadow: "0 0 0 2px rgba(59,130,246,0.15)" },
  promptKey: { fontSize: 13, fontWeight: 600, color: "#111827", marginBottom: 4 },
  promptPreview: { fontSize: 12, color: "#6b7280", lineHeight: 1.4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  promptMeta: { fontSize: 11, color: "#9ca3af", marginTop: 4 },

  editPanel: { flex: 1, background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12, padding: 20, display: "flex", flexDirection: "column" },
  editHeader: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 },
  editFeature: { fontSize: 12, color: "#6b7280", fontWeight: 500 },
  editTitle: { fontSize: 18, fontWeight: 700, color: "#111827", margin: "4px 0 0" },
  editActions: { display: "flex", gap: 8 },
  historyBtn: { padding: "6px 14px", background: "#f3f4f6", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer", fontSize: 12, fontWeight: 500 },
  cancelBtn: { padding: "6px 14px", background: "#fff", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer", fontSize: 12, fontWeight: 500 },
  saveBtn: { padding: "6px 14px", background: "#3b82f6", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 12, fontWeight: 600, color: "#fff" },

  editorInfo: { display: "flex", gap: 8, alignItems: "center", fontSize: 12, color: "#9ca3af", marginBottom: 8 },
  changedBadge: { background: "#fef3c7", color: "#92400e", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  textarea: { flex: 1, minHeight: 400, padding: 14, border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 13, fontFamily: "'JetBrains Mono', 'D2Coding', monospace", lineHeight: 1.6, resize: "vertical", outline: "none", whiteSpace: "pre-wrap", boxSizing: "border-box" },

  historyPanel: { marginTop: 16, padding: 12, background: "#f9fafb", borderRadius: 8, maxHeight: 200, overflowY: "auto" },
  historyTitle: { fontSize: 13, fontWeight: 600, margin: "0 0 8px", color: "#374151" },
  historyItem: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid #e5e7eb" },
  historyMeta: { fontSize: 12, color: "#6b7280" },
  restoreBtn: { padding: "4px 10px", background: "#fff", border: "1px solid #d1d5db", borderRadius: 4, cursor: "pointer", fontSize: 11, fontWeight: 500 },

  emptyEdit: { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" },
  emptyEditText: { color: "#9ca3af", fontSize: 15, marginTop: 8 },
  emptyText: { color: "#9ca3af", fontSize: 13, textAlign: "center", padding: 20 },
};