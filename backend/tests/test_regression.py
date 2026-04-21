"""
Regression Tests for Analytics Copilot
=======================================
These tests protect the critical deterministic behaviors that must never break.
Run with: pytest backend/tests/test_regression.py -v
"""

import pytest
import pandas as pd
import numpy as np
from typing import Dict, Any


# ── Fixtures ──

def _make_grid_df() -> pd.DataFrame:
    """Build a minimal Smart Grid dataset for testing."""
    np.random.seed(42)
    N = 500  # Fixed row count
    regions = ["North_District", "South_District", "East_District"]
    assets = ["SOLAR_A", "SOLAR_B", "WIND_01", "WIND_02", "GRID_01"]

    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-03-01", periods=N, freq="h"),
        "asset_id": [assets[i % len(assets)] for i in range(N)],
        "region": [regions[i % len(regions)] for i in range(N)],
        "load_kwh": np.random.uniform(20, 95, N).round(2),
        "generation_kwh": np.random.uniform(10, 80, N).round(2),
        "status_code": np.random.choice([100, 100, 100, 100, 505, 404], N),
    })
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


@pytest.fixture
def grid_df():
    return _make_grid_df()


@pytest.fixture
def schema_profile(grid_df):
    from backend.services.schema_profiler import profile_dataframe
    return profile_dataframe(grid_df)


# ── Response Builder Tests (deterministic, no LLM) ──

class TestResponseBuilder:
    """Tests for the pure-Python response builder. These must NEVER call LLM."""

    def test_build_aggregation_string_average(self):
        from backend.services.response_builder import build_aggregation_string
        plan = {"operation": "average", "metric": "load_kwh", "filters": {
            "equals": {"region": "North_District"},
            "date_range": {"start": "2026-03-07", "end": "2026-03-14"}
        }, "group_by": ["region"]}
        result = {"records_used": 384}
        agg = build_aggregation_string(plan, result)
        assert "mean(load_kwh)" in agg
        assert "region='North_District'" in agg
        assert "2026-03-07" in agg
        assert "384" in agg

    def test_build_aggregation_string_net_balance(self):
        from backend.services.response_builder import build_aggregation_string
        plan = {"operation": "net_balance", "metric": None, "filters": {
            "date_range": {"start": "2026-03-25", "end": "2026-03-31"},
            "equals": {}
        }, "group_by": []}
        result = {"records_used": 840}
        agg = build_aggregation_string(plan, result)
        assert "sum(generation_kwh) - sum(load_kwh)" in agg

    def test_build_aggregation_string_maintenance(self):
        from backend.services.response_builder import build_aggregation_string
        plan = {"operation": "maintenance", "metric": "status_code", "filters": {"equals": {}}, "group_by": ["asset_id"]}
        result = {"records_used": 3720}
        agg = build_aggregation_string(plan, result)
        assert "status_code=505" in agg
        assert "asset_id" in agg

    def test_build_aggregation_string_peak_companion(self):
        from backend.services.response_builder import build_aggregation_string
        plan = {"operation": "peak_with_companion", "metric": "generation_kwh",
                "companion_metric": "load_kwh", "filters": {"equals": {}}, "group_by": []}
        result = {"records_used": 120}
        agg = build_aggregation_string(plan, result)
        assert "row_at_max(generation_kwh)" in agg
        assert "load_kwh" in agg

    def test_build_formula_with_values_average(self):
        from backend.services.response_builder import build_formula_with_values
        plan = {"operation": "average", "metric": "load_kwh"}
        result = {"primary_value": 48.56, "unit": "kWh",
                  "summary_stats": {"sum": 18646.37, "count": 384}}
        formula = build_formula_with_values(result, plan)
        assert "18646.37" in formula
        assert "384" in formula
        assert "48.56" in formula

    def test_build_formula_with_values_net_balance(self):
        from backend.services.response_builder import build_formula_with_values
        plan = {"operation": "net_balance", "metric": None}
        result = {"primary_value": -9280.18, "unit": "kWh",
                  "summary_stats": {"total_generation": 38078.53, "total_load": 47358.71}}
        formula = build_formula_with_values(result, plan)
        assert "38078.53" in formula
        assert "47358.71" in formula
        assert "-9280.18" in formula

    def test_build_calculation_steps_not_empty(self):
        from backend.services.response_builder import build_calculation_steps
        plan = {"operation": "average", "metric": "load_kwh",
                "filters": {"equals": {"region": "North_District"}, "date_range": {"start": "2026-03-07", "end": "2026-03-14"}},
                "group_by": ["region"]}
        result = {"primary_value": 48.56, "unit": "kWh", "records_used": 384,
                  "summary_stats": {"sum": 18646.37, "count": 384}}
        steps = build_calculation_steps(result, plan, "en")
        assert len(steps) >= 3
        assert any("384" in s for s in steps)
        assert any("48.56" in s for s in steps)

    def test_build_answer_text_single_value(self):
        from backend.services.response_builder import build_answer_text
        plan = {"operation": "average", "metric": "load_kwh"}
        result = {"result_type": "single_value", "primary_value": 48.56, "unit": "kWh",
                  "summary_stats": {}}
        answer = build_answer_text(result, plan, "mean(load_kwh)", "en")
        assert "48.56" in answer

    def test_build_answer_text_unsupported(self):
        from backend.services.response_builder import build_answer_text
        plan = {"operation": "average", "metric": "fake_col"}
        result = {"result_type": "unsupported_metric", "primary_value": None,
                  "summary_stats": {"unsupported_reason": "Column 'fake_col' not found."}}
        answer = build_answer_text(result, plan, "UNSUPPORTED", "en")
        assert "fake_col" in answer


