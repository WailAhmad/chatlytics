import os
import logging
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)

def _deterministic_fallback(df: pd.DataFrame, language: str, error: str = "") -> str:
    row_count = len(df)
    col_count = len(df.columns)
    missing_total = df.isnull().sum().sum()
    
    if language == "ar":
        return f"**ملخص البيانات (تم إنشاؤه تلقائيًا)**\n- **إجمالي الصفوف**: {row_count:,}\n- **إجمالي الأعمدة**: {col_count:,}\n- **إجمالي القيم المفقودة**: {missing_total:,}\n- **الأعمدة**: {', '.join(df.columns.tolist()[:15])} {'...' if col_count > 15 else ''}"
    else:
        return f"**Dataset Summary (Auto-generated fallback)**\n- **Total Rows**: {row_count:,}\n- **Total Columns**: {col_count:,}\n- **Total Missing Values**: {missing_total:,}\n- **Columns**: {', '.join(df.columns.tolist()[:15])} {'...' if col_count > 15 else ''}"

def generate_dataset_explanation(df: pd.DataFrame, language: str = "en", intent: str = "overview") -> Dict[str, Any]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        fallback = _deterministic_fallback(df, language, "Missing API Key")
        return {
            "humanized_chat_answer": fallback,
            "answer": {"summary": "Dataset Analysis", "headline": "Auto-Generated Summary"},
            "conversation_state": {"mode": "dataset_explanation", "used_prior_context": False}
        }

    from groq import Groq
    client = Groq(api_key=api_key)

    # 1. Extract data safely (Token optimization)
    row_count = len(df)
    max_cols = min(15, len(df.columns))
    subset_df = df.iloc[:, :max_cols]
    
    null_counts = subset_df.isnull().sum()
    null_summary_items = [f"- {col}: {count} missing" for col, count in null_counts.items() if count > 0]
    null_summary = "\n".join(null_summary_items) if null_summary_items else "No missing values detected."

    sample_data = subset_df.head(5).to_csv(index=False)
    dtypes_str = ", ".join([f"{col} ({dtype})" for col, dtype in subset_df.dtypes.items()])
    columns_str = ", ".join(subset_df.columns.tolist())

    # 2. Build prompt based on intent
    if intent == "columns":
        task_instruction = "Explain each column in detail, including its likely business meaning, data type, and its role in the dataset."
        headline = "Column Explanations"
    elif intent == "use_cases":
        task_instruction = "Suggest 4-5 specific, actionable business use cases or analytical questions this dataset can answer."
        headline = "Business Use Cases"
    elif intent == "data_quality":
        task_instruction = "Summarize the data quality. Point out missing values, data type inconsistencies, and any potential issues or required cleaning steps based on the sample data."
        headline = "Data Quality Summary"
    else:
        task_instruction = "Provide a professional overview of this dataset."
        headline = "Dataset Overview"

    prompt = f"""You are an AI data analyst explaining a dataset.
CRITICAL INSTRUCTION 1: Adopt a confidence-aware tone. Use phrases like "appears to", "likely represents", or "it is not fully certain" when the context is ambiguous.
CRITICAL INSTRUCTION 2: If the purpose of the dataset cannot be confidently inferred, you MUST reply with exactly: "Unclear: The dataset purpose cannot be confidently inferred from the provided samples" and nothing else.
CRITICAL INSTRUCTION 3: Format your response exactly with these markdown sections (adjust based on intent, but keep this general structure):
### Dataset Purpose
### Key Columns
### Business Interpretation
### Suggested Use Cases
### Caveats & Uncertainty

Task: {task_instruction}

Dataset Info:
Row Count: {row_count}
Columns (up to 15): {columns_str}
Data Types: {dtypes_str}
Missing Values: {null_summary}

Sample Data (First 5 rows):
{sample_data}

Respond entirely in {"Arabic" if language == "ar" else "English"}. Ensure the headers are translated if replying in Arabic."""

    try:
        from backend.services.enrichment_engine import _call_groq
        content = _call_groq(
            client,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000,
        ).strip()

        return {
            "humanized_chat_answer": content,
            "answer": {
                "summary": "Dataset Analysis",
                "headline": headline
            },
            "conversation_state": {
                "mode": "dataset_explanation",
                "used_prior_context": False,
            }
        }
    except Exception as e:
        logger.error(f"Failed to generate dataset explanation: {e}")
        fallback = _deterministic_fallback(df, language, str(e))
        return {
            "humanized_chat_answer": fallback,
            "answer": {"summary": "Dataset Analysis", "headline": "Auto-Generated Summary"},
            "conversation_state": {
                "mode": "dataset_explanation",
                "used_prior_context": False
            }
        }
