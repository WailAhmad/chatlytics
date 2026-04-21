import json
import logging
import os
import pandas as pd
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Model priority: try the best model first, fall back on rate limit
PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"


def _call_groq(client, messages, temperature=0.2, max_tokens=800, response_format=None):
    """Call Groq with automatic fallback to smaller model on rate limit."""
    for model in [PRIMARY_MODEL, FALLBACK_MODEL]:
        try:
            kwargs = {"messages": messages, "model": model, "temperature": temperature, "max_tokens": max_tokens}
            if response_format:
                kwargs["response_format"] = response_format
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if content:
                if model == FALLBACK_MODEL:
                    logger.info(f"Used fallback model {FALLBACK_MODEL} due to rate limit on primary")
                return content
        except Exception as e:
            err_str = str(e)
            if "rate_limit" in err_str.lower() or "429" in err_str:
                logger.warning(f"Rate limit on {model}, trying fallback...")
                continue
            raise  # Non-rate-limit errors propagate immediately
    raise RuntimeError("All Groq models rate-limited")


def _deterministic_fallback(df: pd.DataFrame, language: str, error: str = "",
                            execution_result: Optional[Dict] = None) -> Dict[str, Any]:
    """Human-friendly fallback when LLM is unavailable. Never shows raw errors."""
    row_count = len(df)
    col_count = len(df.columns)

    # Build a useful answer from execution result if available
    if execution_result and execution_result.get("primary_value") is not None:
        val = execution_result["primary_value"]
        unit = execution_result.get("unit", "")
        operation = execution_result.get("summary_stats", {}).get("operation_used", "calculation")
        if language == "ar":
            answer_text = f"النتيجة هي {val} {unit}. تم الحساب باستخدام {operation}. لم تتوفر رؤى إضافية مؤقتاً."
        else:
            answer_text = (
                f"The result is {val} {unit}, computed using {operation}. "
                f"Additional narrative insights are temporarily unavailable."
            )
        insights = [
            f"Result computed from {execution_result.get('records_used', '?')} records" if language != "ar"
            else f"تم الحساب من {execution_result.get('records_used', '?')} سجل"
        ]
    else:
        if language == "ar":
            answer_text = f"تحتوي البيانات على {row_count:,} صف و {col_count} عمود. الرؤى الإضافية غير متوفرة مؤقتاً."
        else:
            answer_text = (
                f"This dataset contains {row_count:,} rows and {col_count} columns. "
                f"Additional narrative insights are temporarily unavailable."
            )
        insights = []

    return {
        "answer_text": answer_text,
        "answer_type": "fallback",
        "key_insights": insights,
        "kpis": [],
        "chart_type": "auto",
        "chart_title": "",
        "chart_data": [],
        "caveats": []
    }


