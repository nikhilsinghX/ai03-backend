"""Interview flow: for each criterion ask the planned question, then allow up
to MAX_FOLLOWUPS adaptive follow-ups, then move on. Ends with a closing turn."""
import os

from . import pipeline
from .schemas import Session, Turn

MAX_FOLLOWUPS = int(os.getenv("MAX_FOLLOWUPS", "2"))


def _add(s: Session, speaker, text, crit=None, kind="main") -> Turn:
    t = Turn(idx=len(s.turns), speaker=speaker, text=text, criterion_id=crit, kind=kind)
    s.turns.append(t)
    return t


def _ask_current_main(s: Session) -> Turn:
    c = s.rubric.criteria[s.crit_pos]
    s.followups_used = 0
    return _add(s, "agent", s.plan[c.id], c.id, "main")


def start(s: Session) -> Turn:
    if s.state != "RUBRIC_READY":
        raise ValueError("Session must be RUBRIC_READY to start")
    s.state = "IN_INTERVIEW"
    s.crit_pos = 0
    return _ask_current_main(s)


def submit_answer(s: Session, text: str) -> Turn:
    if s.state != "IN_INTERVIEW":
        raise ValueError("Interview is not in progress")
    c = s.rubric.criteria[s.crit_pos]
    last_agent = next(t for t in reversed(s.turns) if t.speaker == "agent")
    _add(s, "candidate", text, c.id, "answer")

    if s.followups_used < MAX_FOLLOWUPS:
        need, q = pipeline.decide_followup(c, last_agent.text, text)
        if need and q:
            s.followups_used += 1
            return _add(s, "agent", q, c.id, "followup")

    # move to next criterion or finish
    s.crit_pos += 1
    if s.crit_pos >= len(s.rubric.criteria):
        s.state = "COMPLETE"
        return _add(s, "agent", "That's all my questions. Thank you for your time!", None, "closing")
    return _ask_current_main(s)
