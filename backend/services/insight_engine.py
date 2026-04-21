"""
Insight Engine Module
---------------------
Derives deterministic insights purely from execution results.
Z-score anomaly detection. Dynamic KPI generation.
Separate follow_up_questions vs suggested_questions with deduplication.
"""

import statistics
from typing import Dict, Any, List


def _detect_anomalies(values: List[float], labels: List[str], threshold: float = 2.0) -> List[Dict[str, Any]]:
    """Detect anomalies using Z-score method (mean ± threshold * std)."""
    if len(values) < 3:
        return []
    mean = statistics.mean(values)
    std = statistics.stdev(values)
    if std == 0:
        return []
    anomalies = []
    for i, val in enumerate(values):
        z = (val - mean) / std
        if abs(z) >= threshold:
            anomalies.append({
                "label": labels[i] if i < len(labels) else str(i),
                "value": round(val, 2),
                "z_score": round(z, 2),
                "direction": "spike" if z > 0 else "dip",
                "deviation_pct": round(abs(val - mean) / mean * 100, 1) if mean != 0 else 0
            })
    return anomalies


def _deduplicate_questions(q_list: List[str]) -> List[str]:
    """Remove near-duplicate questions by normalized comparison."""
    seen = set()
    result = []
    for q in q_list:
        norm = q.lower().strip().rstrip("?").rstrip("؟").strip()
        # Collapse whitespace
        norm = " ".join(norm.split())
        if norm not in seen:
            seen.add(norm)
            result.append(q)
    return result


def _separate_follow_up_and_suggested(all_questions: List[str], question_type: str, metric: str, is_ar: bool) -> tuple:
    """
    Split questions into follow_up (deepen current answer) and suggested (explore new).
    Generate deterministic follow-ups based on current answer type.
    """
    follow_ups = []
    suggested = []

    # Deterministic follow-ups by question type
    if question_type in ("trend", "timeseries"):
        follow_ups = [
            f"هل توجد أي طفرات غير طبيعية في {metric}?" if is_ar else f"Were there any abnormal spikes in {metric}?",
            f"ما هي أعلى 5 أيام في {metric}?" if is_ar else f"What were the top 5 peak days for {metric}?",
        ]
    elif question_type in ("ranking", "table"):
        follow_ups = [
            f"أظهر اتجاه {metric} عبر الزمن" if is_ar else f"Show the trend of {metric} over time",
            f"ما هو توزيع {metric}?" if is_ar else f"Show the distribution of {metric}",
        ]
    elif question_type in ("distribution",):
        follow_ups = [
            f"أظهر الاتجاه اليومي لـ {metric}" if is_ar else f"Show the daily trend of {metric}",
            f"هل توجد طفرات غير طبيعية في {metric}?" if is_ar else f"Are there any anomalies in {metric}?",
        ]
    elif question_type in ("comparison",):
        follow_ups = [
            f"أظهر الاتجاه اليومي لـ {metric}" if is_ar else f"Show the daily trend of {metric}",
        ]

    # LLM questions go to suggested (broader exploration)
    for q in all_questions:
        q_norm = q.lower().strip()
        is_follow_up = False
        for fu in follow_ups:
            if _text_similarity(q_norm, fu.lower()) > 0.6:
                is_follow_up = True
                break
        if not is_follow_up:
            suggested.append(q)

    follow_ups = _deduplicate_questions(follow_ups)
    suggested = _deduplicate_questions(suggested)

    # Remove any suggested that duplicate follow-ups
    fu_norms = {q.lower().strip().rstrip("?").rstrip("؟").strip() for q in follow_ups}
    suggested = [q for q in suggested if q.lower().strip().rstrip("?").rstrip("؟").strip() not in fu_norms]

    return follow_ups[:3], suggested[:3]


def _text_similarity(a: str, b: str) -> float:
    """Simple word-overlap similarity."""
    a_words = set(a.lower().split())
    b_words = set(b.lower().split())
    if not a_words or not b_words:
        return 0
    return len(a_words & b_words) / max(len(a_words), len(b_words))


