"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Language } from "@/lib/i18n";
import { askQuestion, fetchStats, uploadDataset, resetSession, clearDataset, ApiResponse } from "@/lib/api";
import { ActionZone, ChatTurn } from "@/components/ActionZone";
import { InsightZone } from "@/components/InsightZone";
import { UploadCloud, Loader2, Server, BrainCircuit, Code2, CheckCircle2, MessageSquare, Send, Lock } from "lucide-react";

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

  useEffect(() => {
    fetchStats().then(setStats);
  }, []);

  useEffect(() => {
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);

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
    <div className="h-screen bg-[#FAFAFA] flex flex-col font-sans overflow-hidden">
      {/* Top Bar */}
      <div className="flex-shrink-0 flex justify-end p-3 border-b border-[#EEEEEE] bg-white">
        <div className="flex bg-gray-100 rounded-lg p-0.5">
          <button
            onClick={() => setLang("en")}
            className={`px-4 py-1 text-xs font-semibold rounded-md transition-all ${lang === "en" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}
          >
            EN
          </button>
          <button
            onClick={() => setLang("ar")}
            className={`px-4 py-1 text-xs font-semibold rounded-md transition-all ${lang === "ar" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}
          >
            عربي
          </button>
        </div>
      </div>

      {/* Main Area */}
      {!stats ? (
        /* Premium Empty State Landing Layout — 50/50 Split */
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-0 bg-[#F8F9FA]">
          {/* Left: Branded Hero Area */}
          <div className="w-full lg:w-[60%] flex flex-col justify-center p-8 lg:p-16 min-h-0 bg-white relative shadow-[20px_0_40px_-20px_rgba(0,0,0,0.03)] overflow-hidden z-10">
            {/* Aldar HQ HD Background (Transparent & Shaded) */}
            <div className="absolute inset-0 z-0 pointer-events-none flex items-center justify-center overflow-hidden">
               <img 
                 src="/aldar_hq.jpg" 
                 alt="ALDAR HQ Skyline" 
                 className="w-full h-full object-cover scale-[1.3] opacity-[0.15] grayscale mix-blend-multiply"
                 onError={(e) => { e.currentTarget.style.display='none'; }}
               />
            </div>
            
            <div className="max-w-xl mx-auto w-full relative z-10 pt-2 flex flex-col items-center text-center">
              <div className="w-[180px] h-[180px] bg-white border-[1.5px] border-gray-900/10 rounded-2xl flex items-center justify-center p-5 mb-8 shadow-[0_4px_20px_rgba(0,0,0,0.03)]">
                <img src="/aldar_logo.png" alt="ALDAR" className="max-h-full max-w-full object-contain" onError={(e) => { e.currentTarget.style.display='none'; }} />
              </div>
              
              <h1 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4 tracking-tight">
                {lang === "ar" ? "مساعد تحليل البيانات" : "Data Analytics Copilot"}
              </h1>
              
              <p className="text-base lg:text-lg text-gray-500 leading-relaxed mb-10">
                {lang === "ar" ? "رؤى مدعومة بالذكاء الاصطناعي مع تحقق حتمي عبر بايثون." : "Schema-driven AI insights with deterministic Python verification."}
              </p>

              {/* Capability Badges */}
              <div className="grid grid-cols-2 gap-4 mt-2">
                <div className="flex items-center gap-3.5 bg-blue-50/40 rounded-xl p-4 border border-blue-100 shadow-[0_0_40px_rgba(59,130,246,0.15)] relative overflow-hidden">
                  <div className="bg-blue-100/80 text-blue-600 p-2.5 rounded-lg">
                    <Server className="w-5 h-5" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold text-gray-900">{lang === "ar" ? "متصل بالـ API" : "API Connected"}</span>
                    <span className="text-[11px] text-gray-500">{lang === "ar" ? "متصل بالخادم النشط" : "Live server link"}</span>
                  </div>
                </div>
                
                <div className="flex items-center gap-3.5 bg-purple-50/40 rounded-xl p-4 border border-purple-100 shadow-[0_0_40px_rgba(168,85,247,0.15)] relative overflow-hidden">
                  <div className="bg-purple-100/80 text-purple-600 p-2.5 rounded-lg">
                    <BrainCircuit className="w-5 h-5" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold text-gray-900">{lang === "ar" ? "مدعوم بنماذج لغوية" : "LLM Enabled"}</span>
                    <span className="text-[11px] text-gray-500">{lang === "ar" ? "فهم سياقي ذكي" : "Semantic understanding"}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3.5 bg-amber-50/40 rounded-xl p-4 border border-amber-100 shadow-[0_0_40px_rgba(245,158,11,0.15)] relative overflow-hidden">
                  <div className="bg-amber-100/80 text-amber-600 p-2.5 rounded-lg">
                    <Code2 className="w-5 h-5" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold text-gray-900">{lang === "ar" ? "محقق ببايثون" : "Python Verified"}</span>
                    <span className="text-[11px] text-gray-500">{lang === "ar" ? "تنفيذ حتمي للأكواد" : "Code execution"}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3.5 bg-emerald-50/40 rounded-xl p-4 border border-emerald-100 shadow-[0_0_40px_rgba(16,185,129,0.15)] relative overflow-hidden">
                  <div className="bg-emerald-100/80 text-emerald-600 p-2.5 rounded-lg">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold text-gray-900">{lang === "ar" ? "تحليل حتمي" : "Deterministic"}</span>
                    <span className="text-[11px] text-gray-500">{lang === "ar" ? "دقة بيانات مضمونة" : "Guaranteed accuracy"}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Action Area */}
          <div className="w-full lg:w-[40%] flex flex-col justify-center items-center p-6 lg:p-10 min-h-0 bg-[#F9FAFB]">
            <div className="max-w-md mx-auto w-full bg-white rounded-[2rem] shadow-[0_20px_60px_-15px_rgba(0,0,0,0.05)] border border-gray-100 p-8 flex flex-col gap-6 relative">
              
              {/* Uploader */}
              <div className="w-full relative z-10">
                <input type="file" accept=".csv" className="hidden" ref={fileInputRef} onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleUpload(file);
                }} />
                <div
                  onClick={() => !uploading && fileInputRef.current?.click()}
                  className={`min-h-[220px] border-[1.5px] border-dashed rounded-[1.5rem] p-10 flex flex-col items-center justify-center text-center transition-all cursor-pointer group bg-white ${
                    uploading ? "border-gray-200 opacity-50 cursor-not-allowed" : "border-gray-300 hover:border-gray-400 hover:bg-gray-50/50"
                  }`}
                >
                  {uploading ? (
                    <Loader2 className="w-8 h-8 text-gray-400 animate-spin mb-4" />
                  ) : (
                    <UploadCloud className="w-8 h-8 text-gray-500 group-hover:text-gray-700 mb-4 transition-colors" />
                  )}
                  <h3 className="text-base font-bold text-gray-900 mb-2">
                    {lang === "ar" ? "قم بتحميل ملف بيانات للبدء" : "Upload a CSV to begin analysis"}
                  </h3>
                  <p className="text-sm text-gray-500 max-w-[280px] mx-auto leading-relaxed">
                    {lang === "ar" ? "قم بإسقاط ملف بياناتك هنا لإنشاء لوحة معلومات ديناميكية." : "Drop your dataset here to generate your dynamic dashboard."}
                  </p>
                </div>
              </div>

              {/* Disabled Chat Preview */}
              <div className="w-full bg-[#F9FAFB] rounded-2xl p-5 border border-gray-100">
                <div className="flex items-center gap-3 mb-4">
                  <div className="text-gray-400 bg-white p-1.5 rounded-md border border-gray-100 shadow-sm">
                    <Lock className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-[13px] font-semibold text-gray-700">
                      {lang === "ar" ? "محادثة البيانات مقفلة" : "Data Chat Locked"}
                    </h4>
                    <p className="text-[11.5px] text-gray-500">
                      {lang === "ar" ? "قم بتحميل ملف أولاً للبدء بطرح الأسئلة." : "Upload a dataset first to start chatting with your data."}
                    </p>
                  </div>
                </div>
                
                {/* Fake Input */}
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-gray-100 border border-transparent rounded-full px-5 py-3 text-[13px] text-gray-400 cursor-not-allowed">
                    {lang === "ar" ? "اسأل سؤالاً أو تابع التحليل..." : "Ask a question or continue your analysis..."}
                  </div>
                  <div className="bg-gray-100 text-gray-400 rounded-full p-3.5 flex-shrink-0 cursor-not-allowed">
                    <Send className="w-[18px] h-[18px]" />
                  </div>
                </div>
              </div>

            </div>
          </div>
        </div>
      ) : (
        /* Active State Layout — 50/50 Split */
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-0">
          {/* Left: Chat Zone */}
          <div className="w-full lg:w-1/2 border-r border-[#EEEEEE] bg-white flex flex-col overflow-hidden min-h-0">
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
