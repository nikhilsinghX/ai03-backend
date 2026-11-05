# ai03-backend

FastAPI backend. It also serves the frontend from `../frontend`, so there is only ONE server.

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python run.py            # then open http://127.0.0.1:8000

Tests: `python -m pytest -q` and `python -m pytest app/member2 -q`
Rehearsal run (server running): `python scripts/demo_run.py`
API docs: http://127.0.0.1:8000/docs. See the root README.md for the full picture.
