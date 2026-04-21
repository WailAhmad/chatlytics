"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Language, translations } from "@/lib/i18n";
import { buildInsightLayout, InsightLayout, KpiDescriptor } from "@/lib/layoutBuilder";
import { DatasetProfiler } from "@/components/DatasetProfiler";
import { ChevronDown, ChevronRight, Code2, Search, BarChart3, Lightbulb, Hash } from "lucide-react";
import { PlotlyChart } from "@/components/PlotlyChart";

const fadeIn = { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0, transition: { duration: 0.35 } } };
const containerVariants = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const itemVariants = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 140, damping: 16 } } };

export function InsightZone({ lang, stats, response }: { lang: Language; stats: any; response: any }) {
  const t = translations[lang];
  const isAr = lang === "ar";

  if (!stats) {
    return (
      <div className="flex flex-col h-full items-center justify-center p-10 w-full bg-[#FAFAFA]">
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5 }} className="flex flex-col items-center justify-center max-w-md text-center">
          <div className="w-64 h-64 bg-white border border-gray-100 shadow-xl rounded-3xl flex items-center justify-center p-8 mb-8">
            <img src="/aldar_logo.png" alt="ALDAR" className="w-full h-full object-contain" onError={(e) => { e.currentTarget.style.display='none'; e.currentTarget.parentElement!.innerHTML='<h2 class="font-bold tracking-widest text-4xl text-gray-900">ALDAR</h2>'; }} />
          </div>
          <h2 className="text-xl font-bold text-gray-900 tracking-tight">{t.emptyStateTitle}</h2>
          <p className="text-base text-gray-500 mt-2">{t.emptyStateSub}</p>
        </motion.div>
      </div>
    );
  }

  const layout = buildInsightLayout(response, stats, lang);
  const data = response?.data;

  if (layout.layoutMode === "overview") {
    return <DatasetProfiler lang={lang} stats={stats} />;
  }

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6 w-full bg-[#FAFAFA]">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
          {isAr ? "رؤى الإجابة" : "Answer Insights"}
          {layout.answerType === "python" && <span className="bg-emerald-50 text-emerald-600 border border-emerald-200 px-2 py-0.5 rounded text-[10px] ml-2 flex items-center gap-1"><Code2 className="w-3 h-3"/> {isAr ? "محسوب" : "Calculated"}</span>}
          {layout.answerType === "llm" && <span className="bg-purple-50 text-purple-600 border border-purple-200 px-2 py-0.5 rounded text-[10px] ml-2 flex items-center gap-1">✨ {isAr ? "شرح بواسطة الذكاء الاصطناعي" : "Explained by AI"}</span>}
          {layout.answerType === "hybrid" && <span className="bg-blue-50 text-blue-600 border border-blue-200 px-2 py-0.5 rounded text-[10px] ml-2 flex items-center gap-1"><Search className="w-3 h-3"/> {isAr ? "محسوب ومفسر" : "Calculated + Interpreted"}</span>}
        </h2>
      </div>

      {/* Hero Card */}
      {layout.headline && (
        <motion.div {...fadeIn} className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
          <div className="p-5">
            <h3 className="text-lg font-bold text-gray-900 leading-tight">{layout.headline}</h3>
            {layout.summary && (
              <p className="text-sm text-gray-600 mt-3 leading-relaxed whitespace-pre-line">{layout.summary}</p>
            )}
            {/* Deterministic result badge */}
            {layout.primaryValue && (
              <div className="mt-3 inline-flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-1.5">
                <Code2 className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-sm font-bold text-emerald-800">
                  {isAr ? "النتيجة:" : "Result:"} {Number(layout.primaryValue).toLocaleString(undefined, { maximumFractionDigits: 2 })} {layout.unit}
                </span>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* ── Explainability Panels (labeled, expandable) ── */}
      {data && (
        <div className="flex flex-col gap-2">
          {/* Panel 1: How the request was interpreted */}
          {data.query_plan && (
            <ExpandableSection
              icon={<Search className="w-4 h-4 text-blue-600" />}
              title={isAr ? "كيف تم فهم سؤالك" : "How your question was understood"}
              color="blue"
              defaultOpen={false}
            >
              <InterpretationContent plan={data.query_plan} verification={data.verification} isAr={isAr} />
            </ExpandableSection>
          )}

          {/* Panel 2: How the result was calculated */}
          {data.insights?.deterministic?.calculation_steps?.length > 0 && (
            <ExpandableSection
              icon={<Lightbulb className="w-4 h-4 text-emerald-600" />}
              title={isAr ? "كيف تم حساب النتيجة" : "How the result was calculated"}
              color="emerald"
              defaultOpen={false}
            >
              <CalculationContent details={data.calculation_details} insights={data.insights} isAr={isAr} />
            </ExpandableSection>
          )}

          {/* Panel 3: Python details (advanced) */}
          {data.insights?.deterministic?.aggregation_string && (
            <ExpandableSection
              icon={<Code2 className="w-4 h-4 text-gray-500" />}
              title={isAr ? "تفاصيل الحساب المتقدمة" : "Advanced calculation details"}
              color="gray"
              defaultOpen={false}
            >
              <div className="space-y-3">
                <div className="bg-gray-900 rounded-lg p-3">
                  <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">
                    {isAr ? "الاستعلام الحسابي" : "Aggregation Query"}
                  </p>
                  <code className="text-xs font-mono text-emerald-400 break-all">
                    {data.insights.deterministic.aggregation_string}
                  </code>
                </div>
                {data.insights.deterministic.formula_with_values && (
                  <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                    <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">
                      {isAr ? "المعادلة" : "Formula"}
                    </p>
                    <code className="text-xs font-mono text-gray-800 break-all">
                      {data.insights.deterministic.formula_with_values}
                    </code>
                  </div>
                )}
                <div className="flex gap-3 text-xs">
                  <span className="text-gray-400">{isAr ? "السجلات:" : "Records:"}</span>
                  <span className="font-bold text-gray-700">
                    {(data.insights.deterministic.records_used || 0).toLocaleString()}
                  </span>
                </div>
              </div>
            </ExpandableSection>
          )}
        </div>
      )}

      {/* KPIs */}
      {layout.heroKpis.length > 0 && (
        <motion.div key={layout.heroKpis.map(k => k.label).join(",")} variants={containerVariants} initial="hidden" animate="show" className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {layout.heroKpis.map((kpi, i) => <DynamicKpiCard key={`${kpi.label}-${i}`} kpi={kpi} />)}
        </motion.div>
      )}

      {/* Chart OR KPI Fallback */}
      <motion.div key={JSON.stringify(layout.mainChart.plotly_layout)} initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col min-h-[350px]">
        {(!layout.mainChart.plotly_data || layout.mainChart.plotly_data.length === 0) ? (
          /* KPI fallback instead of empty "No Chart" */
          layout.primaryValue ? (
            <div className="m-auto flex flex-col items-center max-w-sm text-center py-8">
              <div className="w-20 h-20 bg-emerald-50 rounded-2xl flex items-center justify-center mb-4 border border-emerald-100">
                <Hash className="w-8 h-8 text-emerald-600" />
              </div>
              <div className="text-3xl font-black text-gray-900 mb-1">
                {Number(layout.primaryValue).toLocaleString(undefined, { maximumFractionDigits: 2 })}
                <span className="text-lg text-gray-500 font-medium ml-2">{layout.unit}</span>
              </div>
              <p className="text-sm text-gray-500 mt-2">{layout.headline}</p>
            </div>
          ) : (
            <div className="m-auto flex flex-col items-center max-w-sm text-center py-8">
              <div className="w-14 h-14 bg-gray-50 rounded-full flex items-center justify-center mb-4"><span className="text-xl">📊</span></div>
              <h3 className="text-base font-bold text-gray-800 mb-1">{layout.mainChart.plotly_layout?.title || (isAr ? "لا يوجد رسم بياني" : "No Chart Available")}</h3>
              <p className="text-sm text-gray-500">{layout.mainChart.empty_reason || (isAr ? "البيانات غير قابلة للتصور" : "The data cannot be visualized.")}</p>
            </div>
          )
        ) : (
          <>
             <PlotlyChart
               data={layout.mainChart.plotly_data}
               layout={layout.mainChart.plotly_layout}
               height="350px"
             />
             {layout.mainChart.caption && <p className="text-[11px] text-gray-500 mt-3 text-center italic">{layout.mainChart.caption}</p>}
          </>
        )}
      </motion.div>

      {/* AI Insights — always present */}
      <motion.div {...fadeIn} className="bg-blue-50/60 border border-blue-200 rounded-xl p-5">
        <h4 className="text-xs font-bold text-blue-800 uppercase tracking-wider mb-3 flex items-center gap-1.5"><span>✨</span> {isAr ? "رؤى ذكية" : "Insights"}</h4>
        {layout.aiInsights.length > 0 ? (
          <ul className="space-y-2">{layout.aiInsights.map((ins, i) => <li key={i} className="text-sm text-blue-900 leading-relaxed flex gap-2 items-start"><span className="text-blue-500 mt-0.5 shrink-0">•</span><span>{ins}</span></li>)}</ul>
        ) : (
          /* Deterministic fallback insights when LLM insights are missing */
          <ul className="space-y-2">
            {layout.primaryValue && (
              <li className="text-sm text-blue-900 leading-relaxed flex gap-2 items-start">
                <span className="text-blue-500 mt-0.5 shrink-0">•</span>
                <span>{isAr
                  ? `النتيجة المحسوبة هي ${Number(layout.primaryValue).toLocaleString(undefined, {maximumFractionDigits: 2})} ${layout.unit}`
                  : `The computed result is ${Number(layout.primaryValue).toLocaleString(undefined, {maximumFractionDigits: 2})} ${layout.unit}`
                }</span>
              </li>
            )}
            {data?.insights?.deterministic?.records_used && (
              <li className="text-sm text-blue-900 leading-relaxed flex gap-2 items-start">
                <span className="text-blue-500 mt-0.5 shrink-0">•</span>
                <span>{isAr
                  ? `تم الحساب من ${data.insights.deterministic.records_used.toLocaleString()} سجل مطابق`
                  : `Calculated from ${data.insights.deterministic.records_used.toLocaleString()} matching records`
                }</span>
              </li>
            )}
          </ul>
        )}
      </motion.div>

      {/* Key Facts */}
      {layout.keyFacts.length > 0 && (
        <motion.div {...fadeIn} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-1.5"><span>📋</span> {isAr ? "حقائق رئيسية" : "Key Facts"}</h4>
          <ul className="space-y-2">{layout.keyFacts.map((f, i) => <li key={i} className="text-sm text-gray-700 leading-relaxed flex gap-2 items-start"><span className="text-blue-400 mt-0.5 shrink-0 font-bold">▸</span><span>{f}</span></li>)}</ul>
        </motion.div>
      )}

      {/* Anomalies */}
      {layout.anomalies.length > 0 && (
        <motion.div {...fadeIn} className="bg-amber-50 border border-amber-200 rounded-xl p-5">
          <h4 className="text-xs font-bold text-amber-800 uppercase tracking-wider mb-2 flex items-center gap-1.5"><span>⚠️</span> {isAr ? "ملاحظات" : "Notes"}</h4>
          <ul className="space-y-1.5">{layout.anomalies.map((a, i) => <li key={i} className="text-sm text-amber-900 leading-relaxed flex gap-2 items-start"><span className="text-amber-500 mt-0.5">⚡</span><span>{a}</span></li>)}</ul>
        </motion.div>
      )}

    </div>
  );
}


/* ───── Expandable Section ───── */
function ExpandableSection({ icon, title, color, defaultOpen, children }: {
  icon: React.ReactNode; title: string; color: string; defaultOpen: boolean; children: React.ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const bgMap: Record<string, string> = { blue: "bg-blue-50/40 border-blue-100 hover:bg-blue-50/70", emerald: "bg-emerald-50/40 border-emerald-100 hover:bg-emerald-50/70", gray: "bg-gray-50 border-gray-100 hover:bg-gray-100/50" };
  const bgClass = bgMap[color] || bgMap.gray;

  return (
    <div className={`rounded-xl border overflow-hidden ${bgClass} transition-colors`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2.5 px-4 py-3 text-left"
      >
        {icon}
        <span className="text-xs font-semibold text-gray-700 flex-1">{title}</span>
        {isOpen ? <ChevronDown className="w-3.5 h-3.5 text-gray-400" /> : <ChevronRight className="w-3.5 h-3.5 text-gray-400" />}
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}


/* ───── Interpretation Content ───── */
function InterpretationContent({ plan, verification, isAr }: { plan: any; verification: any; isAr: boolean }) {
  const rows: [string, string][] = [];
  if (plan.metric) rows.push([isAr ? "المقياس" : "Metric", plan.metric]);
  if (plan.operation) rows.push([isAr ? "العملية" : "Operation", plan.operation]);
  if (plan.question_type) rows.push([isAr ? "نوع السؤال" : "Question Type", plan.question_type]);
  const dr = plan.filters?.date_range;
  if (dr?.start && dr?.end) rows.push([isAr ? "نطاق التاريخ" : "Date Range", `${dr.start} → ${dr.end}`]);
  const eq = plan.filters?.equals;
  if (eq && Object.keys(eq).length > 0) rows.push([isAr ? "الفلاتر" : "Filters", Object.entries(eq).map(([k, v]) => `${k} = ${v}`).join(", ")]);
  const gb = plan.group_by;
  if (gb && gb.length > 0) rows.push([isAr ? "التجميع حسب" : "Group By", gb.join(", ")]);
  if (plan.limit) rows.push([isAr ? "الحد" : "Limit", String(plan.limit)]);

  return (
    <div className="space-y-1.5">
      {rows.map(([label, value], i) => (
        <div key={i} className="flex gap-3 text-xs">
          <span className="text-gray-400 font-medium min-w-[100px] shrink-0">{label}</span>
          <span className="text-gray-800 font-mono">{value}</span>
        </div>
      ))}
    </div>
  );
}

/* ───── Calculation Content ───── */
function CalculationContent({ details, insights, isAr }: { details: any; insights: any; isAr: boolean }) {
  const det = insights?.deterministic || {};
  const steps: string[] = det.calculation_steps || [];
  const formula = det.formula_with_values || "";
  const records = det.records_used ?? details?.records_used ?? 0;

  return (
    <div className="space-y-3">
      {/* Step-by-step explanation */}
      {steps.length > 0 && (
        <ol className="space-y-2">
          {steps.map((step: string, i: number) => (
            <li key={i} className="flex gap-3 text-sm text-gray-700 leading-relaxed">
              <span className="shrink-0 w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 text-[10px] font-bold flex items-center justify-center mt-0.5">
                {i + 1}
              </span>
              <span>{step.replace(/^Step \d+: /i, "").replace(/^الخطوة \d+: /i, "")}</span>
            </li>
          ))}
        </ol>
      )}

      {/* Formula badge */}
      {formula && (
        <div className="bg-gray-900 rounded-lg p-3">
          <code className="text-xs font-mono text-emerald-400 break-all">{formula}</code>
        </div>
      )}

      {/* Records used */}
      <div className="text-xs text-gray-500">
        {isAr ? "السجلات المستخدمة:" : "Records used:"} <strong className="text-gray-800">{records.toLocaleString()}</strong>
      </div>
    </div>
  );
}

/* ───── Sub-components ───── */
function DynamicKpiCard({ kpi }: { kpi: KpiDescriptor }) {
  const colorClass: Record<string, string> = { blue: "text-blue-600", emerald: "text-emerald-600", purple: "text-purple-600", amber: "text-amber-600", red: "text-red-600", gray: "text-gray-900" };
  return (
    <motion.div variants={itemVariants} className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
      <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-1 truncate" title={kpi.label}>{kpi.label}</h4>
      <div className={`text-2xl font-bold truncate ${colorClass[kpi.color] || 'text-gray-900'}`}>{kpi.value}</div>
      <div className="text-[10px] text-gray-400 mt-1.5 truncate">{kpi.sub}</div>
    </motion.div>
  );
}