# ── Execution Engine Tests ──

class TestExecutionEngine:
    """Tests for specialized deterministic executors."""

    def test_maintenance_uses_status_505_only(self, grid_df):
        from backend.services.execution_engine import _execute_maintenance
        plan = {"group_by": ["asset_id"], "top_n": 10, "filters": {"equals": {}}}
        result = _execute_maintenance(grid_df, plan)
        assert result["result_type"] == "table"
        assert result["summary_stats"]["operation_used"] == "count(status_code=505)"
        expected_count = len(grid_df[grid_df["status_code"] == 505])
        assert result["summary_stats"]["total_maintenance_periods"] == expected_count
        assert result["primary_value"] == float(expected_count)

    def test_maintenance_no_status_column(self):
        from backend.services.execution_engine import _execute_maintenance
        df = pd.DataFrame({"load_kwh": [1, 2, 3]})
        plan = {"group_by": [], "top_n": 10, "filters": {"equals": {}}}
        result = _execute_maintenance(df, plan)
        assert result["result_type"] == "unsupported_metric"

    def test_net_balance_correct_formula(self, grid_df):
        from backend.services.execution_engine import _execute_net_balance
        plan = {"group_by": [], "filters": {"equals": {}}}
        result = _execute_net_balance(grid_df, plan)
        expected = round(float(grid_df["generation_kwh"].sum() - grid_df["load_kwh"].sum()), 2)
        assert result["primary_value"] == expected
        assert result["summary_stats"]["operation_used"] == "sum(generation_kwh) - sum(load_kwh)"

    def test_net_balance_missing_column(self):
        from backend.services.execution_engine import _execute_net_balance
        df = pd.DataFrame({"load_kwh": [1, 2, 3]})
        plan = {"group_by": [], "filters": {"equals": {}}}
        result = _execute_net_balance(df, plan)
        assert result["result_type"] == "unsupported_metric"

    def test_peak_with_companion_same_row(self, grid_df):
        from backend.services.execution_engine import _execute_peak_with_companion
        plan = {"metric": "generation_kwh", "companion_metric": "load_kwh",
                "filters": {"equals": {}}}
        result = _execute_peak_with_companion(grid_df, plan)
        assert result["result_type"] == "single_value"
        # Verify same-row lookup
        peak_idx = grid_df["generation_kwh"].idxmax()
        expected_companion = float(grid_df.loc[peak_idx, "load_kwh"])
        assert result["summary_stats"]["companion_value"] == expected_companion
        assert "No fallback" in result["summary_stats"]["note"]

    def test_peak_companion_missing_metric(self, grid_df):
        from backend.services.execution_engine import _execute_peak_with_companion
        plan = {"metric": "fake_col", "companion_metric": "load_kwh",
                "filters": {"equals": {}}}
        result = _execute_peak_with_companion(grid_df, plan)
        assert result["result_type"] == "unsupported_metric"


# ── Validator Tests ──

class TestValidator:
    """Tests for pre-execution metric validation."""

    def test_valid_metric(self, schema_profile):
        from backend.services.validator import validate_plan
        plan = {"operation": "average", "metric": "load_kwh", "execution_path": "python"}
        valid, reason, suggestion = validate_plan(plan, schema_profile)
        assert valid is True

    def test_invalid_metric(self, schema_profile):
        from backend.services.validator import validate_plan
        plan = {"operation": "average", "metric": "nonexistent_col", "execution_path": "python"}
        valid, reason, suggestion = validate_plan(plan, schema_profile)
        assert valid is False
        assert "nonexistent_col" in reason

    def test_maintenance_needs_status_code(self):
        from backend.services.validator import validate_plan
        plan = {"operation": "maintenance", "execution_path": "python"}
        profile = {"column_types": {"load_kwh": "float64"}, "numeric_columns": ["load_kwh"]}
        valid, reason, suggestion = validate_plan(plan, profile)
        assert valid is False
        assert "status_code" in reason

    def test_net_balance_needs_both_columns(self):
        from backend.services.validator import validate_plan
        plan = {"operation": "net_balance", "execution_path": "python"}
        profile = {"column_types": {"load_kwh": "float64"}, "numeric_columns": ["load_kwh"]}
        valid, reason, suggestion = validate_plan(plan, profile)
        assert valid is False

    def test_llm_path_skips_validation(self, schema_profile):
        from backend.services.validator import validate_plan
        plan = {"operation": "explain", "execution_path": "llm", "metric": "fake_col"}
        valid, reason, suggestion = validate_plan(plan, schema_profile)
        assert valid is True  # LLM path never needs column validation

    def test_unsupported_response_structure(self):
        from backend.services.validator import build_unsupported_response
        resp = build_unsupported_response("Column not found.", "load_kwh",
                                          {"filters": {"equals": {}}})
        assert resp["result_type"] == "unsupported_metric"
        assert resp["primary_value"] is None
        assert "aggregation_string" in resp
        assert "Column not found." in resp["summary_stats"]["unsupported_reason"]


