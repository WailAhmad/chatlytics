"""
Conversational Analytics API
----------------------------
Multi-turn session-aware query planning and deterministic execution.
"""

import logging
import os
import shutil
import subprocess
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from backend.services.data_service import set_active_dataset, get_active_dataframe, clear_active_dataset, has_active_dataset, set_active_dataframe
from backend.services.schema_profiler import profile_dataframe
from backend.services.query_planner import generate_query_plan
from backend.services.filter_validator import validate_and_fix_plan, apply_semantic_mappings
from backend.services.execution_engine import execute_query_plan

from backend.services.session_store import (
    get_session, update_session, clear_session,
    get_session_context_for_planner, get_conversation_history
)
from backend.services.context_resolver import resolve_conversational_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AskRequest(BaseModel):
    question: str
    language: str = "en"
    session_id: Optional[str] = None


class ResetRequest(BaseModel):
    session_id: str


class DbConnectionRequest(BaseModel):
    db_type: str  # "mysql" or "sqlserver"
    host: str
    port: int
    database: str
    username: str
    password: str
    table_name: Optional[str] = None
    query: Optional[str] = None
    row_limit: int = 50000


class ListTablesRequest(BaseModel):
    db_type: str
    host: str
    port: int
    database: str
    username: str
    password: str


app = FastAPI(title="Conversational Analytics Copilot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_db_url(params) -> str:
    """Build a SQLAlchemy connection URL."""
    if params.db_type == "mysql":
        return f"mysql+pymysql://{params.username}:{params.password}@{params.host}:{params.port}/{params.database}"
    elif params.db_type == "sqlserver":
        # Try pymssql first, fallback guidance in error
        return f"mssql+pymssql://{params.username}:{params.password}@{params.host}:{params.port}/{params.database}"
    else:
        raise ValueError(f"Unsupported database type: {params.db_type}. Use 'mysql' or 'sqlserver'.")


@app.post("/list-tables")
async def list_tables(body: ListTablesRequest):
    """Connect to a database and list available tables."""
    try:
        from sqlalchemy import create_engine, inspect
        url = _build_db_url(body)
        engine = create_engine(url, connect_args={"connect_timeout": 10})
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        engine.dispose()
        return {"status": "ok", "tables": tables}
    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")


@app.post("/connect-db")
async def connect_db(body: DbConnectionRequest):
    """Connect to a database, fetch data from a table, and load it for analysis."""
    global _cached_upload_summary
    try:
        import pandas as pd
        from sqlalchemy import create_engine, text

        url = _build_db_url(body)
        engine = create_engine(url, connect_args={"connect_timeout": 15})

        if body.query:
            sql = body.query
        elif body.table_name:
            sql = f"SELECT * FROM `{body.table_name}` LIMIT {body.row_limit}"
            if body.db_type == "sqlserver":
                sql = f"SELECT TOP {body.row_limit} * FROM [{body.table_name}]"
        else:
            raise HTTPException(status_code=400, detail="Provide either table_name or query.")

        logger.info(f"Executing DB query: {sql[:200]}...")
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
        engine.dispose()

        if df.empty:
            raise HTTPException(status_code=400, detail="Query returned no data.")

        logger.info(f"Loaded {len(df)} rows × {len(df.columns)} columns from {body.db_type}://{body.host}/{body.database}")

        # Strip whitespace from string columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()

        set_active_dataframe(df, source_label=f"{body.db_type}:{body.database}.{body.table_name or 'query'}")
        profile = profile_dataframe(df)

        from backend.services.enrichment_engine import generate_upload_summary
        summary = generate_upload_summary(df, profile, language="en")
        _cached_upload_summary = summary
        profile["upload_summary"] = summary
        profile["source"] = f"{body.db_type}://{body.host}/{body.database}/{body.table_name or 'custom_query'}"

        return {"message": f"Connected and loaded {len(df)} rows from {body.db_type}", "profile": profile}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/health")
def health():
    git_commit = "unknown"
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.dirname(__file__)),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        pass

    return {
        "status": "ok",
        "app": "chatlytics",
        "commit": git_commit,
        "cwd": os.getcwd(),
        "dataset_loaded": has_active_dataset(),
    }


