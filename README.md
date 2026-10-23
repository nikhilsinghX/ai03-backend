# AI-03 Backend (Member 1)

## Run
    python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env        # add ANTHROPIC_API_KEY later; empty = mock mode
    uvicorn app.main:app --reload --port 8000
    # docs: http://localhost:8000/docs

## Test
    pytest -q

## API contract (share with the team)
| Method | Path | Purpose |
|---|---|---|
| GET | /health | liveness + mock flag |
| POST | /sessions | body {jd_text, resume_text} -> session with rubric + plan |
| GET | /sessions/{id} | full session incl. transcript |
| PUT | /sessions/{id}/rubric | recruiter edits rubric (before start) |
| POST | /sessions/{id}/start | returns first agent question |
| POST | /sessions/{id}/answer | body {text} -> next agent turn, `done` flag |
| GET | /sessions/{id}/assessment | scores + verified evidence quotes |

## Ownership
- Member 2 edits prompts in app/pipeline.py
- Member 3 consumes the endpoints above (voice text <-> /answer)
- Member 4 uses tests/ and sample_*.md
