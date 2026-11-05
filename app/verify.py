"""Evidence verifier (code, not LLM): a score may only cite quotes that really exist in the
candidate's answers. Unverifiable quotes are dropped; a criterion with no verified quote gets
score None ("insufficient evidence") instead of a number."""
import re
from typing import List, Optional

from .schemas import Assessment, CriterionScore, Evidence, Turn


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", s.lower())).strip()


def quote_in_transcript(quote: str, turns: List[Turn]) -> bool:
    q = _norm(quote)
    if len(q) < 8:
        return False
    return any(q in _norm(t.text) for t in turns if t.speaker == "candidate")


def find_turn_id(quote: str, turns: List[Turn]) -> Optional[int]:
    q = _norm(quote)
    for t in turns:
        if t.speaker == "candidate" and q in _norm(t.text):
            return t.idx
    return None


def verify_assessment(a: Assessment, turns: List[Turn]) -> Assessment:
    fixed: List[CriterionScore] = []
    flags = list(a.flags)
    for s in a.scores:
        good = [q for q in dict.fromkeys(s.evidence_quotes) if quote_in_transcript(q, turns)]
        evidence = [Evidence(turn_id=find_turn_id(q, turns), quote=q) for q in good]
        score, confidence, rationale = s.score, s.confidence, s.rationale
        if not good:
            if score is not None:
                flags.append(f"{s.criterion_id}: score withheld, no verifiable evidence in the transcript")
            score, confidence = None, "low"
            if "nsufficient" not in rationale:
                rationale = (rationale + " " if rationale else "") + "Insufficient verified evidence in transcript."
        else:
            if len(good) < len(set(s.evidence_quotes)):
                flags.append(f"{s.criterion_id}: some quotes removed (not found in the transcript)")
            confidence = "high" if len(good) >= 2 else "med"
        fixed.append(s.model_copy(update={
            "score": score, "confidence": confidence, "rationale": rationale,
            "evidence_quotes": good, "evidence": evidence,
        }))
    return a.model_copy(update={"scores": fixed, "flags": flags})
