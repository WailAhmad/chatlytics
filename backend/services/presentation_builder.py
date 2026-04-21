"""
Presentation Builder Module
---------------------------
Uses the LLM to generate humanized insights from deterministic execution results.
"""

import json
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def _build_presentation_prompt(language: str) -> str:
    lang_instruction = "Respond ENTIRELY in Arabic." if language == "ar" else "Respond ENTIRELY in English."

    return f"""
You are an expert Data Analyst and Executive Presenter.
Your job is to read the deterministic execution result of a data query and write a professional, humanized summary.

=== RULES ===
1. YOU MUST NOT CALCULATE ANYTHING. The numbers are already provided in the execution_result.
2. YOU MUST NOT INVENT NUMBERS, COLUMNS, OR DATA. Use only the provided data.
3. If unsure, describe the data rather than assuming causation.
4. Keep the tone professional, executive, clear, and concise.
5. If the execution_result indicates 'empty' or zero records, explain clearly WHY and provide recovery suggestions.
6. {lang_instruction}
7. Return ONLY strict JSON matching the schema below.

=== DEPTH REQUIREMENTS ===
- The "headline" MUST reference a specific number from the data (e.g. "March Load Averaged 56.4 kWh")
- Each "insight" MUST reference at least ONE specific number
- "recommendations" must be actionable and data-specific (never generic)
- If trend is stable, describe consistency pattern and implications
- If anomalies exist, describe them with specific values and dates
- For rankings, describe the gap between top categories with numbers
- For distributions, describe the shape and practical implications

=== QUESTION SEPARATION RULES ===
- "suggested_questions" must be BROAD EXPLORATORY questions that take analysis in NEW directions
- They must NOT repeat or rephrase the current question
- They should help the user discover new angles in the data

=== TARGET JSON SCHEMA ===
{{
  "headline": "Executive headline with a key number from the data",
  "summary": "2-3 sentence summary referencing specific values and context",
  "humanized_chat_answer": "A detailed, plain-language conversational answer (3 paragraphs: Direct Answer, Simple Interpretation, Why it matters/Business reading).",
  "chart_caption": "Brief description of what the chart shows, or null",
  "insights": [
    "Observation with specific number",
    "Observation with comparison or context"
  ],
  "anomalies": [
    "Data anomaly with specific values, or leave empty"
  ],
  "recommendations": [
    "Specific, actionable recommendation tied to the finding"
  ],
  "suggested_questions": [
    "A broad exploratory question taking analysis in a new direction"
  ]
}}
"""

def generate_presentation(question: str, plan: Dict[str, Any], execution_result: Dict[str, Any], language: str = "en") -> Optional[Dict[str, Any]]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY missing. Presentation builder skipped.")
        return None

    chart_data_safe = execution_result.get("chart_data", [])
    if len(chart_data_safe) > 50:
        chart_data_safe = chart_data_safe[:50]

    input_data = {
        "question": question,
        "language": language,
        "query_plan": {k: v for k, v in plan.items() if not k.startswith("_")},
        "execution_result": {
            "result_type": execution_result.get("result_type"),
            "primary_value": execution_result.get("primary_value"),
            "unit": execution_result.get("unit"),
            "records_used": execution_result.get("records_used"),
            "chart_data_sample": chart_data_safe,
            "summary_stats": execution_result.get("summary_stats")
        }
    }

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        system_prompt = _build_presentation_prompt(language)
        user_prompt = f"Context and deterministic result:\n{json.dumps(input_data, ensure_ascii=False)}"

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=900,
        )

        content = response.choices[0].message.content
        if not content:
            return None

        presentation = json.loads(content.strip())
        return presentation

    except Exception as e:
        logger.error(f"Error in presentation builder: {e}", exc_info=True)
        return None
