"""
Response Builder Module
-----------------------
Builds deterministic answer text, step-by-step calculation explanations,
and formula-with-values strings directly from execution results.
No LLM calls. Fully traceable.
"""

from typing import Dict, Any, Optional, List


def build_aggregation_string(plan: Dict[str, Any], execution_result: Dict[str, Any]) -> str:
    operation = plan.get("operation", "unknown")
    metric = plan.get("metric", "?")
    filters = plan.get("filters", {})
    group_by = plan.get("group_by", [])
    date_range = filters.get("date_range", {})
    equals = filters.get("equals", {})
    hours = filters.get("hours_filter", [])

    op_map = {"average": "mean", "avg": "mean", "mean": "mean", "sum": "sum",
              "max": "max", "min": "min", "count": "count", "rank": "rank"}

    if operation == "maintenance":
        base = "count(rows) where status_code=505"
    elif operation == "net_balance":
        base = "sum(generation_kwh) - sum(load_kwh)"
    elif operation == "peak_with_companion":
        companion = plan.get("companion_metric", "?")
        base = f"row_at_max({metric})[{companion}]"
    elif operation == "forecast":
        base = f"forecast({metric}) via moving_average"
    elif operation == "trend":
        base = f"mean({metric}) grouped by date"
    elif operation == "distribution":
        base = f"histogram({metric})"
    else:
        pd_op = op_map.get(operation, operation)
        base = f"{pd_op}({metric})"

    parts = []
    eq_parts = [f"{k}='{v}'" for k, v in equals.items()]
    if eq_parts:
        parts.append(" AND ".join(eq_parts))
    if date_range.get("start") or date_range.get("end"):
        parts.append(f"between {date_range.get('start','?')} and {date_range.get('end','?')}")
    if hours:
        parts.append(f"hours IN {hours}")

    where_clause = " where " + " AND ".join(parts) if parts else ""

    group_clause = ""
    if group_by and operation not in ("net_balance", "trend"):
        group_clause = f" grouped by {', '.join(group_by)}"
    elif operation == "maintenance" and group_by:
        group_clause = f" grouped by {', '.join(group_by)}"

    records = execution_result.get("records_used")
    rec_note = f" [{records} rows]" if records else ""

    return f"{base}{where_clause}{group_clause}{rec_note}"


