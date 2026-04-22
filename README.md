# Conversational Analytics

A conversational analytics proof of concept built for the Aldar AI Architect assessment. The backend accepts natural-language analytics questions, converts them into structured query plans, executes calculations deterministically with pandas, and returns a traceable JSON response.

## Project Structure

```
├── backend/
│   ├── main.py          # FastAPI entry point
│   ├── services/        # Business logic (empty for now)
│   └── models/          # Data models (empty for now)
├── web/                 # Next.js reviewer UI
├── docs/
│   └── ARCHITECTURE.md  # Part 2 Azure production architecture
├── data/                # Data storage
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

The calculation, validation, response-building, and chart layers are deterministic Python. The LLM is used to translate natural-language questions into a structured query plan and to optionally enrich the narrative summary.

If the hosted LLM is rate-limited or unavailable, the backend falls back to deterministic planning for the assessment-critical intents: average load by region, March date filters, peak generation with companion load, maintenance hours, solar business-vs-off-peak comparison, and net balance. Successful LLM plans are cached briefly by `question + schema` to reduce repeat token usage.

## Running

### Backend (FastAPI)

```bash
uvicorn backend.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Health check: `http://localhost:8000/health`

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

## Verification

```bash
backend/venv/bin/python -m pytest backend/tests/test_regression.py -q
backend/venv/bin/python -m compileall backend -q
```
