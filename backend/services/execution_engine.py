"""
Execution Engine Module
-----------------------
Safely executes structured Query Plans deterministically in pandas.
No dynamic eval/exec used.

Supports: sum, average, max, min, count, rank, trend, distribution, compare
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List


def _apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    if not filters:
        return df

    filtered_df = df.copy()

    # Date Range
    date_range = filters.get("date_range", {})
    start = date_range.get("start")
    end = date_range.get("end")

    if start or end:
        datetime_cols = filtered_df.select_dtypes(include=['datetime64[ns]']).columns
        if len(datetime_cols) > 0:
            dt_col = datetime_cols[0]
            if start:
                filtered_df = filtered_df[filtered_df[dt_col] >= pd.to_datetime(start)]
            if end:
                end_dt = pd.to_datetime(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                filtered_df = filtered_df[filtered_df[dt_col] <= end_dt]

    # Equals matches
    equals = filters.get("equals", {})
    if equals:
        for col, val in equals.items():
            if col in filtered_df.columns:
                if isinstance(val, str) and filtered_df[col].dtype == 'object':
                    filtered_df = filtered_df[filtered_df[col].astype(str).str.lower().str.strip() == val.lower().strip()]
                else:
                    filtered_df = filtered_df[filtered_df[col] == val]

    return filtered_df


def _infer_unit(metric: str) -> str:
    if not metric:
        return ""
    ml = metric.lower()
    if "load" in ml or "kwh" in ml or "generation" in ml:
        return "kWh"
    elif "price" in ml or "cost" in ml or "revenue" in ml:
        return "$"
    elif "percent" in ml or "pct" in ml:
        return "%"
    return ""


def _build_summary_stats(filtered_df: pd.DataFrame, metric: str, datetime_cols: List[str], pd_op: str) -> Dict[str, Any]:
    """Build comprehensive summary statistics for the metric column."""
    stats: Dict[str, Any] = {"operation_used": pd_op}

    if metric not in filtered_df.columns:
        return stats

    series = filtered_df[metric].dropna()
    if len(series) == 0:
        return stats

    stats["mean"] = round(float(series.mean()), 2)
    stats["median"] = round(float(series.median()), 2)
    stats["min"] = round(float(series.min()), 2)
    stats["max"] = round(float(series.max()), 2)
    stats["std"] = round(float(series.std()), 2) if len(series) > 1 else 0
    stats["sum"] = round(float(series.sum()), 2)
    stats["count"] = int(len(series))

    # Volatility score (coefficient of variation)
    if stats["mean"] != 0:
        stats["volatility_score"] = round(stats["std"] / abs(stats["mean"]) * 100, 1)
    else:
        stats["volatility_score"] = 0

    # Peak and lowest day
    if datetime_cols and len(datetime_cols) > 0:
        dt_col = datetime_cols[0]
        if dt_col in filtered_df.columns:
            try:
                daily = filtered_df.groupby(filtered_df[dt_col].dt.date)[metric].sum()
                if len(daily) > 0:
                    stats["peak_day"] = str(daily.idxmax())
                    stats["peak_day_value"] = round(float(daily.max()), 2)
                    stats["lowest_day"] = str(daily.idxmin())
                    stats["lowest_day_value"] = round(float(daily.min()), 2)
            except Exception:
                pass

    return stats


def _execute_maintenance(df: pd.DataFrame, plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Count maintenance periods using status_code == 505 ONLY.
    Never infers maintenance from load or generation.
    """
    if "status_code" not in df.columns:
        return {
            "result_type": "unsupported_metric", "primary_value": None, "unit": "",
            "records_used": 0, "applied_filters": plan.get("filters", {}),
            "grouped_result": [], "chart_data": [],
            "summary_stats": {"unsupported_reason": "Column 'status_code' not found. Cannot compute maintenance."}
        }

    maint_df = df[df["status_code"] == 505]
    group_by = plan.get("group_by", [])
    if not group_by:
        # Auto-group by asset_id if present, else region
        for col in ["asset_id", "region", "asset_type"]:
            if col in df.columns:
                group_by = [col]
                break

    if group_by and group_by[0] in maint_df.columns:
        gb_col = group_by[0]
        grouped = maint_df.groupby(gb_col).size().reset_index(name="value")
        grouped = grouped.sort_values("value", ascending=False)
        top_n = plan.get("top_n", 10) or 10
        grouped = grouped.head(top_n)
        chart_data = grouped.rename(columns={gb_col: "name"}).to_dict(orient="records")
        grouped_result = grouped.rename(columns={gb_col: "name"}).to_dict(orient="records")
        primary_value = float(grouped["value"].sum())
    else:
        primary_value = float(len(maint_df))
        chart_data = []
        grouped_result = []

    return {
        "result_type": "table",
        "primary_value": primary_value,
        "unit": "maintenance periods",
        "records_used": len(df),
        "applied_filters": plan.get("filters", {}),
        "grouped_result": grouped_result,
        "chart_data": chart_data,
        "summary_stats": {
            "operation_used": "count(status_code=505)",
            "total_maintenance_periods": int(len(maint_df)),
        }
    }


