"""
Filter Validator Module
-----------------------
Validates and corrects LLM-generated filter values against the actual schema.
Uses fuzzy matching to auto-correct misspellings and hallucinated values.
"""

import logging
from difflib import get_close_matches
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def validate_and_fix_plan(plan: Dict[str, Any], schema_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-processes a query plan from the LLM:
    1. Validates equals filters against unique_values
    2. Fuzzy-matches incorrect values to closest real value
    3. Removes hallucinated filters with no match
    4. Applies semantic mappings for natural language terms
    """
    corrections: List[str] = []
    
    filters = plan.get("filters", {})
    equals = filters.get("equals", {})
    unique_values = schema_profile.get("unique_values", {})
    columns = schema_profile.get("columns", [])
    
    if not equals:
        plan["_filter_corrections"] = corrections
        return plan
    
    cleaned_equals = {}
    
    for col, val in equals.items():
        # Skip if column doesn't exist
        if col not in columns:
            corrections.append(f"Removed filter on '{col}': column does not exist in schema.")
            continue
        
        # If column is not categorical (e.g. numeric), validate it
        if col not in unique_values:
            # Check if it's a numeric column with a non-numeric value (hallucination)
            dtypes = schema_profile.get("dtypes", {})
            col_dtype = dtypes.get(col, "")
            if "int" in col_dtype or "float" in col_dtype:
                try:
                    float(val)
                    cleaned_equals[col] = val  # Valid numeric value
                except (ValueError, TypeError):
                    corrections.append(f"Removed hallucinated filter on numeric column '{col}': '{val}' is not a valid number.")
                    logger.warning(f"Removed non-numeric filter: {col}='{val}' on {col_dtype} column")
            else:
                cleaned_equals[col] = val
            continue
        
        actual_values = unique_values[col]
        
        # Exact match (case-insensitive)
        val_lower = str(val).lower().strip()
        exact = [v for v in actual_values if str(v).lower().strip() == val_lower]
        if exact:
            cleaned_equals[col] = exact[0]
            continue
        
        # Word-overlap match: split on underscores/spaces and find best keyword overlap
        # Exclude generic structural tokens that don't carry semantic meaning
        STOP_WORDS = {"district", "zone", "region", "hub", "area", "sector", "block", "unit", "type", "group"}
        val_tokens = set(val_lower.replace("_", " ").replace("-", " ").split()) - STOP_WORDS
        
        if val_tokens:  # Only do keyword matching if we have meaningful tokens
            best_overlap = None
            best_overlap_score = 0
            best_overlap_ratio = 0.0
            for av in actual_values:
                av_lower = str(av).lower().strip()
                av_tokens = set(av_lower.replace("_", " ").replace("-", " ").split()) - STOP_WORDS
                overlap = len(val_tokens & av_tokens)
                # Require at least 50% of meaningful tokens to match
                ratio = overlap / max(len(val_tokens), 1)
                if overlap > best_overlap_score or (overlap == best_overlap_score and ratio > best_overlap_ratio):
                    best_overlap_score = overlap
                    best_overlap_ratio = ratio
                    best_overlap = av
            
            # Only accept if at least 50% of tokens matched
            if best_overlap and best_overlap_score > 0 and best_overlap_ratio >= 0.5:
                corrections.append(f"Corrected filter '{col}': '{val}' → '{best_overlap}' (keyword match)")
                logger.info(f"Filter correction (keyword): {col}: '{val}' → '{best_overlap}'")
                cleaned_equals[col] = best_overlap
                continue
        
        # Fallback: difflib fuzzy match — use strict cutoff (0.8) to avoid wrong substitutions
        actual_lower_map = {str(v).lower().strip(): v for v in actual_values}
        matches = get_close_matches(val_lower, actual_lower_map.keys(), n=1, cutoff=0.8)
        
        if matches:
            best = actual_lower_map[matches[0]]
            corrections.append(f"Corrected filter '{col}': '{val}' → '{best}' (fuzzy match)")
            logger.info(f"Filter correction: {col}: '{val}' → '{best}'")
            cleaned_equals[col] = best
        else:
            corrections.append(f"Removed filter on '{col}': '{val}' does not exist in the dataset. Available values: {actual_values[:10]}")
            logger.warning(f"Removed hallucinated filter: {col}='{val}'. Available: {actual_values[:10]}")
    
    plan["filters"]["equals"] = cleaned_equals
    plan["_filter_corrections"] = corrections

    # ── Maintenance operation guard ──
    # The maintenance executor uses status_code==505 internally.
    # Any status_code equals filter set by the planner is incorrect and must be removed.
    if plan.get("operation") == "maintenance":
        equals_now = plan.get("filters", {}).get("equals", {})
        if "status_code" in equals_now:
            removed = equals_now.pop("status_code")
            plan["_filter_corrections"].append(
                f"Removed planner-set status_code='{removed}' filter for maintenance operation "
                f"(executor uses status_code=505 internally)"
            )

    return plan


# ── Semantic Mapping Layer ──
# Maps natural language concepts to actual filter transformations

SEMANTIC_MAP = {
    "peak hours": {"_hour_filter": {"column": "hour", "values": [17, 18, 19, 20, 21, 22]}},
    "off-peak": {"_hour_filter": {"column": "hour", "values": [0, 1, 2, 3, 4, 5, 6, 7]}},
    "off peak": {"_hour_filter": {"column": "hour", "values": [0, 1, 2, 3, 4, 5, 6, 7]}},
    "ساعات الذروة": {"_hour_filter": {"column": "hour", "values": [17, 18, 19, 20, 21, 22]}},
    "خارج الذروة": {"_hour_filter": {"column": "hour", "values": [0, 1, 2, 3, 4, 5, 6, 7]}},
    "daytime": {"_hour_filter": {"column": "hour", "values": [8, 9, 10, 11, 12, 13, 14, 15, 16]}},
    "nighttime": {"_hour_filter": {"column": "hour", "values": [20, 21, 22, 23, 0, 1, 2, 3, 4, 5]}},
}

# Keywords that indicate the user is using a semantic concept, not a column value
SEMANTIC_KEYWORDS = {"peak", "off-peak", "off peak", "الذروة", "خارج الذروة", "ساعات الذروة", "daytime", "nighttime"}


def apply_semantic_mappings(question: str, plan: Dict[str, Any], schema_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detects semantic keywords in the question and converts them into
    deterministic filters. Also strips hallucinated status_code filters.
    """
    q_lower = question.lower()
    semantic_detected = False

    # Detect peak vs off-peak hours
    has_peak = any(kw in q_lower for kw in ["peak hours", "ساعات الذروة", "peak"])
    has_offpeak = any(kw in q_lower for kw in ["off-peak", "off peak", "خارج الذروة"])
    has_compare = any(kw in q_lower for kw in ["compare", "vs", "versus", "differ", "between", "قارن", "مقارنة", "بين"])
    has_morning = any(kw in q_lower for kw in ["morning peak", "morning", "صباح"])
    has_evening = any(kw in q_lower for kw in ["evening peak", "evening", "مساء"])

    # Detect status-based comparisons
    has_normal = any(kw in q_lower for kw in ["normal operation", "normal", "عادي", "طبيعي"])
    has_outage = any(kw in q_lower for kw in ["outage", "انقطاع", "عطل"])

    # Detect peak days vs normal days
    has_peak_days = any(kw in q_lower for kw in ["peak days", "أيام الذروة"])
    has_normal_days = any(kw in q_lower for kw in ["normal days", "الأيام العادية", "أيام عادية"])

    if has_peak_days and has_normal_days and has_compare:
        plan["_semantic_comparison"] = {
            "type": "peak_vs_normal_days"
        }
        plan["operation"] = "compare"
        plan["question_type"] = "comparison"
        semantic_detected = True
        logger.info("Semantic comparison detected: peak days vs normal days")
    elif has_morning and has_evening and has_compare:
        # Morning peak vs evening peak comparison
        plan["_semantic_comparison"] = {
            "type": "peak_vs_offpeak",
            "peak_hours": list(range(7, 11)),      # morning: 07–10
            "offpeak_hours": list(range(17, 22)),   # evening: 17–21
            "labels": ["Morning Peak (07–10)", "Evening Peak (17–21)"],
        }
        plan["operation"] = "compare"
        plan["question_type"] = "comparison"
        semantic_detected = True
        logger.info("Semantic comparison detected: morning peak vs evening peak")
    elif has_normal and has_outage and has_compare:
        # Normal operation vs outage comparison (status_code 100 vs 404)
        plan["_semantic_comparison"] = {
            "type": "status_split",
            "column": "status_code",
            "group_a": {"value": 100, "label": "Normal Operation (100)"},
            "group_b": {"value": 404, "label": "Outage (404)"},
        }
        plan["operation"] = "compare"
        plan["question_type"] = "comparison"
        semantic_detected = True
        logger.info("Semantic comparison detected: normal vs outage")
    elif has_peak and has_offpeak and has_compare:
        # Generic peak-vs-offpeak comparison
        plan["_semantic_comparison"] = {
            "type": "peak_vs_offpeak",
            "peak_hours": [17, 18, 19, 20, 21, 22],
            "offpeak_hours": [0, 1, 2, 3, 4, 5, 6, 7],
        }
        plan["operation"] = "compare"
        plan["question_type"] = "comparison"
        semantic_detected = True
        logger.info("Semantic comparison detected: peak vs off-peak")
    else:
        # Only apply semantic hour mappings if hours_filter is NOT already set
        # (the deterministic post-processor in query_planner handles specific phrases like "morning peak")
        existing_hours = plan.get("filters", {}).get("hours_filter", [])
        if not existing_hours:
            for keyword, mapping in SEMANTIC_MAP.items():
                if keyword in q_lower:
                    if "_hour_filter" in mapping:
                        hour_info = mapping["_hour_filter"]
                        plan.setdefault("_semantic_filters", []).append({
                            "type": "hour_range",
                            "hours": hour_info["values"],
                            "label": keyword
                        })
                        semantic_detected = True
                        logger.info(f"Semantic mapping applied: '{keyword}' → hour filter {hour_info['values']}")
        else:
            logger.info(f"Skipped semantic hour mapping — deterministic hours_filter already set: {existing_hours}")

    # Strip status_code filters when semantic keywords are present
    if semantic_detected:
        equals = plan.get("filters", {}).get("equals", {})
        if "status_code" in equals:
            removed_val = equals.pop("status_code")
            plan.setdefault("_filter_corrections", []).append(
                f"Removed hallucinated filter 'status_code': '{removed_val}' (handled by semantic mapping)"
            )
            logger.info(f"Stripped status_code filter '{removed_val}' — semantic keyword detected")

    # Also strip if the question contains "peak" keywords and no semantic map was triggered
    # but status_code was added (e.g. "top 3 peak days" — "peak" = highest, not a status)
    if not semantic_detected and any(kw in q_lower for kw in ["peak", "الذروة", "أعلى"]):
        equals = plan.get("filters", {}).get("equals", {})
        if "status_code" in equals:
            removed_val = equals.pop("status_code")
            plan.setdefault("_filter_corrections", []).append(
                f"Removed hallucinated filter 'status_code': '{removed_val}' ('peak' refers to highest value, not a status)"
            )
            logger.info(f"Stripped status_code filter '{removed_val}' — 'peak' used as adjective")

    return plan

