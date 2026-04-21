"""
Context Resolver Module
-----------------------
Determines whether a user message is a new query or a follow-up,
and merges it with prior analytical context when appropriate.
"""

import logging
import json
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Keywords that signal follow-up intent (English + Arabic)
FOLLOW_UP_SIGNALS = {
    # Narrowing
    "only", "just", "filter", "but for", "for only", "narrow", "limit to",
    "بس", "فقط", "بس لـ", "حدد",
    # Comparison
    "compare", "versus", "vs", "against", "compared to",
    "قارن", "مقارنة", "بالمقارنة", "ضد",
    # Visualization change
    "plot", "chart", "show as", "display as", "make it", "as bars", "as line", "as histogram",
    "اعرض", "كخط", "كأعمدة", "كرسم",
    # Refinement
    "top", "bottom", "first", "last", "show only", "limit",
    "أعلى", "أسفل", "أول", "آخر", "وريني",
    # Metric switch
    "instead", "switch to", "use", "now use", "change to",
    "بدل", "استخدم", "غيّر", "دلوقتي",
    # Explanation
    "explain", "why", "what does", "meaning", "clarify", "tell me more",
    "اشرح", "ليه", "ليش", "يعني", "وضّح", "اشرح أكتر",
    # Time refinement
    "first week", "last week", "first half", "second half",
    "أول أسبوع", "آخر أسبوع",
}

# Keywords that signal a completely new query
NEW_QUERY_SIGNALS = {
    "show me", "what is", "what are", "how many", "how much",
    "calculate", "find", "give me", "list",
    "اعرض لي", "ما هو", "ما هي", "كم", "احسب", "أعطني",
}


def resolve_conversational_context(
    question: str,
    session_context: Optional[Dict[str, Any]],
    schema_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Determine if the current question is new or a follow-up,
    and prepare the merged context for the query planner.
    """
    q_lower = question.lower().strip()

    # No prior context → always new
    if not session_context or not session_context.get("last_query_plan"):
        return {
            "mode": "new_query",
            "base_query_plan": None,
            "context_prompt": None,
            "carry_over_fields": _no_carry(),
        }

    # Heuristic detection
    is_short = len(q_lower.split()) <= 6
    has_follow_up_signal = any(sig in q_lower for sig in FOLLOW_UP_SIGNALS)
    has_new_query_signal = any(sig in q_lower for sig in NEW_QUERY_SIGNALS)

    # Determine mode
    if has_new_query_signal and not has_follow_up_signal:
        mode = "new_query"
    elif has_follow_up_signal or is_short:
        mode = _classify_follow_up(q_lower)
    else:
        # Longer question with no clear signal → use LLM to decide
        mode = _llm_classify_intent(question, session_context)

    if mode == "new_query":
        return {
            "mode": "new_query",
            "base_query_plan": None,
            "context_prompt": None,
            "carry_over_fields": _no_carry(),
        }

    # Build context for the planner
    last_plan = session_context["last_query_plan"]
    carry = _determine_carry_fields(mode, q_lower)

    context_prompt = _build_context_prompt(session_context, mode)

    return {
        "mode": mode,
        "base_query_plan": last_plan,
        "context_prompt": context_prompt,
        "carry_over_fields": carry,
    }


def _classify_follow_up(q_lower: str) -> str:
    """Classify the type of follow-up from keywords."""
    # Explanation
    explain_kw = ["explain", "why", "what does", "meaning", "اشرح", "ليه", "ليش", "يعني", "وضّح"]
    if any(kw in q_lower for kw in explain_kw):
        return "explanation"

    # Visualization change
    viz_kw = ["plot", "chart", "as bars", "as line", "as histogram", "كخط", "كأعمدة", "كرسم", "make it"]
    if any(kw in q_lower for kw in viz_kw):
        return "refinement"

    # Comparison
    cmp_kw = ["compare", "versus", "vs", "against", "قارن", "مقارنة"]
    if any(kw in q_lower for kw in cmp_kw):
        return "comparison"

    # Metric switch
    switch_kw = ["instead", "switch to", "now use", "بدل", "دلوقتي"]
    if any(kw in q_lower for kw in switch_kw):
        return "follow_up"

    # Default follow-up (narrowing, limit change, etc.)
    return "follow_up"


def _determine_carry_fields(mode: str, q_lower: str) -> Dict[str, bool]:
    """Determine which fields to carry forward from previous plan."""
    if mode == "explanation":
        return {"metric": True, "filters": True, "group_by": True, "chart": True, "time_range": True}
    elif mode == "refinement":
        return {"metric": True, "filters": True, "group_by": True, "chart": False, "time_range": True}
    elif mode == "comparison":
        return {"metric": True, "filters": True, "group_by": False, "chart": False, "time_range": True}
    elif mode == "follow_up":
        return {"metric": True, "filters": True, "group_by": True, "chart": True, "time_range": True}
    return _no_carry()


def _no_carry() -> Dict[str, bool]:
    return {"metric": False, "filters": False, "group_by": False, "chart": False, "time_range": False}


def _build_context_prompt(session_context: Dict[str, Any], mode: str) -> str:
    """Build a compact context string for the LLM planner."""
    last = session_context
    plan = last.get("last_query_plan", {})

    lines = [
        "=== CONVERSATION CONTEXT (PRIOR ANALYSIS) ===",
        f"Mode: {mode} (this is a follow-up to the previous analysis)",
        f"Previous question: \"{last.get('last_question', '')}\"",
        f"Previous metric: {plan.get('metric', 'unknown')}",
        f"Previous operation: {plan.get('operation', 'unknown')}",
        f"Previous filters: {json.dumps(plan.get('filters', {}), ensure_ascii=False)}",
        f"Previous group_by: {plan.get('group_by', [])}",
        f"Previous result type: {last.get('last_result_type', 'unknown')}",
        f"Previous result summary: {last.get('last_result_summary', '')}",
        f"Previous chart type: {last.get('last_chart_type', 'unknown')}",
        "",
        "=== FOLLOW-UP RULES ===",
        "1. The user's new message modifies the PREVIOUS analysis. Do NOT start from scratch.",
        "2. CARRY FORWARD all fields from the previous plan that the user did NOT explicitly change.",
        "3. Only OVERRIDE fields that the user explicitly mentions in their new message.",
        "4. If the user adds a filter (e.g. 'for North_District only'), ADD it to existing filters.",
        "5. If the user changes the metric (e.g. 'now use generation'), change metric but keep other fields.",
        "6. If the user changes visualization (e.g. 'plot as bars'), keep the same query, only change chart.type.",
        "7. If the user asks for explanation, return the SAME plan with question_type='explanation'.",
        "8. If the user narrows results (e.g. 'top 3 only'), keep everything but change limit.",
    ]
    return "\n".join(lines)


def _llm_classify_intent(question: str, session_context: Dict[str, Any]) -> str:
    """Use LLM to classify whether a question is new or follow-up."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        # Fallback: treat ambiguous as follow-up if session exists
        return "follow_up"

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        prompt = f"""Classify the user's message as one of: new_query, follow_up, refinement, comparison, explanation.

Previous question: "{session_context.get('last_question', '')}"
Previous analysis: {session_context.get('last_result_summary', '')}
Current message: "{question}"

Return ONLY one word: new_query, follow_up, refinement, comparison, or explanation."""

        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.0,
            max_tokens=10,
        )
        result = response.choices[0].message.content.strip().lower()
        if result in ("new_query", "follow_up", "refinement", "comparison", "explanation"):
            logger.info(f"LLM classified intent: {result}")
            return result
        return "follow_up"
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return "follow_up"
