"use client";

import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, CheckCircle2, Loader2, Send, RotateCcw, User, Bot, Sparkles, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Language, translations } from "@/lib/i18n";
import { useRef, useEffect } from "react";

export interface ChatTurn {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: any; // Full API response for assistant turns
  timestamp: number;
}

export function ActionZone({
  lang,
  question,
  setQuestion,
  onAsk,
  onReset,
  onUpload,
  onClearDataset,
  onFollowUp,
  loading,
  uploading,
  chatHistory,
  stats,
  sessionId,
}: {
  lang: Language;
  question: string;
  setQuestion: (q: string) => void;
  onAsk: () => void;
  onReset: () => void;
  onUpload: (file: File) => void;
  onClearDataset: () => void;
  onFollowUp: (q: string) => void;
  loading: boolean;
  uploading: boolean;
  chatHistory: ChatTurn[];
  stats: any;
  sessionId: string | null;
}) {
  const t = translations[lang];
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const isAr = lang === "ar";

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory.length]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onUpload(e.target.files[0]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onAsk();
    }
  };

  const getDynamicChips = () => {
    if (!stats) return [];
    const chips = [];
    if (stats.numeric_columns?.length > 0 && stats.datetime_columns?.length > 0) {
      chips.push({ label: isAr ? "تحليل الاتجاه" : "Trend Analysis", query: `Show the trend of ${stats.numeric_columns[0]} over ${stats.datetime_columns[0]}` });
    }
    if (stats.categorical_columns?.length > 0 && stats.numeric_columns?.length > 0) {
      chips.push({ label: isAr ? "أهم الفئات" : "Top Categories", query: `What are the top 5 ${stats.categorical_columns[0]} by ${stats.numeric_columns[0]}?` });
    }
    if (stats.numeric_columns?.length > 0) {
      chips.push({ label: isAr ? "متوسط القيمة" : "Average Value", query: `What is the average ${stats.numeric_columns[0]}?` });
    }
    return chips;
  };

  const chips = getDynamicChips();
  const hasHistory = chatHistory.length > 0;

  return (
    <div className="flex flex-col h-full w-full">
      {/* ── Fixed Header ── */}
      <div className="flex-shrink-0 p-4 lg:px-8 lg:pt-6 border-b border-gray-100 bg-white">
        <div className="flex items-start justify-between">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-3">
              <img src="/aldar_logo.png" alt="ALDAR" className="h-10 w-auto object-contain" onError={(e) => { e.currentTarget.style.display='none'; }} />
              <h1 className="text-xl font-bold tracking-tight text-gray-900">{t.title}</h1>
            </div>
            <div className="flex items-center gap-2 text-gray-500">
              <p className="text-xs">{t.subtitle}</p>
              <span className="flex items-center gap-1 text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-full text-[10px] font-medium border border-emerald-200">
                <CheckCircle2 className="w-2.5 h-2.5" />
                Deterministic
              </span>
            </div>
          </div>
          {/* Session indicator + Reset */}
          {hasHistory && (
            <button
              onClick={onReset}
              className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-red-600 transition-colors bg-gray-50 hover:bg-red-50 px-3 py-1.5 rounded-lg border border-gray-200 hover:border-red-200"
              title={isAr ? "بدء تحليل جديد" : "New Analysis"}
            >
              <RotateCcw className="w-3 h-3" />
              {isAr ? "جديد" : "New Chat"}
            </button>
          )}
        </div>
      </div>

      {/* ── Upload Zone (only when no dataset) ── */}
      {!stats && (
        <div className="flex-shrink-0 p-4 lg:px-8 bg-white border-b border-gray-100">
          <input type="file" accept=".csv" className="hidden" ref={fileInputRef} onChange={handleFileChange} />
          <div
            onClick={() => !uploading && fileInputRef.current?.click()}
            className={cn(
              "border border-dashed border-gray-300 rounded-xl p-6 bg-gray-50 flex flex-col items-center justify-center text-center transition-colors cursor-pointer group shadow-sm",
              uploading ? "opacity-50 cursor-not-allowed" : "hover:bg-gray-100 hover:border-blue-300"
            )}
          >
            {uploading ? (
              <Loader2 className="w-6 h-6 text-blue-500 animate-spin mb-2" />
            ) : (
              <UploadCloud className="w-6 h-6 text-gray-400 group-hover:text-blue-500 mb-2 transition-colors" />
            )}
            <p className="text-sm font-medium text-gray-700">{uploading ? t.uploading : t.uploadPlaceholder}</p>
            <p className="text-xs text-gray-400 mt-1">{t.uploadNote}</p>
          </div>
        </div>
      )}

      {/* ── Upload + Clear when dataset loaded ── */}
      {stats && (
        <div className="flex-shrink-0 px-4 lg:px-8 pt-3 flex items-center gap-3">
          <input type="file" accept=".csv" className="hidden" ref={fileInputRef} onChange={handleFileChange} />
          <button
            onClick={() => !uploading && fileInputRef.current?.click()}
            className="text-[10px] text-gray-400 hover:text-blue-600 transition-colors flex items-center gap-1"
          >
            <UploadCloud className="w-3 h-3" />
            {isAr ? "تغيير مجموعة البيانات" : "Change dataset"}
          </button>
          <span className="text-gray-200">|</span>
          <button
            onClick={onClearDataset}
            className="text-[10px] text-gray-400 hover:text-red-500 transition-colors flex items-center gap-1"
          >
            <Trash2 className="w-3 h-3" />
            {isAr ? "مسح البيانات" : "Clear dataset"}
          </button>
        </div>
      )}

      {/* ── Chat History (scrollable) ── */}
      <div className="flex-1 overflow-y-auto px-4 lg:px-8 py-3 space-y-3">
        {/* Initial Assistant Message for Empty State */}
        {!stats && chatHistory.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              "flex gap-2.5",
              isAr ? "flex-row-reverse" : "flex-row"
            )}
          >
            <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 bg-blue-500">
              <Bot className="w-3.5 h-3.5 text-white" />
            </div>
            <div className="max-w-[85%] rounded-xl px-4 py-2.5 text-sm leading-relaxed bg-white border border-gray-200 text-gray-800 shadow-sm">
              <p>{isAr ? "مرحباً! يرجى تحميل ملف بيانات (CSV) أولاً، ثم يمكنني مساعدتك في تحليله." : "Hi there! Please upload a CSV dataset first, then I can help you analyze it."}</p>
            </div>
          </motion.div>
        )}

        {/* Welcome / Quick start chips after dataset load */}
        {!hasHistory && stats && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center text-center py-8 gap-4"
          >
            <div className="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-blue-500" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-800">
                {isAr ? "ابدأ التحليل" : "Start Your Analysis"}
              </h3>
              <p className="text-xs text-gray-500 mt-1 max-w-xs">
                {isAr ? "اسأل أي سؤال عن بياناتك. يمكنك المتابعة بأسئلة إضافية." : "Ask any question about your data. You can follow up with additional questions."}
              </p>
            </div>
            {/* Quick start chips */}
            {chips.length > 0 && (
              <div className="flex flex-wrap gap-2 justify-center">
                {chips.map((chip, i) => (
                  <button
                    key={i}
                    onClick={() => onFollowUp(chip.query)}
                    className="bg-white border border-gray-200 rounded-lg px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 transition-all shadow-sm"
                  >
                    {chip.label}
                  </button>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {/* Chat Messages */}
        <AnimatePresence mode="popLayout">
          {chatHistory.map((turn) => (
            <motion.div
              key={turn.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className={cn(
                "flex gap-2.5",
                turn.role === "user" ? (isAr ? "flex-row-reverse" : "flex-row") : (isAr ? "flex-row-reverse" : "flex-row")
              )}
            >
              {/* Avatar */}
              <div className={cn(
                "w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5",
                turn.role === "user" ? "bg-gray-900" : "bg-blue-500"
              )}>
                {turn.role === "user"
                  ? <User className="w-3.5 h-3.5 text-white" />
                  : <Bot className="w-3.5 h-3.5 text-white" />
                }
              </div>

              {/* Bubble */}
              <div className={cn(
                "max-w-[85%] rounded-xl px-4 py-2.5 text-sm leading-relaxed",
                turn.role === "user"
                  ? "bg-gray-900 text-white"
                  : "bg-white border border-gray-200 text-gray-800 shadow-sm"
              )}>
                <div className="whitespace-pre-wrap">{turn.content}</div>

                {/* Conversation state badge */}
                {turn.role === "assistant" && turn.response?.data?.conversation_state?.used_prior_context && (
                  <span className="inline-flex items-center gap-1 mt-2 text-[9px] text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200">
                    🔗 {isAr ? "بناءً على السياق السابق" : "Built on prior context"}
                  </span>
                )}

                {/* Follow-up + Suggested in assistant bubbles */}
                {turn.role === "assistant" && (
                  <div className="mt-2 space-y-2">
                    {/* Follow-up questions */}
                    {turn.response?.data?.follow_up_questions?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {turn.response.data.follow_up_questions.map((q: string, qi: number) => (
                          <button
                            key={qi}
                            onClick={() => onFollowUp(q)}
                            className="text-[10px] text-blue-600 bg-blue-50 border border-blue-200 rounded-md px-2 py-1 hover:bg-blue-100 transition-colors text-left"
                          >
                            🔍 {q}
                          </button>
                        ))}
                      </div>
                    )}
                    {/* Suggested questions */}
                    {turn.response?.data?.suggested_questions?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {turn.response.data.suggested_questions.map((q: string, qi: number) => (
                          <button
                            key={qi}
                            onClick={() => onFollowUp(q)}
                            className="text-[10px] text-gray-500 bg-gray-50 border border-gray-200 rounded-md px-2 py-1 hover:bg-gray-100 transition-colors text-left"
                          >
                            💬 {q}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Loading indicator */}
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex gap-2.5"
          >
            <div className="w-7 h-7 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
              <Bot className="w-3.5 h-3.5 text-white" />
            </div>
            <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 shadow-sm flex items-center gap-2">
              <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
              <span className="text-xs text-gray-500">{isAr ? "جاري التحليل..." : "Analyzing..."}</span>
            </div>
          </motion.div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* ── Input Bar (fixed bottom) ── */}
      <div className="flex-shrink-0 p-3 lg:px-8 lg:pb-5 border-t border-gray-100 bg-white">
          <div className="flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={!stats ? (isAr ? "يرجى تحميل مجموعة بيانات أولاً..." : "Please upload a dataset first...") : (isAr ? "اسأل أو تابع التحليل السابق..." : "Ask a question or continue your analysis...")}
                disabled={loading || !stats}
                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 focus:bg-white transition-all resize-none disabled:opacity-50 disabled:cursor-not-allowed"
                rows={1}
                dir={isAr && !question ? "rtl" : "auto"}
              />
            </div>
            <button
              onClick={onAsk}
              disabled={loading || !question.trim() || !stats}
              className="bg-gray-900 text-white rounded-xl p-3 hover:bg-gray-800 disabled:opacity-40 transition-all flex-shrink-0 disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        {/* Session ID indicator */}
        {sessionId && hasHistory && (
          <div className="flex items-center justify-center mt-2">
            <span className="text-[9px] text-gray-400">
              {isAr ? "جلسة" : "Session"}: {sessionId.slice(0, 8)}… • {chatHistory.filter(t => t.role === "user").length} {isAr ? "أسئلة" : "turns"}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
