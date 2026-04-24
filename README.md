# Conversational Analytics

A conversational analytics proof of concept built for the Aldar AI Architect assessment. The backend accepts natural-language analytics questions, converts them into structured query plans, executes calculations deterministically with pandas, and returns a traceable JSON response.

![Runtime Architecture and Guardrails](docs/images/runtime-architecture.png)

_LLM for language understanding, Python for deterministic analytics. See [docs/RUNTIME_ARCHITECTURE.md](docs/RUNTIME_ARCHITECTURE.md) for the full walkthrough._

![Data Analytics Copilot landing page](docs/images/landing-page.png)

## Project Structure

```
├── backend/
│   ├── main.py          # FastAPI entry point and route handlers
│   ├── services/        # Query planner, execution engine, validators, response builder
│   └── tests/           # Regression + assessment-scenario tests (pytest, 43 passing)
├── web/                 # Next.js reviewer UI (chat, charts, calculation traces)
├── docs/
│   ├── ARCHITECTURE.md  # Part 2 Azure production architecture
│   └── SUBMISSION_AUDIT.md # Assessment-readiness checklist
├── data/                # Uploaded datasets (gitignored active copy)
├── scripts/             # Local run + submission helpers
├── requirements.txt
└── README.md
```

## Design Decisions

- **LLM for planning, Python for math**: the LLM maps natural language to JSON operations; pandas performs the actual filters, aggregations, comparisons, and rankings.
- **Traceable responses**: `/ask` returns the answer plus filters, operation, rows considered, and columns used so reviewers can see how the result was derived.
- **Schema-aware execution**: uploaded CSVs are profiled before planning, and invalid or missing columns return structured unsupported responses instead of empty JSON.
- **Single frontend**: use the Next.js app in `web/` for submission review.

## Setup

```bash
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file for LLM-backed query planning:

```bash
GROQ_API_KEY=your_key_here
```

This key is optional for the assessment-critical path. The four example
questions from the brief use deterministic planning first, so reviewers can run
and verify the core demo without an LLM provider key.

The calculation, validation, response-building, and chart layers are deterministic Python. The LLM is used to translate open-ended natural-language questions into a structured query plan and to optionally enrich the narrative summary.

Assessment-critical intents use deterministic planning first: average load by region, March date filters, peak generation with companion load, maintenance hours, solar business-vs-off-peak comparison, and net balance. This keeps the demo path available even if the hosted LLM is rate-limited. Successful plans are cached briefly by `question + schema` to reduce repeat token usage.

## Running

### Backend (FastAPI)

Recommended for demos, because it kills any stale process on port `8000` before starting the latest code:

```bash
./scripts/restart_backend.sh
```

Manual equivalent:

```bash
uvicorn backend.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Health check: `http://localhost:8000/health`

The health response includes the running git commit and working directory. If the UI ever behaves like old code is running, check this endpoint first and restart with `./scripts/restart_backend.sh`.

The backend restores the last uploaded dataset from `data/active_dataset.csv` across local reloads/restarts, so a code reload does not force reviewers to upload the CSV again.

### Frontend (Next.js)

```bash
cd web
npm install
npm run dev
```

The reviewer UI will be available at `http://localhost:3000`.

## API Quickstart

Upload the supplied smart-grid CSV:

```bash
curl -X POST http://localhost:8000/upload-csv \
  -F "file=@data/Smart_Grid_Master_March_2026.csv"
```

Ask a natural-language question:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What was the average hourly load in North_District during the second week of March?","language":"en"}'
```

Assessment example prompts:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What was the average hourly load in North_District during the second week of March?","language":"en"}'

curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"On March 12, which hour had the highest generation and what was the load at that time?","language":"en"}'

curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Which assets had the highest maintenance hours during the month?","language":"en"}'

curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Compare solar output during business hours vs off-peak hours.","language":"en"}'
```

## Assessment Notes

- `POST /ask` is the main natural-language analytics endpoint.
- Maintenance questions are mapped deterministically to `status_code == 505`.
- Solar-output questions are mapped to `generation_kwh` for assets whose ID contains `SOLAR` when the dataset has no literal solar-output column.
- Week phrases such as `second week of March` are resolved as the assessment example window; for March 2026, week 2 is `2026-03-07` through `2026-03-14`.
- Peak-generation wording is explicit: `which hour had the highest generation` returns the hourly sum across matching assets, while row-level peak wording can return the single asset row where generation peaked.
- The assessment data dictionary mentions `curtailment_flag`, but the supplied CSV does not contain that column. The schema validator returns a structured unsupported response for missing-column questions rather than fabricating an answer.
- See `docs/ARCHITECTURE.md` for the Azure production architecture discussion.

## Submission Packaging

Preferred submission is a Git repository link so reviewers can inspect history and avoid local archive artifacts. If a zip archive is required, create it with:

```bash
./scripts/create_submission_archive.sh
```

The script excludes local secrets and generated dependencies such as `.env`, `.git`, `backend/venv`, `web/node_modules`, `web/.next`, and `data/active_dataset.csv`. Reviewers should create their own `.env` from `.env.example` and set `GROQ_API_KEY` if they want LLM-backed open-ended planning.

Authoritative repository: `https://github.com/WailAhmad/aldar-conversational-analytics`.

See `docs/SUBMISSION_AUDIT.md` for a concise checklist showing how this project maps to the assessment brief.

## One-Command Local Start

To bring both backend and frontend up in two clean terminal windows (killing any stale processes first), use:

```bash
./scripts/start_demo.sh
```

This starts the backend on `http://localhost:8000` and the frontend on `http://localhost:3000`.

## Verification

```bash
backend/venv/bin/python -m pytest backend/tests/test_assessment_scenarios.py -q
backend/venv/bin/python -m pytest backend/tests/test_regression.py -q
backend/venv/bin/python -m compileall backend -q
cd web && npm run lint
```
