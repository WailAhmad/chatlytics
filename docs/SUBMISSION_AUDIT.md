# Submission Audit

This checklist maps the repository to the Aldar AI Architect assessment brief.
The authoritative submission repository is:

`https://github.com/WailAhmad/aldar-conversational-analytics`

## Part 1: Technical Implementation

- REST API: FastAPI routes in `backend/main.py` expose health, CSV upload, dataset profile, natural-language `/ask`, session state, and reset endpoints.
- Natural-language analytics: `backend/services/query_planner.py` maps questions to constrained query plans, with deterministic rules for assessment-critical intents and LLM fallback for broader open-ended questions.
- Deterministic calculations: `backend/services/execution_engine.py` performs averages, comparisons, rankings, peak lookup, maintenance counts, and net balance calculations with pandas.
- Traceable JSON: responses include answer metadata, query plan, calculation details, trace filters, rows considered, formula/value details, and chart specifications where applicable.
- Assessment prompts: `backend/tests/test_assessment_scenarios.py` covers all four example questions from the brief using pandas-computed ground truth.
- Reviewer UI: `web/` provides a Next.js chat interface with upload, chart, insight, and calculation-trace views.
- API review flow: `postman/aldar-conversational-analytics.postman_collection.json` covers health, upload, profile, the four assessment questions, session follow-up, session state, and reset.

## Part 2: Azure Architecture

`docs/ARCHITECTURE.md` covers:

- NL-to-structured-operation flow.
- Deterministic compute boundary versus LLM planning and narrative enrichment.
- Azure API Management, App Service or Container Apps, Azure OpenAI, ADLS Gen2, Data Factory or IoT/Event Hubs, Redis, Key Vault, App Insights, and scale-out options.
- Accuracy controls through schema validation, guarded plans, deterministic execution, and golden-query regression tests.
- Failure handling for invalid plans, missing columns, LLM outages, empty results, and data-source availability.
- Security, authorization, prompt-safety, monitoring, and cost-control considerations.

## Dataset Notes

- The tracked assessment dataset is `data/Smart_Grid_Master_March_2026.csv`.
- The supplied CSV contains `timestamp`, `asset_id`, `region`, `load_kwh`, `generation_kwh`, and `status_code`.
- The assessment data dictionary mentions `curtailment_flag`, but the supplied CSV does not include it. The API intentionally returns structured unsupported responses for missing-column questions instead of fabricating values.
- Maintenance hours are interpreted as records with `status_code == 505`, matching the brief's status-code dictionary.

## Verification Commands

Run these from the repository root:

```bash
backend/venv/bin/python -m pytest backend/tests/test_assessment_scenarios.py -q
backend/venv/bin/python -m pytest backend/tests/test_regression.py -q
backend/venv/bin/python -m compileall backend -q
cd web && npm run lint
```

Latest local audit result before submission:

- Assessment scenario tests: passing.
- Regression tests: passing.
- Backend compile check: passing.
- Frontend lint: passing.

## Submission Packaging

The preferred deliverable is the GitHub repository link. If a zip archive is required, run:

```bash
./scripts/create_submission_archive.sh
```

The archive script excludes local secrets and generated dependencies, including `.env`, `.git`, `backend/venv`, `web/node_modules`, `web/.next`, and `data/active_dataset.csv`.
