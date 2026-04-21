"""
Query Planner Module
--------------------
Uses the LLM to map natural language questions into a strict JSON query plan.
Supports multi-turn conversation context for follow-up queries.
"""

import json
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


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
11. If the user asks for an EXPLANATION of the dataset, set execution_path="llm" and operation="explain".
12. If the user asks for a FORECAST, PROJECTION, or EXPECTATION: set operation="forecast", question_type="forecast", output_mode="timeseries", chart.type="line", execution_path="hybrid".
13. MAINTENANCE/DOWNTIME questions: set operation="maintenance", question_type="maintenance". NEVER use load_kwh/generation_kwh as metric for this.
14. NET BALANCE/SURPLUS/DEFICIT questions: set operation="net_balance", question_type="net_balance". Leave metric null.
15. PEAK + COMPANION (e.g. "load when generation peaked"): set operation="peak_with_companion", metric=primary peak metric, companion_metric=the secondary metric.
16. If the user specifies an HOUR range ("peak hours", "evening", specific hours), populate filters.hours_filter with a list of integers (0-23).
17. Return ONLY JSON.

=== TARGET JSON SCHEMA ===
{{
  "execution_path": "python|llm|hybrid",
  "task": "analyze|explain",
  "metric": "column_name_or_null",
  "metric_role": "load|generation|count|custom|unknown",
  "operation": "average|sum|max|min|count|rank|compare|trend|distribution|explain|forecast|maintenance|net_balance|peak_with_companion|unknown",
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
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY missing. Query planning failed.")
        return None

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

        # If follow-up, merge carry-over fields from prior plan
        if conversation_context and conversation_context.get("mode") != "new_query":
            plan = _merge_with_prior(plan, conversation_context)

        logger.info(f"Query Plan Generated: {json.dumps(plan, ensure_ascii=False)}")
        return plan

    except Exception as e:
        logger.error(f"Error in query planner: {e}", exc_info=True)
        return None


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
