"""Interview flow: ask each planned question, allow up to MAX_FOLLOWUPS adaptive follow-ups on it,
then move on. Guards: total candidate-turn budget, time limit, and coverage (every planned question
still gets asked). Ends with a closing turn."""
import os
import time

from . import pipeline
from .schemas import Session, Turn

MAX_FOLLOWUPS = int(os.getenv("MAX_FOLLOWUPS", "2"))
MAX_CANDIDATE_TURNS = int(os.getenv("MAX_CANDIDATE_TURNS", "14"))
INTERVIEW_MINUTES = float(os.getenv("INTERVIEW_MINUTES", "15"))

OPENING = ("Hello, I'm an AI interviewer. A human reviewer, not me, will make any hiring decision. "
           "Let's begin.")


def _add(s: Session, speaker, text, crit=None, kind="main", reason=None, qid=None) -> Turn:
    t = Turn(idx=len(s.turns), speaker=speaker, text=text, criterion_id=crit, kind=kind,
             reason=reason, question_id=qid)
    s.turns.append(t)
    return t


def _crit(s: Session, cid):
    return next(c for c in s.rubric.criteria if c.id == cid)


def _ask_current_main(s: Session) -> Turn:
    q = s.questions[s.q_pos]
    c = _crit(s, q.criterion_id)
    s.followups_used = 0
    why = (f"Question {s.q_pos + 1} of {len(s.questions)} tests '{c.name}'. "
           f"Source: {q.source.type.upper()} - {q.source.ref}.")
    text = (OPENING + " " if not s.turns else "") + q.text
    return _add(s, "agent", text, c.id, "main", why, q.id)


def start(s: Session) -> Turn:
    if s.state != "RUBRIC_READY":
        raise ValueError("Session must be RUBRIC_READY to start")
    if not s.questions:
        s.questions = pipeline.plan_questions(s.rubric, s.resume_text, s.jd_text)
    s.state = "IN_INTERVIEW"
    s.q_pos = 0
    s.started_at = time.time()
    return _ask_current_main(s)


def _followup_allowed(s: Session) -> bool:
    if s.followups_used >= MAX_FOLLOWUPS:
        return False
    if s.started_at and (time.time() - s.started_at) / 60 > INTERVIEW_MINUTES:
        return False  # out of time: only uncovered questions remain
    asked = sum(1 for t in s.turns if t.speaker == "candidate")
    remaining = len(s.questions) - s.q_pos - 1
    return (MAX_CANDIDATE_TURNS - asked) > remaining  # keep one turn for every uncovered question


def submit_answer(s: Session, text: str) -> Turn:
    if s.state != "IN_INTERVIEW":
        raise ValueError("Interview is not in progress")
    q = s.questions[s.q_pos]
    c = _crit(s, q.criterion_id)
    last_agent = next(t for t in reversed(s.turns) if t.speaker == "agent")
    _add(s, "candidate", text, c.id, "answer", None, q.id)

    if _followup_allowed(s):
        need, fq, why = pipeline.decide_followup(c, last_agent.text, text, s.followups_used, q.text)
        if need and fq:
            s.followups_used += 1
            reason = f"Follow-up {s.followups_used} of {MAX_FOLLOWUPS} on '{c.name}': " + (
                why or "the answer looked vague or lacked a concrete example or trade-offs.")
            return _add(s, "agent", fq, c.id, "followup", reason, q.id)

    s.q_pos += 1
    if s.q_pos >= len(s.questions):
        s.state = "COMPLETE"
        return _add(s, "agent", "That's all my questions. Thank you for your time!", None, "closing",
                    "All planned questions are covered; the interview is complete.")
    return _ask_current_main(s)
