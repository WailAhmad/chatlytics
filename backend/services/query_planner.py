"""
Query Planner Module
--------------------
Uses the LLM to map natural language questions into a strict JSON query plan.
Supports multi-turn conversation context for follow-up queries.
"""

import json
import logging
import os
import re
import time
from calendar import monthrange
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

PLAN_CACHE_TTL_SECONDS = 600
_PLAN_CACHE: Dict[str, Dict[str, Any]] = {}

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

ORDINAL_WEEKS = {
    "first": 1,
    "1st": 1,
    "one": 1,
    "second": 2,
    "2nd": 2,
    "two": 2,
    "third": 3,
    "3rd": 3,
    "three": 3,
    "fourth": 4,
    "4th": 4,
    "four": 4,
    "fifth": 5,
    "5th": 5,
    "five": 5,
}

# ── Deterministic peak hours mapping ──
# These business phrases are mapped to hour ranges AFTER the LLM plan,
# ensuring they always work even if the LLM misses them.
PEAK_HOURS_MAP = {
    "morning peak": list(range(7, 11)),       # 07:00–10:00
    "morning": list(range(6, 12)),             # 06:00–11:00
    "evening peak": list(range(17, 22)),       # 17:00–21:00
    "evening": list(range(17, 22)),            # 17:00–21:00
    "night": list(range(22, 24)) + list(range(0, 6)),  # 22:00–05:00
    "off-peak": list(range(22, 24)) + list(range(0, 7)),  # 22:00–06:00
    "peak hours": list(range(7, 11)) + list(range(17, 22)),  # morning + evening
    "business hours": list(range(8, 18)),      # 08:00–17:00
    "afternoon": list(range(12, 17)),          # 12:00–16:00
    "midday": list(range(11, 14)),             # 11:00–13:00
    # Arabic equivalents
    "ساعات الذروة الصباحية": list(range(7, 11)),
    "ساعات الذروة المسائية": list(range(17, 22)),
    "ساعات الذروة": list(range(7, 11)) + list(range(17, 22)),
    "صباح": list(range(6, 12)),
    "مساء": list(range(17, 22)),
    "ليل": list(range(22, 24)) + list(range(0, 6)),
}