def _execute_net_balance(df: pd.DataFrame, plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute net grid balance = sum(generation_kwh) - sum(load_kwh).
    Strict formula. No fallbacks to other columns.
    """
    for col in ["generation_kwh", "load_kwh"]:
        if col not in df.columns:
            return {
                "result_type": "unsupported_metric", "primary_value": None, "unit": "",
                "records_used": 0, "applied_filters": plan.get("filters", {}),
                "grouped_result": [], "chart_data": [],
                "summary_stats": {"unsupported_reason": f"Column '{col}' is required for net balance but was not found."}
            }

    group_by = plan.get("group_by", [])
    if group_by and group_by[0] in df.columns:
        gb_col = group_by[0]
        grouped = df.groupby(gb_col).agg(
            generation=("generation_kwh", "sum"),
            load=("load_kwh", "sum")
        ).reset_index()
        grouped["value"] = (grouped["generation"] - grouped["load"]).round(2)
        grouped = grouped[[gb_col, "value"]].rename(columns={gb_col: "name"})
        chart_data = grouped.to_dict(orient="records")
        grouped_result = grouped.to_dict(orient="records")
        primary_value = float(grouped["value"].sum())
    else:
        total_gen = float(df["generation_kwh"].sum())
        total_load = float(df["load_kwh"].sum())
        primary_value = round(total_gen - total_load, 2)
        chart_data = []
        grouped_result = []

    unit = _infer_unit("load_kwh")
    return {
        "result_type": "single_value" if not group_by else "table",
        "primary_value": primary_value,
        "unit": unit,
        "records_used": len(df),
        "applied_filters": plan.get("filters", {}),
        "grouped_result": grouped_result,
        "chart_data": chart_data,
        "summary_stats": {
            "operation_used": "sum(generation_kwh) - sum(load_kwh)",
            "total_generation": round(float(df["generation_kwh"].sum()), 2),
            "total_load": round(float(df["load_kwh"].sum()), 2),
        }
    }


def _execute_peak_with_companion(df: pd.DataFrame, plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find peak of 'metric', then return the companion_metric value from that EXACT same row.
    Never uses mean/median fallback.
    """
    metric = plan.get("metric")
    companion = plan.get("companion_metric")

    if not metric or metric not in df.columns:
        return {
            "result_type": "unsupported_metric", "primary_value": None, "unit": "",
            "records_used": 0, "applied_filters": plan.get("filters", {}),
            "grouped_result": [], "chart_data": [],
            "summary_stats": {"unsupported_reason": f"Peak metric '{metric}' not found."}
        }
    if not companion or companion not in df.columns:
        return {
            "result_type": "unsupported_metric", "primary_value": None, "unit": "",
            "records_used": 0, "applied_filters": plan.get("filters", {}),
            "grouped_result": [], "chart_data": [],
            "summary_stats": {"unsupported_reason": f"Companion metric '{companion}' not found."}
        }

    peak_idx = df[metric].idxmax()
    peak_row = df.loc[peak_idx]
    peak_val = float(peak_row[metric])
    companion_val = float(peak_row[companion]) if pd.notna(peak_row[companion]) else None

    dt_cols = df.select_dtypes(include=["datetime64[ns]"]).columns
    peak_ts = str(peak_row[dt_cols[0]]) if len(dt_cols) > 0 else "unknown"

    unit = _infer_unit(metric)
    return {
        "result_type": "single_value",
        "primary_value": peak_val,
        "unit": unit,
        "records_used": len(df),
        "applied_filters": plan.get("filters", {}),
        "grouped_result": [],
        "chart_data": [
            {"name": metric, "value": peak_val},
            {"name": companion, "value": companion_val or 0},
        ],
        "summary_stats": {
            "operation_used": f"row_at_max({metric})[{companion}]",
            "peak_value": peak_val,
            "companion_value": companion_val,
            "peak_timestamp": peak_ts,
            "note": "Companion value is from the exact same row as the peak. No fallback used."
        }
    }


def execute_query_plan(df: pd.DataFrame, plan: Dict[str, Any], schema_profile: Dict[str, Any]) -> Dict[str, Any]:
    filters = plan.get("filters", {})
    operation = plan.get("operation", "unknown")

    if operation == "forecast":
        # For forecasting, we need historical data to build the baseline.
        # Ignore future date_range filters that would result in an empty dataframe.
        if "date_range" in filters:
            filters = filters.copy()
            del filters["date_range"]

    filtered_df = _apply_filters(df, filters)

    # Apply hours_filter if present (but NOT when a semantic comparison will handle time windows)
    hours_filter = filters.get("hours_filter", [])
    has_semantic_compare = plan.get("_semantic_comparison") is not None
    if hours_filter and not has_semantic_compare:
        dt_cols = filtered_df.select_dtypes(include=["datetime64[ns]"]).columns
        if len(dt_cols) > 0:
            filtered_df = filtered_df[filtered_df[dt_cols[0]].dt.hour.isin(hours_filter)]

    # ── Specialized Executors ──
    if operation == "maintenance":
        return _execute_maintenance(filtered_df, plan)
    if operation == "net_balance":
        return _execute_net_balance(filtered_df, plan)
    if operation == "peak_with_companion":
        return _execute_peak_with_companion(filtered_df, plan)


    # Apply semantic filters (e.g., peak hours)
    semantic_filters = plan.get("_semantic_filters", [])
    for sf in semantic_filters:
        if sf["type"] == "hour_range":
            datetime_cols = filtered_df.select_dtypes(include=['datetime64[ns]']).columns
            if len(datetime_cols) > 0:
                dt_col = datetime_cols[0]
                filtered_df = filtered_df[filtered_df[dt_col].dt.hour.isin(sf["hours"])]

    # Handle semantic comparison (peak vs off-peak, morning vs evening)
    sem_compare = plan.get("_semantic_comparison")
    if sem_compare and sem_compare.get("type") == "peak_vs_offpeak":
        metric = plan.get("metric")
        if metric and metric in filtered_df.columns:
            datetime_cols_cmp = filtered_df.select_dtypes(include=['datetime64[ns]']).columns
            if len(datetime_cols_cmp) > 0:
                dt_col = datetime_cols_cmp[0]
                peak_df = filtered_df[filtered_df[dt_col].dt.hour.isin(sem_compare["peak_hours"])]
                offpeak_df = filtered_df[filtered_df[dt_col].dt.hour.isin(sem_compare["offpeak_hours"])]

                pd_op = {"average": "mean", "avg": "mean", "mean": "mean", "sum": "sum", "compare": "mean"}.get(
                    plan.get("operation", "mean").lower(), "mean"
                )
                peak_val = round(float(peak_df[metric].agg(pd_op)), 2) if len(peak_df) > 0 else 0
                offpeak_val = round(float(offpeak_df[metric].agg(pd_op)), 2) if len(offpeak_df) > 0 else 0

                # Use custom labels if provided (e.g., morning vs evening)
                labels = sem_compare.get("labels", [
                    f"Peak Hours ({sem_compare['peak_hours'][0]}-{sem_compare['peak_hours'][-1]})",
                    f"Off-Peak ({sem_compare['offpeak_hours'][0]}-{sem_compare['offpeak_hours'][-1]})"
                ])
                chart_data = [
                    {"name": labels[0], "value": peak_val},
                    {"name": labels[1], "value": offpeak_val},
                ]
                unit = _infer_unit(metric)
                delta = round(peak_val - offpeak_val, 2)
                ratio = round(peak_val / offpeak_val, 2) if offpeak_val != 0 else 0

                return {
                    "result_type": "table",
                    "primary_value": peak_val,
                    "unit": unit,
                    "records_used": len(peak_df) + len(offpeak_df),
                    "applied_filters": plan.get("filters", {}),
                    "grouped_result": chart_data,
                    "chart_data": chart_data,
                    "summary_stats": {
                        "operation_used": pd_op,
                        "peak_value": peak_val,
                        "offpeak_value": offpeak_val,
                        "delta": delta,
                        "ratio": ratio,
                        "peak_records": len(peak_df),
                        "offpeak_records": len(offpeak_df),
                    }
                }
    # Handle status_code split comparisons (normal vs outage)
    elif sem_compare and sem_compare.get("type") == "status_split":
        metric = plan.get("metric")
        col = sem_compare.get("column", "status_code")
        group_a = sem_compare["group_a"]
        group_b = sem_compare["group_b"]
        if metric and metric in filtered_df.columns and col in filtered_df.columns:
            pd_op = {"average": "mean", "avg": "mean", "mean": "mean", "sum": "sum", "compare": "mean"}.get(
                plan.get("operation", "mean").lower(), "mean"
            )
            df_a = filtered_df[filtered_df[col] == group_a["value"]]
            df_b = filtered_df[filtered_df[col] == group_b["value"]]
            val_a = round(float(df_a[metric].agg(pd_op)), 2) if len(df_a) > 0 else 0
            val_b = round(float(df_b[metric].agg(pd_op)), 2) if len(df_b) > 0 else 0

            chart_data = [
                {"name": group_a["label"], "value": val_a},
                {"name": group_b["label"], "value": val_b},
            ]
            unit = _infer_unit(metric)
            delta = round(val_a - val_b, 2)
            ratio = round(val_a / val_b, 2) if val_b != 0 else 0

            return {
                "result_type": "table",
                "primary_value": val_a,
                "unit": unit,
                "records_used": len(df_a) + len(df_b),
                "applied_filters": plan.get("filters", {}),
                "grouped_result": chart_data,
                "chart_data": chart_data,
                "summary_stats": {
                    "operation_used": pd_op,
                    f"{group_a['label']}_value": val_a,
                    f"{group_b['label']}_value": val_b,
                    f"{group_a['label']}_records": len(df_a),
                    f"{group_b['label']}_records": len(df_b),
                    "delta": delta,
                    "ratio": ratio,
                }
            }
    elif sem_compare and sem_compare.get("type") == "peak_vs_normal_days":
        metric = plan.get("metric")
        if metric and metric in filtered_df.columns:
            datetime_cols_cmp = filtered_df.select_dtypes(include=['datetime64[ns]']).columns
            if len(datetime_cols_cmp) > 0:
                dt_col = datetime_cols_cmp[0]
                
                # Compute daily totals to find peak days
                daily_totals = filtered_df.groupby(filtered_df[dt_col].dt.date)[metric].sum()
                if len(daily_totals) > 0:
                    # Top 10% of days are peak days (at least 1)
                    n_peak = max(1, int(len(daily_totals) * 0.10))
                    peak_dates = daily_totals.nlargest(n_peak).index.tolist()
                    
                    # Split dataset
                    peak_df = filtered_df[filtered_df[dt_col].dt.date.isin(peak_dates)]
                    normal_df = filtered_df[~filtered_df[dt_col].dt.date.isin(peak_dates)]
                    
                    pd_op = {"average": "mean", "avg": "mean", "mean": "mean", "sum": "sum"}.get(
                        plan.get("operation", "average").lower(), "mean"
                    )
                    
                    peak_val = round(float(peak_df[metric].agg(pd_op)), 2) if len(peak_df) > 0 else 0
                    normal_val = round(float(normal_df[metric].agg(pd_op)), 2) if len(normal_df) > 0 else 0

                    chart_data = [
                        {"name": "Peak Days (Top 10%)", "value": peak_val},
                        {"name": "Normal Days", "value": normal_val},
                    ]
                    unit = _infer_unit(metric)
                    delta = round(peak_val - normal_val, 2)
                    ratio = round(peak_val / normal_val, 2) if normal_val != 0 else 0

                    return {
                        "result_type": "table",
                        "primary_value": peak_val,
                        "unit": unit,
                        "records_used": len(filtered_df),
                        "applied_filters": plan.get("filters", {}),
                        "grouped_result": chart_data,
                        "chart_data": chart_data,
                        "summary_stats": {
                            "operation_used": pd_op,
                            "peak_value": peak_val,
                            "offpeak_value": normal_val,
                            "delta": delta,
                            "ratio": ratio,
                            "peak_records": len(peak_df),
                            "offpeak_records": len(normal_df),
                        }
                    }

    records_used = len(filtered_df)

    if records_used == 0:
        # Detailed empty reason
        corrections = plan.get("_filter_corrections", [])
        equals = plan.get("filters", {}).get("equals", {})
        date_range = plan.get("filters", {}).get("date_range", {})
        parts = []
        if equals:
            parts.append(f"equals filters: {equals}")
        if date_range.get("start") or date_range.get("end"):
            parts.append(f"date range: {date_range.get('start')} to {date_range.get('end')}")
        if semantic_filters:
            labels = [sf.get("label", "unknown") for sf in semantic_filters]
            parts.append(f"semantic filters: {', '.join(labels)}")
        if corrections:
            parts.append(f"corrections applied: {'; '.join(corrections)}")

        empty_reason = f"No records found. Applied: {' | '.join(parts) if parts else 'no filters'}."

        return {
            "result_type": "empty",
            "primary_value": None,
            "unit": "",
            "records_used": 0,
            "applied_filters": plan.get("filters", {}),
            "grouped_result": [],
            "chart_data": [],
            "summary_stats": {"empty_reason": empty_reason}
        }

    op = plan.get("operation", "sum").lower()
    metric = plan.get("metric")
    group_by = plan.get("group_by", [])
    if isinstance(group_by, str):
        group_by = [group_by]

    op_map = {
        "average": "mean", "avg": "mean", "mean": "mean",
        "sum": "sum",
        "max": "max",
        "min": "min",
        "count": "count",
        "rank": "sum",
    }
    pd_op = op_map.get(op, "sum")

    is_trend = op == "trend" or plan.get("output_mode") == "timeseries"
    is_distribution = op == "distribution"
    is_compare = op == "compare" or plan.get("question_type") == "comparison"
    datetime_cols = schema_profile.get("datetime_columns", [])

    # Auto-group by date for "top N days" queries
    limit = plan.get("limit", 10)
    if not group_by and op in ("max", "min", "rank") and limit and limit > 1 and datetime_cols:
        group_by = ["__date_group__"]
        filtered_df = filtered_df.copy()
        filtered_df['__date_group__'] = filtered_df[datetime_cols[0]].dt.date
        pd_op = "sum"  # Sum per day to find top days

    if is_trend and datetime_cols:
        group_by = ["__date_group__"]
        filtered_df = filtered_df.copy()
        filtered_df['__date_group__'] = filtered_df[datetime_cols[0]].dt.date

    unit = _infer_unit(metric) if metric else ""

    # ── Distribution mode ──
    if is_distribution and metric and metric in filtered_df.columns:
        series = filtered_df[metric].dropna()
        if len(series) > 0:
            bin_count = min(20, max(5, int(len(series) ** 0.5)))
            counts, bin_edges = np.histogram(series, bins=bin_count)
            chart_data = []
            for i in range(len(counts)):
                label = f"{bin_edges[i]:.0f}-{bin_edges[i+1]:.0f}"
                chart_data.append({"name": label, "value": int(counts[i])})

            return {
                "result_type": "distribution",
                "primary_value": round(float(series.mean()), 2),
                "unit": unit,
                "records_used": records_used,
                "applied_filters": plan.get("filters", {}),
                "grouped_result": chart_data,
                "chart_data": chart_data,
                "summary_stats": {
                    "operation_used": "histogram",
                    "mean": round(float(series.mean()), 2),
                    "median": round(float(series.median()), 2),
                    "min": round(float(series.min()), 2),
                    "max": round(float(series.max()), 2),
                    "std": round(float(series.std()), 2) if len(series) > 1 else 0,
                    "sum": round(float(series.sum()), 2),
                    "count": int(len(series)),
                    "skewness": round(float(series.skew()), 2) if len(series) > 2 else 0,
                    "volatility_score": round(float(series.std() / series.mean() * 100), 1) if series.mean() != 0 else 0,
                }
            }

    is_forecast = op == "forecast"

    primary_value = None
    grouped_result = []
    chart_data = []
    result_type = "single_value"
    summary_stats = _build_summary_stats(filtered_df, metric, datetime_cols, pd_op) if metric else {"operation_used": pd_op}

    # ── Forecast mode ──
    if is_forecast and metric and metric in filtered_df.columns and datetime_cols:
        dt_col = datetime_cols[0]
        agg_df = filtered_df.groupby(filtered_df[dt_col].dt.date)[metric].agg(pd_op).reset_index()
        agg_df.columns = ["date", "value"]
        agg_df = agg_df.sort_values(by="date")
        
        if len(agg_df) > 0:
            actual_mean = agg_df["value"].mean()
            last_actual_date = pd.to_datetime(agg_df["date"].max())
            
            # Build Actual trace
            for _, row in agg_df.iterrows():
                chart_data.append({"name": str(row["date"]), "value": float(row["value"]), "series": "Actual"})
            
            # Build Forecast trace (simple average projection for next 30 days)
            future_dates = [last_actual_date + pd.Timedelta(days=i) for i in range(1, 31)]
            for fd in future_dates:
                chart_data.append({"name": str(fd.date()), "value": float(actual_mean), "series": "Forecast"})
            
            summary_stats["forecast_basis"] = f"Historical average ({actual_mean:.2f})"
            summary_stats["forecast_method"] = "Simple Average Extrapolation"
            
            return {
                "result_type": "forecast",
                "primary_value": float(actual_mean),
                "unit": unit,
                "records_used": records_used,
                "applied_filters": plan.get("filters", {}),
                "grouped_result": [],
                "chart_data": chart_data,
                "summary_stats": summary_stats
            }

    if metric and metric in filtered_df.columns:
        if not group_by:
            val = filtered_df[metric].agg(pd_op)
            primary_value = float(val) if not pd.isna(val) else 0
        else:
            gb_col = group_by[0]
            if gb_col in filtered_df.columns:
                result_type = "timeseries" if is_trend else "table"
                agg_df = filtered_df.groupby(gb_col)[metric].agg(pd_op).reset_index()

                # Sorting
                sort_cfg = plan.get("sort", {})
                asc = sort_cfg.get("direction") == "asc"
                if not is_trend:
                    agg_df = agg_df.sort_values(by=metric, ascending=asc)

                limit = plan.get("limit", 10)
                if limit and limit > 0 and not is_trend:
                    agg_df = agg_df.head(limit)

                agg_df[gb_col] = agg_df[gb_col].astype(str)
                grouped_result = agg_df.to_dict(orient="records")
                chart_data = agg_df.rename(columns={gb_col: "name", metric: "value"}).to_dict(orient="records")

                if chart_data:
                    primary_value = float(chart_data[0]["value"])

                # Enrich summary_stats for table/ranking
                if result_type == "table" and len(chart_data) > 0:
                    summary_stats["top_category"] = chart_data[0].get("name")
                    summary_stats["top_category_value"] = chart_data[0].get("value")
                    if len(chart_data) > 1:
                        summary_stats["second_category"] = chart_data[1].get("name")
                        summary_stats["second_category_value"] = chart_data[1].get("value")
                        summary_stats["delta_to_second"] = round(float(chart_data[0]["value"]) - float(chart_data[1]["value"]), 2)
                    total = sum(float(r.get("value", 0)) for r in chart_data)
                    if total > 0:
                        summary_stats["share_of_total"] = round(float(chart_data[0]["value"]) / total * 100, 1)
    else:
        primary_value = records_used
        unit = "records"

    return {
        "result_type": result_type,
        "primary_value": primary_value,
        "unit": unit,
        "records_used": records_used,
        "applied_filters": plan.get("filters", {}),
        "grouped_result": grouped_result,
        "chart_data": chart_data,
        "summary_stats": summary_stats
    }
