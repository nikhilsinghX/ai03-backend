import os
import sqlite3
import uuid
from contextlib import closing

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from . import llm, pipeline, report, state_machine
from .schemas import AnswerIn, Rubric, Session, SessionCreate
from .verify import verify_assessment

app = FastAPI(title="AI-03 Adaptive Hiring Interview Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# SQLite storage: sessions survive a server restart. DB_PATH can be overridden (tests do).
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).resolve().parents[1] / "interviewlens.db"))


def _db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
    return con


def _save(s: Session) -> None:
    with closing(_db()) as con:
        con.execute("INSERT OR REPLACE INTO sessions (id, data) VALUES (?, ?)", (s.id, s.model_dump_json()))
        con.commit()


def _get(sid: str) -> Session:
    with closing(_db()) as con:
        row = con.execute("SELECT data FROM sessions WHERE id = ?", (sid,)).fetchone()
    if not row:
        raise HTTPException(404, "Session not found")
    return Session.model_validate_json(row[0])


def _plan(s: Session) -> None:
    """Build the 6-8 tagged questions; `plan` keeps the first question per criterion for old clients."""
    s.questions = pipeline.plan_questions(s.rubric, s.resume_text, s.jd_text)
    s.plan = {}
    for q in s.questions:
        s.plan.setdefault(q.criterion_id, q.text)


@app.get("/health")
def health():
    return {"ok": True, "mock_llm": llm.is_mock()}


@app.post("/sessions", response_model=Session)
def create_session(body: SessionCreate):
    s = Session(id=uuid.uuid4().hex[:8], jd_text=body.jd_text, resume_text=body.resume_text)
    s.rubric = pipeline.generate_rubric(body.jd_text)
    _plan(s)
    s.state = "RUBRIC_READY"
    _save(s)
    return s


@app.get("/sessions/{sid}", response_model=Session)
def get_session(sid: str):
    return _get(sid)


@app.put("/sessions/{sid}/rubric", response_model=Session)
def edit_rubric(sid: str, rubric: Rubric):
    s = _get(sid)
    if s.state != "RUBRIC_READY":
        raise HTTPException(409, "Rubric can only be edited before the interview starts")
    s.rubric = rubric
    _plan(s)
    _save(s)
    return s


@app.post("/sessions/{sid}/consent")
def consent(sid: str):
    s = _get(sid)
    if s.state != "RUBRIC_READY":
        raise HTTPException(409, "Consent can only be recorded before the interview starts")
    s.consent_given = True
    _save(s)
    return {"ok": True, "consent_given": True}


@app.post("/sessions/{sid}/start")
def start(sid: str):
    s = _get(sid)
    if not s.consent_given:
        raise HTTPException(403, "Candidate consent is required before starting the interview")
    try:
        turn = state_machine.start(s)
    except ValueError as e:
        raise HTTPException(409, str(e))
    _save(s)
    return {"state": s.state, "turn": turn}


@app.post("/sessions/{sid}/answer")
def answer(sid: str, body: AnswerIn):
    s = _get(sid)
    if not body.text.strip():
        raise HTTPException(422, "Empty answer")
    try:
        turn = state_machine.submit_answer(s, body.text)
    except ValueError as e:
        raise HTTPException(409, str(e))
    _save(s)
    return {"state": s.state, "turn": turn, "done": s.state == "COMPLETE"}


@app.get("/sessions/{sid}/assessment")
def assessment(sid: str):
    s = _get(sid)
    if s.state != "COMPLETE":
        raise HTTPException(409, "Interview not complete")
    if s.assessment is None:
        raw = pipeline.assess(s.rubric, s.turns)
        s.assessment = report.finalize(verify_assessment(raw, s.turns), s.rubric, s.turns)
        _save(s)
    return s.assessment


# Workflow-PDF contract aliases. The original /sessions routes remain supported.
from pydantic import BaseModel as _BaseModel

class _ApiSessionCreate(_BaseModel):
    jd_text: str
    resume_text: str

@app.get("/api/health")
def api_health():
    return health()

@app.post("/api/session")
def api_create_session(body: _ApiSessionCreate):
    s = create_session(SessionCreate(jd_text=body.jd_text, resume_text=body.resume_text))
    return {"session_id": s.id, "state": s.state, "requirements": [], "claims": []}

@app.post("/api/session/{sid}/rubric")
def api_rubric(sid: str):
    s = _get(sid)
    return s.rubric

@app.post("/api/session/{sid}/plan")
def api_plan(sid: str):
    s = _get(sid)
    return {"questions": [q.model_dump() for q in s.questions]}

@app.post("/api/session/{sid}/consent")
def api_consent(sid: str):
    return consent(sid)

@app.post("/api/session/{sid}/start")
def api_start(sid: str):
    return start(sid)

@app.post("/api/session/{sid}/answer")
def api_answer(sid: str, body: AnswerIn):
    result = answer(sid, body)
    t = result["turn"]
    session = _get(sid)
    latest_answer = next((x.text for x in reversed(session.turns) if x.speaker == "candidate"), "")
    words = latest_answer.split()
    if t.kind == "followup":
        if len(words) < 25:
            reason = "The answer was brief, so the agent is asking for a concrete example and the trade-offs considered."
        elif not any(token in latest_answer.lower() for token in ("i ", "my ", "built", "implemented", "created", "led", "designed")):
            reason = "Personal ownership was not clear, so the follow-up asks what the candidate personally contributed."
        else:
            reason = "The answer may need more detail about evidence or outcomes, so the agent is probing for specifics."
    elif t.kind == "closing":
        reason = "All planned rubric criteria have been covered; the interview is complete."
    else:
        criterion = next((c for c in session.rubric.criteria if c.id == t.criterion_id), None)
        reason = f"This question assesses {criterion.name} using the approved job-related rubric." if criterion else "This is the next planned question in the interview."
    reason = t.reason or reason
    return {"state": result["state"], "done": result["done"],
            "utterance": t.text, "kind": "follow_up" if t.kind == "followup" else ("closing" if t.kind == "closing" else "question"),
            "reason": reason, "turn": t, "coverage": _coverage(session)}

def _coverage(s: Session):
    total = len(s.rubric.criteria) if s.rubric else 0
    done = len({t.criterion_id for t in s.turns if t.speaker == "candidate" and t.criterion_id})
    return {"covered": min(done, total), "total": total, "percent": round(min(done, total) * 100 / total) if total else 0}

@app.post("/api/session/{sid}/finish")
def api_finish(sid: str):
    s = _get(sid)
    if s.state == "IN_INTERVIEW":
        if not any(t.kind == "closing" for t in s.turns):
            from .schemas import Turn
            s.turns.append(Turn(idx=len(s.turns), speaker="agent", text="The interview is ending here. Thank you for your time.", kind="closing"))
        s.state = "COMPLETE"
        _save(s)
    if s.state != "COMPLETE":
        raise HTTPException(409, "Interview has not started")
    return {"ok": True, "assessment": assessment(sid)}

@app.get("/api/session/{sid}/assessment")
def api_assessment(sid: str):
    return assessment(sid)

@app.get("/api/session/{sid}/transcript")
def api_transcript(sid: str):
    s = _get(sid)
    return {"turns": [{"turn_id": t.idx, "speaker": t.speaker, "text": t.text,
                       "question_id": t.criterion_id, "kind": t.kind} for t in s.turns]}


# Serve the frontend from this same FastAPI process/port. Keep this mount last so
# the API routes above take precedence over the catch-all static route.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
