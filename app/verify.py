"""Evidence verifier: every score must cite a quote that really exists in the
candidate's answers. Unverifiable quotes are dropped; scores with no verified
quote are capped at 2 and flagged."""
import re
from typing import List, Tuple

from .schemas import Assessment, CriterionScore, Turn


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", s.lower())).strip()


def quote_in_transcript(quote: str, turns: List[Turn]) -> bool:
    q = _norm(quote)
    if len(q) < 8:
        return False
    return any(q in _norm(t.text) for t in turns if t.speaker == "candidate")


def verify_assessment(a: Assessment, turns: List[Turn]) -> Assessment:
    fixed: List[CriterionScore] = []
    flags = list(a.flags)
    for s in a.scores:
        good = [q for q in s.evidence_quotes if quote_in_transcript(q, turns)]
        score = s.score
        if not good:
            score = min(score, 2)
            flags.append(f"{s.criterion_id}: no verifiable evidence, score capped at 2")
        elif len(good) < len(s.evidence_quotes):
            flags.append(f"{s.criterion_id}: some quotes removed (not found in transcript)")
        fixed.append(s.model_copy(update={"evidence_quotes": good, "score": score}))
    return a.model_copy(update={"scores": fixed, "flags": flags})