def _build_planner_prompt(schema_profile: Dict[str, Any], language: str, context_prompt: Optional[str] = None) -> str:
    schema_str = json.dumps(
        {k: v for k, v in schema_profile.items() if k not in ["sample_rows", "summary"]},
        indent=2
    )

    current_date = "2026-03-31"  # Fixed for demo context

    context_block = ""
    if context_prompt:
        context_block = f"\n{context_prompt}\n"

    return f"""
You are an expert Query Planner and Intelligent Router for an analytics copilot.
Your job is to read a user's question, look at the active dataset schema, and output a strict JSON Query Plan.
{context_block}
=== ACTIVE SCHEMA ===
{schema_str}

=== ROUTING RULES ===
You must classify the question into one of three execution paths:
1. "python": Use for exact calculations (counts, sums, averages, groupby, filtering, sorting, distributions, anomalies).
2. "llm": Use for semantic reasoning, dataset explanation, interpretation, business insights, or recommendations WITHOUT needing math.
3. "hybrid": Use when BOTH exact calculations AND semantic reasoning are needed.

=== PLANNER RULES ===
1. YOU MUST NEVER CALCULATE VALUES. The execution engine will do the math if execution_path is "python" or "hybrid".
2. YOU MUST NEVER GENERATE PYTHON CODE.
3. You must map the user's intent to the schema columns provided. Only reference columns that exist in the schema above.
4. Synonyms: "consumption"/"usage" = load, "output" = generation, "trend" = over time, "highest" = max/rank, "distribution"/"variability"/"spread" = distribution.
5. Reference date is ALWAYS 2026-03-31. "this month" = March 2026 (2026-03-01 to 2026-03-31), "last week" = 2026-03-25 to 2026-03-31, "second week of March" = 2026-03-07 to 2026-03-14.
6. For a SPECIFIC DAY like "March 12", set BOTH start and end to that same date.
7. If the user asks for a trend, set operation="trend", output_mode="timeseries", chart.type="line".
8. If the user asks for distribution, variability, or spread, set operation="distribution", output_mode="single_value".
9. If the user asks to compare two things, set operation="compare", question_type="comparison".
10. NEVER ADD FILTERS THE USER DID NOT EXPLICITLY MENTION. Do not guess or invent values for the "equals" filters.
11. If the user asks for a GENERAL EXPLANATION of the dataset structure, set execution_path="llm" and operation="explain". However, if they ask HOW to calculate a specific metric (e.g., "how did you calculate average load"), you MUST plan the actual calculation (e.g., operation="average") and set execution_path="hybrid" so the execution engine can generate the calculation steps for the LLM to explain.
12. If the user asks for a FORECAST, PROJECTION, or EXPECTATION: set operation="forecast", question_type="forecast", output_mode="timeseries", chart.type="line", execution_path="hybrid".
13. MAINTENANCE/DOWNTIME questions: set operation="maintenance", question_type="maintenance". NEVER use load_kwh/generation_kwh as metric for this.
14. NET BALANCE/SURPLUS/DEFICIT questions: set operation="net_balance", question_type="net_balance". Leave metric null.
15. PEAK + COMPANION (e.g. "load when generation peaked"): set operation="peak_with_companion", metric=primary peak metric, companion_metric=the secondary metric.
16. If the user specifies an HOUR range ("peak hours", "morning peak", "evening", specific hours), populate filters.hours_filter with a list of integers (0-23).
    Examples:
    - "morning peak hours" → hours_filter: [7, 8, 9, 10]
    - "evening peak" → hours_filter: [17, 18, 19, 20, 21]
    - "off-peak hours" → hours_filter: [22, 23, 0, 1, 2, 3, 4, 5, 6]
    - "peak hours" → hours_filter: [7, 8, 9, 10, 17, 18, 19, 20, 21]
    - "between 9am and 2pm" → hours_filter: [9, 10, 11, 12, 13]
17. STABILITY/CONSISTENCY questions (e.g., "most stable", "least variable", "lowest standard deviation", "most consistent"): set operation="stability", question_type="ranking", output_mode="table". The metric is the column to measure stability of. MUST have a group_by field (e.g., ["region"] or ["asset_id"]).
18. Return ONLY JSON.

=== TARGET JSON SCHEMA ===
{{
  "execution_path": "python|llm|hybrid",
  "task": "analyze|explain",
  "metric": "column_name_or_null",
  "metric_role": "load|generation|count|custom|unknown",
  "operation": "average|sum|max|min|count|rank|compare|trend|distribution|explain|forecast|maintenance|net_balance|peak_with_companion|stability|unknown",
  "companion_metric": "column_name_or_null",
  "group_by": ["column1"],
  "top_n": 10,
  "filters": {{
    "date_range": {{
      "start": "YYYY-MM-DD or null",
      "end": "YYYY-MM-DD or null"
    }},
    "equals": {{
      "column_name": "exact_value"
    }},
    "hours_filter": []
  }},
  "sort": {{
    "by": "column_or_metric",
    "direction": "asc|desc"
  }},
  "chart": {{
    "type": "line|bar|histogram|none",
    "x": "column_name_or_null",
    "y": "column_name_or_null"
  }},
  "output_mode": "single_value|table|timeseries|comparison",
  "language": "{language}",
  "question_type": "summary|trend|comparison|ranking|lookup|distribution|anomaly|explanation|forecast|maintenance|net_balance|unknown"
}}
"""


