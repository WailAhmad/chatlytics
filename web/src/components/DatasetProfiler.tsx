"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Language, translations } from "@/lib/i18n";
import { 
  Database, Columns, AlertTriangle, ShieldCheck, Copy, 
  BarChart3, Activity, Hash, Clock, List, Zap, Lightbulb, CheckCircle2, AlertCircle, ChevronDown, ChevronUp
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LineChart, Line, ScatterChart, Scatter, ZAxis
} from "recharts";

const CHART_COLORS = ['#3B82F6', '#10B981', '#8B5CF6', '#F59E0B', '#EF4444', '#06B6D4'];

export function DatasetProfiler({ lang, stats }: { lang: Language; stats: any }) {
  const isAr = lang === "ar";
  const [showDetails, setShowDetails] = useState(false);

  if (!stats || !stats.health) return null;

  const { health, detailed_columns, correlations, scatter_plots, anomalies, key_takeaways, quality_metrics } = stats;
  const cols = Object.entries(detailed_columns || {});
  
  const numericCols = cols.filter(([_, data]: any) => data.type === "numeric");
  const catCols = cols.filter(([_, data]: any) => data.type === "categorical");
  const dtCols = cols.filter(([_, data]: any) => data.type === "datetime");

  return (
    <div dir={isAr ? "rtl" : "ltr"} className={`flex flex-col gap-8 w-full max-w-[1400px] mx-auto p-4 lg:p-6 bg-gray-50/30 ${isAr ? 'text-right' : 'text-left'}`}>
      
      {/* ── 0. DATASET SUMMARY (AUTO-GENERATED) ── */}
      {/* ── 0. WHAT THIS DATASET IS ABOUT ── */}
      {stats.upload_summary && (
        <section className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <div className="flex flex-col gap-5">
            <div>
              <h2 className={`text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 flex items-center gap-2 ${isAr ? 'flex-row-reverse' : ''}`}>
                <Lightbulb className="w-4 h-4 text-amber-500" />
                {isAr ? "ما هي هذه البيانات" : "What This Dataset Is About"}
              </h2>
              <p className="text-gray-800 text-sm leading-relaxed">{stats.upload_summary.dataset_overview}</p>
            </div>
            <div className="flex flex-col md:flex-row gap-5 pt-4 border-t border-gray-100">
              <div className="flex-1">
                <h2 className={`text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 flex items-center gap-2 ${isAr ? 'flex-row-reverse' : ''}`}>
                  <ShieldCheck className="w-4 h-4 text-emerald-500" />
                  {isAr ? "جودة البيانات" : "Data Quality"}
                </h2>
                <p className="text-gray-800 text-sm leading-relaxed">{stats.upload_summary.health_notes}</p>
              </div>
              {stats.upload_summary.data_readiness && (
                <div className="flex items-start">
                  <span className={`text-xs font-bold px-3 py-1.5 rounded-lg border ${
                    stats.upload_summary.data_readiness === "Ready for analysis" ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
                    stats.upload_summary.data_readiness === "Some cleaning recommended" ? "bg-amber-50 text-amber-700 border-amber-200" :
                    "bg-red-50 text-red-700 border-red-200"
                  }`}>
                    <CheckCircle2 className={`w-3 h-3 inline ${isAr ? 'ml-1' : 'mr-1'}`} />
                    {stats.upload_summary.data_readiness}
                  </span>
                </div>
              )}
            </div>
            {/* Key observations */}
            {stats.upload_summary.key_observations && stats.upload_summary.key_observations.length > 0 && (
              <div className="pt-4 border-t border-gray-100">
                <h2 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">
                  {isAr ? "ملاحظات رئيسية" : "Key Things to Notice"}
                </h2>
                <ul className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {stats.upload_summary.key_observations.map((obs: string, i: number) => (
                    <li key={i} className={`flex items-start gap-2 text-sm text-gray-700 bg-gray-50/50 p-2.5 rounded-lg border border-gray-100 ${isAr ? 'flex-row-reverse text-right' : ''}`}>
                      <span className="text-blue-500 mt-0.5 shrink-0 font-bold">{isAr ? '◂' : '▸'}</span>
                      <span>{obs}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {/* Suggested questions */}
            {stats.upload_summary.suggested_questions && stats.upload_summary.suggested_questions.length > 0 && (
              <div className="pt-4 border-t border-gray-100">
                <h2 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">
                  {isAr ? "أسئلة مقترحة" : "Recommended Questions"}
                </h2>
                <div className="flex flex-wrap gap-2">
                  {stats.upload_summary.suggested_questions.map((q: string, i: number) => (
                    <span key={i} className="bg-blue-50 border border-blue-200 text-blue-700 text-xs px-3 py-1.5 rounded-lg font-medium cursor-pointer hover:bg-blue-100 transition-colors">
                      {q}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── 1. OVERVIEW STRIP ── */}
      <section className={`bg-white border border-gray-200 rounded-xl p-4 shadow-sm flex flex-wrap lg:flex-nowrap items-center justify-between gap-4 ${isAr ? 'flex-row-reverse' : ''}`}>
        <div className={`flex items-center gap-6 ${isAr ? 'divide-x-reverse' : ''} divide-x divide-gray-100`}>
          <div className="flex flex-col px-4">
            <span className="text-[10px] text-gray-400 uppercase tracking-widest font-semibold">{isAr ? "الصفوف" : "Rows"}</span>
            <span className="text-xl font-bold text-gray-900">{health.row_count.toLocaleString()}</span>
          </div>
          <div className={`flex flex-col ${isAr ? 'pr-6' : 'pl-6'}`}>
            <span className="text-[10px] text-gray-400 uppercase tracking-widest font-semibold">{isAr ? "الأعمدة" : "Columns"}</span>
            <span className="text-xl font-bold text-gray-900">{health.column_count.toLocaleString()}</span>
          </div>
          <div className={`flex flex-col ${isAr ? 'pr-6' : 'pl-6'}`}>
            <span className="text-[10px] text-gray-400 uppercase tracking-widest font-semibold">{isAr ? "حقول البيانات" : "Data Fields"}</span>
            <div className="flex items-center gap-3 mt-1">
               <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded flex items-center gap-1"><Hash className="w-3 h-3"/> {health.numeric_count}</span>
               <span className="text-xs font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded flex items-center gap-1"><List className="w-3 h-3"/> {health.categorical_count}</span>
               <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded flex items-center gap-1"><Clock className="w-3 h-3"/> {health.datetime_count}</span>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-4 bg-gray-50 p-2.5 rounded-lg border border-gray-100">
           <div className="flex flex-col items-center px-3">
             <span className="text-[10px] text-gray-500 font-semibold">{isAr ? "نقص" : "Missing"}</span>
             <span className={`text-sm font-bold ${health.missing_pct > 5 ? 'text-amber-500' : 'text-emerald-500'}`}>{health.missing_pct}%</span>
           </div>
           <div className={`flex flex-col items-center px-3 ${isAr ? 'border-r' : 'border-l'} border-gray-200`}>
             <span className="text-[10px] text-gray-500 font-semibold">{isAr ? "تكرار" : "Duplicates"}</span>
             <span className={`text-sm font-bold ${health.duplicate_pct > 5 ? 'text-amber-500' : 'text-emerald-500'}`}>{health.duplicate_pct}%</span>
           </div>
           <div className={`flex flex-col items-center px-3 ${isAr ? 'border-r' : 'border-l'} border-gray-200`}>
             <span className="text-[10px] text-gray-500 font-semibold">{isAr ? "الجودة" : "Quality"}</span>
             <span className={`text-sm font-bold ${health.quality_score > 90 ? 'text-emerald-600' : 'text-amber-600'}`}>{health.quality_score}%</span>
           </div>
        </div>
      </section>

      {/* ── 2. KEY TAKEAWAYS ── */}
      {key_takeaways && key_takeaways.length > 0 && (
        <section>
          <SectionHeader icon={<Lightbulb className="w-4 h-4 text-yellow-500" />} title={isAr ? "الاستنتاجات الرئيسية" : "Key Takeaways"} isAr={isAr} />
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {key_takeaways.map((takeaway: string, idx: number) => (
                <li key={idx} className="flex items-start gap-3 bg-gray-50/50 p-3 rounded-lg border border-gray-100">
                  <div className="mt-0.5 w-5 h-5 flex-shrink-0 bg-blue-50 rounded-full flex items-center justify-center border border-blue-100 text-blue-600 text-xs font-bold">
                    {idx + 1}
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed font-medium">{takeaway}</p>
                </li>
              ))}
            </ul>
          </motion.div>
        </section>
      )}

      {/* ── 3. DATA QUALITY ── */}
      {quality_metrics && quality_metrics.length > 0 && (
        <section>
          <SectionHeader icon={<ShieldCheck className="w-4 h-4 text-emerald-500" />} title={isAr ? "جودة البيانات حسب العمود" : "Data Quality by Column"} isAr={isAr} />
          <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
             <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
               {quality_metrics.map((qm: any, idx: number) => (
                 <div key={idx} className="flex flex-col gap-1">
                   <div className="flex justify-between items-center text-xs">
                     <span className="font-semibold text-gray-700 truncate" title={qm.name}>{qm.name}</span>
                     <span className={`font-bold ${qm.missing_pct > 0 ? 'text-amber-500' : 'text-emerald-500'}`}>{qm.missing_pct}%</span>
                   </div>
                   <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                     <div className={`h-full rounded-full ${qm.missing_pct > 0 ? 'bg-amber-400' : 'bg-emerald-400'}`} style={{ width: `${Math.max(qm.missing_pct, 2)}%` }} />
                   </div>
                 </div>
               ))}
             </div>
          </div>
        </section>
      )}

      {/* ── 4. ANOMALIES ── */}
      {anomalies && anomalies.length > 0 && (
        <section>
          <SectionHeader icon={<Zap className="w-4 h-4 text-red-500" />} title={isAr ? "قيم غير معتادة" : "Unusual Values"} isAr={isAr} />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {anomalies.map((anom: any, idx: number) => (
              <motion.div key={idx} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="bg-red-50 border border-red-200 rounded-xl p-4 shadow-sm relative overflow-hidden flex flex-col justify-center">
                <div className="absolute -right-4 -top-4 opacity-5">
                  <AlertTriangle className="w-32 h-32 text-red-600" />
                </div>
                <div className="flex items-center gap-2 mb-2 relative z-10">
                   <AlertCircle className="w-4 h-4 text-red-600" />
                   <h3 className="font-bold text-red-900 text-sm">{anom.column}</h3>
                </div>
                <div className="text-2xl font-black text-red-700 mb-1 relative z-10">{anom.count} <span className="text-[10px] font-bold uppercase tracking-wider text-red-500 opacity-80">{isAr ? "سجلات غير عادية" : "Unusual Records"}</span></div>
                <p className="text-xs text-red-800 leading-relaxed relative z-10">{anom.description}</p>
              </motion.div>
            ))}
          </div>
        </section>
      )}

      {/* ── SHOW FULL DETAILS TOGGLE ── */}
      <div className="flex justify-center">
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="flex items-center gap-2 text-xs font-semibold text-gray-500 hover:text-blue-600 bg-white border border-gray-200 hover:border-blue-200 rounded-lg px-4 py-2 transition-all shadow-sm"
        >
          {showDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          {showDetails
            ? (isAr ? "إخفاء التفاصيل الفنية" : "Hide technical details")
            : (isAr ? "عرض التفاصيل الفنية الكاملة" : "Show full profiling details")
          }
        </button>
      </div>

      {showDetails && (<>

      {/* ── 5. TIME TRENDS ── */}
      {dtCols.length > 0 && (
        <section>
          <SectionHeader icon={<Clock className="w-4 h-4 text-emerald-500" />} title={isAr ? "اتجاهات الوقت" : "Time Profiling"} isAr={isAr} />
          <div className="grid grid-cols-1 gap-4">
            {dtCols.map(([name, data]: any) => (
              <div key={name} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-col lg:flex-row gap-6">
                 <div className="lg:w-1/4 flex flex-col justify-center border-b lg:border-b-0 lg:border-r border-gray-100 pb-4 lg:pb-0 lg:pr-6">
                    <h3 className="font-bold text-gray-900 text-lg flex items-center gap-2"><Clock className="w-4 h-4 text-emerald-500"/> {name}</h3>
                    <div className="mt-4 flex flex-col gap-3">
                       <div>
                         <span className="text-[10px] text-gray-400 uppercase tracking-widest block mb-0.5">{isAr ? "التغطية" : "Coverage"}</span>
                         <span className="text-xs font-semibold text-gray-700">{data.stats.min} <span className="text-gray-400 mx-1">→</span> {data.stats.max}</span>
                       </div>
                       {data.insight && (
                         <div className="bg-emerald-50 text-emerald-800 p-2.5 rounded text-xs leading-relaxed font-medium">
                           {data.insight}
                         </div>
                       )}
                    </div>
                 </div>
                 <div className="lg:w-3/4 h-[200px] w-full">
                    {data.trend && data.trend.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={data.trend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                          <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                          <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                          <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', fontSize: '12px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                          <Line type="monotone" dataKey="count" stroke="#10B981" strokeWidth={2} dot={false} activeDot={{ r: 6, fill: "#10B981", stroke: "#fff", strokeWidth: 2 }} />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex items-center justify-center text-gray-400 text-sm">{isAr ? "لا توجد بيانات اتجاه" : "No trend data"}</div>
                    )}
                 </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── 6. NUMERIC PROFILING ── */}
      {numericCols.length > 0 && (
        <section>
          <SectionHeader icon={<Hash className="w-4 h-4 text-blue-500" />} title={isAr ? "التوزيع الرقمي" : "Numeric Distribution"} isAr={isAr} />
          <div className="flex flex-col gap-4">
            {numericCols.map(([name, data]: any) => (
              <NumericAccordion key={name} name={name} data={data} isAr={isAr} />
            ))}
          </div>
        </section>
      )}

      {/* ── 7. CATEGORICAL COMPOSITION ── */}
      {catCols.length > 0 && (
        <section>
          <SectionHeader icon={<List className="w-4 h-4 text-amber-500" />} title={isAr ? "توزيع الفئات" : "Category Distribution"} isAr={isAr} />
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            {catCols.map(([name, data]: any) => (
              <div key={name} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-col h-[320px]">
                <div className="flex items-center justify-between mb-4 border-b border-gray-100 pb-3">
                  <h3 className="font-bold text-gray-900 truncate">{name}</h3>
                  <span className="text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-100 uppercase tracking-wider">{isAr ? "فئوي" : "Categorical"}</span>
                </div>
                
                <div className="flex-1 w-full min-h-0 relative mb-4">
                  {data.distribution && data.distribution.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={data.distribution} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
                        <XAxis type="number" hide />
                        <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#4B5563' }} axisLine={false} tickLine={false} width={80} />
                        <Tooltip cursor={{ fill: '#F3F4F6' }} formatter={(val: any, name: any, props: any) => [`${props.payload.percentage}% (${val})`, 'Count']} contentStyle={{ borderRadius: '8px', border: 'none', fontSize: '11px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                        <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={20}>
                          {data.distribution.map((_: any, index: number) => (
                            <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-xs">{isAr ? "لا توجد بيانات" : "No data"}</div>
                  )}
                </div>
                
                {data.insight && (
                  <div className="mt-auto pt-3 border-t border-gray-100 flex items-start gap-2 text-xs text-gray-600">
                    <Lightbulb className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
                    <span className="font-medium">{data.insight}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── 8. RELATIONSHIPS (SCATTER + HEATMAP) ── */}
      {correlations && correlations.length > 0 && (
        <section>
          <SectionHeader icon={<Activity className="w-4 h-4 text-purple-500" />} title={isAr ? "الترابط بين الأعمدة" : "Relationships & Correlations"} isAr={isAr} />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            
            {/* Scatter Plots */}
            {scatter_plots && scatter_plots.map((plot: any, idx: number) => {
              const corrObj = correlations.find((c: any) => (c.col1 === plot.col1 && c.col2 === plot.col2) || (c.col1 === plot.col2 && c.col2 === plot.col1));
              return (
                <div key={`scatter-${idx}`} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm h-[320px] flex flex-col">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-bold text-gray-900 text-sm truncate">{plot.col1} vs {plot.col2}</h3>
                    {corrObj && (
                      <span className={`text-[10px] font-bold px-2 py-1 rounded border ${corrObj.score > 0 ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-red-50 text-red-700 border-red-100'}`}>
                        {isAr ? "ارتباط:" : "Corr:"} {corrObj.score > 0 ? "+" : ""}{corrObj.score}
                      </span>
                    )}
                  </div>
                  <div className="flex-1 w-full relative min-h-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <ScatterChart margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
                        <XAxis type="number" dataKey="x" tick={{ fontSize: 9, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                        <YAxis type="number" dataKey="y" tick={{ fontSize: 9, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                        <ZAxis type="number" range={[15, 15]} />
                        <Tooltip cursor={{ strokeDasharray: '3 3' }} formatter={(val: any, name: any) => [val, name === 'x' ? plot.col1 : plot.col2]} contentStyle={{ borderRadius: '8px', border: 'none', fontSize: '11px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                        <Scatter data={plot.data} fill={corrObj && corrObj.score < 0 ? "#EF4444" : "#8B5CF6"} fillOpacity={0.6} />
                      </ScatterChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              );
            })}

            {/* Correlation List (Alternative to complex matrix if space is constrained) */}
            <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm h-[320px] overflow-y-auto">
               <h3 className="font-bold text-gray-900 text-sm mb-4 border-b border-gray-100 pb-2">{isAr ? "أقوى الارتباطات" : "Strongest Correlations"}</h3>
               <div className="flex flex-col gap-2">
                 {correlations.map((c: any, i: number) => (
                   <div key={i} className="flex items-center justify-between p-2 rounded hover:bg-gray-50 transition-colors border border-transparent hover:border-gray-100">
                     <div className="flex items-center gap-2 text-xs font-semibold text-gray-600">
                        <span>{c.col1}</span>
                        <span className="text-gray-300">↔</span>
                        <span>{c.col2}</span>
                     </div>
                     <span className={`text-xs font-bold px-2 py-0.5 rounded ${c.score > 0 ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'}`}>
                       {c.score > 0 ? "+" : ""}{c.score}
                     </span>
                   </div>
                 ))}
               </div>
            </div>

          </div>
        </section>
      )}

      </>)}{/* end showDetails */}

    </div>
  );
}

/* ── Sub-components ── */

function SectionHeader({ icon, title, isAr = false }: { icon: React.ReactNode, title: string, isAr?: boolean }) {
  return (
    <h2 className={`text-xs font-bold text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2 ${isAr ? 'flex-row-reverse pr-1' : 'pl-1'}`}>
      {icon}
      {title}
    </h2>
  );
}

function NumericAccordion({ name, data, isAr }: { name: string, data: any, isAr: boolean }) {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
       {/* Header */}
       <button onClick={() => setIsOpen(!isOpen)} className="w-full flex items-center justify-between p-4 bg-white hover:bg-gray-50 transition-colors">
          <div className="flex items-center gap-3">
             <Hash className="w-4 h-4 text-blue-500" />
             <span className="font-bold text-gray-900">{name}</span>
             {data.missing > 0 && <span className="text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded">{data.missing_pct}% {isAr ? "مفقود" : "Missing"}</span>}
          </div>
          <div className="flex items-center gap-4">
             {/* Mini stats preview */}
             <div className="hidden md:flex items-center gap-4 text-xs">
                <span className="text-gray-500">{isAr ? "المتوسط:" : "Mean:"} <strong className="text-gray-800">{Number(data.stats.mean).toLocaleString(undefined, { maximumFractionDigits: 1 })}</strong></span>
                <span className="text-gray-500">{isAr ? "الأقصى:" : "Max:"} <strong className="text-gray-800">{Number(data.stats.max).toLocaleString(undefined, { maximumFractionDigits: 1 })}</strong></span>
             </div>
             {isOpen ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
          </div>
       </button>

       {/* Body */}
       <AnimatePresence initial={false}>
         {isOpen && (
           <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden border-t border-gray-100">
             <div className="p-5 bg-[#FAFAFA] flex flex-col lg:flex-row gap-8 items-center">
                
                {/* Left: Stats & Box Plot */}
                <div className="w-full lg:w-1/3 flex flex-col gap-6">
                   {/* Custom CSS Box Plot */}
                   {data.stats && (
                     <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                       <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block mb-4">{isAr ? "انتشار التوزيع" : "Distribution Spread (Box Plot)"}</span>
                       <CustomBoxPlot stats={data.stats} />
                     </div>
                   )}
                   
                   {/* Stats Grid */}
                   <div className="grid grid-cols-4 gap-2 text-center">
                      <StatBlock label={isAr ? "أدنى" : "Min"} value={data.stats.min} />
                      <StatBlock label={isAr ? "الربع1" : "Q1"} value={data.stats.q1} />
                      <StatBlock label={isAr ? "الوسيط" : "Median"} value={data.stats.median} highlight />
                      <StatBlock label={isAr ? "الربع3" : "Q3"} value={data.stats.q3} />
                   </div>
                </div>

                {/* Right: Histogram */}
                <div className="w-full lg:w-2/3 h-[200px]">
                   {data.histogram && data.histogram.length > 0 ? (
                     <ResponsiveContainer width="100%" height="100%">
                       <BarChart data={data.histogram} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                         <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                         <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                         <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                         <Tooltip cursor={{ fill: '#F3F4F6' }} contentStyle={{ borderRadius: '8px', border: 'none', fontSize: '11px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                         <Bar dataKey="count" fill="#3B82F6" radius={[2, 2, 0, 0]} maxBarSize={40} />
                       </BarChart>
                     </ResponsiveContainer>
                   ) : (
                     <div className="h-full flex items-center justify-center text-gray-400 text-sm">{isAr ? "لا توجد بيانات توزيع" : "No histogram data"}</div>
                   )}
                </div>

             </div>
             {/* Insight Footer */}
             {data.insight && (
                <div className="bg-blue-50/50 p-3 px-5 border-t border-blue-100 flex items-center gap-2 text-xs text-blue-800">
                  <Lightbulb className="w-4 h-4 text-blue-500 flex-shrink-0" />
                  <span className="font-medium">{data.insight}</span>
                </div>
             )}
           </motion.div>
         )}
       </AnimatePresence>
    </div>
  );
}

function StatBlock({ label, value, highlight = false }: { label: string, value: number, highlight?: boolean }) {
  return (
    <div className={`flex flex-col p-2 rounded ${highlight ? 'bg-blue-50 border border-blue-100' : 'bg-gray-100'}`}>
       <span className="text-[9px] text-gray-500 uppercase tracking-widest">{label}</span>
       <span className={`text-xs font-bold truncate mt-0.5 ${highlight ? 'text-blue-700' : 'text-gray-800'}`}>
         {Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 })}
       </span>
    </div>
  );
}

// Visual HTML/CSS Box Plot based on stats
function CustomBoxPlot({ stats }: { stats: any }) {
  const { min, q1, median, q3, max } = stats;
  // If spread is 0, just show a line to avoid NaN
  const spread = max - min;
  if (spread === 0 || isNaN(spread)) {
    return <div className="h-4 bg-gray-200 rounded w-full" />;
  }

  // Calculate percentages for positioning (0 to 100%)
  const leftWhisker = 0; // min is always 0% relative to min
  const boxLeft = ((q1 - min) / spread) * 100;
  const boxWidth = ((q3 - q1) / spread) * 100;
  const medianPos = ((median - min) / spread) * 100;
  const rightWhisker = 100; // max is always 100% relative to min

  return (
    <div className="w-full py-4 relative flex items-center justify-center h-8">
      {/* Background track (optional, helps see full bounds) */}
      <div className="absolute w-full h-[1px] bg-gray-200 top-1/2" />
      
      {/* Whisker Line (Min to Max) */}
      <div className="absolute h-[2px] bg-gray-400 top-1/2 translate-y-[-50%]" style={{ left: `0%`, right: `0%` }} />
      
      {/* Min Tick */}
      <div className="absolute h-3 w-[2px] bg-gray-500 top-1/2 translate-y-[-50%]" style={{ left: `0%` }} />
      
      {/* Max Tick */}
      <div className="absolute h-3 w-[2px] bg-gray-500 top-1/2 translate-y-[-50%]" style={{ right: `0%` }} />

      {/* The Box (Q1 to Q3) */}
      <div 
        className="absolute h-6 bg-blue-100 border-2 border-blue-400 rounded-sm top-1/2 translate-y-[-50%]" 
        style={{ left: `${boxLeft}%`, width: `${Math.max(boxWidth, 1)}%` }}
      />
      
      {/* Median Line */}
      <div 
        className="absolute h-6 w-[2px] bg-blue-600 top-1/2 translate-y-[-50%] z-10" 
        style={{ left: `${medianPos}%` }}
      />
    </div>
  );
}
