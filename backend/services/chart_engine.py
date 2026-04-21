"""
Chart Engine Module
-------------------
Determines the most appropriate visualization based on execution result shape.
Generates fully valid Plotly.js JSON specifications.
"""

from typing import Dict, Any, List

def build_chart_spec(plan: Dict[str, Any], execution_result: Dict[str, Any], schema_profile: Dict[str, Any], llm_chart_type: str = "auto") -> Dict[str, Any]:
    result_type = execution_result.get("result_type", "empty")
    chart_data = execution_result.get("chart_data", [])
    lang = plan.get("language", "en")
    is_ar = lang == "ar"

    spec = {
        "plotly_data": [],
        "plotly_layout": {
            "title": "",
            "showlegend": False,
            "margin": {"t": 40, "r": 20, "b": 40, "l": 50},
            "paper_bgcolor": "transparent",
            "plot_bgcolor": "transparent",
            "xaxis": {"automargin": True},
            "yaxis": {"automargin": True}
        },
        "empty_reason": "No data available to visualize."
    }

    if llm_chart_type == "none" or result_type in ("empty", "unsupported_metric") or not chart_data:
        reason = execution_result.get("summary_stats", {}).get("empty_reason") or \
                 execution_result.get("summary_stats", {}).get("unsupported_reason") or \
                 "The query returned no results."
        spec["empty_reason"] = reason
        return spec

    op = plan.get("operation", "sum").capitalize()
    metric = plan.get("metric", "records")
    group_by_raw = plan.get("group_by", [])
    group_by = ", ".join(group_by_raw) if isinstance(group_by_raw, list) else str(group_by_raw)
    stats = execution_result.get("summary_stats", {})

    x_vals = [str(row.get("name", "")) for row in chart_data]
    y_vals = [row.get("value", 0) for row in chart_data]

    # Resolve actual plotly type based on LLM suggestion or fallback
    plotly_type = "bar"
    if llm_chart_type == "line": plotly_type = "scatter"
    elif llm_chart_type == "scatter": plotly_type = "scatter"
    elif llm_chart_type == "histogram": plotly_type = "bar" # pre-binned
    elif result_type == "timeseries": plotly_type = "scatter"

    # ── Forecast ──
    if result_type == "forecast":
        spec["plotly_layout"]["title"] = f"{'الفعلي مقابل المتوقع' if is_ar else 'Actual vs Forecast'}"
        spec["plotly_layout"]["showlegend"] = True
        
        actual_x = [str(row["name"]) for row in chart_data if row.get("series") == "Actual"]
        actual_y = [row["value"] for row in chart_data if row.get("series") == "Actual"]
        
        forecast_x = [str(row["name"]) for row in chart_data if row.get("series") == "Forecast"]
        forecast_y = [row["value"] for row in chart_data if row.get("series") == "Forecast"]

        # Link actual to forecast by adding the last actual point to the start of the forecast series
        if len(actual_x) > 0 and len(forecast_x) > 0:
            forecast_x.insert(0, actual_x[-1])
            forecast_y.insert(0, actual_y[-1])

        spec["plotly_data"] = [
            {
                "name": "Actual",
                "x": actual_x,
                "y": actual_y,
                "type": "scatter",
                "mode": "lines+markers",
                "line": {"color": "#3B82F6", "width": 3, "shape": "spline"},
                "marker": {"size": 6, "color": "#3B82F6"}
            },
            {
                "name": "Forecast",
                "x": forecast_x,
                "y": forecast_y,
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#8B5CF6", "width": 3, "dash": "dot", "shape": "spline"}
            }
        ]
        spec["empty_reason"] = ""
        return spec

    # ── Timeseries ──
    if result_type == "timeseries" or llm_chart_type == "line":
        spec["plotly_layout"]["title"] = f"{'اتجاه' if is_ar else 'Trend of'} {metric}"
        spec["plotly_data"] = [{
            "x": x_vals,
            "y": y_vals,
            "type": plotly_type,
            "mode": "lines+markers" if plotly_type == "scatter" else None,
            "line": {"color": "#10B981", "width": 3, "shape": "spline"} if plotly_type == "scatter" else None,
            "marker": {"size": 6, "color": "#10B981"},
            "fill": "tozeroy" if plotly_type == "scatter" else None,
            "fillcolor": "rgba(16, 185, 129, 0.1)" if plotly_type == "scatter" else None
        }]
        
        # Anomaly / peak annotation
        annotations = []
        if stats.get("peak_day"):
            peak_day = stats["peak_day"]
            try:
                peak_val = next(row["value"] for row in chart_data if str(row["name"]) == peak_day)
                annotations.append({
                    "x": peak_day,
                    "y": peak_val,
                    "text": "Peak",
                    "showarrow": True,
                    "arrowhead": 2,
                    "ax": 0,
                    "ay": -40
                })
            except StopIteration:
                pass
        spec["plotly_layout"]["annotations"] = annotations
        spec["empty_reason"] = ""

    # ── Distribution ──
    elif result_type == "distribution" or llm_chart_type == "histogram":
        spec["plotly_layout"]["title"] = f"{'توزيع' if is_ar else 'Distribution of'} {metric}"
        spec["plotly_layout"]["bargap"] = 0.05
        spec["plotly_data"] = [{
            "x": x_vals,
            "y": y_vals,
            "type": "bar",
            "marker": {"color": "#3B82F6", "line": {"width": 0}}
        }]
        spec["empty_reason"] = ""

    # ── Table / Ranking ──
    elif result_type == "table" or llm_chart_type == "bar":
        n_categories = len(chart_data)
        is_ranking = plan.get("operation") in ("rank", "max", "min") or plan.get("question_type") == "ranking"

        if is_ranking or n_categories <= 8:
            spec["plotly_layout"]["title"] = f"{'ترتيب' if is_ar else 'Ranking:'} {metric}"
            spec["plotly_data"] = [{
                "x": y_vals,
                "y": x_vals,
                "type": "bar",
                "orientation": "h",
                "marker": {"color": "#8B5CF6"}
            }]
            spec["plotly_layout"]["yaxis"]["autorange"] = "reversed" # Largest at top
        else:
            spec["plotly_layout"]["title"] = f"{op} {'لـ' if is_ar else 'of'} {metric}"
            spec["plotly_data"] = [{
                "x": x_vals,
                "y": y_vals,
                "type": plotly_type,
                "marker": {"color": "#3B82F6"}
            }]
        spec["empty_reason"] = ""

    # ── Single Value ──
    elif result_type == "single_value":
        spec["plotly_data"] = []
        spec["empty_reason"] = (
            "تم حساب قيمة إجمالية واحدة. لا يوجد تفصيل متاح للرسم البياني."
            if is_ar else
            "A single aggregate value was calculated. No breakdown is available for a chart."
        )

    return spec

