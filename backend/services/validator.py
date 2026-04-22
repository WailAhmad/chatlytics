"""
Validator Module
----------------
Validates execution plans before they reach the execution engine.
- Checks metric columns exist in the active dataset schema
- Prevents hallucination by blocking unsupported patterns early
- Returns structured validation results
"""

from typing import Dict, Any, Tuple, Optional


ALWAYS_SUPPORTED_OPERATIONS = {"explain", "llm", "forecast"}

SPECIAL_OPERATIONS = {
    "maintenance",      # uses status_code=505, never metric column
    "net_balance",      # uses generation_kwh - load_kwh, no single metric
}


def validate_plan(plan: Dict[str, Any], schema_profile: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
    """
    Returns (is_valid, error_reason, suggestion).
    If is_valid is False, execution must be aborted and unsupported_metric returned.
    """
    operation = plan.get("operation", "unknown")
    execution_path = plan.get("execution_path", "llm")

    # LLM-only paths don't need column validation
    if execution_path == "llm" or operation in ALWAYS_SUPPORTED_OPERATIONS:
        return True, "", None

    # Special operations with fixed column requirements
    if operation == "maintenance":
        schema_cols = _get_all_columns(schema_profile)
        if "status_code" not in schema_cols:
            return False, "Column 'status_code' is required for maintenance queries but was not found in the dataset.", "Try asking about load_kwh trends instead."
        return True, "", None

    if operation == "net_balance":
        schema_cols = _get_all_columns(schema_profile)
        missing = [c for c in ["generation_kwh", "load_kwh"] if c not in schema_cols]
        if missing:
            return False, f"Net balance calculation requires columns {missing} which are missing from the dataset.", None
        return True, "", None

    # For standard operations, validate the metric column
    metric = plan.get("metric")
    if not metric:
        # No metric — allow (e.g. count, groupby without numeric)
        return True, "", None

    schema_cols = _get_all_columns(schema_profile)
    if metric not in schema_cols:
        # Try to suggest a close match
        suggestion = _find_closest(metric, schema_cols)
        suggestion_msg = f"Did you mean '{suggestion}'?" if suggestion else "Please check available columns."
        return False, f"Metric column '{metric}' does not exist in the dataset. {suggestion_msg}", suggestion

    # Validate companion_metric if present
    companion = plan.get("companion_metric")
    if companion and companion not in schema_cols:
        suggestion = _find_closest(companion, schema_cols)
        suggestion_msg = f"Did you mean '{suggestion}'?" if suggestion else "Please check available columns."
        return False, f"Companion metric column '{companion}' does not exist in the dataset. {suggestion_msg}", suggestion

    # Validate group_by columns
    group_by = plan.get("group_by", [])
    if isinstance(group_by, list):
        for col in group_by:
            if col not in schema_cols and col != "__date_group__":
                suggestion = _find_closest(col, schema_cols)
                suggestion_msg = f"Did you mean '{suggestion}'?" if suggestion else ""
                return False, f"Group-by column '{col}' does not exist in the dataset. {suggestion_msg}", suggestion

    return True, "", None


def _get_all_columns(schema_profile: Dict[str, Any]) -> set:
    """Extract all column names from schema_profile."""
    cols = set()

    # From column_types dict
    ct = schema_profile.get("column_types", {})
    if isinstance(ct, dict):
        cols.update(ct.keys())

    # From explicit column lists
    for key in ["numeric_columns", "categorical_columns", "datetime_columns"]:
        val = schema_profile.get(key, [])
        if isinstance(val, list):
            cols.update(val)

    # From health quality_metrics list
    for qm in schema_profile.get("quality_metrics", []):
        if isinstance(qm, dict) and "name" in qm:
            cols.add(qm["name"])

    return cols


def _find_closest(name: str, candidates: set) -> Optional[str]:
    """Find a candidate column name that contains the search term, or vice versa."""
    name_lower = name.lower()
    for c in sorted(candidates):
        c_lower = c.lower()
        if name_lower in c_lower or c_lower in name_lower:
            return c
    return None


def build_unsupported_response(reason: str, suggestion: Optional[str], plan: Dict[str, Any]) -> Dict[str, Any]:
    """Build the structured response returned when a query cannot be executed."""
    return {
        "result_type": "unsupported_metric",
        "primary_value": None,
        "unit": "",
        "records_used": 0,
        "applied_filters": plan.get("filters", {}),
        "grouped_result": [],
        "chart_data": [],
        "summary_stats": {
            "unsupported_reason": reason,
            "suggestion": suggestion or "No suggestion available.",
            "available_columns": plan.get("_available_columns", []),
        },
        "aggregation_string": "UNSUPPORTED",
    }
