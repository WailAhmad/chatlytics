"""
Data Service Module
-------------------
Manages the active dataset state and loading.
Dataset is ONLY loaded when explicitly uploaded by the user.
"""

import os
import pandas as pd
from typing import Optional

# Dataset is uploaded by the user, then restored from data/active_dataset.csv
# across backend restarts/reloads for a smoother local demo.
ACTIVE_DATA_PATH: Optional[str] = None
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
LAST_UPLOADED_DATASET = os.path.join(DATA_DIR, "active_dataset.csv")

# Cached dataframe
_ACTIVE_DF: Optional[pd.DataFrame] = None
_ACTIVE_PATH: Optional[str] = None


def set_active_dataset(filepath: str):
    global ACTIVE_DATA_PATH, _ACTIVE_DF, _ACTIVE_PATH
    ACTIVE_DATA_PATH = filepath
    _ACTIVE_DF = None
    _ACTIVE_PATH = None


def clear_active_dataset():
    """Remove the active dataset from memory AND delete the cached file."""
    global ACTIVE_DATA_PATH, _ACTIVE_DF, _ACTIVE_PATH
    ACTIVE_DATA_PATH = None
    _ACTIVE_DF = None
    _ACTIVE_PATH = None
    # Delete the cached CSV file so it won't auto-reload on refresh
    if os.path.exists(LAST_UPLOADED_DATASET):
        try:
            os.remove(LAST_UPLOADED_DATASET)
        except OSError:
            pass


def set_active_dataframe(df: pd.DataFrame, source_label: str = "database"):
    """Set a DataFrame directly as the active dataset (used for DB connections).
    Also saves a CSV copy so the existing pipeline works seamlessly."""
    global ACTIVE_DATA_PATH, _ACTIVE_DF, _ACTIVE_PATH
    os.makedirs(DATA_DIR, exist_ok=True)
    csv_path = os.path.join(DATA_DIR, "active_dataset.csv")
    df.to_csv(csv_path, index=False)
    ACTIVE_DATA_PATH = csv_path
    _ACTIVE_DF = df
    _ACTIVE_PATH = csv_path


def has_active_dataset() -> bool:
    """Check if a dataset is currently loaded."""
    global ACTIVE_DATA_PATH
    if ACTIVE_DATA_PATH is not None and os.path.exists(ACTIVE_DATA_PATH):
        return True
    if os.path.exists(LAST_UPLOADED_DATASET):
        ACTIVE_DATA_PATH = LAST_UPLOADED_DATASET
        return True
    return False


def get_active_dataframe() -> pd.DataFrame:
    global _ACTIVE_DF, _ACTIVE_PATH

    if ACTIVE_DATA_PATH is None and not has_active_dataset():
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