def build_calculation_steps(
    execution_result: Dict[str, Any],
    plan: Dict[str, Any],
    language: str = "en"
) -> List[str]:
    """Returns plain-English step-by-step calculation explanation."""
    is_ar = language == "ar"
    operation = plan.get("operation", "unknown")
    metric = plan.get("metric", "?")
    companion = plan.get("companion_metric", "")
    filters = plan.get("filters", {})
    group_by = plan.get("group_by", [])
    records = execution_result.get("records_used", 0)
    primary_value = execution_result.get("primary_value")
    unit = execution_result.get("unit", "")
    stats = execution_result.get("summary_stats", {})
    equals = filters.get("equals", {})
    date_range = filters.get("date_range", {})

    filter_desc = ""
    if equals:
        filter_desc += ", ".join(f"{k}='{v}'" for k, v in equals.items())
    if date_range.get("start"):
        filter_desc += f" between {date_range['start']} and {date_range.get('end', '?')}"
    if not filter_desc:
        filter_desc = "no additional filters" if not is_ar else "بدون فلاتر إضافية"

    steps = []

    if operation == "net_balance":
        total_gen = stats.get("total_generation", "?")
        total_load = stats.get("total_load", "?")
        result = primary_value
        if is_ar:
            steps = [
                f"الخطوة 1: تصفية البيانات بناءً على {filter_desc}",
                f"الخطوة 2: تم تحديد {records} سجل",
                f"الخطوة 3: المعادلة = sum(generation_kwh) - sum(load_kwh)",
                f"الخطوة 4: الأرقام الفعلية = {total_gen} - {total_load}",
                f"الخطوة 5: النتيجة = {round(float(result), 2) if result else '?'} {unit}",
            ]
        else:
            steps = [
                f"Step 1: Filtered the dataset using {filter_desc}",
                f"Step 2: This returned {records} records",
                f"Step 3: Formula = sum(generation_kwh) - sum(load_kwh)",
                f"Step 4: Substituting actual values = {total_gen} - {total_load}",
                f"Step 5: Final result = {round(float(result), 2) if result else '?'} {unit}",
            ]

    elif operation == "maintenance":
        total = stats.get("total_maintenance_periods", "?")
        top = execution_result.get("grouped_result", [])[:3]
        top_str = ", ".join(f"{r.get('name','?')}: {r.get('value','?')}" for r in top)
        if is_ar:
            steps = [
                f"الخطوة 1: تصفية البيانات بناءً على {filter_desc}",
                f"الخطوة 2: تم تحديد {records} سجل",
                f"الخطوة 3: المعادلة = count(rows) حيث status_code = 505 فقط",
                f"الخطوة 4: إجمالي فترات الصيانة = {total}",
                f"الخطوة 5: أعلى الأصول: {top_str}",
            ]
        else:
            steps = [
                f"Step 1: Filtered the dataset using {filter_desc}",
                f"Step 2: This returned {records} records",
                f"Step 3: Formula = count(rows) where status_code = 505 ONLY",
                f"Step 4: Total maintenance periods found = {total}",
                f"Step 5: Top assets: {top_str}",
            ]

    elif operation == "peak_with_companion":
        peak_val = primary_value
        companion_val = stats.get("companion_value", "?")
        peak_ts = stats.get("peak_timestamp", "?")
        if is_ar:
            steps = [
                f"الخطوة 1: تصفية البيانات بناءً على {filter_desc}",
                f"الخطوة 2: تم تحديد {records} سجل",
                f"الخطوة 3: البحث عن الصف الذي يحتوي على أعلى قيمة لـ {metric}",
                f"الخطوة 4: وجدنا الذروة = {round(float(peak_val), 2) if peak_val else '?'} {unit} في {peak_ts}",
                f"الخطوة 5: من نفس الصف، قيمة {companion} = {companion_val}",
            ]
        else:
            steps = [
                f"Step 1: Filtered the dataset using {filter_desc}",
                f"Step 2: This returned {records} records",
                f"Step 3: Located the row with the maximum value of {metric}",
                f"Step 4: Peak = {round(float(peak_val), 2) if peak_val else '?'} {unit} at {peak_ts}",
                f"Step 5: From that exact same row, {companion} = {companion_val} (no mean/median fallback used)",
            ]

    elif operation in ("average", "avg", "mean"):
        total_sum = stats.get("sum", "?")
        count = stats.get("count", records)
        val = round(float(primary_value), 2) if primary_value is not None else "?"
        gb_str = f" grouped by {', '.join(group_by)}" if group_by else ""
        if is_ar:
            steps = [
                f"الخطوة 1: تصفية البيانات بناءً على {filter_desc}",
                f"الخطوة 2: تم تحديد {records} سجل",
                f"الخطوة 3: المعادلة = sum({metric}) / count{gb_str}",
                f"الخطوة 4: الأرقام الفعلية = {total_sum} / {count}",
                f"الخطوة 5: النتيجة = {val} {unit}",
            ]
        else:
            steps = [
                f"Step 1: Filtered the dataset using {filter_desc}",
                f"Step 2: This returned {records} records",
                f"Step 3: Formula = sum({metric}) / count{gb_str}",
                f"Step 4: Substituting actual values = {total_sum} / {count}",
                f"Step 5: Final result = {val} {unit}",
            ]

    elif operation in ("sum",):
        val = round(float(primary_value), 2) if primary_value is not None else "?"
        if is_ar:
            steps = [
                f"الخطوة 1: تصفية البيانات بناءً على {filter_desc}",
                f"الخطوة 2: تم تحديد {records} سجل",
                f"الخطوة 3: المعادلة = sum({metric})",
                f"الخطوة 4: مجموع جميع القيم = {val} {unit}",
            ]
        else:
            steps = [
                f"Step 1: Filtered the dataset using {filter_desc}",
                f"Step 2: This returned {records} records",
                f"Step 3: Formula = sum({metric})",
                f"Step 4: Sum of all values = {val} {unit}",
            ]

    elif operation in ("max", "min"):
        val = round(float(primary_value), 2) if primary_value is not None else "?"
        if is_ar:
            steps = [
                f"الخطوة 1: تصفية البيانات بناءً على {filter_desc}",
                f"الخطوة 2: تم تحديد {records} سجل",
                f"الخطوة 3: البحث عن القيمة {'الأعلى' if operation=='max' else 'الأدنى'} لـ {metric}",
                f"الخطوة 4: النتيجة = {val} {unit}",
            ]
        else:
            steps = [
                f"Step 1: Filtered the dataset using {filter_desc}",
                f"Step 2: This returned {records} records",
                f"Step 3: Found the {'maximum' if operation=='max' else 'minimum'} value of {metric}",
                f"Step 4: Result = {val} {unit}",
            ]

    elif operation == "forecast":
        basis = stats.get("forecast_basis", "historical average")
        val = round(float(primary_value), 2) if primary_value is not None else "?"
        if is_ar:
            steps = [
                f"الخطوة 1: استخدام كامل البيانات التاريخية للمقياس {metric}",
                f"الخطوة 2: حساب القاعدة: {basis}",
                f"الخطوة 3: المعادلة = moving_average({metric})",
                f"الخطوة 4: قيمة التوقع الأساسية = {val} {unit}",
                f"الخطوة 5: تم إسقاط هذه القيمة للأيام الـ 30 القادمة",
            ]
        else:
            steps = [
                f"Step 1: Used full historical data for metric {metric}",
                f"Step 2: Computed baseline: {basis}",
                f"Step 3: Formula = moving_average({metric})",
                f"Step 4: Baseline forecast value = {val} {unit}",
                f"Step 5: This value was projected forward for the next 30 days",
            ]

    else:
        # Generic fallback
        val = round(float(primary_value), 2) if primary_value is not None else "?"
        if is_ar:
            steps = [
                f"الخطوة 1: تصفية البيانات بناءً على {filter_desc}",
                f"الخطوة 2: تم تحديد {records} سجل",
                f"الخطوة 3: تطبيق العملية الحسابية على {metric}",
                f"الخطوة 4: النتيجة = {val} {unit}",
            ]
        else:
            steps = [
                f"Step 1: Filtered the dataset using {filter_desc}",
                f"Step 2: This returned {records} records",
                f"Step 3: Applied {operation} operation on {metric}",
                f"Step 4: Result = {val} {unit}",
            ]

    return steps