def generate_query_plan(
    question: str,
    schema_profile: Dict[str, Any],
    language: str = "en",
    conversation_context: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    cache_key = _build_plan_cache_key(question, schema_profile, language, conversation_context)
    cached = _get_cached_plan(cache_key)
    if cached:
        logger.info("Query plan cache hit")
        cached["_plan_cache_hit"] = True
        return cached

    # Prefer deterministic plans for known assessment/domain intents. This keeps
    # the demo-critical path fast and available even when the hosted LLM is
    # rate-limited.
    if not conversation_context or conversation_context.get("mode") == "new_query":
        deterministic = _build_deterministic_plan(question, schema_profile, language)
        if deterministic:
            _set_cached_plan(cache_key, deterministic)
            logger.info("Using deterministic rule planner for known intent.")
            return deterministic

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY missing. Trying deterministic fallback planner.")
        fallback = _build_deterministic_plan(question, schema_profile, language)
        if fallback:
            _set_cached_plan(cache_key, fallback)
        return fallback

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        # Extract context prompt if this is a follow-up
        context_prompt = None
        if conversation_context and conversation_context.get("mode") != "new_query":
            context_prompt = conversation_context.get("context_prompt")

        system_prompt = _build_planner_prompt(schema_profile, language, context_prompt)

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=500,
        )

        content = response.choices[0].message.content
        if not content:
            return None

        plan = json.loads(content.strip())

        # Safe fallback defaults
        plan.setdefault("filters", {})
        plan["filters"].setdefault("date_range", {"start": None, "end": None})
        plan["filters"].setdefault("equals", {})
        plan.setdefault("group_by", [])

        # ── Deterministic post-processing ──
        plan = _normalize_plan(plan, question)

        # If follow-up, merge carry-over fields from prior plan
        if conversation_context and conversation_context.get("mode") != "new_query":
            plan = _merge_with_prior(plan, conversation_context)

        _set_cached_plan(cache_key, plan)
        logger.info(f"Query Plan Generated: {json.dumps(plan, ensure_ascii=False)}")
        return plan

    except Exception as e:
        logger.error(f"Error in query planner: {e}", exc_info=True)
        fallback = _build_deterministic_plan(question, schema_profile, language)
        if fallback:
            _set_cached_plan(cache_key, fallback)
        return fallback


def _normalize_plan(plan: Dict[str, Any], question: str) -> Dict[str, Any]:
    plan.setdefault("filters", {})
    plan["filters"].setdefault("date_range", {"start": None, "end": None})
    plan["filters"].setdefault("equals", {})
    plan["filters"].setdefault("hours_filter", [])
    plan.setdefault("group_by", [])
    plan = _apply_date_range_rules(plan, question)
    plan = _apply_hours_filter_rules(plan, question)
    return plan


def _build_plan_cache_key(
    question: str,
    schema_profile: Dict[str, Any],
    language: str,
    conversation_context: Optional[Dict[str, Any]] = None,
) -> str:
    columns = ",".join(schema_profile.get("columns", []))
    row_count = schema_profile.get("row_count", 0)
    context_mode = (conversation_context or {}).get("mode", "new_query")
    prior = ""
    if conversation_context and context_mode != "new_query":
        prior_plan = conversation_context.get("base_query_plan", {}) or {}
        prior = json.dumps({
            "metric": prior_plan.get("metric"),
            "operation": prior_plan.get("operation"),
            "filters": prior_plan.get("filters"),
            "group_by": prior_plan.get("group_by"),
        }, sort_keys=True)
    return f"{language}|{question.strip().lower()}|{row_count}|{columns}|{context_mode}|{prior}"


def _get_cached_plan(cache_key: str) -> Optional[Dict[str, Any]]:
    entry = _PLAN_CACHE.get(cache_key)
    if not entry:
        return None
    if time.time() - entry["created_at"] > PLAN_CACHE_TTL_SECONDS:
        _PLAN_CACHE.pop(cache_key, None)
        return None
    return json.loads(json.dumps(entry["plan"]))


def _set_cached_plan(cache_key: str, plan: Dict[str, Any]) -> None:
    _PLAN_CACHE[cache_key] = {
        "created_at": time.time(),
        "plan": json.loads(json.dumps(plan)),
    }
    # Tiny bounded cache for POC use.
    if len(_PLAN_CACHE) > 128:
        oldest = sorted(_PLAN_CACHE.items(), key=lambda item: item[1]["created_at"])[:32]
        for key, _ in oldest:
            _PLAN_CACHE.pop(key, None)


