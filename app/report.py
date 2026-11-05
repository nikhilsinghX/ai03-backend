"""Turns a verified assessment into the reviewer report: weighted rubric summary, strengths,
gaps, human-review items and suggested questions for the human round. No hire/reject field."""
from typing import List

from .schemas import Assessment, HumanReview, Rubric, Turn
from .schemas import DISCLAIMER

IDK_PHRASES = ("i don't know", "i do not know", "i dont know", "no idea", "not sure",
               "don't remember", "do not remember", "dont remember")


def says_dont_know(text: str) -> bool:
    t = text.lower().replace("\u2019", "'")
    return any(p in t for p in IDK_PHRASES)


def finalize(a: Assessment, rubric: Rubric, turns: List[Turn]) -> Assessment:
    names = {c.id: c.name for c in rubric.criteria}
    weights = {c.id: max(0.0, float(c.weight or 0)) for c in rubric.criteria}
    strengths, gaps, review, suggestions = [], [], [], []
    for s in a.scores:
        name = names.get(s.criterion_id, s.criterion_id)
        ask = f"Can you walk me through a concrete example of {name.lower()} from your own work?"
        if s.score is None:
            gaps.append(f"{name}: insufficient verified evidence")
            review.append(HumanReview(topic=name, why="No verified quote supports a score; cover it in the human round."))
            suggestions.append(ask)
        elif s.score >= 4:
            strengths.append(f"{name}: {s.score}/5, backed by {len(s.evidence_quotes)} verified quote(s)")
        elif s.score <= 2:
            gaps.append(f"{name}: {s.score}/5, review the evidence and rationale")
            suggestions.append(ask)
    seen = set()
    for t in turns:
        if t.speaker == "candidate" and t.criterion_id and t.criterion_id not in seen and says_dont_know(t.text):
            seen.add(t.criterion_id)
            name = names.get(t.criterion_id, t.criterion_id)
            review.append(HumanReview(topic=name, why="Candidate said they did not know. Recorded as a gap; no pressure was applied."))
    scored = [s for s in a.scores if s.score is not None]
    overall = None
    if scored:
        total = sum(weights.get(s.criterion_id, 0.0) for s in scored)
        if total > 0:
            overall = round(sum(weights.get(s.criterion_id, 0.0) * s.score for s in scored) / total, 1)
        else:
            overall = round(sum(s.score for s in scored) / len(scored), 1)
    summary = a.summary.strip()
    if not summary or summary == "Mock assessment.":
        summary = (f"Rubric summary {overall}/5 across {len(scored)} of {len(a.scores)} criteria with verified evidence. "
                   if overall is not None else "No criterion has verified evidence yet. ")
        summary += "Assessment to support a human reviewer; not a hiring decision."
    return a.model_copy(update={
        "overall": overall, "summary": summary, "strengths": strengths, "gaps": gaps,
        "needs_human_review": review + list(a.needs_human_review),
        "suggested_human_questions": list(dict.fromkeys(suggestions + list(a.suggested_human_questions))),
        "disclaimer": a.disclaimer or DISCLAIMER,
    })
