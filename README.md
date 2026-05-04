# Chatlytics

An open-source conversational analytics tool. Ask analytics questions in natural language; the backend converts them into structured query plans, executes the calculations deterministically with pandas, and returns a traceable JSON response with charts and a narrative summary.

![Runtime Architecture and Guardrails](docs/images/runtime-architecture.png)

_LLM for language understanding, Python for deterministic analytics. See [docs/RUNTIME_ARCHITECTURE.md](docs/RUNTIME_ARCHITECTURE.md) for the full walkthrough._

![Chatlytics landing page](docs/images/landing-page.png)

## Why Chatlytics

- **LLM for planning, Python for math.** The LLM maps natural language to a JSON query plan; pandas performs the actual filters, aggregations, comparisons, and rankings — no hallucinated numbers.
- **Traceable answers.** Every response includes the operation, filters, columns used, and rows considered so a reviewer can see how the answer was derived.
- **Schema-aware.** Uploaded CSVs are profiled before planning. Missing-column questions return structured "unsupported" responses instead of fabricated answers.
- **Bilingual UI.** English / Arabic toggle in the Next.js reviewer interface.

## Project Structure

```
├── backend/
│   ├── main.py          # FastAPI entry point and route handlers
│   ├── services/        # Query planner, execution engine, validators, response builder
│   └── tests/           # Regression + scenario tests (pytest)
├── web/                 # Next.js reviewer UI (chat, charts, calculation traces)
├── docs/
│   ├── ARCHITECTURE.md          # Production architecture discussion
│   └── RUNTIME_ARCHITECTURE.md  # Runtime data flow and guardrails
├── data/                # Uploaded datasets (gitignored active copy)
├── scripts/             # Local run helpers
├── requirements.txt
└── README.md
```

## Setup

```bash
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r requirements.txt
```

Optionally create a `.env` file for LLM-backed query planning of open-ended questions:

```bash
GROQ_API_KEY=your_key_here
```

The key is optional. The included sample scenarios use deterministic planning first, so you can run and verify the core demo without an LLM provider key. The LLM is used only to translate open-ended natural-language questions into a structured query plan and to optionally enrich the narrative summary. Calculation, validation, response-building, and chart layers are deterministic Python.

Successful plans are cached briefly by `question + schema` to reduce repeat token usage.

## Running

### One-command local start (recommended)

```bash
./scripts/start.sh
```

Runs both the backend and frontend **in a single terminal** with colour-coded output. Press `Ctrl+C` once to shut down both services.

- Backend (FastAPI) → `http://localhost:8000`
- Frontend (Next.js) → `http://localhost:3100`
- Health check → `http://localhost:8000/health`

The script automatically kills stale processes, installs npm dependencies if needed, and restores the last uploaded dataset across reloads.

### Manual start (two terminals)

**Backend:**

```bash
./scripts/restart_backend.sh
```

Or directly:

```bash
uvicorn backend.main:app --reload --port 8000
```

**Frontend:**

```bash
cd web
npm install
npm run dev
```

## API Quickstart

Upload a CSV (the repo includes a sample smart-grid dataset):

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

More example prompts against the sample dataset:

```bash
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
  -d '{"question":"On March 12, which hour had the highest generation and what was the load at that time?","language":"en"}'

curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
  -d '{"question":"Which assets had the highest maintenance hours during the month?","language":"en"}'

curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
  -d '{"question":"Compare solar output during business hours vs off-peak hours.","language":"en"}'
```

## Verification

```bash
backend/venv/bin/python -m pytest backend/tests/test_assessment_scenarios.py -q
backend/venv/bin/python -m pytest backend/tests/test_regression.py -q
backend/venv/bin/python -m compileall backend -q
cd web && npm run lint
```

## License

MIT — see `LICENSE`. Use it freely for your own conversational analytics projects.
