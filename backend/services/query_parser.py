"""
Query Parser Module
--------------------
Parses natural language questions (English and Arabic) into structured
intent dictionaries. Deterministic regex-based — no LLM involved.

Improvements:
  - Input is normalized before matching (whitespace, punctuation, casing)
  - Region names are canonicalized regardless of user capitalization
  - All patterns tolerate extra spaces and optional trailing punctuation
  - Arabic patterns handle optional trailing ؟

Supported intents:
  average_load       : average load_kwh for a region over a date range
  peak_generation    : hour with highest generation_kwh on a given date
  maintenance_ranking: assets ranked by maintenance hours in a date range
  peak_vs_offpeak    : compare avg generation during peak vs off-peak hours

Date formats accepted: YYYY-MM-DD
"""

import re
from datetime import datetime
from typing import Optional

# ── Date sub-pattern ───────────────────────────────────────────────────────────
_D = r"(\d{4}-\d{2}-\d{2})"  # captures YYYY-MM-DD

# ── Region canonicalization map ────────────────────────────────────────────────
# Keys are lowercase; values are the canonical (dataset-matching) forms.
_REGION_CANON = {
    "north_district": "North_District",
    "central_hub": "Central_Hub",
    "south_zone": "South_Zone",
    "east_grid": "East_Grid",
    "west_grid": "West_Grid",
}


def canonicalize_region(raw: str) -> str:
    """
    Return the canonical region name, normalizing capitalization variations.
    Falls back to the original (stripped) value if no mapping is found.

    Examples:
        "north_district"  -> "North_District"
        "CENTRAL_HUB"     -> "Central_Hub"
        "North_district"  -> "North_District"
        "Unknown_Region"  -> "Unknown_Region"  (unchanged)
    """
    key = raw.strip().lower()
    return _REGION_CANON.get(key, raw.strip())


def _normalize(text: str) -> str:
    """
    Normalize a question string before regex matching:
      1. Strip leading/trailing whitespace.
      2. Collapse runs of whitespace into a single space.
      3. Remove any space that appears immediately before a ? or ؟.
      4. Strip trailing ? or ؟ (made optional in all patterns).
    """
    text = text.strip()
    text = re.sub(r"\s+", " ", text)            # collapse multiple spaces
    text = re.sub(r"\s+([?؟])", r"\1", text)    # remove space before punctuation
    text = text.rstrip("?؟").strip()            # drop trailing punctuation
    return text


# ── Pattern builder helpers ────────────────────────────────────────────────────
# Use \s+ inside patterns to tolerate extra spaces between words.

def _en(*parts: str) -> re.Pattern:
    """Compile a case-insensitive English pattern from space-joined parts."""
    return re.compile(r"\s+".join(parts), re.IGNORECASE)


def _ar(*parts: str) -> re.Pattern:
    """Compile an Arabic pattern (no IGNORECASE needed)."""
    return re.compile(r"\s+".join(parts))


# ── Compiled patterns ──────────────────────────────────────────────────────────

# average_load ─────────────────────────────────────────────────────────────────
_AVG_EN = _en(r"what", r"was", r"the", r"average", r"load", r"for",
              r"(.+?)", r"from", _D, r"to", _D)
_AVG_AR = _ar(r"ما", r"متوسط", r"الحمل", r"في", r"(.+?)", r"من", _D, r"إلى", _D)

# peak_generation ──────────────────────────────────────────────────────────────
# Optional trailing region: "... in <region>" / "... في <region>"
_PEAK_EN = _en(r"identify", r"the", r"hour", r"on", _D,
               r"where", r"generation", r"peaked(?:", r"in", r"(.+?))?$")
_PEAK_AR = _ar(r"حدد", r"الساعة", r"في", _D,
               r"التي", r"بلغ", r"فيها", r"التوليد", r"ذروته(?:", r"في", r"(.+?))?$")

# maintenance_ranking ──────────────────────────────────────────────────────────
_MAINT_EN = _en(r"which", r"assets", r"had", r"the", r"highest",
                r"number", r"of", r"maintenance", r"hours", r"from", _D, r"to", _D)
_MAINT_AR = _ar(r"ما", r"الأصول", r"التي", r"سجلت", r"أعلى",
                r"عدد", r"من", r"ساعات", r"الصيانة", r"من", _D, r"إلى", _D)

# peak_vs_offpeak ──────────────────────────────────────────────────────────────
_COMP_EN = _en(r"compare", r"generation", r"in", r"(.+?)",
               r"between", r"peak", r"hours", r"and", r"off-peak",
               r"from", _D, r"to", _D)
_COMP_AR = _ar(r"قارن", r"التوليد", r"في", r"(.+?)",
               r"بين", r"ساعات", r"الذروة", r"وخارج", r"الذروة",
               r"من", _D, r"إلى", _D)


# ── Validation ─────────────────────────────────────────────────────────────────

def _valid_date(s: str) -> bool:
    """Return True if s is a valid YYYY-MM-DD date string."""
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _dates_ok(*dates: str) -> bool:
    """Return True if every supplied date string passes validation."""
    return all(_valid_date(d) for d in dates)


# ── Public API ─────────────────────────────────────────────────────────────────

def parse_question(question: str) -> dict:
    """
    Parse a natural language analytics question into a structured intent dict.

    The input is normalized before matching (whitespace collapse, optional
    punctuation removal, trailing ? stripped). Region names are canonicalized.

    Matching order: average_load → peak_generation →
                    maintenance_ranking → peak_vs_offpeak.

    Returns {'intent': 'unknown'} if no pattern matches or dates are invalid.

    Args:
        question: Raw question string from the user.

    Returns:
        dict with 'intent' key plus intent-specific fields on success.
    """
    q = _normalize(question)

    # ── average_load ──────────────────────────────────────────────────────────
    m = _AVG_EN.search(q) or _AVG_AR.search(q)
    if m:
        region, start, end = m.group(1).strip(), m.group(2), m.group(3)
        if _dates_ok(start, end):
            return {
                "intent": "average_load",
                "region": canonicalize_region(region),
                "start_date": start,
                "end_date": end,
            }

    # ── peak_generation ───────────────────────────────────────────────────────
    m = _PEAK_EN.search(q) or _PEAK_AR.search(q)
    if m:
        date = m.group(1)
        raw_region = m.group(2)
        if _valid_date(date):
            result: dict = {"intent": "peak_generation", "date": date}
            if raw_region:
                result["region"] = canonicalize_region(raw_region)
            return result

    # ── maintenance_ranking ───────────────────────────────────────────────────
    m = _MAINT_EN.search(q) or _MAINT_AR.search(q)
    if m:
        start, end = m.group(1), m.group(2)
        if _dates_ok(start, end):
            return {
                "intent": "maintenance_ranking",
                "start_date": start,
                "end_date": end,
            }

    # ── peak_vs_offpeak ───────────────────────────────────────────────────────
    m = _COMP_EN.search(q) or _COMP_AR.search(q)
    if m:
        region, start, end = m.group(1).strip(), m.group(2), m.group(3)
        if _dates_ok(start, end):
            return {
                "intent": "peak_vs_offpeak",
                "region": canonicalize_region(region),
                "start_date": start,
                "end_date": end,
            }

    return {"intent": "unknown"}
