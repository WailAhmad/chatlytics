"""
Generic LLM Parser Module
-------------------------
Uses Groq API for dynamic NLU based on uploaded schemas.
"""

import json
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def _build_system_prompt(schema: Dict[str, Any]) -> str:
    schema_str = json.dumps(schema, indent=2)
    return f"""
You are a dynamic query classification assistant for a business intelligence system.
Your ONLY job is to map natural language questions into deterministic JSON intents based on the provided dataset schema.

=== ACTIVE DATASET SCHEMA ===
{schema_str}

=== SUPPORTED INTENTS ===
1. aggregate: Use to calculate sum, average, max, min, or count of a numeric column. Optionally group by a categorical or datetime column.
2. trend: Use to analyze a numeric column over time (requires a datetime_column).
3. top_n: Use to rank a categorical column by a numeric metric.

=== OUTPUT SCHEMA ===
You must return a single valid JSON object exactly matching this structure:
{{
  "intent": "aggregate" | "trend" | "top_n",
  "metric_column": "string (must exist in numeric_columns)",
  "aggregation": "sum" | "avg" | "max" | "min" | "count",
  "group_by_column": "string (optional, must exist in categorical_columns or datetime_columns)",
  "date_column": "string (optional, for trends)",
  "date_range": {{ "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" }} | null,
  "filters": {{ "column_name": "value_to_filter" }} | null,
  "n": int (for top_n),
  "chart_requested": boolean
}}

Never make up columns. Only use columns provided in the schema.
Return ONLY JSON.
"""

def parse_question_with_llm(question: str, schema: Dict[str, Any]) -> Optional[dict]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not set. Cannot use LLM parser.")
        return None

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        
        system_prompt = _build_system_prompt(schema)
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            model="llama-3.1-8b-instant", # or another groq model
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=300,
        )
        
        content = response.choices[0].message.content
        if not content:
            return None
            
        parsed = json.loads(content.strip())
        logger.info(f"LLM Generic Parsed Output: {json.dumps(parsed, ensure_ascii=False)}")
        return parsed
        
    except Exception as e:
        logger.error(f"Error calling Groq API: {e}", exc_info=True)
        return None
