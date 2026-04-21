"""
Session Store Module
--------------------
In-memory analytical session store for multi-turn conversational analytics.
Stores analytical context (last plan, filters, metric, result) per session.
"""

import time
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# In-memory session store — keyed by session_id
_sessions: Dict[str, Dict[str, Any]] = {}

# Max turns to keep per session
MAX_TURNS = 20
# Session TTL in seconds (2 hours)
SESSION_TTL = 7200


def _empty_session() -> Dict[str, Any]:
    return {
        "created_at": time.time(),
        "updated_at": time.time(),
        "turns": [],  # List of {role, content, timestamp}
        "last_query_plan": None,
        "last_filters": None,
        "last_metric": None,
        "last_operation": None,
        "last_group_by": None,
        "last_chart_type": None,
        "last_entities": [],
        "last_time_range": None,
        "last_result_type": None,
        "last_result_summary": None,
        "last_question": None,
    }


def get_session(session_id: str) -> Dict[str, Any]:
    """Get or create a session."""
    if session_id not in _sessions:
        _sessions[session_id] = _empty_session()
        logger.info(f"Created new session: {session_id}")
    session = _sessions[session_id]
    # Check TTL
    if time.time() - session["updated_at"] > SESSION_TTL:
        _sessions[session_id] = _empty_session()
        logger.info(f"Session {session_id} expired, created fresh")
    return _sessions[session_id]


def update_session(session_id: str, question: str, plan: Dict[str, Any],
                   execution_result: Dict[str, Any], response_data: Dict[str, Any]) -> None:
    """Update session with the latest turn's analytical context."""
    session = get_session(session_id)
    session["updated_at"] = time.time()

    # Add user turn
    session["turns"].append({
        "role": "user",
        "content": question,
        "timestamp": time.time()
    })

    # Add assistant turn (compact summary)
    answer = response_data.get("answer", {})
    session["turns"].append({
        "role": "assistant",
        "content": answer.get("headline", answer.get("summary", "")),
        "result_type": answer.get("result_type"),
        "timestamp": time.time()
    })

    # Trim turns
    if len(session["turns"]) > MAX_TURNS * 2:
        session["turns"] = session["turns"][-MAX_TURNS * 2:]

    # Update analytical context
    session["last_question"] = question
    session["last_query_plan"] = {k: v for k, v in plan.items() if not k.startswith("_")}
    session["last_filters"] = plan.get("filters")
    session["last_metric"] = plan.get("metric")
    session["last_operation"] = plan.get("operation")
    session["last_group_by"] = plan.get("group_by")
    session["last_chart_type"] = response_data.get("chart", {}).get("type")
    session["last_time_range"] = plan.get("filters", {}).get("date_range")
    session["last_result_type"] = execution_result.get("result_type")

    # Build compact result summary
    pv = execution_result.get("primary_value")
    unit = execution_result.get("unit", "")
    records = execution_result.get("records_used", 0)
    session["last_result_summary"] = f"{pv} {unit} ({records} records)" if pv is not None else f"{records} records"

    # Extract entities from equals filters
    equals = plan.get("filters", {}).get("equals", {})
    session["last_entities"] = list(equals.values()) if equals else []

    logger.info(f"Session {session_id} updated — turn {len(session['turns'])}")


def clear_session(session_id: str) -> None:
    """Reset a session to empty state."""
    _sessions[session_id] = _empty_session()
    logger.info(f"Session {session_id} cleared")


def get_session_context_for_planner(session_id: str) -> Optional[Dict[str, Any]]:
    """Extract compact context suitable for the LLM planner prompt."""
    session = get_session(session_id)
    if not session["last_query_plan"]:
        return None

    return {
        "last_question": session["last_question"],
        "last_query_plan": session["last_query_plan"],
        "last_result_type": session["last_result_type"],
        "last_result_summary": session["last_result_summary"],
        "last_chart_type": session["last_chart_type"],
        "turn_count": len(session["turns"]) // 2,
    }


def get_conversation_history(session_id: str) -> List[Dict[str, Any]]:
    """Return conversation turns for display."""
    session = get_session(session_id)
    return session.get("turns", [])