def build_formula_with_values(
    execution_result: Dict[str, Any],
    plan: Dict[str, Any],
) -> str:
    """Returns the formula with actual numeric values substituted in."""
    operation = plan.get("operation", "unknown")
    metric = plan.get("metric", "?")
    companion = plan.get("companion_metric", "")
    stats = execution_result.get("summary_stats", {})
    primary_value = execution_result.get("primary_value")
    val = round(float(primary_value), 2) if primary_value is not None else "?"
    unit = execution_result.get("unit", "")

    if operation == "net_balance":
        gen = stats.get("total_generation", "?")
        load = stats.get("total_load", "?")
        return f"Net Balance = {gen} - {load} = {val} {unit}"

    elif operation == "maintenance":
        total = stats.get("total_maintenance_periods", "?")
        return f"count(status_code=505) = {total} maintenance periods"

    elif operation == "peak_with_companion":
        companion_val = stats.get("companion_value", "?")
        peak_ts = stats.get("peak_timestamp", "?")
        return f"row_at_max({metric}) → peak={val} {unit} at {peak_ts}, {companion}={companion_val}"

    elif operation in ("average", "avg", "mean"):
        total_sum = stats.get("sum", "?")
        count = stats.get("count", execution_result.get("records_used", "?"))
        return f"mean({metric}) = {total_sum} ÷ {count} = {val} {unit}"

    elif operation == "sum":
        return f"sum({metric}) = {val} {unit}"

    elif operation in ("max", "min"):
        return f"{operation}({metric}) = {val} {unit}"

    elif operation == "forecast":
        basis = stats.get("forecast_basis", "historical mean")
        return f"forecast({metric}) based on [{basis}] → projected = {val} {unit}"

    return f"{operation}({metric}) = {val} {unit}"


