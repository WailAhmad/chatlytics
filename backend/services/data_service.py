"""
Data Service Module
-------------------
Manages the active dataset state and loading.
Dataset is ONLY loaded when explicitly uploaded by the user.
"""

import os
import pandas as pd
from typing import Optional

# No default dataset — must be uploaded
ACTIVE_DATA_PATH: Optional[str] = None

# Cached dataframe
_ACTIVE_DF: Optional[pd.DataFrame] = None
_ACTIVE_PATH: Optional[str] = None


def set_active_dataset(filepath: str):
    global ACTIVE_DATA_PATH, _ACTIVE_DF, _ACTIVE_PATH
    ACTIVE_DATA_PATH = filepath
    _ACTIVE_DF = None
    _ACTIVE_PATH = None


def clear_active_dataset():
    """Remove the active dataset from memory (does not delete the file)."""
    global ACTIVE_DATA_PATH, _ACTIVE_DF, _ACTIVE_PATH
    ACTIVE_DATA_PATH = None
    _ACTIVE_DF = None
    _ACTIVE_PATH = None


def has_active_dataset() -> bool:
    """Check if a dataset is currently loaded."""
    return ACTIVE_DATA_PATH is not None and os.path.exists(ACTIVE_DATA_PATH)


def get_active_dataframe() -> pd.DataFrame:
    global _ACTIVE_DF, _ACTIVE_PATH

    if ACTIVE_DATA_PATH is None:
        raise FileNotFoundError("No dataset loaded. Please upload a CSV first.")

    if _ACTIVE_DF is not None and _ACTIVE_PATH == ACTIVE_DATA_PATH:
        return _ACTIVE_DF

    if not os.path.exists(ACTIVE_DATA_PATH):
        raise FileNotFoundError(f"Dataset not found at {ACTIVE_DATA_PATH}")

    df = pd.read_csv(ACTIVE_DATA_PATH)

    # Strip whitespace/carriage returns from string columns
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].str.strip()

    # Auto-detect and parse datetime columns
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                parsed = pd.to_datetime(df[col], dayfirst=True, format='mixed')
                if parsed.notna().sum() > len(df) * 0.5:
                    df[col] = parsed
            except (ValueError, TypeError):
                pass

    _ACTIVE_DF = df
    _ACTIVE_PATH = ACTIVE_DATA_PATH
    return df
