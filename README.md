# Conversational Analytics

A conversational analytics system built with FastAPI and Streamlit.

## Project Structure

```
├── backend/
│   ├── main.py          # FastAPI entry point
│   ├── services/        # Business logic (empty for now)
│   └── models/          # Data models (empty for now)
├── frontend/
│   └── app.py           # Streamlit dashboard
├── data/                # Data storage
├── requirements.txt
└── README.md
```

## Setup

```bash
pip install -r requirements.txt
```

## Running

### Backend (FastAPI)

```bash
uvicorn backend.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Health check: `http://localhost:8000/health`

### Frontend (Streamlit)

```bash
streamlit run frontend/app.py
```

The dashboard will open at `http://localhost:8501`.