def build_answer_text(
    execution_result: Dict[str, Any],
    plan: Dict[str, Any],
    aggregation_string: str,
    language: str = "en"
) -> Optional[str]:
    result_type = execution_result.get("result_type", "empty")
    primary_value = execution_result.get("primary_value")
    unit = execution_result.get("unit", "")
    operation = plan.get("operation", "unknown")
    metric = plan.get("metric", "")
    stats = execution_result.get("summary_stats", {})
    is_ar = language == "ar"

    if result_type == "empty":
        return None
    if result_type == "unsupported_metric":
        return stats.get("unsupported_reason", "This query is not supported.")

    if operation == "net_balance":
        if primary_value is None:
            return None
        net_val = round(float(primary_value), 2)
        sign = ("surplus" if not is_ar else "فائض") if net_val >= 0 else ("deficit" if not is_ar else "عجز")
        return (f"صافي توازن الشبكة هو {abs(net_val)} {unit} ({sign})." if is_ar
                else f"Net grid balance is {net_val} {unit} ({sign}).")

    if operation == "maintenance":
        top = execution_result.get("grouped_result", [])[:3]
        if not top:
            return ("لا يوجد سجل صيانة (status_code=505)." if is_ar
                    else "No maintenance records (status_code=505) found.")
        top_str = ", ".join(f"{r.get('name','?')}: {r['value']}" for r in top)
        return (f"فترات الصيانة (status_code=505): {top_str}." if is_ar
                else f"Maintenance periods (status_code=505): {top_str}.")

    if operation == "peak_with_companion":
        companion = plan.get("companion_metric", "")
        companion_val = stats.get("companion_value")
        if primary_value is None:
            return None
        return (f"ذروة {metric} كانت {round(float(primary_value), 2)} {unit}. في نفس الصف: {companion} = {companion_val}." if is_ar
                else f"Peak {metric} was {round(float(primary_value), 2)} {unit}. From that exact row: {companion} = {companion_val}.")

    if result_type == "single_value" and primary_value is not None:
        val = round(float(primary_value), 2)
        return (f"النتيجة هي {val} {unit}." if is_ar else f"The result is {val} {unit}.")

    if result_type == "table":
        top = execution_result.get("grouped_result", [])[:5]
        if not top:
            return None
        top_str = ", ".join(f"{list(r.values())[0]}: {list(r.values())[1]}" for r in top)
        return (f"أعلى النتائج: {top_str}." if is_ar else f"Top results: {top_str}.")

    if result_type == "timeseries":
        count = len(execution_result.get("chart_data", []))
        mean = stats.get("mean")
        mean_str = f" (avg: {round(float(mean), 2)} {unit})" if mean is not None else ""
        return (f"الاتجاه الزمني لـ {metric}: {count} نقطة{mean_str}." if is_ar
                else f"Time trend for {metric}: {count} data points{mean_str}.")

    if result_type == "forecast":
        basis = stats.get("forecast_basis", "historical average")
        if primary_value is not None:
            val = round(float(primary_value), 2)
            return (f"التوقع ({basis}): {val} {unit}. هذا تقدير إحصائي أساسي." if is_ar
                    else f"Forecast ({basis}): {val} {unit}. This is a simple statistical baseline.")

    return None
