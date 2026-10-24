"""AI steps: rubric, question plan, follow-up decision, assessment.
PROMPTS live here -> Member 2 owns this file. MOCK mode keeps everything
working without an API key so other members are never blocked."""
import re
from typing import List, Tuple

from . import llm
from .schemas import Assessment, Criterion, CriterionScore, Rubric, Turn

SAFETY = (
    "Judge ONLY job-related skills. Never use or infer age, gender, religion, "
    "caste, nationality, appearance, accent, or any personal/demographic trait."
)

RUBRIC_SYSTEM = (
    "You design interview rubrics. " + SAFETY +
    ' Output JSON: {"role_title": str, "criteria": [{"id": "c1", "name": str, '
    '"description": str, "weight": number, "anchors": {"1": str, "3": str, "5": str}}]}. '
    "Produce 4-6 criteria drawn from the job description."
)

PLAN_SYSTEM = (
    "You write ONE interview question per criterion, tailored to the resume. " + SAFETY +
    ' Output JSON: {"c1": "question", "c2": "question"}.'
)

FOLLOWUP_SYSTEM = (
    "You are an interviewer deciding whether to probe deeper. " + SAFETY +
    ' Output JSON: {"needs_followup": bool, "question": str}. '
    "Follow up only if the answer is vague, lacks an example, or skips trade-offs."
)

ASSESS_SYSTEM = (
    "You score a finished interview against the rubric. " + SAFETY +
    " Every score MUST cite 1-2 verbatim quotes from the candidate's answers. "
    'Output JSON: {"scores": [{"criterion_id": str, "score": 1-5, "rationale": str, '
    '"evidence_quotes": [str]}], "overall": number, "summary": str}.'
)


# ---------- MOCK helpers ----------
def _mock_rubric(jd: str) -> Rubric:
    first = jd.strip().splitlines()[0].lstrip("# ").strip() if jd.strip() else "Role"
    names = [
        ("Technical fundamentals", "Core concepts needed for the role"),
        ("Problem solving", "Breaks down problems and reasons about trade-offs"),
        ("Project ownership", "Has built and shipped real work"),
        ("Communication clarity", "Explains job-related ideas clearly and directly"),
        ("Learning agility and collaboration", "Learns from feedback and contributes effectively with others"),
        ("Evaluation and experimentation", "Chooses sensible metrics and tests assumptions with evidence"),
    ]
    crit = [
        Criterion(
            id=f"c{i+1}", name=n, description=d,
            anchors={"1": "Cannot explain basics", "3": "Correct with small gaps",
                     "5": "Accurate, discusses trade-offs"},
        )
        for i, (n, d) in enumerate(names)
    ]
    return Rubric(role_title=first, criteria=crit)


def _mock_plan(rubric: Rubric, resume: str = "") -> dict:
    return {
        c.id: (
            f"Your resume mentions {resume.strip().splitlines()[0][:80]}. "
            f"Can you give a concrete example demonstrating {c.name.lower()}, including your own contribution and the result?"
            if resume.strip() else f"Can you give a concrete example demonstrating {c.name.lower()}, including your own contribution and the result?"
        ) for c in rubric.criteria
    }


# ---------- Public API ----------
def generate_rubric(jd: str) -> Rubric:
    if llm.is_mock():
        return _mock_rubric(jd)
    data = llm.call_json(RUBRIC_SYSTEM, f"JOB DESCRIPTION:\n{jd}")
    return Rubric(**data)


def plan_questions(rubric: Rubric, resume: str) -> dict:
    if llm.is_mock():
        return _mock_plan(rubric, resume)
    data = llm.call_json(
        PLAN_SYSTEM, f"RUBRIC:\n{rubric.model_dump_json()}\n\nRESUME:\n{resume}"
    )
    return {c.id: data.get(c.id, f"Tell me about your experience with {c.name}.") for c in rubric.criteria}


def decide_followup(criterion: Criterion, question: str, answer: str) -> Tuple[bool, str]:
    if llm.is_mock():
        if len(answer.split()) < 25:
            return True, "Could you give a specific example and explain the trade-offs you considered?"
        return False, ""
    data = llm.call_json(
        FOLLOWUP_SYSTEM,
        f"CRITERION: {criterion.model_dump_json()}\nQUESTION: {question}\nANSWER: {answer}",
        max_tokens=400,
    )
    return bool(data.get("needs_followup")), data.get("question", "")


def assess(rubric: Rubric, turns: List[Turn]) -> Assessment:
    transcript = "\n".join(f"{t.speaker.upper()}: {t.text}" for t in turns)
    if llm.is_mock():
        scores = []
        for c in rubric.criteria:
            answers = [t for t in turns if t.speaker == "candidate" and t.criterion_id == c.id]
            quote = ""
            if answers:
                quote = " ".join(answers[0].text.split()[:12])
            scores.append(CriterionScore(
                criterion_id=c.id, score=3,
                rationale="Mock score for pipeline testing.",
                evidence_quotes=[quote] if quote else [],
            ))
        return Assessment(scores=scores, overall=3.0, summary="Mock assessment.")
    data = llm.call_json(
        ASSESS_SYSTEM, f"RUBRIC:\n{rubric.model_dump_json()}\n\nTRANSCRIPT:\n{transcript}",
        max_tokens=2500,
    )
    return Assessment(**data)
