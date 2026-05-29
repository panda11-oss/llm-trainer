import { useState, useEffect } from "react";
import {
  BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";

const API = "http://localhost:8001";

const S = {
  app: {
    minHeight: "100vh",
    background: "#07090f",
    color: "#e2e8f0",
    fontFamily: "'JetBrains Mono', 'Noto Sans JP', monospace",
    position: "relative",
  },
  scanline: {
    position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0,
    backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,170,0.015) 2px, rgba(0,255,170,0.015) 4px)`,
  },
  header: {
    position: "sticky", top: 0, zIndex: 100,
    background: "rgba(7,9,15,0.9)",
    backdropFilter: "blur(20px)",
    borderBottom: "1px solid rgba(0,255,170,0.15)",
    padding: "0 32px",
    display: "flex", alignItems: "center", justifyContent: "space-between",
    height: 60,
  },
  logo: {
    fontSize: 15, fontWeight: 700, letterSpacing: "0.15em",
    color: "#00ffaa",
    display: "flex", alignItems: "center", gap: 10,
  },
  logoIcon: {
    width: 28, height: 28, borderRadius: 6,
    background: "linear-gradient(135deg, #00ffaa, #00aaff)",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 14,
  },
  nav: { display: "flex", gap: 2 },
  navBtn: (active) => ({
    padding: "6px 16px", borderRadius: 6, border: "none",
    background: active ? "rgba(0,255,170,0.12)" : "transparent",
    color: active ? "#00ffaa" : "#475569",
    fontSize: 12, fontWeight: 500, cursor: "pointer",
    borderBottom: active ? "2px solid #00ffaa" : "2px solid transparent",
    transition: "all 0.2s", letterSpacing: "0.05em",
    fontFamily: "'JetBrains Mono', monospace",
  }),
  status: {
    display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: "#475569",
  },
  dot: (color) => ({
    width: 6, height: 6, borderRadius: "50%",
    background: color, boxShadow: `0 0 6px ${color}`,
  }),
  main: {
    position: "relative", zIndex: 1,
    padding: "24px 32px", maxWidth: 1400, margin: "0 auto",
  },
  grid4: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 20 },
  kpi: (accent) => ({
    background: "rgba(255,255,255,0.02)",
    border: `1px solid rgba(${accent},0.2)`,
    borderRadius: 10, padding: "16px 20px",
    position: "relative", overflow: "hidden",
  }),
  kpiAccent: (accent) => ({
    position: "absolute", top: 0, left: 0, right: 0, height: 2,
    background: `linear-gradient(90deg, rgba(${accent},0.8), transparent)`,
  }),
  kpiLabel: {
    fontSize: 10, color: "#475569", letterSpacing: "0.15em",
    textTransform: "uppercase", marginBottom: 6,
  },
  kpiValue: (accent) => ({
    fontSize: 26, fontWeight: 700, color: `rgb(${accent})`, lineHeight: 1,
  }),
  kpiSub: { fontSize: 11, color: "#334155", marginTop: 4 },
  card: {
    background: "rgba(255,255,255,0.02)",
    border: "1px solid rgba(0,255,170,0.08)",
    borderRadius: 10, padding: "18px 20px",
  },
  cardTitle: {
    fontSize: 11, color: "#00ffaa", letterSpacing: "0.15em",
    textTransform: "uppercase", marginBottom: 16,
    display: "flex", alignItems: "center", justifyContent: "space-between",
  },
  sourceRow: (enabled) => ({
    display: "flex", alignItems: "center", gap: 12, padding: "10px 14px",
    background: enabled ? "rgba(0,255,170,0.03)" : "rgba(255,255,255,0.01)",
    border: `1px solid ${enabled ? "rgba(0,255,170,0.12)" : "rgba(255,255,255,0.04)"}`,
    borderRadius: 8, marginBottom: 8, transition: "all 0.2s",
  }),
  logRow: (status) => ({
    display: "flex", alignItems: "flex-start", gap: 12, padding: "8px 12px",
    borderLeft: `2px solid ${status === "success" ? "#00ffaa" : status === "error" ? "#ff4444" : "#ffaa00"}`,
    marginBottom: 6, background: "rgba(255,255,255,0.01)", borderRadius: "0 6px 6px 0",
  }),
  logStatus: (status) => ({
    fontSize: 10, padding: "2px 6px", borderRadius: 4, flexShrink: 0,
    background: status === "success" ? "rgba(0,255,170,0.1)" : status === "error" ? "rgba(255,68,68,0.1)" : "rgba(255,170,0,0.1)",
    color: status === "success" ? "#00ffaa" : status === "error" ? "#ff4444" : "#ffaa00",
    border: `1px solid ${status === "success" ? "rgba(0,255,170,0.2)" : status === "error" ? "rgba(255,68,68,0.2)" : "rgba(255,170,0,0.2)"}`,
  }),
  badge: (color) => ({
    display: "inline-block", fontSize: 9, padding: "1px 6px", borderRadius: 10,
    background: `rgba(${color},0.1)`, color: `rgb(${color})`,
    border: `1px solid rgba(${color},0.2)`, letterSpacing: "0.05em",
  }),
  btn: (variant) => ({
    padding: "7px 16px", borderRadius: 6, cursor: "pointer", fontSize: 11,
    fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.05em",
    background: variant === "primary" ? "rgba(0,255,170,0.12)"
      : variant === "purple" ? "rgba(168,85,247,0.12)"
      : "rgba(255,255,255,0.04)",
    border: `1px solid ${variant === "primary" ? "rgba(0,255,170,0.3)" : variant === "purple" ? "rgba(168,85,247,0.3)" : "rgba(255,255,255,0.08)"}`,
    color: variant === "primary" ? "#00ffaa" : variant === "purple" ? "#a855f7" : "#64748b",
    transition: "all 0.2s",
  }),
  input: {
    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 6, color: "#e2e8f0", padding: "6px 12px", fontSize: 12,
    fontFamily: "'JetBrains Mono', monospace", outline: "none",
  },
  tag: {
    display: "inline-flex", alignItems: "center", gap: 5,
    padding: "3px 10px", borderRadius: 20, fontSize: 11,
    background: "rgba(0,255,170,0.08)", color: "#00ffaa",
    border: "1px solid rgba(0,255,170,0.2)", cursor: "default",
  },
};

// ── タグセット デフォルト値 ──────────────────────────────
const DEFAULT_TAGSETS = [
  {
    id: "general",
    name: "技術全般",
    icon: "🖥",
    subcategories: [
      { id: "g1", name: "インフラ系",                   enabled: true, tags: ["linux", "docker", "bash", "ssh", "systemd"] },
      { id: "g2", name: "開発ツール",                   enabled: true, tags: ["python", "git", "vim", "rust"] },
      { id: "g3", name: "コンテナ/オーケストレーション", enabled: true, tags: ["kubernetes", "terraform"] },
    ],
  },
  {
    id: "study",
    name: "資格勉強",
    icon: "📚",
    subcategories: [
      { id: "s1", name: "サーバー系",     enabled: true,  tags: ["linuc", "lpic", "ccna", "rhcsa", "shell-script", "networking"] },
      { id: "s2", name: "コーディング系", enabled: false, tags: ["algorithm", "atcoder", "paiza", "competitive-programming"] },
      { id: "s3", name: "クラウド系",     enabled: false, tags: ["aws", "gcp", "azure", "terraform"] },
    ],
  },
];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "rgba(7,9,15,0.95)", border: "1px solid rgba(0,255,170,0.2)",
      borderRadius: 6, padding: "8px 12px", fontSize: 11,
    }}>
      <p style={{ color: "#00ffaa", marginBottom: 4 }}>{label}</p>
      {payload.map(p => (
        <p key={p.dataKey} style={{ color: p.color, margin: "2px 0" }}>
          {p.name}: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  );
};

// ── TagsetManager コンポーネント ────────────────────────
function TagsetManager({ tagsets, setTagsets, activeTagsetIds, setActiveTagsetIds }) {
  const [openFolders, setOpenFolders] = useState({ general: true, study: true });
  const [tagInputs, setTagInputs] = useState({});

  const toggleFolder = (id) => setOpenFolders(prev => ({ ...prev, [id]: !prev[id] }));

  const activateTagset = async (id) => {
    try {
      await fetch(`${API}/api/tagsets/${id}/activate`, { method: "PUT" });
    } catch (_) {}
    setActiveTagsetIds(prev =>
      prev.includes(id)
        ? prev.length > 1 ? prev.filter(i => i !== id) : prev
        : [...prev, id]
    );
  };

  const addTag = (subId) => {
    const val = (tagInputs[subId] || "").trim().toLowerCase();
    if (!val) return;
    setTagsets(prev => prev.map(f => ({
      ...f,
      subcategories: f.subcategories.map(s =>
        s.id === subId && !s.tags.includes(val)
          ? { ...s, tags: [...s.tags, val] }
          : s
      ),
    })));
    setTagInputs(prev => ({ ...prev, [subId]: "" }));
  };

  const removeTag = (subId, tag) => {
    setTagsets(prev => prev.map(f => ({
      ...f,
      subcategories: f.subcategories.map(s =>
        s.id === subId ? { ...s, tags: s.tags.filter(t => t !== tag) } : s
      ),
    })));
  };

  const addFolder = () => {
    const name = window.prompt("タグセット名を入力してください");
    if (!name) return;
    const id = "f" + Date.now();
    setTagsets(prev => [...prev, { id, name, icon: "📁", subcategories: [] }]);
    setOpenFolders(prev => ({ ...prev, [id]: true }));
  };

  const toggleSubcategory = (subId) => {
    setTagsets(prev => prev.map(f => ({
      ...f,
      subcategories: f.subcategories.map(s =>
        s.id === subId ? { ...s, enabled: !s.enabled } : s
      ),
    })));
  };

  const addSubcategory = (folderId) => {
    const name = window.prompt("カテゴリ名を入力してください");
    if (!name) return;
    setTagsets(prev => prev.map(f =>
      f.id === folderId
        ? { ...f, subcategories: [...f.subcategories, { id: "sub_" + Date.now(), name, enabled: true, tags: [] }] }
        : f
    ));
  };

  return (
    <div>
      <div style={{ fontSize: 10, color: "#475569", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 10 }}>
        自動収集 タグセット
      </div>

      {tagsets.map(folder => {
        const isActive = activeTagsetIds.includes(folder.id);
        const isOpen = openFolders[folder.id];
        const hasMult = folder.subcategories.length >= 2;
        const onCount = folder.subcategories.filter(s => s.enabled).length;
        const total = folder.subcategories.length;

        return (
          <div key={folder.id} style={{
            background: "rgba(255,255,255,0.02)",
            border: `1px solid ${isActive ? "rgba(168,85,247,0.3)" : "rgba(0,255,170,0.08)"}`,
            borderLeft: isActive ? "3px solid #a855f7" : "1px solid rgba(0,255,170,0.08)",
            borderRadius: 10, marginBottom: 8, overflow: "hidden",
          }}>
            {/* フォルダヘッダー */}
            <div
              onClick={() => toggleFolder(folder.id)}
              style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "12px 16px", cursor: "pointer",
                background: isActive ? "rgba(168,85,247,0.05)" : "transparent",
              }}
            >
              <span style={{ fontSize: 16 }}>{folder.icon}</span>
              <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: isActive ? "#c084fc" : "#e2e8f0" }}>
                {folder.name}
              </span>
              {isActive ? (
                <span style={{
                  fontSize: 10, padding: "2px 8px", borderRadius: 20,
                  background: "rgba(168,85,247,0.15)", color: "#a855f7",
                  border: "1px solid rgba(168,85,247,0.3)",
                }}>✅ 収集中</span>
              ) : (
                <span style={{
                  fontSize: 10, padding: "2px 8px", borderRadius: 20,
                  background: "rgba(255,255,255,0.03)", color: "#475569",
                  border: "1px solid rgba(255,255,255,0.08)",
                }}>
                  {total === 0 ? "カテゴリなし" : hasMult ? `${onCount}/${total} ON` : `${folder.subcategories[0]?.tags.length || 0}タグ`}
                </span>
              )}
              <span style={{ fontSize: 10, color: "#334155", transition: "transform 0.2s", transform: isOpen ? "rotate(90deg)" : "rotate(0deg)" }}>▶</span>
            </div>

            {/* フォルダボディ */}
            {isOpen && (
              <div style={{ borderTop: "1px solid rgba(255,255,255,0.04)", padding: "14px 16px" }}>
                {/* カテゴリ0個のとき */}
                {folder.subcategories.length === 0 && (
                  <div style={{ fontSize: 12, color: "#334155", textAlign: "center", padding: "12px 0" }}>
                    カテゴリを追加してください
                  </div>
                )}

                {folder.subcategories.map((sub, idx) => (
                  <div key={sub.id}>
                    {idx > 0 && <div style={{ borderTop: "1px solid rgba(255,255,255,0.04)", margin: "12px 0" }} />}
                    <div style={{ marginBottom: 10, opacity: sub.enabled ? 1 : 0.45, transition: "opacity 0.2s" }}>
                      <div style={{ fontSize: 11, color: "#64748b", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ flex: 1 }}>{sub.name}</span>
                        {/* カテゴリが2個以上のときだけトグル表示 */}
                        {hasMult && (
                          <button
                            onClick={() => toggleSubcategory(sub.id)}
                            style={{
                              fontSize: 10, padding: "2px 10px", borderRadius: 20, cursor: "pointer",
                              fontFamily: "'JetBrains Mono', monospace",
                              background: sub.enabled ? "rgba(0,255,170,0.1)" : "rgba(255,255,255,0.03)",
                              border: `1px solid ${sub.enabled ? "rgba(0,255,170,0.25)" : "rgba(255,255,255,0.08)"}`,
                              color: sub.enabled ? "#00ffaa" : "#334155",
                              transition: "all 0.2s",
                            }}
                          >
                            {sub.enabled ? "ON" : "OFF"}
                          </button>
                        )}
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
                        {sub.tags.map(tag => (
                          <span key={tag} style={{
                            display: "inline-flex", alignItems: "center", gap: 5,
                            padding: "3px 8px 3px 10px", borderRadius: 20, fontSize: 11,
                            background: "rgba(0,255,170,0.06)", color: "#00ffaa",
                            border: "1px solid rgba(0,255,170,0.15)",
                          }}>
                            {tag}
                            <span
                              onClick={() => removeTag(sub.id, tag)}
                              style={{ fontSize: 13, color: "#334155", cursor: "pointer", lineHeight: 1 }}
                            >×</span>
                          </span>
                        ))}
                      </div>
                      <div style={{ display: "flex", gap: 6 }}>
                        <input
                          style={{ ...S.input, flex: 1, fontSize: 11, padding: "4px 10px" }}
                          placeholder="タグを追加..."
                          value={tagInputs[sub.id] || ""}
                          onChange={e => setTagInputs(prev => ({ ...prev, [sub.id]: e.target.value }))}
                          onKeyDown={e => e.key === "Enter" && addTag(sub.id)}
                        />
                        <button style={{ ...S.btn("primary"), padding: "4px 12px", fontSize: 11 }} onClick={() => addTag(sub.id)}>+ 追加</button>
                      </div>
                    </div>
                  </div>
                ))}

                {/* カテゴリ追加ボタン（常に表示） */}
                <button
                  onClick={() => addSubcategory(folder.id)}
                  style={{
                    width: "100%", padding: "8px", marginTop: folder.subcategories.length > 0 ? 8 : 0,
                    borderRadius: 8, cursor: "pointer", fontSize: 11,
                    fontFamily: "'JetBrains Mono', monospace",
                    background: "transparent",
                    border: "1px dashed rgba(0,255,170,0.15)",
                    color: "#334155", display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                  }}
                >
                  + カテゴリを追加
                </button>

                {/* 切り替えボタン */}
                <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.04)" }}>
                  {isActive ? (
                    <button style={{ ...S.btn("purple"), opacity: 0.6 }} onClick={() => activateTagset(folder.id)}>
                      ✅ 収集中 → 解除する
                    </button>
                  ) : (
                    <button style={S.btn("purple")} onClick={() => activateTagset(folder.id)}>
                      + 収集対象に追加
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* 新規追加 */}
      <button
        onClick={addFolder}
        style={{
          width: "100%", padding: "10px", borderRadius: 10, cursor: "pointer",
          background: "transparent", border: "1px dashed rgba(0,255,170,0.15)",
          color: "#334155", fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
          display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
        }}
      >
        + 新しいタグセットを追加
      </button>
    </div>
  );
}

// ── メインApp ───────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [time, setTime] = useState(new Date());
  const [stats, setStats] = useState({});
  const [sources, setSources] = useState([]);
  const [logs, setLogs] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [collecting, setCollecting] = useState(false);
  const [searching, setSearching] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [keywordCollecting, setKeywordCollecting] = useState(false);
  const [autoTags, setAutoTags] = useState([]);

  // タグセット管理
  const [tagsets, setTagsets] = useState(DEFAULT_TAGSETS);
  const [activeTagsetIds, setActiveTagsetIds] = useState(["general"]);

  // 設定
  const [autoShutdown, setAutoShutdown] = useState(false);
  const [toast, setToast] = useState("");
  const [collectTime, setCollectTime] = useState("09:00");
  const [timezone, setTimezone] = useState("Asia/Tokyo");
  const [retryCount, setRetryCount] = useState("3");
  const [timeoutSec, setTimeoutSec] = useState("30");

  // アクティブなタグセットの全タグ（enabledなカテゴリのみ）
  const activeTags = [...new Set(
    tagsets
      .filter(f => activeTagsetIds.includes(f.id))
      .flatMap(f => f.subcategories.filter(s => s.enabled !== false).flatMap(s => s.tags))
  )] || autoTags;
  const activeTagset = tagsets.find(f => activeTagsetIds.includes(f.id));

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    fetchStats();
    fetchSources();
    fetchTags();
    // タグセットAPIから取得を試みる
    fetchTagsets();
    fetchSettings();
    fetchLogs();
    return () => clearInterval(t);
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API}/api/stats`);
      const data = await res.json();
      setStats(data.stats || {});
    } catch (e) { console.error(e); }
  };

  const fetchSources = async () => {
    try {
      const res = await fetch(`${API}/api/sources`);
      const data = await res.json();
      setSources(data.sources || []);
    } catch (e) { console.error(e); }
  };

  const fetchTags = async () => {
    try {
      const res = await fetch(`${API}/api/tags`);
      const data = await res.json();
      setAutoTags(data.tags || []);
    } catch (e) { console.error(e); }
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${API}/api/logs?limit=200`);
      const data = await res.json();
      setLogs(data.logs || []);
    } catch (e) { console.error(e); }
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API}/api/settings`);
      const data = await res.json();
      setAutoShutdown(data.auto_shutdown || false);
      const h = String(data.collect_hour ?? 9).padStart(2, "0");
      const m = String(data.collect_minute ?? 0).padStart(2, "0");
      setCollectTime(`${h}:${m}`);
      setTimezone(data.timezone || "Asia/Tokyo");
      setRetryCount(String(data.retry_count ?? 3));
      setTimeoutSec(String(data.timeout ?? 30));
    } catch (_) {}
  };

  const fetchTagsets = async () => {
    try {
      const res = await fetch(`${API}/api/tagsets`);
      const data = await res.json();
      if (data.tagsets?.length) {
        setTagsets(data.tagsets);
        setActiveTagsetIds(data.active_ids || ["general"]);
      }
    } catch (_) { /* APIが未実装の場合はデフォルト値を使用 */ }
  };

  const collectAll = async () => {
    setCollecting(true);
    const startTime = new Date().toLocaleTimeString("ja-JP");
    try {
      const res = await fetch(`${API}/api/collect/all`, { method: "POST" });
      const data = await res.json();
      const newLogs = Object.entries(data.results || {}).map(([source, result]) => ({
        id: Date.now() + Math.random(),
        time: startTime, source, status: "success",
        message: `${result.count}件取得 (${result.saved}件保存)`,
      }));
      const errorLogs = Object.entries(data.errors || {}).map(([source, error]) => ({
        id: Date.now() + Math.random(),
        time: startTime, source, status: "error", message: error,
      }));
      setLogs(prev => [...newLogs, ...errorLogs, ...prev].slice(0, 100));
      await fetchStats();
    } catch (e) {
      setLogs(prev => [{ id: Date.now(), time: startTime, source: "system", status: "error", message: e.message }, ...prev]);
    }
    setCollecting(false);
  };

  const collectKeyword = async () => {
    const kw = keyword.trim();
    if (!kw) return;
    setKeywordCollecting(true);
    const startTime = new Date().toLocaleTimeString("ja-JP");
    try {
      const res = await fetch(`${API}/api/collect/keyword`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keyword: kw }),
      });
      const data = await res.json();
      setLogs(prev => [{
        id: Date.now(), time: startTime, source: `🔍 ${kw}`, status: "success",
        message: `合計 ${data.total}件を取得しました`,
      }, ...prev].slice(0, 100));
      setKeyword("");
      await fetchStats();
    } catch (e) {
      setLogs(prev => [{ id: Date.now(), time: startTime, source: `🔍 ${kw}`, status: "error", message: e.message }, ...prev]);
    }
    setKeywordCollecting(false);
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await fetch(`${API}/api/search?q=${encodeURIComponent(searchQuery)}&n=20`);
      const data = await res.json();
      setSearchResults(data.results || []);
    } catch (e) { console.error(e); }
    setSearching(false);
  };

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(""), 2000);
  };

  const updateSetting = async (key, value) => {
    try {
      await fetch(`${API}/api/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [key]: value }),
      });
      showToast("✅ 設定を保存しました");
    } catch (_) {
      showToast("❌ 保存に失敗しました");
    }
  };

  const toggleAutoShutdown = async () => {
    const newVal = !autoShutdown;
    setAutoShutdown(newVal);
    try {
      await fetch(`${API}/api/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auto_shutdown: newVal }),
      });
    } catch (_) {}
  };

  const totalDocs = Object.values(stats).reduce((s, v) => s + v, 0);
  const statsData = Object.entries(stats).map(([name, count]) => ({ name, 件数: count }));

  return (
    <div style={S.app}>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: rgba(0,255,170,0.2); border-radius: 2px; }
        button:hover { filter: brightness(1.15); }
        input:focus { border-color: rgba(0,255,170,0.35) !important; outline: none; }
      `}</style>
      <div style={S.scanline} />

      <header style={S.header}>
        <div style={S.logo}>
          <div style={S.logoIcon}>🧠</div>
          LLM-TRAINER
        </div>
        <nav style={S.nav}>
          {[["dashboard","ダッシュボード"], ["sources","データソース"], ["logs","収集ログ"], ["data","データ閲覧"], ["settings","設定"]].map(([key, label]) => (
            <button key={key} style={S.navBtn(tab === key)} onClick={() => setTab(key)}>{label}</button>
          ))}
        </nav>
        <div style={S.status}>
          <div style={S.dot("#00ffaa")} />
          <span>{time.toLocaleTimeString("ja-JP")}</span>
        </div>
      </header>

      <main style={S.main}>

        {/* ══ DASHBOARD ══ */}
        {tab === "dashboard" && (
          <>
            <div style={S.grid4}>
              {[
                { label: "総ドキュメント数", value: totalDocs.toLocaleString(), unit: "件", accent: "0,255,170", sub: "DB保存済み" },
                { label: "アクティブソース", value: sources.filter(s => s.enabled).length, unit: "個", accent: "0,170,255", sub: `全${sources.length}ソース中` },
                { label: "コレクション数", value: Object.keys(stats).length, unit: "個", accent: "255,170,0", sub: "ChromaDB" },
                { label: "ログ件数", value: logs.length, unit: "件", accent: "168,85,247", sub: "今セッション" },
              ].map((k, i) => (
                <div key={i} style={S.kpi(k.accent)}>
                  <div style={S.kpiAccent(k.accent)} />
                  <div style={S.kpiLabel}>{k.label}</div>
                  <div style={S.kpiValue(k.accent)}>{k.value}<span style={{ fontSize: 13, marginLeft: 4 }}>{k.unit}</span></div>
                  <div style={S.kpiSub}>{k.sub}</div>
                </div>
              ))}
            </div>

            {/* キーワード収集 */}
            <div style={{ ...S.card, marginBottom: 16 }}>
              <div style={S.cardTitle}><span>▸ キーワード収集</span></div>
              <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
                <input
                  style={{ ...S.input, flex: 1 }}
                  placeholder="気になるキーワードを入力（例: rust, kubernetes, neovim）"
                  value={keyword}
                  onChange={e => setKeyword(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && collectKeyword()}
                />
                <button style={S.btn("purple")} onClick={collectKeyword} disabled={keywordCollecting || !keyword.trim()}>
                  {keywordCollecting ? "収集中..." : "▶ 今すぐ収集"}
                </button>
              </div>

              {/* アクティブなタグセット表示 */}
              {activeTags.length > 0 && (
                <div>
                  <div style={{ fontSize: 10, color: "#475569", marginBottom: 6, letterSpacing: "0.1em", display: "flex", alignItems: "center", gap: 8 }}>
                    自動収集タグ (毎日09:00)
                    {tagsets.filter(f => activeTagsetIds.includes(f.id)).map(f => (
                      <span key={f.id} style={{
                        fontSize: 9, padding: "1px 8px", borderRadius: 20,
                        background: "rgba(168,85,247,0.12)", color: "#a855f7",
                        border: "1px solid rgba(168,85,247,0.25)", marginRight: 4,
                      }}>
                        {f.name}
                      </span>
                    ))}
                    <button
                      onClick={() => setTab("settings")}
                      style={{ fontSize: 9, color: "#334155", background: "none", border: "none", cursor: "pointer", fontFamily: "'JetBrains Mono', monospace" }}
                    >
                      変更 →
                    </button>
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {activeTags.map(tag => (
                      <span key={tag} style={S.tag}>{tag}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div style={{ marginBottom: 20 }}>
              <div style={S.card}>
                <div style={S.cardTitle}>
                  <span>▸ ソース別ドキュメント数</span>
                  <button style={S.btn("primary")} onClick={collectAll} disabled={collecting}>
                    {collecting ? "収集中..." : "▶ 全ソース収集"}
                  </button>
                </div>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={statsData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 10, fill: "#334155" }} />
                    <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 11, fill: "#64748b" }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="件数" fill="rgba(0,170,255,0.6)" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {logs.length > 0 && (
              <div style={S.card}>
                <div style={S.cardTitle}><span>▸ 最新ログ</span></div>
                {logs.slice(0, 5).map(log => (
                  <div key={log.id} style={S.logRow(log.status)}>
                    <span style={{ fontSize: 10, color: "#334155", flexShrink: 0 }}>{log.time}</span>
                    <span style={S.logStatus(log.status)}>{log.status}</span>
                    <span style={{ fontSize: 11, color: "#64748b", flexShrink: 0 }}>{log.source}</span>
                    <span style={{ fontSize: 11, color: "#94a3b8" }}>{log.message}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* ══ SOURCES ══ */}
        {tab === "sources" && (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div style={{ fontSize: 11, color: "#00ffaa", letterSpacing: "0.15em", textTransform: "uppercase" }}>▸ データソース ({sources.length}件)</div>
              <button style={S.btn("primary")} onClick={collectAll} disabled={collecting}>
                {collecting ? "収集中..." : "▶ 全ソース収集"}
              </button>
            </div>
            <div style={{ ...S.card, marginBottom: 16 }}>
              <div style={S.cardTitle}><span>▸ キーワード都度収集</span></div>
              <div style={{ fontSize: 11, color: "#475569", marginBottom: 10 }}>
                気になるキーワードを入力すると、全ソースからまとめて収集してDBに追加します。
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  style={{ ...S.input, flex: 1 }}
                  placeholder="例: rust, neovim, kubernetes, tailscale..."
                  value={keyword}
                  onChange={e => setKeyword(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && collectKeyword()}
                />
                <button style={S.btn("purple")} onClick={collectKeyword} disabled={keywordCollecting || !keyword.trim()}>
                  {keywordCollecting ? "収集中..." : "▶ 収集"}
                </button>
              </div>
            </div>
            {sources.map(src => (
              <div key={src.id} style={S.sourceRow(src.enabled)}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: src.enabled ? "#e2e8f0" : "#475569", marginBottom: 2 }}>
                    {src.name}
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <span style={S.badge("0,170,255")}>{src.enabled ? "有効" : "無効"}</span>
                    <span style={{ fontSize: 10, color: "#334155" }}>
                      保存済み: {stats[src.name.toLowerCase().replace(" api", "").replace(" rss", "").replace(" ", "")] || 0}件
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </>
        )}

        {/* ══ LOGS ══ */}
        {tab === "logs" && (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div style={{ fontSize: 11, color: "#00ffaa", letterSpacing: "0.15em", textTransform: "uppercase" }}>▸ 収集ログ ({logs.length}件)</div>
              <div style={{ display: "flex", gap: 8 }}>
                <button style={S.btn("primary")} onClick={collectAll} disabled={collecting}>
                  {collecting ? "収集中..." : "▶ 収集実行"}
                </button>
                <button style={S.btn("default")} onClick={async () => {
                  await fetch(`${API}/api/logs`, { method: "DELETE" });
                  setLogs([]);
                }}>クリア</button>
              </div>
            </div>
            <div style={S.card}>
              {logs.length === 0 ? (
                <div style={{ fontSize: 12, color: "#334155", textAlign: "center", padding: 40 }}>
                  ログがありません。「収集実行」ボタンを押してください。
                </div>
              ) : (
                logs.map(log => (
                  <div key={log.id} style={S.logRow(log.status)}>
                    <span style={{ fontSize: 10, color: "#334155", flexShrink: 0 }}>{log.time}</span>
                    <span style={S.logStatus(log.status)}>{log.status}</span>
                    <span style={{ fontSize: 11, color: "#64748b", flexShrink: 0 }}>{log.source}</span>
                    <span style={{ fontSize: 11, color: log.status === "error" ? "#ff6666" : "#94a3b8" }}>{log.message}</span>
                  </div>
                ))
              )}
            </div>
          </>
        )}

        {/* ══ DATA ══ */}
        {tab === "data" && (
          <>
            <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
              <input
                style={{ ...S.input, flex: 1 }}
                placeholder="検索キーワードを入力（例: Linux, Python, Docker）"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSearch()}
              />
              <button style={S.btn("primary")} onClick={handleSearch} disabled={searching}>
                {searching ? "検索中..." : "検索"}
              </button>
            </div>
            <div style={S.card}>
              {searchResults.length === 0 ? (
                <div style={{ fontSize: 12, color: "#334155", textAlign: "center", padding: 40 }}>
                  キーワードを入力して検索してください
                </div>
              ) : (
                searchResults.map((item, i) => (
                  <div key={i} style={{ padding: "12px 0", borderBottom: "1px solid rgba(255,255,255,0.04)", display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ flex: 1 }}>
                      <a href={item.url} target="_blank" rel="noreferrer" style={{ fontSize: 13, color: "#e2e8f0", textDecoration: "none" }}>
                        {item.title}
                      </a>
                      <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                        <span style={S.badge("0,255,170")}>{item.source}</span>
                        <span style={{ fontSize: 10, color: "#334155" }}>{item.created_at?.slice(0, 10)}</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </>
        )}

        {/* ══ SETTINGS ══ */}
        {tab === "settings" && (
          <>
            <div style={{ fontSize: 11, color: "#00ffaa", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 16 }}>▸ 設定</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>

              <div style={S.card}>
                <div style={{ fontSize: 12, color: "#00ffaa", marginBottom: 16 }}>スケジュール設定</div>
                {[
                  { label: "取得時刻", value: collectTime, onChange: (v) => { setCollectTime(v); const [h,m] = v.split(":"); const hour = parseInt(h); const min = parseInt(m); if (!isNaN(hour) && !isNaN(min) && hour >= 0 && hour <= 23 && min >= 0 && min <= 59) { updateSetting("collect_hour", hour); updateSetting("collect_minute", min); } }, placeholder: "09:00" },
                  { label: "タイムゾーン", value: timezone, onChange: (v) => { setTimezone(v); updateSetting("timezone", v); }, placeholder: "Asia/Tokyo" },
                  { label: "リトライ回数", value: retryCount, onChange: (v) => { setRetryCount(v); updateSetting("retry_count", parseInt(v)); }, placeholder: "3" },
                  { label: "タイムアウト(秒)", value: timeoutSec, onChange: (v) => { setTimeoutSec(v); updateSetting("timeout", parseInt(v)); }, placeholder: "30" },
                ].map((item, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                    <span style={{ fontSize: 12, color: "#64748b" }}>{item.label}</span>
                    <input
                      value={item.value}
                      onChange={e => item.onChange(e.target.value)}
                      onBlur={e => item.onChange(e.target.value)}
                      placeholder={item.placeholder}
                      style={{ ...S.input, width: 120, textAlign: "right" }}
                    />
                  </div>
                ))}
              </div>

              <div style={S.card}>
                <div style={{ fontSize: 12, color: "#00ffaa", marginBottom: 16 }}>DB設定</div>
                {[
                  { label: "DBタイプ", value: "ChromaDB" },
                  { label: "保存先", value: "D:\\develop\\data" },
                  { label: "総件数", value: totalDocs.toLocaleString() },
                  { label: "コレクション数", value: Object.keys(stats).length },
                ].map((item, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                    <span style={{ fontSize: 12, color: "#64748b" }}>{item.label}</span>
                    <span style={{ fontSize: 12, color: "#e2e8f0" }}>{item.value}</span>
                  </div>
                ))}
              </div>

              {/* 収集後自動シャットダウン */}
              <div style={{ gridColumn: "1 / -1", ...S.card }}>
                <div style={{ fontSize: 12, color: "#00ffaa", marginBottom: 16 }}>収集後自動シャットダウン</div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontSize: 13, color: "#e2e8f0", marginBottom: 4 }}>定期収集完了後にPCをシャットダウン</div>
                    <div style={{ fontSize: 11, color: "#475569" }}>帰省中など離席時にONにすると収集完了後に自動でPCがOFFになります</div>
                  </div>
                  <button
                    onClick={toggleAutoShutdown}
                    style={{
                      padding: "6px 20px", borderRadius: 20, cursor: "pointer",
                      fontFamily: "'JetBrains Mono', monospace", fontSize: 12,
                      background: autoShutdown ? "rgba(255,68,68,0.12)" : "rgba(255,255,255,0.04)",
                      border: `1px solid ${autoShutdown ? "rgba(255,68,68,0.3)" : "rgba(255,255,255,0.08)"}`,
                      color: autoShutdown ? "#ff6666" : "#475569",
                      transition: "all 0.2s", flexShrink: 0, marginLeft: 16,
                    }}
                  >
                    {autoShutdown ? "ON (収集後シャットダウン)" : "OFF"}
                  </button>
                </div>
              </div>

              {/* タグセット管理 - 2カラムにまたがる */}
              <div style={{ gridColumn: "1 / -1", ...S.card }}>
                <div style={{ fontSize: 12, color: "#00ffaa", marginBottom: 16 }}>タグセット管理</div>
                <TagsetManager
                  tagsets={tagsets}
                  setTagsets={setTagsets}
                  activeTagsetIds={activeTagsetIds}
                  setActiveTagsetIds={setActiveTagsetIds}
                />
              </div>

            </div>
          </>
        )}

      </main>

      {toast && (
        <div style={{
          position: "fixed", bottom: 24, left: "50%", transform: "translateX(-50%)",
          background: "rgba(7,9,15,0.95)", border: "1px solid rgba(0,255,170,0.2)",
          borderRadius: 8, padding: "8px 20px", fontSize: 13, color: "#e2e8f0",
          boxShadow: "0 2px 12px rgba(0,0,0,0.3)", zIndex: 9999, whiteSpace: "nowrap",
        }}>
          {toast}
        </div>
      )}
    </div>
  );
}