/**
 * Layout Builder
 * ──────────────
 * Transforms a backend API response into a structured layout descriptor.
 * Fully dynamic — supports all result types including distribution.
 */

export interface KpiDescriptor {
  label: string;
  value: string;
  sub: string;
  color: string;
  icon: string;
}

export interface InsightLayout {
  layoutMode: "empty" | "overview" | "single_value" | "timeseries" | "table" | "distribution" | "error" | "explanation";
  answerType: "python" | "llm" | "hybrid" | "unknown";
  heroKpis: KpiDescriptor[];
  mainChart: {
    plotly_data: any[];
    plotly_layout: any;
    caption: string;
    empty_reason: string;
  };
  headline: string;
  summary: string;
  primaryValue: string | null;
  unit: string;
  keyFacts: string[];
  anomalies: string[];
  recommendations: string[];
  businessImplications: string[];
  aiInsights: string[];
  followUpQuestions: string[];
  suggestedQuestions: string[];
}

export function buildInsightLayout(response: any, stats: any, lang: string): InsightLayout {
  const empty: InsightLayout = {
    layoutMode: "empty",
    answerType: "unknown",
    heroKpis: [],
    mainChart: { plotly_data: [], plotly_layout: {}, caption: "", empty_reason: "" },
    headline: "",
    summary: "",
    primaryValue: null,
    unit: "",
    keyFacts: [],
    anomalies: [],
    recommendations: [],
    businessImplications: [],
    aiInsights: [],
    followUpQuestions: [],
    suggestedQuestions: [],
  };

  if (!response || response.status !== 200) {
    if (!stats) return empty;
    return { ...empty, layoutMode: "overview" };
  }

  const data = response.data;
  const resultType = data.answer?.result_type || "single_value";
  const answerType = data.answer?.answer_type || "unknown";
  const detInsights = data.insights?.deterministic || {};

  const heroKpis: KpiDescriptor[] = (detInsights.dynamic_kpis || []).map((k: any) => ({
    label: k.label,
    value: String(k.value),
    sub: k.sub || "",
    color: k.color || "gray",
    icon: k.icon || "hash",
  }));

  const chart = data.chart || {};

  // Headline: prefer LLM business-friendly title, fallback to deterministic answer
  const headline = data.answer?.headline || data.humanized_chat_answer || "";
  // Summary: LLM humanized explanation
  const summary = data.answer?.summary || "";

  return {
    layoutMode: resultType === "empty" ? "empty" : resultType,
    answerType: answerType,
    heroKpis,
    mainChart: {
      plotly_data: chart.plotly_data || [],
      plotly_layout: chart.plotly_layout || {},
      caption: chart.caption || "",
      empty_reason: chart.empty_reason || "",
    },
    headline,
    summary,
    primaryValue: data.answer?.primary_value != null ? String(data.answer.primary_value) : null,
    unit: data.answer?.unit || "",
    keyFacts: detInsights.insight_facts || detInsights.key_facts || [],
    anomalies: (data.anomalies || []).map((a: any) => typeof a === "string" ? a : (a.description || a.text || JSON.stringify(a))),
    recommendations: data.recommendations || [],
    businessImplications: detInsights.business_implications || [],
    aiInsights: data.insights?.ai || [],
    followUpQuestions: data.follow_up_questions || [],
    suggestedQuestions: data.suggested_questions || [],
  };
}