@app.post("/upload-csv")
async def upload_file(file: UploadFile = File(...)):
    global _cached_upload_summary
    logger.info(f"Received file upload request: filename={file.filename}, content_type={file.content_type}")
    if not file.filename.endswith(".csv"):
        logger.error(f"Invalid file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    upload_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, "active_dataset.csv")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"File saved to {file_path}")

        set_active_dataset(file_path)
        df = get_active_dataframe()
        profile = profile_dataframe(df)
        logger.info(f"Dataset profiled successfully. Row count: {profile.get('row_count')}")

        from backend.services.enrichment_engine import generate_upload_summary
        summary = generate_upload_summary(df, profile, language="en")
        _cached_upload_summary = summary  # Cache for refresh
        profile["upload_summary"] = summary

        return {"message": "File uploaded successfully", "profile": profile}
    except Exception as e:
        logger.error(f"Error processing file upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {str(e)}")


# Module-level cache for upload summary (survives page refreshes)
_cached_upload_summary: dict = None


@app.get("/profile")
@app.get("/dataset-profile")
def get_profile():
    global _cached_upload_summary
    if not has_active_dataset():
        return None
    try:
        df = get_active_dataframe()
        profile = profile_dataframe(df)
        # Use cached summary if available, otherwise regenerate
        if _cached_upload_summary:
            profile["upload_summary"] = _cached_upload_summary
        else:
            from backend.services.enrichment_engine import generate_upload_summary
            summary = generate_upload_summary(df, profile, language="en")
            _cached_upload_summary = summary
            profile["upload_summary"] = summary
        return profile
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        return None


@app.post("/clear-dataset")
async def clear_dataset():
    """Remove the active dataset from memory."""
    global _cached_upload_summary
    clear_active_dataset()
    _cached_upload_summary = None
    return {"status": "ok", "message": "Dataset cleared."}


@app.post("/ask")
async def ask(body: AskRequest):
    try:
        df = get_active_dataframe()
    except Exception:
        raise HTTPException(status_code=400, detail="No active dataset. Please upload a CSV first.")

    # Session management
    session_id = body.session_id or str(uuid.uuid4())
    schema_profile = profile_dataframe(df)

    # ── Step 1: Resolve conversational context ──
    session_context = get_session_context_for_planner(session_id)
    conv_context = resolve_conversational_context(body.question, session_context, schema_profile)

    logger.info(f"Session: {session_id} | Mode: {conv_context['mode']}")

    # ── Step 2: Generate Query Plan & Route ──
    plan = generate_query_plan(body.question, schema_profile, body.language, conv_context)
    if not plan:
        raise HTTPException(status_code=400, detail="Could not generate a query plan for this question.")

    plan = validate_and_fix_plan(plan, schema_profile)
    plan = apply_semantic_mappings(body.question, plan, schema_profile)

    # ── Guard: if a user-specified filter was REMOVED (not corrected), abort ──
    corrections = plan.get("_filter_corrections", [])
    removed_filters = [c for c in corrections if c.startswith("Removed filter")]
    if removed_filters:
        execution_result = {
            "result_type": "empty",
            "primary_value": None,
            "unit": "",
            "records_used": 0,
            "applied_filters": plan.get("filters", {}),
            "grouped_result": [],
            "chart_data": [],
            "summary_stats": {"empty_reason": "; ".join(removed_filters)},
        }
        execution_path = "python"
    else:

        execution_path = plan.get("execution_path", "hybrid")
        logger.info(f"Execution Path: {execution_path} | Validated Plan: {plan}")

        # ── Step 2b: Metric Validation (fail-fast before execution) ──
        from backend.services.validator import validate_plan as validate_metrics, build_unsupported_response
        is_valid, invalid_reason, suggestion = validate_metrics(plan, schema_profile)
        if not is_valid:
            plan["_available_columns"] = schema_profile.get("columns", [])
            execution_result = build_unsupported_response(invalid_reason, suggestion, plan)
            execution_path = "python"
        else:
            # ── Step 3: Execute Deterministic Python (if needed) ──
            execution_result = None
            if execution_path in ["python", "hybrid"]:
                try:
                    execution_result = execute_query_plan(df, plan, schema_profile)
                except Exception as e:
                    logger.error(f"Execution engine failed: {e}", exc_info=True)
                    execution_path = "llm"
                    execution_result = {"error": str(e)}

    # ══════════════════════════════════════════════════════════════
    # CORE RESPONSE LAYER (mandatory, LLM-independent, always runs)
    # ══════════════════════════════════════════════════════════════
    from backend.services.response_builder import (
        build_aggregation_string, build_answer_text,
        build_calculation_steps, build_formula_with_values,
        build_trace_metadata
    )
    aggregation_string = ""
    deterministic_answer = None
    calculation_steps: list = []
    formula_with_values = ""
    trace_metadata = {}
    records_used = None

    if execution_result and execution_result.get("result_type") not in ("empty", None):
        aggregation_string = build_aggregation_string(plan, execution_result)
        deterministic_answer = build_answer_text(execution_result, plan, aggregation_string, body.language)
        calculation_steps = build_calculation_steps(execution_result, plan, body.language)
        formula_with_values = build_formula_with_values(execution_result, plan)
        trace_metadata = build_trace_metadata(plan, execution_result)
        records_used = execution_result.get("records_used")

    # Build core chart from execution payload (deterministic, no LLM)
    from backend.services.chart_engine import build_chart_spec
    core_chart_spec = {}
    if execution_result and execution_result.get("result_type") not in ("empty", "unsupported_metric", None):
        try:
            core_chart_spec = build_chart_spec(plan, execution_result, schema_profile, "auto")
        except Exception as e:
            logger.warning(f"Chart engine failed (safe fallback): {e}")
            core_chart_spec = {}

    # Assemble the CORE response — this is always valid even if LLM is down
    core_response = {
        "humanized_chat_answer": deterministic_answer or "",
        "answer": {
            "headline": deterministic_answer or "Analysis Result",
            "summary": "",
            "primary_value": execution_result.get("primary_value") if execution_result else None,
            "unit": execution_result.get("unit", "") if execution_result else "",
            "result_type": execution_result.get("result_type", "explanation") if execution_result else "explanation",
            "answer_type": execution_path,
            "trace": trace_metadata,
        },
        "chart": core_chart_spec,
        "insights": {
            "ai": [],
            "deterministic": {
                "aggregation_string": aggregation_string,
                "calculation_steps": calculation_steps,
                "formula_with_values": formula_with_values,
                "records_used": records_used,
                "trace": trace_metadata,
            }
        },
        "anomalies": [],
        "kpis": [],
        "suggested_questions": [],
        "follow_up_questions": [],
        "query_plan": plan,
        "calculation_details": execution_result if execution_result else {},
        "session_id": session_id,
        "conversation_state": {
            "mode": conv_context["mode"],
            "used_prior_context": conv_context["mode"] != "new_query",
            "carried_from_previous": [k for k, v in conv_context.get("carry_over_fields", {}).items() if v],
            "turn_count": len(get_session(session_id).get("turns", [])) // 2 + 1,
        }
    }

    if plan.get("_filter_corrections"):
        core_response.setdefault("verification", {})["filter_corrections"] = plan["_filter_corrections"]

    if plan.get("_planner_fallback"):
        core_response.setdefault("verification", {})["planner_fallback"] = plan["_planner_fallback"]
    if plan.get("_plan_cache_hit"):
        core_response.setdefault("verification", {})["plan_cache_hit"] = True

    if execution_result and execution_result.get("result_type") == "unsupported_metric":
        stats = execution_result.get("summary_stats", {})
        core_response["answer"]["error"] = stats.get("unsupported_reason", "Unsupported query.")
        core_response["answer"]["available_columns"] = stats.get("available_columns", [])

    # ══════════════════════════════════════════════════════════════
    # OPTIONAL ENHANCEMENT LAYER (LLM — additive only, never destructive)
    # If this entire block fails, core_response is returned as-is.
    # ══════════════════════════════════════════════════════════════

    # GUARD: Never call LLM when execution returned empty — it will hallucinate.
    is_empty = execution_result and execution_result.get("result_type") in ("empty", None)
    if is_empty:
        # Generate human-friendly empty message
        empty_reason = execution_result.get("summary_stats", {}).get("empty_reason", "")
        corrections = plan.get("_filter_corrections", [])
        is_ar = body.language == "ar"
        if corrections:
            correction_text = "; ".join(corrections)
            empty_msg = (
                f"لم يتم العثور على بيانات مطابقة. تعديلات الفلتر: {correction_text}" if is_ar
                else f"No matching data found. Filter adjustments: {correction_text}"
            )
        elif empty_reason:
            empty_msg = (
                f"لم يتم العثور على بيانات. {empty_reason}" if is_ar
                else f"No data found. {empty_reason}"
            )
        else:
            empty_msg = (
                "لم يتم العثور على بيانات مطابقة للمعايير المحددة." if is_ar
                else "No data matched the specified criteria. Please check the filters and try again."
            )
        core_response["humanized_chat_answer"] = empty_msg
        core_response["answer"]["summary"] = empty_msg
        core_response["answer"]["headline"] = "لا توجد نتائج" if is_ar else "No Results Found"

    skip_llm_enrichment = bool(plan.get("_planner_fallback") or plan.get("_plan_cache_hit"))
    if skip_llm_enrichment and not is_empty:
        fallback_summary = deterministic_answer or "Deterministic result returned without LLM enrichment."
        core_response["answer"]["summary"] = fallback_summary
        core_response["humanized_chat_answer"] = fallback_summary
        core_response.setdefault("verification", {})["llm_enrichment_skipped"] = (
            "planner_fallback_or_cache_hit"
        )

    if not is_empty and not skip_llm_enrichment:
      try:
        from backend.services.enrichment_engine import generate_enrichment
        enriched = generate_enrichment(body.question, df, schema_profile, plan, execution_result, body.language)

        # Additive enrichments — only ADD to core, never REPLACE deterministic values
        llm_answer_text = enriched.get("answer_text", "")
        llm_insights = enriched.get("key_insights", [])
        llm_kpis = enriched.get("kpis", [])
        llm_caveats = enriched.get("caveats", [])
        llm_chart_type = enriched.get("chart_type", "auto")
        llm_chart_title = enriched.get("chart_title", "")

        # Enrich headline with business-friendly title from LLM
        if llm_chart_title:
            core_response["answer"]["headline"] = llm_chart_title

        # Enrich summary with LLM humanized explanation
        if llm_answer_text:
            core_response["answer"]["summary"] = llm_answer_text

        # Use LLM humanized text as the PRIMARY chat answer
        if llm_answer_text:
            core_response["humanized_chat_answer"] = llm_answer_text

        # Enrich insights (additive only)
        if llm_insights:
            core_response["insights"]["ai"] = llm_insights

        # Enrich KPIs (additive only)
        if llm_kpis:
            core_response["kpis"] = llm_kpis

        # Enrich caveats (additive only)
        if llm_caveats:
            core_response["anomalies"] = llm_caveats

        # Chart override: only if LLM says "none" AND execution had no chart
        if llm_chart_type == "none" and not core_chart_spec.get("plotly_data"):
            core_response["chart"] = {}

        # For pure LLM path with no execution result, inject LLM chart data
        llm_chart_data = enriched.get("chart_data", [])
        if execution_path == "llm" and not core_chart_spec.get("plotly_data") and llm_chart_data:
            try:
                injected_result = {"result_type": "table", "chart_data": llm_chart_data, "summary_stats": {}}
                core_response["chart"] = build_chart_spec(plan, injected_result, schema_profile, llm_chart_type)
            except Exception:
                pass  # Chart is optional, fail silently

      except Exception as e:
        # LLM enrichment failed — provide human-friendly fallback, never raw errors
        logger.warning(f"Optional enhancement layer failed (safe fallback used): {e}")
        is_ar = body.language == "ar"
        if deterministic_answer:
            fallback_summary = (
                f"{deterministic_answer} الرؤى الإضافية غير متوفرة مؤقتاً." if is_ar
                else f"{deterministic_answer} Additional narrative insights are temporarily unavailable."
            )
        else:
            fallback_summary = (
                "الرؤى الإضافية غير متوفرة مؤقتاً." if is_ar
                else "Additional narrative insights are temporarily unavailable."
            )
        core_response["answer"]["summary"] = fallback_summary

    # ── Final: Update Session ──
    update_session(session_id, body.question, plan, execution_result if execution_result else {}, core_response)

    return core_response


@app.post("/reset-session")
async def reset_session(body: ResetRequest):
    clear_session(body.session_id)
    return {"status": "ok", "session_id": body.session_id, "message": "Session cleared."}


@app.get("/session-state")
def session_state(session_id: str):
    """Debug endpoint to view session state."""
    session = get_session(session_id)
    return {
        "session_id": session_id,
        "turns": len(session.get("turns", [])),
        "last_question": session.get("last_question"),
        "last_metric": session.get("last_metric"),
        "last_operation": session.get("last_operation"),
        "last_result_type": session.get("last_result_type"),
        "last_result_summary": session.get("last_result_summary"),
    }
