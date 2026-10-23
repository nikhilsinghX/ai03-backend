"""Deterministic, code-based verification of P5 evidence quotes."""
from __future__ import annotations

import re
from typing import Any


def normalize_quote(value: str) -> str:
    """Lowercase and remove punctuation/spacing differences for substring checks."""
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _candidate_turn(turn: dict) -> bool:
    speaker = str(turn.get("speaker", "")).strip().casefold()
    kind = str(turn.get("kind", "")).strip().casefold()
    return speaker in {"candidate", "user", "human", "candidate_answer"} or kind in {"answer", "candidate_answer"} and speaker not in {"ai", "assistant", "interviewer"}


def verify_assessment(assessment: dict, rubric: dict, transcript: list[dict]) -> dict:
    """Drop unverified quotes; withhold a score if no evidence quote is verified.

    A quote must match text from the same candidate turn_id. Verification is deterministic.
    """
    if not isinstance(assessment, dict):
        raise ValueError("assessment must be a dictionary")
    if not isinstance(rubric, dict) or not isinstance(rubric.get("criteria"), list):
        raise ValueError("rubric must contain a criteria list")
    if not isinstance(transcript, list):
        raise ValueError("transcript must be a list")

    candidate_text_by_id = {}
    for turn in transcript:
        if not isinstance(turn, dict) or not _candidate_turn(turn):
            continue
        tid = str(turn.get("turn_id", ""))
        text = str(turn.get("text", "") or "")
        if tid:
            candidate_text_by_id[tid] = text

    supplied_criteria = assessment.get("criteria", [])
    if not isinstance(supplied_criteria, list):
        supplied_criteria = []
    result_by_id = {}
    for row in supplied_criteria:
        if isinstance(row, dict) and row.get("criterion_id") is not None:
            result_by_id[str(row["criterion_id"])] = row

    verified_criteria = []
    for criterion in rubric["criteria"]:
        cid = str(criterion["id"])
        row = result_by_id.get(cid, {})
        raw_evidence = row.get("evidence", []) if isinstance(row, dict) else []
        if not isinstance(raw_evidence, list):
            raw_evidence = []
        verified_quotes = []
        seen = set()
        for evidence in raw_evidence:
            if not isinstance(evidence, dict):
                continue
            tid = str(evidence.get("turn_id", ""))
            quote = str(evidence.get("quote", "") or "").strip()
            if not tid or not quote or tid not in candidate_text_by_id:
                continue
            normalized_quote = normalize_quote(quote)
            normalized_turn = normalize_quote(candidate_text_by_id[tid])
            if normalized_quote and normalized_quote in normalized_turn:
                key = (tid, normalized_quote)
                if key not in seen:
                    verified_quotes.append({"turn_id": evidence.get("turn_id"), "quote": quote})
                    seen.add(key)
                    if cid == "project_ownership":
                        print("\n--- PROJECT OWNERSHIP VERIFIER DEBUG ---")
                        print("Criterion found:", bool(row))
                        print("Raw score:", row.get("score") if isinstance(row, dict) else None)
                        print("Raw evidence:", repr(raw_evidence))
                        print("Candidate turn IDs:", list(candidate_text_by_id.keys()))
                        print("Verified evidence count:", len(verified_quotes))

        score = row.get("score") if isinstance(row, dict) else None
        try:
            score = int(score) if score is not None else None
        except (TypeError, ValueError):
            score = None
        if score is not None and not 1 <= score <= 5:
            score = None
        if not verified_quotes:
            score = None
            confidence = "low"
            rationale = "Insufficient verified candidate evidence; score withheld."
        else:
            confidence = str(row.get("confidence", "medium")).casefold() if isinstance(row, dict) else "medium"
            if confidence == "med":
                confidence = "medium"
            if confidence not in {"low", "medium", "high"}:
                confidence = "low"
            rationale = str(row.get("rationale", "Evidence verified against candidate transcript.") or "Evidence verified against candidate transcript.")
            if score is None:
                rationale = "Evidence was verified, but the score was invalid or missing; human review is needed. " + rationale
        verified_criteria.append({
            "criterion_id": cid,
            "score": score,
            "confidence": confidence,
            "evidence": verified_quotes,
            "rationale": rationale,
        })

    # Discard any non-rubric criterion and preserve only safe expected fields.
    def safe_string_list(field: str) -> list[str]:
        value = assessment.get(field, [])
        if not isinstance(value, list):
            return []
        return [str(x) for x in value if isinstance(x, (str, int, float))]

    review = assessment.get("needs_human_review", [])
    if not isinstance(review, list):
        review = []
    cleaned_review = []
    for entry in review:
        if isinstance(entry, dict):
            cleaned_review.append({"topic": str(entry.get("topic", "Unverified claim")), "why": str(entry.get("why", "Needs human review."))})

    return {
        "criteria": verified_criteria,
        "strengths": safe_string_list("strengths"),
        "gaps": safe_string_list("gaps"),
        "needs_human_review": cleaned_review,
        "suggested_human_questions": safe_string_list("suggested_human_questions"),
        "disclaimer": "Assessment to support a human reviewer. Not a hiring decision.",
    }
