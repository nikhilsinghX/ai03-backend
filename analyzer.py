"""P4 answer analysis and follow-up decision logic."""
from __future__ import annotations

import json
from typing import Any

from llm import generate_json
from prompts import P4_ANALYZER_SYSTEM

_ALLOWED_TYPES = {"example", "ownership", "outcome", "trade_off", "clarification", "none"}
_SKIP_PHRASES = (
    "i don't know", "i do not know", "not sure", "i want to skip", "can i skip", "skip this"
)


def _next(reason: str) -> dict:
    return {
        "claims": [],
        "evidence_found": [],
        "missing": [],
        "decision": "NEXT",
        "followup_type": "none",
        "utterance": "",
        "reason_for_decision": reason,
    }


def analyze_answer(
    question: dict,
    answer: str,
    criterion: dict,
    follow_up_count: int = 0,
    resume_claims: list | None = None,
) -> dict:
    """Analyze one answer; code enforces the maximum of two follow-ups."""
    if not isinstance(question, dict) or not isinstance(criterion, dict):
        raise ValueError("question and criterion must be dictionaries")
    answer = answer if isinstance(answer, str) else ""
    try:
        follow_up_count = int(follow_up_count)
    except (TypeError, ValueError):
        follow_up_count = 0

    if follow_up_count >= 2:
        return _next("The maximum of two follow-ups for this question has been reached.")
    if not answer.strip():
        return _next("The answer was empty; moving on without pressuring the candidate.")
    lowered = answer.casefold()
    if any(phrase in lowered for phrase in _SKIP_PHRASES):
        return _next("The candidate indicated uncertainty or asked to skip; moving on respectfully.")

    context = {
        "question": question,
        "candidate_answer": answer,
        "rubric_criterion": criterion,
        "follow_up_count_already_asked": follow_up_count,
        "resume_claims_for_neutral_clarification": resume_claims or [],
    }
    result = generate_json(P4_ANALYZER_SYSTEM, json.dumps(context, ensure_ascii=False))
    if not isinstance(result, dict):
        raise ValueError("P4 output must be a JSON object")

    decision = str(result.get("decision", "NEXT")).strip().upper()
    followup_type = str(result.get("followup_type", "none")).strip().lower()
    utterance = str(result.get("utterance", "") or "").strip()
    reason = str(result.get("reason_for_decision", "No reason supplied.") or "No reason supplied.").strip()
    claims = result.get("claims", []) if isinstance(result.get("claims", []), list) else []
    evidence = result.get("evidence_found", []) if isinstance(result.get("evidence_found", []), list) else []
    missing = result.get("missing", []) if isinstance(result.get("missing", []), list) else []

    if decision != "FOLLOW_UP" or followup_type not in _ALLOWED_TYPES or followup_type == "none" or not utterance:
        return {
            "claims": claims,
            "evidence_found": evidence,
            "missing": missing,
            "decision": "NEXT",
            "followup_type": "none",
            "utterance": "",
            "reason_for_decision": reason,
        }
    if len(utterance.split()) > 25:
        # Safer to ask one brief generic clarification than speak an overlong prompt.
        utterance = "Could you give one specific example and explain what you personally did?"
    return {
        "claims": claims,
        "evidence_found": evidence,
        "missing": missing,
        "decision": "FOLLOW_UP",
        "followup_type": followup_type,
        "utterance": utterance,
        "reason_for_decision": reason,
    }
