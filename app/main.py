import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import llm, pipeline, state_machine
from .schemas import AnswerIn, Rubric, Session, SessionCreate
from .verify import verify_assessment

app = FastAPI(title="AI-03 Adaptive Hiring Interview Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

STORE: Dict[str, Session] = {}  # in-memory; swap for SQLite later if time permits


def _get(sid: str) -> Session:
    if sid not in STORE:
        raise HTTPException(404, "Session not found")
    return STORE[sid]


@app.get("/health")
def health():
    return {"ok": True, "mock_llm": llm.is_mock()}


@app.post("/sessions", response_model=Session)
def create_session(body: SessionCreate):
    s = Session(id=uuid.uuid4().hex[:8], jd_text=body.jd_text, resume_text=body.resume_text)
    s.rubric = pipeline.generate_rubric(body.jd_text)
    s.plan = pipeline.plan_questions(s.rubric, body.resume_text)
    s.state = "RUBRIC_READY"
    STORE[s.id] = s
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
    s.plan = pipeline.plan_questions(rubric, s.resume_text)
    return s


@app.post("/sessions/{sid}/start")
def start(sid: str):
    s = _get(sid)
    try:
        turn = state_machine.start(s)
    except ValueError as e:
        raise HTTPException(409, str(e))
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
    return {"state": s.state, "turn": turn, "done": s.state == "COMPLETE"}


@app.get("/sessions/{sid}/assessment")
def assessment(sid: str):
    s = _get(sid)
    if s.state != "COMPLETE":
        raise HTTPException(409, "Interview not complete")
    if s.assessment is None:
        raw = pipeline.assess(s.rubric, s.turns)
        s.assessment = verify_assessment(raw, s.turns)
    return s.assessment