def build_deterministic_insights(plan: Dict[str, Any], execution_result: Dict[str, Any], schema_profile: Dict[str, Any]) -> Dict[str, Any]:
    insights = {
        "trend_label": "not_applicable",
        "top_dimension": None,
        "records_used": execution_result.get("records_used", 0),
        "comparison_delta": None,
        "comparison_direction": "same",
        "has_anomaly": False,
        "anomaly_details": [],
        "insight_facts": [],
        "key_facts": [],
        "opportunities": [],
        "business_implications": [],
        "dynamic_kpis": [],
        "follow_up_questions": [],
    }

    result_type = execution_result.get("result_type", "empty")
    chart_data = execution_result.get("chart_data", [])
    stats = execution_result.get("summary_stats", {})
    op = plan.get("operation", "sum")
    metric = plan.get("metric", "value")
    unit = execution_result.get("unit", "")
    lang = plan.get("language", "en")
    is_ar = lang == "ar"

    if result_type == "empty":
        empty_reason = stats.get("empty_reason", "")
        insights["insight_facts"].append(
            f"لم يتم العثور على بيانات مطابقة. {empty_reason}" if is_ar
            else f"No data matched the specified filters. {empty_reason}"
        )
        return insights

    # ── Dynamic KPIs ──
    kpis: List[Dict[str, Any]] = []

    pv = execution_result.get("primary_value")
    if pv is not None:
        pv_fmt = f"{pv:,.2f}" if isinstance(pv, float) else str(pv)
        kpis.append({
            "label": f"{op.capitalize()} {metric}" if not is_ar else f"{op.capitalize()} {metric}",
            "value": pv_fmt, "sub": unit, "color": "blue", "icon": "target"
        })

    if "mean" in stats and op not in ("mean", "average", "avg"):
        kpis.append({
            "label": "المتوسط" if is_ar else "Average",
            "value": f"{stats['mean']:,.2f}", "sub": unit, "color": "emerald", "icon": "bar_chart"
        })

    if "peak_day" in stats:
        kpis.append({
            "label": "يوم الذروة" if is_ar else "Peak Day",
            "value": stats["peak_day"],
            "sub": f"{stats.get('peak_day_value', 0):,.2f} {unit}", "color": "amber", "icon": "zap"
        })

    if "lowest_day" in stats and result_type == "timeseries":
        kpis.append({
            "label": "أدنى يوم" if is_ar else "Lowest Day",
            "value": stats["lowest_day"],
            "sub": f"{stats.get('lowest_day_value', 0):,.2f} {unit}", "color": "red", "icon": "arrow_down"
        })

    if "volatility_score" in stats and stats["volatility_score"] > 0:
        vol = stats["volatility_score"]
        vol_label = ("مستقر" if vol < 10 else "معتدل" if vol < 25 else "متقلب") if is_ar else ("Stable" if vol < 10 else "Moderate" if vol < 25 else "Volatile")
        kpis.append({
            "label": "التقلب" if is_ar else "Volatility",
            "value": f"{vol:.1f}%", "sub": vol_label, "color": "red" if vol > 25 else "amber" if vol > 10 else "emerald", "icon": "activity"
        })

    kpis.append({
        "label": "السجلات" if is_ar else "Records",
        "value": f"{insights['records_used']:,}", "sub": "مطابق" if is_ar else "matched",
        "color": "gray", "icon": "database"
    })

    # ── Timeseries Insights ──
    if result_type == "timeseries" and len(chart_data) > 1:
        vals = [float(d.get("value", 0)) for d in chart_data]
        labels = [str(d.get("name", "")) for d in chart_data]
        first_val, last_val = vals[0], vals[-1]

        try:
            pct_change = ((last_val - first_val) / first_val * 100) if first_val != 0 else 0
            insights["comparison_delta"] = round(pct_change, 2)

            if pct_change > 5:
                insights["trend_label"] = "increasing"
                insights["comparison_direction"] = "up"
            elif pct_change < -5:
                insights["trend_label"] = "decreasing"
                insights["comparison_direction"] = "down"
            else:
                insights["trend_label"] = "stable"

            trend_display = insights["trend_label"].capitalize()
            kpis.append({
                "label": "الاتجاه" if is_ar else "Trend",
                "value": ({"increasing": "تصاعدي", "decreasing": "تنازلي", "stable": "مستقر"}.get(insights["trend_label"], insights["trend_label"])) if is_ar else trend_display,
                "sub": f"{insights['comparison_delta']}%",
                "color": "emerald" if insights["comparison_direction"] == "up" else "red" if insights["comparison_direction"] == "down" else "gray",
                "icon": "trending_up" if insights["comparison_direction"] == "up" else "trending_down" if insights["comparison_direction"] == "down" else "minus"
            })

            mean_val = statistics.mean(vals)
            std_val = statistics.stdev(vals) if len(vals) > 1 else 0
            cv = (std_val / mean_val * 100) if mean_val != 0 else 0

            if is_ar:
                if cv < 10:
                    insights["key_facts"].append(f"الاتجاه مستقر بتباين {cv:.1f}% مما يشير إلى استهلاك ثابت ومنتظم.")
                elif cv < 25:
                    insights["key_facts"].append(f"تقلبات معتدلة (CV: {cv:.1f}%) مع تغيرات طبيعية يومية.")
                else:
                    insights["key_facts"].append(f"تقلب عالي (CV: {cv:.1f}%). البيانات غير مستقرة.")
                insights["key_facts"].append(f"تغير بنسبة {insights['comparison_delta']}% من {first_val:,.2f} إلى {last_val:,.2f}.")
                insights["business_implications"].append(f"{'الاستقرار' if cv < 15 else 'التقلب'} في {metric} {'يسهّل التخطيط' if cv < 15 else 'يتطلب مراقبة أوثق'}.")
            else:
                if cv < 10:
                    insights["key_facts"].append(f"The trend remained stable with only {cv:.1f}% variance, indicating consistent and predictable behavior.")
                elif cv < 25:
                    insights["key_facts"].append(f"Moderate fluctuations observed (CV: {cv:.1f}%) with natural day-to-day variation.")
                else:
                    insights["key_facts"].append(f"High volatility detected (CV: {cv:.1f}%). The data shows significant instability requiring attention.")
                insights["key_facts"].append(f"The metric moved {insights['comparison_delta']}% from {first_val:,.2f} to {last_val:,.2f} over the period.")
                insights["business_implications"].append(f"{'Stability' if cv < 15 else 'Volatility'} in {metric} {'supports reliable planning' if cv < 15 else 'requires closer monitoring and contingency planning'}.")

        except Exception:
            pass

        # Z-score anomaly detection
        if len(vals) >= 5:
            anomalies = _detect_anomalies(vals, labels, threshold=2.0)
            if anomalies:
                insights["has_anomaly"] = True
                insights["anomaly_details"] = anomalies
                for a in anomalies:
                    direction_str = ("ارتفاع حاد" if a["direction"] == "spike" else "انخفاض حاد") if is_ar else a["direction"]
                    insights["insight_facts"].append(
                        f"{'شذوذ' if is_ar else 'Anomaly'}: {a['label']} ({direction_str}) — {a['value']:,.2f} {unit} ({a['deviation_pct']}% {'من المتوسط' if is_ar else 'from mean'}, Z={a['z_score']})"
                    )

    # ── Table / Ranking Insights ──
    if result_type == "table" and len(chart_data) > 0:
        top_row = chart_data[0]
        insights["top_dimension"] = top_row.get("name")

        kpis.append({
            "label": "أعلى فئة" if is_ar else "Top Category",
            "value": str(insights["top_dimension"]),
            "sub": f"{top_row.get('value', 0):,.2f} {unit}" if isinstance(top_row.get("value"), (int, float)) else "",
            "color": "purple", "icon": "trophy"
        })

        insights["key_facts"].append(
            f"أعلى قيمة: {insights['top_dimension']} = {top_row.get('value'):,.2f} {unit}." if is_ar
            else f"Leader: {insights['top_dimension']} at {top_row.get('value'):,.2f} {unit}."
        )

        if len(chart_data) > 1:
            second = chart_data[1]
            try:
                diff = float(top_row["value"]) - float(second["value"])
                pct = (diff / float(second["value"]) * 100) if second["value"] != 0 else 0
                if is_ar:
                    insights["key_facts"].append(f"الفئة الأولى تتفوق على {second.get('name')} بـ {diff:,.2f} {unit} ({pct:.1f}%).")
                else:
                    insights["key_facts"].append(f"The leader exceeds {second.get('name')} by {diff:,.2f} {unit} ({pct:.1f}% gap).")
            except Exception:
                pass

        # Share of total
        if stats.get("share_of_total"):
            if is_ar:
                insights["key_facts"].append(f"حصة القائد: {stats['share_of_total']}% من الإجمالي.")
            else:
                insights["key_facts"].append(f"The leader accounts for {stats['share_of_total']}% of the total.")

        if len(chart_data) >= 3:
            rank_vals = [float(r.get("value", 0)) for r in chart_data]
            rank_labels = [str(r.get("name", "")) for r in chart_data]
            rank_anomalies = _detect_anomalies(rank_vals, rank_labels, threshold=1.5)
            if rank_anomalies:
                insights["has_anomaly"] = True
                insights["anomaly_details"].extend(rank_anomalies)

    # ── Single Value Insights ──
    if result_type == "single_value":
        if "min" in stats and "max" in stats:
            rng = stats["max"] - stats["min"]
            insights["key_facts"].append(
                f"النطاق: {stats['min']:,.2f} — {stats['max']:,.2f} {unit} (مدى: {rng:,.2f})" if is_ar
                else f"Range: {stats['min']:,.2f} — {stats['max']:,.2f} {unit} (spread: {rng:,.2f})"
            )
        if "std" in stats and stats["std"] > 0 and "mean" in stats:
            cv = (stats["std"] / stats["mean"] * 100) if stats["mean"] != 0 else 0
            insights["key_facts"].append(
                f"الانحراف المعياري: {stats['std']:,.2f} {unit} (CV: {cv:.1f}%)" if is_ar
                else f"Standard deviation: {stats['std']:,.2f} {unit} (CV: {cv:.1f}%)"
            )

    # ── Distribution Insights ──
    if result_type == "distribution":
        if "skewness" in stats:
            skew = stats["skewness"]
            if is_ar:
                shape = "متماثل تقريبًا" if abs(skew) < 0.5 else ("منحرف لليمين" if skew > 0 else "منحرف لليسار")
                insights["key_facts"].append(f"شكل التوزيع: {shape} (الانحراف: {skew}).")
            else:
                shape = "approximately symmetric" if abs(skew) < 0.5 else ("right-skewed" if skew > 0 else "left-skewed")
                insights["key_facts"].append(f"Distribution shape: {shape} (skewness: {skew}).")
        if "mean" in stats and "median" in stats:
            gap = abs(stats["mean"] - stats["median"])
            insights["key_facts"].append(
                f"المتوسط: {stats['mean']:,.2f} | الوسيط: {stats['median']:,.2f} (الفرق: {gap:,.2f})" if is_ar
                else f"Mean: {stats['mean']:,.2f} | Median: {stats['median']:,.2f} (gap: {gap:,.2f})"
            )

    # Merge key_facts into insight_facts for backward compatibility
    insights["insight_facts"] = insights["key_facts"] + insights["insight_facts"]

    # Cap KPIs at 5
    insights["dynamic_kpis"] = kpis[:5]

    return insights