def _build_deterministic_plan(
    question: str,
    schema_profile: Dict[str, Any],
    language: str = "en",
) -> Optional[Dict[str, Any]]:
    """
    Fallback planner for known assessment/domain intents. This is intentionally
    small: it protects demo-critical questions when the hosted LLM is rate
    limited, while leaving open-ended analytics to the LLM planner.
    """
    q_lower = question.lower()
    columns = set(schema_profile.get("columns", []))
    unique_values = schema_profile.get("unique_values", {})

    def base(metric: Optional[str], operation: str) -> Dict[str, Any]:
        return {
            "execution_path": "python",
            "task": "analyze",
            "metric": metric,
            "metric_role": "unknown",
            "operation": operation,
            "companion_metric": None,
            "group_by": [],
            "top_n": 10,
            "filters": {
                "date_range": {"start": None, "end": None},
                "equals": {},
                "hours_filter": [],
            },
            "sort": {"by": metric, "direction": "desc"},
            "chart": {"type": "none", "x": None, "y": metric},
            "output_mode": "single_value",
            "language": language,
            "question_type": "summary",
            "_planner_fallback": "deterministic_rule",
        }

    has_load = "load_kwh" in columns
    has_generation = "generation_kwh" in columns

    if any(term in q_lower for term in ["maintenance", "downtime", "scheduled", "صيانة"]):
        plan = base("status_code" if "status_code" in columns else None, "maintenance")
        plan["metric_role"] = "count"
        plan["question_type"] = "maintenance"
        plan["group_by"] = ["asset_id"] if "asset_id" in columns else ["region"] if "region" in columns else []
        plan["output_mode"] = "table"
        return _normalize_plan(plan, question)

    if has_generation and has_load and any(term in q_lower for term in ["highest generation", "generation peaked", "peak generation"]):
        plan = base("generation_kwh", "peak_with_companion")
        plan["metric_role"] = "generation"
        plan["companion_metric"] = "load_kwh"
        plan["question_type"] = "lookup"
        if any(term in q_lower for term in ["which hour", "what hour", "hour had"]):
            plan["_peak_grain"] = "hourly"
        return _normalize_plan(plan, question)

    if has_load and any(term in q_lower for term in ["average", "avg", "mean", "متوسط"]) and any(term in q_lower for term in ["load", "consumption", "حمل"]):
        plan = base("load_kwh", "average")
        plan["metric_role"] = "load"
        if "region" in columns:
            values = unique_values.get("region", [])
            for value in values:
                if str(value).split("_")[0].lower() in q_lower or str(value).lower() in q_lower:
                    plan["filters"]["equals"]["region"] = value
                    break
        return _normalize_plan(plan, question)

    if has_generation and "solar" in q_lower and any(term in q_lower for term in ["compare", "vs", "versus", "between", "قارن"]):
        plan = base("generation_kwh", "compare")
        plan["metric_role"] = "generation"
        plan["question_type"] = "comparison"
        plan["output_mode"] = "comparison"
        if "region" in columns:
            for value in unique_values.get("region", []):
                if str(value).lower() in q_lower or str(value).split("_")[0].lower() in q_lower:
                    plan["filters"]["equals"]["region"] = value
                    break
        return _normalize_plan(plan, question)

    if has_generation and has_load and any(term in q_lower for term in ["net grid balance", "grid balance", "net balance", "surplus", "deficit", "صافي"]):
        plan = base(None, "net_balance")
        plan["question_type"] = "net_balance"
        return _normalize_plan(plan, question)

    if "curtailment" in q_lower:
        plan = base("curtailment_flag", "count")
        plan["question_type"] = "summary"
        return _normalize_plan(plan, question)

    return None