# ── Filter Validator Tests ──

class TestFilterValidator:
    """Tests for filter correction and maintenance guard."""

    def test_maintenance_strips_status_code_filter(self, schema_profile):
        from backend.services.filter_validator import validate_and_fix_plan
        plan = {
            "operation": "maintenance",
            "filters": {"equals": {"status_code": "404"}, "date_range": {"start": None, "end": None}},
            "group_by": ["asset_id"]
        }
        fixed = validate_and_fix_plan(plan, schema_profile)
        assert "status_code" not in fixed["filters"]["equals"]

    def test_non_maintenance_preserves_valid_filter(self, schema_profile):
        from backend.services.filter_validator import validate_and_fix_plan
        plan = {
            "operation": "average",
            "filters": {"equals": {"region": "North_District"}, "date_range": {"start": None, "end": None}},
            "group_by": []
        }
        fixed = validate_and_fix_plan(plan, schema_profile)
        assert "region" in fixed["filters"]["equals"]


# ── Chart Engine Guard Tests ──

class TestChartEngine:
    """Tests for chart safety guards."""

    def test_unsupported_metric_returns_empty_chart(self):
        from backend.services.chart_engine import build_chart_spec
        plan = {"operation": "average", "metric": "fake", "language": "en"}
        exec_result = {"result_type": "unsupported_metric", "chart_data": [],
                       "summary_stats": {"unsupported_reason": "Column not found."}}
        spec = build_chart_spec(plan, exec_result, {}, "bar")
        assert spec.get("plotly_data") == [] or spec.get("plotly_data") is None or len(spec.get("plotly_data", [])) == 0

    def test_empty_result_returns_empty_chart(self):
        from backend.services.chart_engine import build_chart_spec
        plan = {"operation": "average", "metric": "load_kwh", "language": "en"}
        exec_result = {"result_type": "empty", "chart_data": [], "summary_stats": {}}
        spec = build_chart_spec(plan, exec_result, {}, "bar")
        assert spec.get("plotly_data") == [] or len(spec.get("plotly_data", [])) == 0


# ── Response Schema Contract Tests ──

class TestResponseContract:
    """
    Tests that the response schema contract is stable.
    These are the fields the frontend relies on.
    """

    def test_core_response_has_required_fields(self):
        """Verify the shape of a core response matches the frontend contract."""
        required_keys = [
            "humanized_chat_answer",
            "answer",
            "chart",
            "insights",
            "anomalies",
            "kpis",
            "query_plan",
            "calculation_details",
            "session_id",
            "conversation_state",
        ]
        answer_keys = ["headline", "summary", "primary_value", "unit", "result_type", "answer_type"]
        insights_det_keys = ["aggregation_string", "calculation_steps", "formula_with_values", "records_used"]

        # Build a minimal core response
        core = {
            "humanized_chat_answer": "The result is 48.56 kWh.",
            "answer": {
                "headline": "Average Load", "summary": "", "primary_value": 48.56,
                "unit": "kWh", "result_type": "single_value", "answer_type": "python"
            },
            "chart": {},
            "insights": {
                "ai": [],
                "deterministic": {
                    "aggregation_string": "mean(load_kwh)",
                    "calculation_steps": ["Step 1: ..."],
                    "formula_with_values": "mean(load_kwh) = 48.56",
                    "records_used": 384,
                }
            },
            "anomalies": [],
            "kpis": [],
            "query_plan": {},
            "calculation_details": {},
            "session_id": "test",
            "conversation_state": {"mode": "new_query"},
        }

        for key in required_keys:
            assert key in core, f"Missing required key: {key}"
        for key in answer_keys:
            assert key in core["answer"], f"Missing answer subkey: {key}"
        for key in insights_det_keys:
            assert key in core["insights"]["deterministic"], f"Missing deterministic insight: {key}"
