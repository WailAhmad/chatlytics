"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Language } from "@/lib/i18n";
import { askQuestion, fetchStats, uploadDataset, resetSession, clearDataset, ApiResponse, listTables, connectDatabase } from "@/lib/api";
import { ActionZone, ChatTurn } from "@/components/ActionZone";
import { InsightZone } from "@/components/InsightZone";
import { UploadCloud, Loader2, Server, BrainCircuit, Code2, CheckCircle2, MessageSquare, Send, Lock, Database, ChevronDown, Plug, TableProperties, FileSpreadsheet, Shield, Key } from "lucide-react";
import { NetworkCanvas } from "@/components/NetworkCanvas";

function generateId() {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

export default function Dashboard() {
  const [lang, setLang] = useState<Language>("en");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [stats, setStats] = useState<any>(null);

  // Session state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatTurn[]>([]);
  const [latestResponse, setLatestResponse] = useState<{ status: number; data: ApiResponse } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Database connection state
  const [dataTab, setDataTab] = useState<"csv" | "database">("csv");
  const [dbType, setDbType] = useState("mysql");
  const [dbHost, setDbHost] = useState("localhost");
  const [dbPort, setDbPort] = useState("3306");
  const [dbName, setDbName] = useState("");
  const [dbUser, setDbUser] = useState("");
  const [dbPass, setDbPass] = useState("");
  const [dbTables, setDbTables] = useState<string[]>([]);
  const [dbSelectedTable, setDbSelectedTable] = useState("");
  const [dbConnecting, setDbConnecting] = useState(false);
  const [dbLoading, setDbLoading] = useState(false);
  const [dbError, setDbError] = useState("");
  const [dbSSL, setDbSSL] = useState(false);
  const [dbExtra, setDbExtra] = useState(""); // SID, auth source, schema, etc.
  const [hintIndex, setHintIndex] = useState(0);
  const [dbHintIndex, setDbHintIndex] = useState(0);

  const isAr = lang === "ar";

  useEffect(() => {
    fetchStats().then(setStats);
  }, []);

  useEffect(() => {
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);

  // Auto-rotate upload hints
  useEffect(() => {
    const timer = setInterval(() => setHintIndex(i => (i + 1) % 4), 3500);
    return () => clearInterval(timer);
  }, []);

  // Auto-rotate database hints
  useEffect(() => {
    const timer = setInterval(() => setDbHintIndex(i => (i + 1) % 4), 4000);
    return () => clearInterval(timer);
  }, []);

  const handleAsk = useCallback(async (overrideQuestion?: string) => {
    const q = (overrideQuestion || question).trim();
    if (!q) return;

    setLoading(true);

    // Use existing session or let backend create one
    const currentSession = sessionId;

    // Add user message immediately
    const userTurnId = generateId();
    setChatHistory(prev => [...prev, {
      id: userTurnId,
      role: "user",
      content: q,
      timestamp: Date.now(),
    }]);

    // Clear input
    if (!overrideQuestion) setQuestion("");

    const res = await askQuestion(q, lang, currentSession || undefined);

    // Capture session_id from response
    const newSessionId = res.data?.session_id || currentSession;
    if (newSessionId && !currentSession) {
      setSessionId(newSessionId);
    }

    // Add assistant message
    const assistantTurnId = generateId();
    const humanized = res.data?.humanized_chat_answer || "";
    const headline = res.data?.answer?.headline || res.data?.answer?.summary || "";
    const summary = res.data?.answer?.summary || "";
    const assistantContent = humanized || headline || summary || (res.status !== 200 ? (res.data?.detail || "Error") : "Analysis complete.");

    setChatHistory(prev => [...prev, {
      id: assistantTurnId,
      role: "assistant",
      content: assistantContent,
      response: res,
      timestamp: Date.now(),
    }]);

    setLatestResponse(res);
    setLoading(false);
  }, [question, lang, sessionId]);

  const handleReset = useCallback(async () => {
    if (sessionId) {
      await resetSession(sessionId);
    }
    setSessionId(null);
    setChatHistory([]);
    setLatestResponse(null);
    setQuestion("");
  }, [sessionId]);

  const handleFollowUp = useCallback((q: string) => {
    setQuestion(q);
    // Auto-send
    handleAsk(q);
  }, [handleAsk]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setLatestResponse(null);
    setChatHistory([]);
    setSessionId(null);
    setQuestion("");
    const res = await uploadDataset(file);
    if (res.status === 200 && res.data?.profile) {
      setStats(res.data.profile);
    } else {
      console.error("Upload failed with response:", res);
      alert(`Failed to upload and profile dataset. Error: ${res.data?.detail || "Unknown error"}`);
    }
    setUploading(false);
  };

  const handleClearDataset = async () => {
    await clearDataset();
    if (sessionId) await resetSession(sessionId);
    setStats(null);
    setSessionId(null);
    setChatHistory([]);
    setLatestResponse(null);
    setQuestion("");
  };

  return (
    <div dir={isAr ? "rtl" : "ltr"} className={`h-screen bg-[#F8FAFC] flex flex-col overflow-hidden ${isAr ? 'font-[var(--font-tajawal)]' : 'font-sans'}`}>
      {/* Top Bar */}
      <div className="flex-shrink-0 flex items-center justify-between px-5 py-3 border-b border-[#E2E8F0] bg-white">
        {/* Branding */}
        <div className="flex items-center gap-3">
          <img src="/chatlytics-logo.png" alt="Chatlytics" className="h-10 w-auto object-contain" />
          <div className="flex flex-col">
            <span className="text-[16px] font-black text-[#0A0A0F] tracking-tight leading-none">CHAT<span className="text-[#0EA5E9]">LYTICS</span></span>
            <span className="text-[10px] font-medium text-[#64748B] tracking-wide">{lang === "ar" ? "تحليلات المحادثات بالذكاء الاصطناعي" : "AI-Powered Conversation Analytics"}</span>
          </div>
        </div>
        <div className="flex bg-[#F1F5F9] rounded-lg p-0.5 border border-[#E2E8F0]">
          <button
            onClick={() => setLang("en")}
            className={`px-4 py-1 text-xs font-semibold rounded-md transition-all ${lang === "en" ? "bg-white text-[#0A0A0F] shadow-sm border-b-2 border-[#0EA5E9]" : "text-[#64748B]"}`}
          >
            EN
          </button>
          <button
            onClick={() => setLang("ar")}
            className={`px-4 py-1 text-xs font-semibold rounded-md transition-all ${lang === "ar" ? "bg-white text-[#0A0A0F] shadow-sm border-b-2 border-[#0EA5E9]" : "text-[#64748B]"}`}
          >
            عربي
          </button>
        </div>
      </div>

      {/* Main Area */}
      {!stats ? (
        /* ═══════════════════════════════════════════════════════════
           PREMIUM LANDING — sleek mind-map hero + glowing upload
           ═══════════════════════════════════════════════════════════ */
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-0 relative">

          {/* ── Nav circles ── */}
          <div className="nav-circle absolute top-5 left-5 z-50">N</div>
          <div className="nav-circle absolute bottom-5 left-5 z-50">N</div>

          {/* ══ LEFT: Branded Hero ══ */}
          <div className="w-full lg:w-[68%] flex flex-col justify-center items-center p-8 lg:p-14 min-h-0 bg-white relative overflow-hidden z-10">

            {/* Dynamic animated network background */}
            <NetworkCanvas />

            {/* Floating keyword labels */}
            <span className="floating-label fl-1" style={{ top: '8%', left: '8%' }}>Reasoning</span>
            <span className="floating-label fl-2" style={{ top: '12%', left: '38%' }}>Intelligence</span>
            <span className="floating-label fl-3" style={{ top: '16%', right: '6%' }}>Determinism</span>
            <span className="floating-label fl-4" style={{ bottom: '20%', left: '4%' }}>Reasoning</span>
            <span className="floating-label fl-5" style={{ bottom: '6%', right: '4%' }}>Determinism</span>
            <span className="floating-label fl-6" style={{ top: '48%', left: '1%' }}>Intent Recognition</span>
            <span className="floating-label fl-7" style={{ bottom: '32%', right: '1%' }}>Customer Journey Mapping</span>
            <span className="floating-label fl-8" style={{ top: '42%', right: '12%' }}>Stream Analysis</span>

            {/* ── Hero content ── */}
            <div className="max-w-xl mx-auto w-full relative z-10 flex flex-col items-center text-center">

              {/* Logo — frameless, augmented, floating with blue glow */}
              <div className="mb-6 landing-fade-1 hero-logo-float">
                <img
                  src="/chatlytics-logo.png"
                  alt="Chatlytics"
                  className="w-[320px] h-auto object-contain logo-glow-pulse"
                  onError={(e) => { e.currentTarget.style.display='none'; }}
                />
              </div>

              <h1 className="text-3xl lg:text-[2.6rem] font-extrabold text-[#0A0A0F] mb-3 tracking-tight leading-tight landing-fade-2">
                {lang === "ar" ? "مساعد تحليل البيانات" : "Data Analytics Copilot"}
              </h1>

              <p className="text-base lg:text-[1.05rem] text-[#64748B] leading-relaxed mb-10 max-w-md landing-fade-3">
                {lang === "ar" ? "رؤى مدعومة بالذكاء الاصطناعي مع تحقق حتمي عبر بايثون." : "Schema-driven AI Insights with deterministic Python verification."}
              </p>

              {/* Capability Badges — 2x2 */}
              <div className="grid grid-cols-2 gap-4 w-full max-w-lg landing-fade-4">
                {/* API Connected */}
                <div className="capability-badge flex items-center gap-4 bg-gradient-to-br from-sky-50/60 to-white rounded-xl p-4.5 border border-sky-100/80 shadow-[0_0_30px_rgba(14,165,233,0.08)]">
                  <div className="bg-gradient-to-br from-[#1E293B] to-[#334155] text-[#38BDF8] p-3 rounded-2xl shrink-0 shadow-[0_0_16px_rgba(14,165,233,0.25),inset_0_1px_0_rgba(255,255,255,0.1)] border border-[#0EA5E9]/20">
                    <Server className="w-6 h-6" />
                  </div>
                  <div className="flex flex-col text-left">
                    <span className="text-[15px] font-bold text-[#0A0A0F]">{lang === "ar" ? "متصل بالـ API" : "API Connected"}</span>
                    <span className="text-[12px] text-[#64748B] font-medium">{lang === "ar" ? "متصل بالخادم النشط" : "Live server link"}</span>
                  </div>
                </div>

                {/* LLM Enabled */}
                <div className="capability-badge flex items-center gap-4 bg-gradient-to-br from-sky-50/60 to-white rounded-xl p-4.5 border border-sky-100/80 shadow-[0_0_30px_rgba(14,165,233,0.08)]">
                  <div className="bg-gradient-to-br from-[#1E293B] to-[#334155] text-[#38BDF8] p-3 rounded-2xl shrink-0 shadow-[0_0_16px_rgba(14,165,233,0.25),inset_0_1px_0_rgba(255,255,255,0.1)] border border-[#0EA5E9]/20">
                    <BrainCircuit className="w-6 h-6" />
                  </div>
                  <div className="flex flex-col text-left">
                    <span className="text-[15px] font-bold text-[#0A0A0F]">{lang === "ar" ? "مدعوم بنماذج لغوية" : "LLM Enabled"}</span>
                    <span className="text-[12px] text-[#64748B] font-medium">{lang === "ar" ? "فهم سياقي ذكي" : "Semantic understanding"}</span>
                  </div>
                </div>

                {/* Python Verified */}
                <div className="capability-badge flex items-center gap-4 bg-gradient-to-br from-sky-50/60 to-white rounded-xl p-4.5 border border-sky-100/80 shadow-[0_0_30px_rgba(14,165,233,0.08)]">
                  <div className="bg-gradient-to-br from-[#1E293B] to-[#334155] text-[#38BDF8] p-3 rounded-2xl shrink-0 shadow-[0_0_16px_rgba(14,165,233,0.25),inset_0_1px_0_rgba(255,255,255,0.1)] border border-[#0EA5E9]/20">
                    <Code2 className="w-6 h-6" />
                  </div>
                  <div className="flex flex-col text-left">
                    <span className="text-[15px] font-bold text-[#0A0A0F]">{lang === "ar" ? "محقق ببايثون" : "Python Verified"}</span>
                    <span className="text-[12px] text-[#64748B] font-medium">{lang === "ar" ? "تنفيذ حتمي للأكواد" : "Code execution"}</span>
                  </div>
                </div>

                {/* Deterministic */}
                <div className="capability-badge flex items-center gap-4 bg-gradient-to-br from-sky-50/60 to-white rounded-xl p-4.5 border border-sky-100/80 shadow-[0_0_30px_rgba(14,165,233,0.08)]">
                  <div className="bg-gradient-to-br from-[#1E293B] to-[#334155] text-[#38BDF8] p-3 rounded-2xl shrink-0 shadow-[0_0_16px_rgba(14,165,233,0.25),inset_0_1px_0_rgba(255,255,255,0.1)] border border-[#0EA5E9]/20">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <div className="flex flex-col text-left">
                    <span className="text-[15px] font-bold text-[#0A0A0F]">{lang === "ar" ? "تحليل حتمي" : "Deterministic"}</span>
                    <span className="text-[12px] text-[#64748B] font-medium">{lang === "ar" ? "دقة بيانات مضمونة" : "Guaranteed accuracy"}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ══ RIGHT: Data Source Panel ══ */}
          <div className="w-full lg:w-[32%] flex flex-col justify-stretch items-stretch p-5 lg:p-6 min-h-0 bg-gradient-to-b from-[#F8FAFC] to-[#EFF6FF] overflow-y-auto">
            <div className="upload-card-glow max-w-sm mx-auto w-full rounded-[1.75rem] p-6 flex flex-col gap-5 relative landing-fade-5 flex-1">

              {/* Tab Toggle */}
              <div className="flex w-full bg-[#F1F5F9] rounded-xl p-1 relative z-10 border border-[#0A0A0F]/20">
                <button
                  onClick={() => setDataTab("csv")}
                  className={`flex-1 flex items-center justify-center gap-1.5 text-[13px] font-semibold py-2.5 rounded-lg transition-all ${
                    dataTab === "csv"
                      ? "bg-white text-[#0A0A0F] shadow-sm border-b-2 border-[#0EA5E9]"
                      : "text-[#64748B] hover:text-[#0A0A0F]"
                  }`}
                >
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  {lang === "ar" ? "رفع ملف بيانات" : "File Upload"}
                </button>
                <button
                  onClick={() => setDataTab("database")}
                  className={`flex-1 flex items-center justify-center gap-1.5 text-[13px] font-semibold py-2.5 rounded-lg transition-all ${
                    dataTab === "database"
                      ? "bg-white text-[#0A0A0F] shadow-sm border-b-2 border-[#0EA5E9]"
                      : "text-[#64748B] hover:text-[#0A0A0F]"
                  }`}
                >
                  <Database className="w-3.5 h-3.5" />
                  {lang === "ar" ? "قاعدة بيانات" : "Database"}
                </button>
              </div>

              {/* ── File Upload Tab ── */}
              {dataTab === "csv" && (
                <div className="w-full relative z-10 flex-1 flex flex-col gap-3">
                  <input type="file" accept=".csv,.xlsx,.xls" className="hidden" ref={fileInputRef} onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleUpload(file);
                  }} />
                  <div
                    onClick={() => !uploading && fileInputRef.current?.click()}
                    onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('border-black', 'bg-gray-50/50'); }}
                    onDragLeave={(e) => { e.currentTarget.classList.remove('border-black', 'bg-gray-50/50'); }}
                    onDrop={(e) => {
                      e.preventDefault();
                      e.currentTarget.classList.remove('border-black', 'bg-gray-50/50');
                      const file = e.dataTransfer.files?.[0];
                      if (file && (file.name.endsWith('.csv') || file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))) handleUpload(file);
                    }}
                    className={`flex-1 min-h-[280px] border-[2px] border-dashed rounded-2xl p-6 flex flex-col items-center justify-center text-center transition-all cursor-pointer group bg-white/80 backdrop-blur-sm ${
                      uploading ? "border-gray-300 opacity-50 cursor-not-allowed" : "border-black/70 hover:border-black hover:bg-gray-50/30 hover:shadow-[0_0_30px_rgba(0,0,0,0.06)]"
                    }`}
                  >
                    {uploading ? (
                      <Loader2 className="w-8 h-8 text-black animate-spin mb-4" />
                    ) : (
                      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#1E293B] to-[#334155] flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-[0_0_20px_rgba(14,165,233,0.2),inset_0_1px_0_rgba(255,255,255,0.1)] border border-[#0EA5E9]/20">
                        <UploadCloud className="w-7 h-7 text-[#38BDF8]" />
                      </div>
                    )}
                    <h3 className="text-[16px] font-bold text-black mb-1">
                      {lang === "ar" ? "رفع ملف بيانات منظّم" : "Upload Structured Data"}
                    </h3>
                    <p className="text-[12px] text-black/50 max-w-[260px] mx-auto leading-relaxed font-medium mb-4">
                      {lang === "ar" ? "اسحب وأفلت ملفك هنا أو اضغط للاختيار" : "Drag & drop your file here, or click to browse"}
                    </p>

                    {/* Format badges */}
                    <div className="flex items-center gap-2 mb-5">
                      <span className="text-[10px] font-bold text-black/70 bg-gray-100 border border-black/15 px-2.5 py-1 rounded-md tracking-wide">.CSV</span>
                      <span className="text-[10px] font-bold text-black/70 bg-gray-100 border border-black/15 px-2.5 py-1 rounded-md tracking-wide">.XLSX</span>
                      <span className="text-[10px] font-bold text-black/70 bg-gray-100 border border-black/15 px-2.5 py-1 rounded-md tracking-wide">.XLS</span>
                    </div>

                    {/* ── Sliding Hints Carousel ── */}
                    <div className="w-full max-w-[280px] h-[44px] relative overflow-hidden">
                      {[
                        { en: "💡 Supports up to 50,000 rows of data", ar: "💡 يدعم حتى 50,000 صف من البيانات" },
                        { en: "📊 AI auto-detects columns and data types", ar: "📊 يتعرف تلقائياً على الأعمدة وأنواعها" },
                        { en: "🔒 Your data stays private — processed locally", ar: "🔒 بياناتك خاصة — تُعالج محلياً" },
                        { en: "⚡ Instant profiling and quality analysis", ar: "⚡ تحليل فوري لجودة البيانات" },
                      ].map((hint, i) => (
                        <div
                          key={i}
                          className="absolute inset-0 flex items-center justify-center transition-all duration-700 ease-in-out"
                          style={{
                            opacity: hintIndex === i ? 1 : 0,
                            transform: hintIndex === i ? "translateY(0)" : (hintIndex > i || (hintIndex === 0 && i === 3)) ? "translateY(-20px)" : "translateY(20px)",
                          }}
                        >
                          <span className="text-[11px] text-black/45 font-medium leading-snug text-center">
                            {lang === "ar" ? hint.ar : hint.en}
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* Progress dots */}
                    <div className="flex items-center gap-1.5 mt-2">
                      {[0, 1, 2, 3].map(i => (
                        <div
                          key={i}
                          className={`rounded-full transition-all duration-500 ${hintIndex === i ? "w-4 h-1.5 bg-black/50" : "w-1.5 h-1.5 bg-black/15"}`}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* ── Database Connection Tab ── */}
              {dataTab === "database" && (
                <div className="w-full relative z-10 flex-1 flex flex-col gap-3">
                  {/* Scrollable connection form inside dashed border */}
                  <div className="flex-1 border-[2px] border-dashed border-black/70 rounded-2xl p-5 bg-white/80 backdrop-blur-sm overflow-y-auto flex flex-col gap-3">
                    
                    {/* Header icon */}
                    <div className="flex flex-col items-center mb-1">
                      <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[#1E293B] to-[#334155] flex items-center justify-center shadow-[0_0_16px_rgba(14,165,233,0.2),inset_0_1px_0_rgba(255,255,255,0.1)] border border-[#0EA5E9]/20 mb-2">
                        <Database className="w-6 h-6 text-[#38BDF8]" />
                      </div>
                      <h3 className="text-[14px] font-bold text-black">{lang === "ar" ? "اتصال آمن بقاعدة البيانات" : "Secure Database Connection"}</h3>
                      <p className="text-[11px] text-black/45 font-medium">{lang === "ar" ? "أدخل بيانات الاتصال أدناه" : "Enter your connection credentials below"}</p>
                    </div>

                    {/* Engine badges */}
                    <div className="flex flex-wrap items-center justify-center gap-1.5 mb-1">
                      {[
                        { val: "mysql", label: "MySQL", port: "3306" },
                        { val: "postgresql", label: "PostgreSQL", port: "5432" },
                        { val: "sqlserver", label: "SQL Server", port: "1433" },
                        { val: "oracle", label: "Oracle", port: "1521" },
                        { val: "mongodb", label: "MongoDB", port: "27017" },
                        { val: "duckdb", label: "DuckDB", port: "0" },
                        { val: "cockroachdb", label: "CockroachDB", port: "26257" },
                        { val: "cassandra", label: "Cassandra", port: "9042" },
                      ].map(eng => (
                        <button
                          key={eng.val}
                          onClick={() => {
                            setDbType(eng.val);
                            setDbPort(eng.port);
                            setDbTables([]); setDbSelectedTable(""); setDbError(""); setDbExtra("");
                          }}
                          className={`text-[9px] font-bold px-2 py-1 rounded-md border transition-all tracking-wide ${
                            dbType === eng.val
                              ? "bg-gradient-to-r from-[#0A0A0F] to-[#1E293B] text-[#38BDF8] border-[#0EA5E9] shadow-[0_0_12px_rgba(14,165,233,0.2)]"
                              : "bg-[#F1F5F9] text-[#64748B] border-[#E2E8F0] hover:bg-sky-50 hover:border-[#0EA5E9]/30 hover:text-[#0A0A0F]"
                          }`}
                        >
                          {eng.label}
                        </button>
                      ))}
                    </div>

                    {/* Host + Port */}
                    <div className="grid grid-cols-3 gap-2">
                      <div className="col-span-2">
                        <label className="text-[10px] font-bold text-black/70 uppercase tracking-wider mb-1 block">{lang === "ar" ? "المضيف" : "Host"}</label>
                        <input type="text" value={dbHost} onChange={(e) => setDbHost(e.target.value)} placeholder="localhost"
                          className="w-full bg-white border-2 border-black/20 rounded-xl px-3 py-2 text-[12px] text-black font-medium placeholder:text-black/25 focus:outline-none focus:border-black/50 transition-all" />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-black/70 uppercase tracking-wider mb-1 block">{lang === "ar" ? "المنفذ" : "Port"}</label>
                        <input type="text" value={dbPort} onChange={(e) => setDbPort(e.target.value)}
                          className="w-full bg-white border-2 border-black/20 rounded-xl px-3 py-2 text-[12px] text-black font-medium placeholder:text-black/25 focus:outline-none focus:border-black/50 transition-all" />
                      </div>
                    </div>

                    {/* Database Name / Connection String */}
                    <div>
                      <label className="text-[10px] font-bold text-black/70 uppercase tracking-wider mb-1 block">
                        {dbType === "duckdb" ? (lang === "ar" ? "مسار الملف" : "File Path") : dbType === "mongodb" ? (lang === "ar" ? "اسم قاعدة البيانات" : "Database Name") : (lang === "ar" ? "قاعدة البيانات" : "Database")}
                      </label>
                      <input type="text" value={dbName} onChange={(e) => setDbName(e.target.value)}
                        placeholder={dbType === "duckdb" ? "/path/to/data.duckdb" : "my_database"}
                        className="w-full bg-white border-2 border-black/20 rounded-xl px-3 py-2 text-[12px] text-black font-medium placeholder:text-black/25 focus:outline-none focus:border-black/50 transition-all" />
                    </div>

                    {/* Username + Password (hidden for DuckDB) */}
                    {dbType !== "duckdb" && (
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-[10px] font-bold text-black/70 uppercase tracking-wider mb-1 block">{lang === "ar" ? "المستخدم" : "Username"}</label>
                          <input type="text" value={dbUser} onChange={(e) => setDbUser(e.target.value)}
                            placeholder={dbType === "mongodb" ? "admin" : "root"}
                            className="w-full bg-white border-2 border-black/20 rounded-xl px-3 py-2 text-[12px] text-black font-medium placeholder:text-black/25 focus:outline-none focus:border-black/50 transition-all" />
                        </div>
                        <div>
                          <label className="text-[10px] font-bold text-black/70 uppercase tracking-wider mb-1 block">{lang === "ar" ? "كلمة المرور" : "Password"}</label>
                          <input type="password" value={dbPass} onChange={(e) => setDbPass(e.target.value)} placeholder="••••••"
                            className="w-full bg-white border-2 border-black/20 rounded-xl px-3 py-2 text-[12px] text-black font-medium placeholder:text-black/25 focus:outline-none focus:border-black/50 transition-all" />
                        </div>
                      </div>
                    )}

                    {/* Extra params (contextual) */}
                    {(dbType === "oracle" || dbType === "mongodb" || dbType === "postgresql" || dbType === "cockroachdb") && (
                      <div>
                        <label className="text-[10px] font-bold text-black/70 uppercase tracking-wider mb-1 block">
                          {dbType === "oracle" ? (lang === "ar" ? "معرف الخدمة (SID)" : "Service ID (SID)")
                            : dbType === "mongodb" ? (lang === "ar" ? "مصدر المصادقة" : "Auth Source")
                            : (lang === "ar" ? "المخطط" : "Schema")}
                        </label>
                        <input type="text" value={dbExtra} onChange={(e) => setDbExtra(e.target.value)}
                          placeholder={dbType === "oracle" ? "ORCL" : dbType === "mongodb" ? "admin" : "public"}
                          className="w-full bg-white border-2 border-black/20 rounded-xl px-3 py-2 text-[12px] text-black font-medium placeholder:text-black/25 focus:outline-none focus:border-black/50 transition-all" />
                      </div>
                    )}

                    {/* SSL Toggle */}
                    {dbType !== "duckdb" && (
                      <div className="flex items-center justify-between bg-gray-50 border-2 border-black/10 rounded-xl px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <Shield className="w-3.5 h-3.5 text-black/50" />
                          <span className="text-[11px] font-bold text-black/70">{lang === "ar" ? "اتصال SSL / TLS آمن" : "SSL / TLS Secure Connection"}</span>
                        </div>
                        <button
                          onClick={() => setDbSSL(!dbSSL)}
                          className={`relative w-9 h-5 rounded-full transition-all duration-300 ${dbSSL ? "bg-black" : "bg-black/20"}`}
                        >
                          <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-all duration-300 ${dbSSL ? "left-[18px]" : "left-0.5"}`} />
                        </button>
                      </div>
                    )}

                    {/* Error */}
                    {dbError && (
                      <div className="text-[11px] text-red-600 bg-red-50 border-2 border-red-200 rounded-xl px-3 py-2 font-medium">{dbError}</div>
                    )}

                    {/* Connect Button */}
                    <button
                      disabled={dbConnecting || !dbHost || (!dbName && dbType !== "duckdb") || (!dbUser && dbType !== "duckdb")}
                      onClick={async () => {
                        setDbConnecting(true); setDbError(""); setDbTables([]);
                        try {
                          const res = await listTables({
                            db_type: dbType, host: dbHost, port: parseInt(dbPort),
                            database: dbName, username: dbUser, password: dbPass,
                            ssl: dbSSL, extra: dbExtra,
                          });
                          if (res.status === 200 && res.data.tables) {
                            setDbTables(res.data.tables);
                            if (res.data.tables.length > 0) setDbSelectedTable(res.data.tables[0]);
                          } else {
                            setDbError(res.data.detail || "Connection failed.");
                          }
                        } catch (e: any) { setDbError(e.message); }
                        setDbConnecting(false);
                      }}
                      className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-[#0A0A0F] to-[#1E293B] text-white text-[12px] font-bold py-3 rounded-xl hover:shadow-[0_4px_20px_rgba(14,165,233,0.2)] disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm border border-[#0EA5E9]/30"
                    >
                      {dbConnecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plug className="w-4 h-4" />}
                      {dbConnecting ? (lang === "ar" ? "جاري الاتصال..." : "Connecting...") : (lang === "ar" ? "اتصال وعرض الجداول" : "Connect & List Tables")}
                    </button>

                    {/* Tables List + Load */}
                    {dbTables.length > 0 && (
                      <div className="flex flex-col gap-2.5 pt-1">
                        <div className="flex items-center gap-2 text-[11px] text-[#0EA5E9] font-bold">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          {lang === "ar" ? `تم العثور على ${dbTables.length} جدول` : `${dbTables.length} table${dbTables.length > 1 ? "s" : ""} found`}
                        </div>
                        <div>
                          <label className="text-[10px] font-bold text-black/70 uppercase tracking-wider mb-1 block">{lang === "ar" ? "اختر جدول" : "Select Table"}</label>
                          <div className="relative">
                            <select
                              value={dbSelectedTable}
                              onChange={(e) => setDbSelectedTable(e.target.value)}
                              className="w-full bg-white border-2 border-black/20 rounded-xl px-3 py-2 text-[12px] text-black font-medium appearance-none cursor-pointer focus:outline-none focus:border-black/50 transition-all"
                            >
                              {dbTables.map(t => <option key={t} value={t}>{t}</option>)}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-black/40 pointer-events-none" />
                          </div>
                        </div>
                        <button
                          disabled={dbLoading || !dbSelectedTable}
                          onClick={async () => {
                            setDbLoading(true); setDbError("");
                            try {
                              const res = await connectDatabase({
                                db_type: dbType, host: dbHost, port: parseInt(dbPort),
                                database: dbName, username: dbUser, password: dbPass,
                                table_name: dbSelectedTable, ssl: dbSSL, extra: dbExtra,
                              });
                              if (res.status === 200 && res.data.profile) {
                                setStats(res.data.profile);
                              } else {
                                setDbError(res.data.detail || "Failed to load data.");
                              }
                            } catch (e: any) { setDbError(e.message); }
                            setDbLoading(false);
                          }}
                          className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-[#0EA5E9] to-[#38BDF8] text-white text-[12px] font-bold py-3 rounded-xl hover:shadow-[0_4px_20px_rgba(14,165,233,0.25)] disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm"
                        >
                          {dbLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <TableProperties className="w-4 h-4" />}
                          {dbLoading ? (lang === "ar" ? "جاري تحميل البيانات..." : "Loading data...") : (lang === "ar" ? "تحميل وتحليل" : "Load & Analyze")}
                        </button>
                      </div>
                    )}

                    {/* ── Sliding DB Hints ── */}
                    <div className="w-full h-[36px] relative overflow-hidden mt-auto">
                      {[
                        { en: "🔐 Credentials are never stored — memory only", ar: "🔐 لا يتم تخزين بيانات الاعتماد — في الذاكرة فقط" },
                        { en: "🌐 Supports SQL, NoSQL & embedded databases", ar: "🌐 يدعم SQL و NoSQL وقواعد البيانات المدمجة" },
                        { en: "📋 Select any table for instant AI analysis", ar: "📋 اختر أي جدول للتحليل الفوري بالذكاء الاصطناعي" },
                        { en: "⚡ Direct query — no data export needed", ar: "⚡ استعلام مباشر — لا حاجة لتصدير البيانات" },
                      ].map((hint, i) => (
                        <div
                          key={i}
                          className="absolute inset-0 flex items-center justify-center transition-all duration-700 ease-in-out"
                          style={{
                            opacity: dbHintIndex === i ? 1 : 0,
                            transform: dbHintIndex === i ? "translateY(0)" : (dbHintIndex > i || (dbHintIndex === 0 && i === 3)) ? "translateY(-16px)" : "translateY(16px)",
                          }}
                        >
                          <span className="text-[10px] text-black/40 font-medium text-center">{lang === "ar" ? hint.ar : hint.en}</span>
                        </div>
                      ))}
                    </div>
                    <div className="flex items-center justify-center gap-1.5">
                      {[0, 1, 2, 3].map(i => (
                        <div key={i} className={`rounded-full transition-all duration-500 ${dbHintIndex === i ? "w-4 h-1.5 bg-black/50" : "w-1.5 h-1.5 bg-black/15"}`} />
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Chat Locked Preview */}
              <div className="w-full bg-white/60 backdrop-blur-sm rounded-xl p-4 border-2 border-black/70 relative z-10">
                <div className="flex items-center gap-2.5 mb-3">
                  <div className="text-gray-300 bg-white p-1.5 rounded-md border border-gray-100 shadow-sm">
                    <Lock className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <h4 className="text-[12px] font-bold text-black">
                      {lang === "ar" ? "محادثة البيانات مقفلة" : "Data Chat Locked"}
                    </h4>
                    <p className="text-[10px] text-black/50 font-medium">
                      {lang === "ar" ? "قم بتحميل ملف أو اتصل بقاعدة بيانات." : "Upload a CSV or connect a database to begin."}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2.5">
                  <div className="flex-1 bg-gray-50/80 border border-gray-100 rounded-full px-4 py-2 cursor-not-allowed overflow-hidden">
                    <div className="shimmer-bar w-3/4 mb-0" />
                  </div>
                  <div className="bg-gray-50 text-gray-300 rounded-full p-2.5 flex-shrink-0 cursor-not-allowed border border-gray-100">
                    <Send className="w-3.5 h-3.5" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Active State Layout — 50/50 Split */
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-0">
          {/* Left/Right: Chat Zone */}
          <div className={`w-full lg:w-1/2 bg-white flex flex-col overflow-hidden min-h-0 ${isAr ? 'border-l border-[#E2E8F0]' : 'border-r border-[#E2E8F0]'}`}>
            <ActionZone
              lang={lang}
              question={question}
              setQuestion={setQuestion}
              onAsk={() => handleAsk()}
              onReset={handleReset}
              onUpload={handleUpload}
              onClearDataset={handleClearDataset}
              onFollowUp={handleFollowUp}
              loading={loading}
              uploading={uploading}
              chatHistory={chatHistory}
              stats={stats}
              sessionId={sessionId}
            />
          </div>

          {/* Right: Insight Zone — scrolls internally */}
          <div className="w-full lg:w-1/2 overflow-y-auto min-h-0">
            <InsightZone
              lang={lang}
              stats={stats}
              response={latestResponse}
            />
          </div>
        </div>
      )}
    </div>
  );
}