def _apply_date_range_rules(plan: Dict[str, Any], question: str) -> Dict[str, Any]:
    """
    Deterministically resolves assessment-style date phrases and protects
    against the LLM interpreting "March 12" as hour 12.
    """
    q_lower = question.lower()
    exact_date_pattern = re.compile(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+([0-3]?\d)(?:st|nd|rd|th)?(?:,\s*2026)?\b"
    )
    exact_match = exact_date_pattern.search(q_lower)
    if exact_match:
        month_name, day_text = exact_match.groups()
        month_num = MONTHS.get(month_name)
        day = int(day_text)
        if month_num and 1 <= day <= monthrange(2026, month_num)[1]:
            date_value = f"2026-{month_num:02d}-{day:02d}"
            plan.setdefault("filters", {})
            plan["filters"]["date_range"] = {"start": date_value, "end": date_value}
            # A calendar-day phrase like "March 12" must not become hour 12.
            plan["filters"]["hours_filter"] = []
            logger.info("Deterministic exact date_range applied: %s", date_value)
            return plan

    pattern = re.compile(
        r"\b(?:(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th|one|two|three|four|five)\s+week\s+of\s+"
        r"|week\s+([1-5])\s+of\s+)"
        r"(january|february|march|april|may|june|july|august|september|october|november|december)\b"
    )
    match = pattern.search(q_lower)
    if not match:
        return plan

    ordinal_word, ordinal_digit, month_name = match.groups()
    week_num = int(ordinal_digit) if ordinal_digit else ORDINAL_WEEKS.get(ordinal_word)
    month_num = MONTHS.get(month_name)
    if not week_num or not month_num:
        return plan

    year = 2026
    last_day = monthrange(year, month_num)[1]
    start_day = 1 if week_num == 1 else ((week_num - 1) * 7)
    if start_day > last_day:
        return plan

    end_day = min(start_day + 7, last_day)
    date_range = {
        "start": f"{year}-{month_num:02d}-{start_day:02d}",
        "end": f"{year}-{month_num:02d}-{end_day:02d}",
    }
    plan.setdefault("filters", {})
    plan["filters"]["date_range"] = date_range
    logger.info("Deterministic week date_range applied: %s", date_range)
    return plan


def _apply_hours_filter_rules(plan: Dict[str, Any], question: str) -> Dict[str, Any]:
    """
    Deterministic post-processor: if the question mentions peak hours phrases
    but the LLM didn't populate hours_filter, inject it deterministically.
    This guarantees business-time questions always work.
    """
    existing_hours = plan.get("filters", {}).get("hours_filter", [])
    if existing_hours:
        return plan  # LLM already handled it

    q_lower = question.lower()
    for phrase, hours in PEAK_HOURS_MAP.items():
        if phrase in q_lower:
            plan.setdefault("filters", {})
            plan["filters"]["hours_filter"] = hours
            logger.info(f"Deterministic hours_filter applied: '{phrase}' → {hours}")
            break

    return plan


def _merge_with_prior(plan: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-LLM merge: ensure carry-over fields from previous plan
    are preserved if the LLM dropped them.
    """
    base = context.get("base_query_plan")
    carry = context.get("carry_over_fields", {})
    mode = context.get("mode", "new_query")

    if not base:
        return plan

    # Explanation mode → return exact prior plan with question_type override
    if mode == "explanation":
        result = dict(base)
        result["question_type"] = "explanation"
        result["language"] = plan.get("language", base.get("language", "en"))
        return result

    # Carry forward metric if not explicitly changed
    if carry.get("metric") and not plan.get("metric"):
        plan["metric"] = base.get("metric")
        plan["metric_role"] = base.get("metric_role", "unknown")

    # Carry forward operation if not explicitly changed
    if carry.get("metric") and not plan.get("operation"):
        plan["operation"] = base.get("operation")

    # Carry forward time range if not explicitly changed
    if carry.get("time_range"):
        plan_dr = plan.get("filters", {}).get("date_range", {})
        base_dr = base.get("filters", {}).get("date_range", {})
        if not plan_dr.get("start") and base_dr.get("start"):
            plan["filters"]["date_range"]["start"] = base_dr["start"]
        if not plan_dr.get("end") and base_dr.get("end"):
            plan["filters"]["date_range"]["end"] = base_dr["end"]

    # Carry forward group_by if not explicitly changed
    if carry.get("group_by") and not plan.get("group_by"):
        plan["group_by"] = base.get("group_by", [])

    # Merge equals filters (additive — new filters add to old ones)
    if carry.get("filters"):
        base_equals = base.get("filters", {}).get("equals", {})
        plan_equals = plan.get("filters", {}).get("equals", {})
        merged = {**base_equals, **plan_equals}
        plan["filters"]["equals"] = merged

    return plan
