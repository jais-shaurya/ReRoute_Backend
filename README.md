# ReRoute_Backend

## Local Planner Demo

This repository contains the existing FastAPI supply-chain planner. The
separate `ReRoute_Frontend` repository is a static HTML/CSS/JavaScript client;
no frontend package installation is required.

### Prerequisites

- Python and the PostgreSQL driver supported by `requirements.txt`.
- A PostgreSQL database with the ReRoute tables and development records.
- A local backend `.env` containing `DATABASE_URL`. Do not commit this file.

### Start the backend (PowerShell)

```powershell
cd d:\ReRoute\ReRoute_Backend
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check `http://127.0.0.1:8000/health` or open
`http://127.0.0.1:8000/docs` for the planner API.

### Start the frontend

In a second PowerShell terminal:

```powershell
cd d:\ReRoute\ReRoute_Frontend
python -m http.server 5500
```

Open `http://localhost:5500`. The page posts planning requests to
`http://127.0.0.1:8000/api/planner/recommend`.

### Tests and data safety

Run backend tests with `python -m pytest -q scripts`. The existing suite uses
the configured database for integration tests; make sure it contains the
expected development records before running it.

Do not run `scripts/seed_data.py` against a database with data to keep. That
development helper deletes and recreates the existing supply-chain rows.