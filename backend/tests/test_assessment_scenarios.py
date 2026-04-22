"""
End-to-end assessment scenarios.

These tests exercise the public /ask API with the four questions from the
ALDAR brief and compare the response against pandas-computed ground truth.
They intentionally use deterministic planner paths, so they do not require an
LLM API key or network access.
"""

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.data_service import set_active_dataset


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data" / "Smart_Grid_Master_March_2026.csv"


def _client() -> TestClient:
    set_active_dataset(str(DATASET))
    return TestClient(app)


def _df() -> pd.DataFrame:
    data = pd.read_csv(DATASET)
    data["timestamp"] = pd.to_datetime(data["timestamp"], dayfirst=True, format="mixed")
    return data


def _ask(client: TestClient, question: str) -> dict:
    response = client.post("/ask", json={"question": question, "language": "en"})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["answer"]["trace"]["rows_considered"] > 0
    assert payload["verification"]["planner_fallback"] == "deterministic_rule"
    return payload


def test_q1_average_load_north_second_week_of_march():
    data = _df()
    expected_df = data[
        (data["region"] == "North_District")
        & (data["timestamp"] >= "2026-03-07")
        & (data["timestamp"] <= "2026-03-14 23:59:59")
    ]
    expected = round(float(expected_df["load_kwh"].mean()), 2)

    payload = _ask(
        _client(),
        "What was the average hourly load in North_District during the second week of March?",
    )

    assert payload["query_plan"]["operation"] == "average"
    assert payload["query_plan"]["filters"]["equals"]["region"] == "North_District"
    assert payload["calculation_details"]["records_used"] == len(expected_df)
    assert payload["answer"]["primary_value"] == pytest.approx(expected, abs=0.01)


def test_q2_peak_generation_on_march_12_with_companion_load():
    data = _df()
    day_df = data[
        (data["timestamp"] >= "2026-03-12")
        & (data["timestamp"] <= "2026-03-12 23:59:59")
    ]
    peak_row = day_df.loc[day_df["generation_kwh"].idxmax()]

    payload = _ask(
        _client(),
        "Identify the hour on March 12 where generation peaked and what was the load at that time.",
    )

    stats = payload["calculation_details"]["summary_stats"]
    assert payload["query_plan"]["operation"] == "peak_with_companion"
    assert payload["query_plan"]["filters"]["date_range"] == {
        "start": "2026-03-12",
        "end": "2026-03-12",
    }
    assert payload["query_plan"]["filters"]["hours_filter"] == []
    assert payload["calculation_details"]["records_used"] == len(day_df)
    assert payload["answer"]["primary_value"] == pytest.approx(float(peak_row["generation_kwh"]), abs=0.01)
    assert stats["companion_value"] == pytest.approx(float(peak_row["load_kwh"]), abs=0.01)
    assert stats["peak_timestamp"].startswith("2026-03-12")


def test_q3_highest_maintenance_hours_by_asset():
    data = _df()
    expected = (
        data[data["status_code"] == 505]
        .groupby("asset_id")
        .size()
        .sort_values(ascending=False)
    )
    expected_top = expected.index[0]
    expected_top_count = int(expected.iloc[0])

    payload = _ask(
        _client(),
        "Which assets had the highest maintenance hours during the month?",
    )

    grouped = payload["calculation_details"]["grouped_result"]
    assert payload["query_plan"]["operation"] == "maintenance"
    assert payload["query_plan"]["group_by"] == ["asset_id"]
    assert grouped[0]["name"] == expected_top
    assert grouped[0]["value"] == expected_top_count
    assert payload["calculation_details"]["summary_stats"]["total_maintenance_hours"] == int(expected.sum())


def test_q4_central_hub_solar_business_vs_offpeak():
    data = _df()
    solar = data[
        (data["region"] == "Central_Hub")
        & (data["asset_id"].str.contains("SOLAR", case=False, na=False))
    ]
    business = solar[solar["timestamp"].dt.hour.isin(range(8, 18))]
    offpeak = solar[solar["timestamp"].dt.hour.isin(list(range(0, 8)) + [22, 23])]
    expected_business = round(float(business["generation_kwh"].mean()), 2)
    expected_offpeak = round(float(offpeak["generation_kwh"].mean()), 2)

    payload = _ask(
        _client(),
        "Compare Central_Hub solar output during business hours vs off-peak hours.",
    )

    stats = payload["calculation_details"]["summary_stats"]
    assert payload["query_plan"]["operation"] == "compare"
    assert payload["query_plan"]["filters"]["equals"]["region"] == "Central_Hub"
    assert payload["answer"]["primary_value"] == pytest.approx(expected_business, abs=0.01)
    assert stats["peak_value"] == pytest.approx(expected_business, abs=0.01)
    assert stats["offpeak_value"] == pytest.approx(expected_offpeak, abs=0.01)
    assert stats["peak_records"] == len(business)
    assert stats["offpeak_records"] == len(offpeak)