def generate_upload_summary(df: pd.DataFrame, profile: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return _build_deterministic_upload_summary(df, profile, language)

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        row_count = len(df)
        max_cols = min(15, len(df.columns))
        subset_df = df.iloc[:, :max_cols]
        columns_str = ", ".join(subset_df.columns.tolist())
        dtypes_str = ", ".join([f"{c}({d})" for c, d in subset_df.dtypes.items()])
        sample_data = subset_df.head(5).to_csv(index=False)
        health_summary = json.dumps(profile.get("health", {}))

        prompt = f"""You are an Analytics Copilot helping a non-technical business user understand their dataset.

=== DATASET CONTEXT ===
Row Count: {row_count}
Columns: {columns_str}
Types: {dtypes_str}
Health Stats: {health_summary}
Sample Data (5 rows):
{sample_data}

=== TASK ===
Write a clear, business-friendly overview. Imagine the user has never seen this data before.

1. `dataset_overview`: 2-3 sentences explaining what this dataset is about in plain language. Help the user understand what each main field represents.
2. `health_notes`: 1-2 sentences about data quality. Is it clean? Any missing values? Ready for analysis?
3. `data_readiness`: One of: "Ready for analysis" / "Some cleaning recommended" / "Significant issues detected"
4. `key_observations`: 3-4 specific observations about the data (e.g., "The dataset covers March 2026 with hourly readings", "There are 5 distinct asset types").
5. `suggested_questions`: 4 natural, business-friendly questions a non-technical user would ask to analyze this data. Write them as a real person would ask.
6. Language: Reply in {"Arabic" if language == "ar" else "English"}.

=== JSON SCHEMA ===
{{
  "dataset_overview": "string",
  "health_notes": "string",
  "data_readiness": "string",
  "key_observations": ["obs1", "obs2", "obs3"],
  "suggested_questions": ["q1", "q2", "q3", "q4"]
}}
"""

        content = _call_groq(
            client,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        result = json.loads(content.strip())
        # Ensure all keys exist
        result.setdefault("dataset_overview", "Dataset loaded successfully.")
        result.setdefault("health_notes", "")
        result.setdefault("data_readiness", "Ready for analysis")
        result.setdefault("key_observations", [])
        result.setdefault("suggested_questions", [])
        return result
    except Exception as e:
        logger.error(f"Failed to generate upload summary: {e}")
        return _build_deterministic_upload_summary(df, profile, language)


def _build_deterministic_upload_summary(df: pd.DataFrame, profile: Dict[str, Any], language: str) -> Dict[str, Any]:
    """Pure-Python fallback for upload summary when LLM is unavailable."""
    health = profile.get("health", {})
    row_count = len(df)
    col_count = len(df.columns)
    missing_pct = health.get("missing_pct", 0)
    quality = health.get("quality_score", 100)

    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    dt_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    readiness = "Ready for analysis" if quality > 90 else ("Some cleaning recommended" if quality > 70 else "Significant issues detected")

    overview = (
        f"This dataset contains {row_count:,} rows and {col_count} columns. "
        f"It includes {len(num_cols)} numeric fields, {len(cat_cols)} categorical fields, "
        f"and {len(dt_cols)} date/time fields."
    )
    health_notes = f"Data quality score: {quality}%. Missing values: {missing_pct}%."

    return {
        "dataset_overview": overview,
        "health_notes": health_notes,
        "data_readiness": readiness,
        "key_observations": [
            f"Contains {row_count:,} records across {col_count} fields",
            f"Numeric columns: {', '.join(num_cols[:5])}" if num_cols else "No numeric columns found",
            f"Quality score: {quality}%"
        ],
        "suggested_questions": []
    }


def _generate_default_signals(df: pd.DataFrame) -> Dict[str, Any]:
    signals = {}
    cat_cols = df.select_dtypes(include=['object', 'category']).columns
    if len(cat_cols) > 0:
        top_col = cat_cols[0]
        vc = df[top_col].value_counts().head(5)
        signals["top_categories"] = {
            "column": top_col,
            "data": [{"name": str(k), "value": float(v)} for k, v in vc.items()]
        }
    num_cols = df.select_dtypes(include=['number']).columns
    if len(num_cols) > 0:
        num_col = num_cols[0]
        signals["numeric_summary"] = {
            "column": num_col,
            "mean": float(df[num_col].mean()),
            "max": float(df[num_col].max()),
            "min": float(df[num_col].min()),
            "sum": float(df[num_col].sum())
        }
    return signals


def generate_enrichment(
    question: str,
    df: pd.DataFrame,
    schema_profile: Dict[str, Any],
    plan: Dict[str, Any],
    execution_result: Optional[Dict[str, Any]],
    language: str = "en"
) -> Dict[str, Any]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return _deterministic_fallback(df, language, "Missing GROQ_API_KEY", execution_result)

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        # 1. Prepare Dataset Context
        row_count = len(df)
        max_cols = min(15, len(df.columns))
        subset_df = df.iloc[:, :max_cols]

        null_counts = subset_df.isnull().sum()
        null_summary_items = [f"{col}: {count} nulls" for col, count in null_counts.items() if count > 0]
        null_summary = ", ".join(null_summary_items) if null_summary_items else "None"

        sample_data = subset_df.head(5).to_csv(index=False)
        columns_str = ", ".join(subset_df.columns.tolist())
        dtypes_str = ", ".join([f"{c}({d})" for c, d in subset_df.dtypes.items()])

        # 2. Prepare Execution Result Context
        if execution_result and execution_result.get("result_type") not in ("empty", None):
            primary_value = execution_result.get("primary_value")
            unit = execution_result.get("unit", "")
            grouped_result = execution_result.get("grouped_result", [])
            summary_stats = execution_result.get("summary_stats", {})
            records_used = execution_result.get("records_used", 0)
            exec_context = f"""
            Execution Path: {plan.get('execution_path')}
            Primary Value: {primary_value} {unit}
            Records Used: {records_used}
            Summary Stats: {json.dumps(summary_stats)}
            Top Grouped Results: {json.dumps(grouped_result[:5])}
            """
        else:
            default_signals = _generate_default_signals(df)
            exec_context = f"""
            Execution Path: {plan.get('execution_path', 'llm')}
            No exact python calculation was requested, but here are deterministic signals you MUST use:
            {json.dumps(default_signals, indent=2)}
            """

        # 3. Build Prompt
        is_unsupported = execution_result and execution_result.get("result_type") == "unsupported_metric"
        is_single_value = not execution_result or not execution_result.get("grouped_result")

        prompt = f"""You are an AI Analytics Copilot writing for a non-technical business executive.

=== USER QUESTION ===
{question}

=== EXECUTION RESULT (ground truth — this IS the answer) ===
{exec_context}

=== YOUR ROLE ===
You are NOT computing anything. The execution result above IS the answer.
Your job is to explain this result using ONLY the numbers in the execution payload.

=== WRITING STYLE ===
- Start with the exact result value
- Every sentence MUST reference a specific number from the execution payload (mean, median, min, max, count, etc.)
- Compare the result against other metrics in the payload (e.g., "The average of 48.56 is closer to the minimum of 27.11 than the maximum of 74.45, suggesting most readings are in the lower range")
- NEVER write generic statements like "This reflects energy usage patterns" or "This can inform decisions"
- NEVER write sentences that could apply to any dataset — every sentence must be specific to THIS result
- Use 2-3 short paragraphs maximum
- Be concise and data-driven, not verbose

=== STRICT RULES ===
1. NEVER compute, infer, or estimate any value. Use only numbers from the execution payload.
2. answer_text: 2-3 paragraphs. Every paragraph must contain at least one specific number from the execution result.
3. key_insights: 2-3 insights. Each MUST:
   - Reference a specific number from the execution payload
   - Provide a non-obvious observation (e.g., comparing mean vs median for skew)
   - NEVER state obvious facts like "X accounted for 100% of the total" when only one group was filtered
   - NEVER restate the primary result as an insight
   - NEVER give generic business advice
4. chart_type:
   - If grouped results have 2+ items → "bar"
   - If question is about trend/timeseries → "line"
   - If single value with no grouping → "none"
   - If forecast → "line"
5. chart_data: extract from "Top Grouped Results". If empty or single item, use [].
6. caveats: only if directly supported by execution result.
7. If result_type is "unsupported_metric": explain why and suggest alternatives.
8. Language: Reply entirely in {"Arabic" if language == "ar" else "English"}.

=== BAD INSIGHTS (never generate these) ===
- "X accounted for 100% of the total" (obvious when single filter)
- "This value is significant as it reflects..." (generic fluff)
- "This can inform decisions related to..." (unsupported advice)
- Restating the primary value without adding context

=== GOOD INSIGHTS (follow this pattern) ===
- "The average of 48.56 is higher than the median of 42.27, indicating the distribution is right-skewed with some high-consumption hours pulling the average up"
- "The range between minimum (27.11) and maximum (74.45) spans 47.34 kWh, showing significant hourly variation"
- "With 384 records over 7 days, this represents approximately 55 readings per day"

=== TARGET JSON SCHEMA ===
{{
  "answer_text": "Data-driven paragraphs referencing specific numbers from execution result.",
  "answer_type": "python|llm|hybrid",
  "key_insights": ["insight referencing specific numbers from execution payload"],
  "kpis": [
    {{"label": "metric name", "value": "formatted value string"}}
  ],
  "chart_type": "line|bar|none",
  "chart_title": "Descriptive title",
  "chart_data": [
    {{"name": "category", "value": 123}}
  ],
  "caveats": ["only if supported by execution result"]
}}
"""

        content = _call_groq(
            client,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        result = json.loads(content.strip())

        # Enforce defaults
        result.setdefault("answer_text", "")
        result.setdefault("answer_type", plan.get("execution_path", "llm"))
        result.setdefault("key_insights", [])
        result.setdefault("kpis", [])
        result.setdefault("chart_type", "auto")
        result.setdefault("chart_title", "Analysis")
        result.setdefault("chart_data", [])
        result.setdefault("caveats", [])

        # ── Post-processing: filter low-quality insights ──
        NOISE_PATTERNS = [
            "100% of the total",
            "100% of total",
            "accounted for 100%",
            "reflects the district",
            "can inform decisions",
            "energy management and resource",
            "usage patterns and can",
        ]
        filtered_insights = []
        for ins in result.get("key_insights", []):
            ins_lower = ins.lower()
            if any(p.lower() in ins_lower for p in NOISE_PATTERNS):
                continue
            filtered_insights.append(ins)
        result["key_insights"] = filtered_insights

        # ── Force chart_type to "none" for single-value, no-grouping results ──
        if is_single_value:
            result["chart_type"] = "none"
            result["chart_data"] = []

        return result

    except Exception as e:
        logger.error(f"Enrichment engine failed: {e}")
        return _deterministic_fallback(df, language, str(e), execution_result)

