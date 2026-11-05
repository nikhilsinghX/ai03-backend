"""Runs scripted fictional candidates through the interview logic directly (no HTTP) and checks them
against sample_data/gold.json. Used by tests/test_scenarios.py and scripts/run_scenarios.py."""
import json
import time
from pathlib import Path
from typing import Dict, List

from . import pipeline, report, state_machine
from .schemas import Session
from .verify import quote_in_transcript, verify_assessment

DATA = Path(__file__).resolve().parents[1] / "sample_data"


def load():
    jd = (DATA / "jd_ml_intern.md").read_text(encoding="utf-8")
    answers = json.loads((DATA / "scripted_answers.json").read_text(encoding="utf-8"))
    gold = json.loads((DATA / "gold.json").read_text(encoding="utf-8"))
    return jd, answers, gold


def run_interview(jd: str, resume: str, answers: List[str]) -> Dict:
    s = Session(id="sim", jd_text=jd, resume_text=resume)
    s.rubric = pipeline.generate_rubric(jd)
    s.questions = pipeline.plan_questions(s.rubric, resume, jd)
    s.state = "RUBRIC_READY"
    s.consent_given = True
    state_machine.start(s)
    latencies, i = [], 0
    while s.state != "COMPLETE" and i < 80:
        t0 = time.time()
        state_machine.submit_answer(s, answers[i % len(answers)])
        latencies.append((time.time() - t0) * 1000)
        i += 1
    raw = pipeline.assess(s.rubric, s.turns)
    a = report.finalize(verify_assessment(raw, s.turns), s.rubric, s.turns)
    shown = [q for sc in a.scores for q in sc.evidence_quotes]
    followups = [t for t in s.turns if t.kind == "followup"]
    per_q: Dict[str, int] = {}
    for t in followups:
        per_q[t.question_id] = per_q.get(t.question_id, 0) + 1
    specific = 0
    detail_followups = [t for t in followups if not t.text.startswith("Let me rephrase")]
    for t in detail_followups:
        prev = next(x for x in reversed(s.turns[:t.idx]) if x.speaker == "candidate")
        words = prev.text.split()
        if any(" ".join(words[k:k + 3]).lower() in t.text.lower() for k in range(max(1, len(words) - 2))):
            specific += 1
    return {
        "completed": s.state == "COMPLETE", "questions": len(s.questions), "turns": len(s.turns),
        "followups": len(followups), "max_followups_per_question": max(per_q.values()) if per_q else 0,
        "rephrases": sum(1 for t in followups if t.text.startswith("Let me rephrase")),
        "detail_followups": len(detail_followups), "specific_followups": specific,
        "quotes_shown": len(shown), "quotes_verified": sum(quote_in_transcript(q, s.turns) for q in shown),
        "null_scores": sum(1 for x in a.scores if x.score is None), "criteria": len(a.scores),
        "overall": a.overall, "review_items": len(a.needs_human_review),
        "idk_review": any("did not know" in r.why for r in a.needs_human_review),
        "median_turn_ms": round(sorted(latencies)[len(latencies) // 2], 2) if latencies else 0,
        "session": s, "assessment": a,
    }


def check(name: str, r: Dict, gold: Dict) -> List[str]:
    """Return a list of failed expectations (empty = pass)."""
    g, bad = gold[name], []
    if not r["completed"]: bad.append("interview did not complete")
    if r["max_followups_per_question"] > 2: bad.append("more than 2 follow-ups on one question")
    if r["quotes_shown"] != r["quotes_verified"]: bad.append("a displayed quote failed verification")
    if "min_followups" in g and r["followups"] < g["min_followups"]: bad.append("too few follow-ups")
    if "max_followups" in g and r["followups"] > g["max_followups"]: bad.append("too many follow-ups")
    if "null_scores" in g and r["null_scores"] != g["null_scores"]: bad.append("unexpected insufficient-evidence criteria")
    if g.get("all_null") and r["null_scores"] != r["criteria"]: bad.append("expected every criterion to lack evidence")
    if g.get("rephrase_expected") and r["rephrases"] < 1: bad.append("expected a polite rephrase")
    if g.get("review_expected") and not r["idk_review"]: bad.append("'I don't know' was not flagged for the human reviewer")
    return bad


def run_all():
    jd, answers, gold = load()
    out = {}
    for name, g in gold.items():
        resume = (DATA / "resumes" / f"{g['resume']}.md").read_text(encoding="utf-8")
        r = run_interview(jd, resume, answers[name])
        r["failed"] = check(name, r, gold)
        out[name] = r
    return out
