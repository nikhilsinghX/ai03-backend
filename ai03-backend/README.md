# InterviewLens — AI-03 Adaptive AI Hiring Interview Agent

This merged checkpoint includes the FastAPI backend and the Member 3 plain HTML/CSS/JS frontend for **Setup → Rubric & Question Review → AI Disclosure & Consent**. The live interview loop and reviewer report are intentionally the next stage, as agreed.

## Run on Windows
1. Install Python 3.10+ and open PowerShell in `ai03-backend`.
2. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env`. Leave `ANTHROPIC_API_KEY` empty to use deterministic demo/mock mode; add a valid key only if you want live LLM calls.
4. Start the API from inside `ai03-backend`:
   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```
5. In a second terminal, serve the frontend folder (recommended instead of opening `index.html` directly):
   ```powershell
   cd frontend
   python -m http.server 3000
   ```
6. Open `http://localhost:3000`. API docs: `http://127.0.0.1:8000/docs`.

## Test
From `ai03-backend` with the virtual environment active:
```powershell
pytest -q
```

## Current API
- `GET /health` — backend and mock-mode status
- `POST /sessions` — create session and generate rubric + question plan
- `GET /sessions/{id}` — session, rubric, plan and turns
- `PUT /sessions/{id}/rubric` — save recruiter edits before starting
- `POST /sessions/{id}/consent` — record required candidate consent
- `POST /sessions/{id}/start` — blocked until consent is recorded
- `POST /sessions/{id}/answer` — backend answer endpoint for the next stage
- `GET /sessions/{id}/assessment` — assessment after completion
- `/api/...` aliases — partial aliases matching the project plan's Appendix A

## Notes / limitations at this checkpoint
- Session data is held in memory and is lost when the backend restarts. SQLite persistence is not implemented yet.
- Voice helper functions are prepared, but the full live voice interview, adaptive-reason panel, transcript navigation and reviewer report are not part of this checkpoint yet.
- The mock mode is for integration testing, not a validated hiring assessment. Every hiring decision must remain with a human reviewer.
- Use fictional candidate data in demos. Do not assess protected traits, accent, appearance, personality, or culture fit.
