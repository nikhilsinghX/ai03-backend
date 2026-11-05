"""Lightweight validation/normalization for InterviewLens P1-P5 JSON contracts.

This intentionally uses plain Python so it works with both Pydantic v1 and v2 projects.
"""
from __future__ import annotations

from typing import Any


def _as_dict(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _as_list(value: Any, label: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON array")
    return value


def _text(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text")
    value = value.strip()
    if not allow_empty and not value:
        raise ValueError(f"{label} cannot be empty")
    return value


def validate_requirements(data: Any) -> dict:
    """Validate P1 output and expose both detailed and easy-to-consume fields."""
    data = _as_dict(data, "P1 output")
    role_title = data.get("role_title", "Unknown")
    if not isinstance(role_title, str):
        role_title = "Unknown"

    requirements = _as_list(data.get("requirements", []), "requirements")
    normalized_requirements = []
    used_ids = set()
    allowed_categories = {
        "required_skill", "nice_to_have", "qualification", "responsibility", "experience"
    }
    for i, raw in enumerate(requirements, start=1):
        item = _as_dict(raw, f"requirements[{i - 1}]")
        req_id = str(item.get("id") or f"JD{i}").strip()
        if req_id in used_ids:
            req_id = f"JD{i}"
        used_ids.add(req_id)
        category = str(item.get("category", "required_skill")).strip().lower()
        if category not in allowed_categories:
            category = "required_skill"
        priority = str(item.get("priority", "required")).strip().lower()
        if priority not in {"required", "preferred"}:
            priority = "required"
        normalized_requirements.append({
            "id": req_id,
            "category": category,
            "text": _text(item.get("text", ""), f"requirements[{i - 1}].text"),
            "priority": priority,
            "source_quote": _text(item.get("source_quote", ""), f"requirements[{i - 1}].source_quote", allow_empty=True),
        })

    claims = _as_list(data.get("resume_claims", []), "resume_claims")
    normalized_claims = []
    used_claim_ids = set()
    jd_ids = {item["id"] for item in normalized_requirements}
    for i, raw in enumerate(claims, start=1):
        item = _as_dict(raw, f"resume_claims[{i - 1}]")
        claim_id = str(item.get("claim_id") or f"RES{i}").strip()
        if claim_id in used_claim_ids:
            claim_id = f"RES{i}"
        used_claim_ids.add(claim_id)
        related = item.get("related_requirement_ids", [])
        if not isinstance(related, list):
            related = []
        related = [str(x) for x in related if str(x) in jd_ids]
        normalized_claims.append({
            "claim_id": claim_id,
            "claim": _text(item.get("claim", ""), f"resume_claims[{i - 1}].claim"),
            "evidence_quote": _text(item.get("evidence_quote", ""), f"resume_claims[{i - 1}].evidence_quote", allow_empty=True),
            "related_requirement_ids": related,
        })

    notes = data.get("notes", [])
    if not isinstance(notes, list):
        notes = []
    notes = [str(x) for x in notes]

    # These convenience fields preserve compatibility with simple extractor consumers.
    req_by_category = {category: [] for category in allowed_categories}
    for item in normalized_requirements:
        req_by_category[item["category"]].append(item["text"])
    return {
        "role_title": role_title.strip() or "Unknown",
        "requirements": normalized_requirements,
        "required_skills": req_by_category["required_skill"],
        "nice_to_have_skills": req_by_category["nice_to_have"],
        "qualifications": req_by_category["qualification"],
        "responsibilities": req_by_category["responsibility"],
        "experience_requirements": req_by_category["experience"],
        "resume_claims": normalized_claims,
        "notes": notes,
    }


def validate_rubric(data: Any) -> dict:
    """Validate P2 output and normalize criterion weights to sum to 1.0."""
    data = _as_dict(data, "P2 output")
    criteria = _as_list(data.get("criteria"), "criteria")
    if not 4 <= len(criteria) <= 6:
        raise ValueError(f"Rubric must contain 4-6 criteria; received {len(criteria)}")

    normalized = []
    seen_ids = set()
    total_weight = 0.0
    for i, raw in enumerate(criteria, start=1):
        item = _as_dict(raw, f"criteria[{i - 1}]")
        criterion_id = _text(item.get("id", f"criterion_{i}"), f"criteria[{i - 1}].id")
        if criterion_id in seen_ids:
            raise ValueError(f"Duplicate rubric criterion id: {criterion_id}")
        seen_ids.add(criterion_id)
        try:
            weight = float(item.get("weight", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"criteria[{i - 1}].weight must be numeric") from exc
        if weight <= 0:
            raise ValueError(f"criteria[{i - 1}].weight must be positive")
        # Accept models that mistakenly send 25 for 25%, as well as 0.25.
        if weight > 1:
            weight /= 100.0
        anchors = _as_dict(item.get("anchors"), f"criteria[{i - 1}].anchors")
        cleaned_anchors = {}
        for score in ("1", "3", "5"):
            anchor = anchors.get(score, anchors.get(int(score)))
            if not isinstance(anchor, str) or not anchor.strip():
                raise ValueError(f"criteria[{i - 1}].anchors must contain non-empty keys 1, 3, and 5")
            cleaned_anchors[score] = anchor.strip()
        normalized.append({
            "id": criterion_id,
            "name": _text(item.get("name", criterion_id), f"criteria[{i - 1}].name"),
            "weight": weight,
            "what_good_looks_like": _text(item.get("what_good_looks_like", "Observable, job-related evidence"), f"criteria[{i - 1}].what_good_looks_like"),
            "anchors": cleaned_anchors,
        })
        total_weight += weight

    if total_weight <= 0:
        raise ValueError("Rubric weights must sum to a positive number")
    for item in normalized:
        item["weight"] = round(item["weight"] / total_weight, 6)
    # Correct floating point drift on the final criterion.
    normalized[-1]["weight"] = round(1.0 - sum(x["weight"] for x in normalized[:-1]), 6)
    return {"criteria": normalized}


def validate_question_plan(data: Any, requirements: dict, rubric: dict) -> dict:
    """Validate P3 output and ensure the plan covers every rubric criterion."""
    data = _as_dict(data, "P3 output")
    questions = _as_list(data.get("questions"), "questions")
    if not 6 <= len(questions) <= 8:
        raise ValueError(f"Question plan must contain 6-8 questions; received {len(questions)}")

    criterion_ids = {x["id"] for x in rubric["criteria"]}
    jd_ids = {x["id"] for x in requirements.get("requirements", [])}
    resume_ids = {x["claim_id"] for x in requirements.get("resume_claims", [])}
    normalized = []
    seen_question_ids = set()
    for i, raw in enumerate(questions, start=1):
        item = _as_dict(raw, f"questions[{i - 1}]")
        qid = str(item.get("id") or f"Q{i}").strip()
        if qid in seen_question_ids:
            raise ValueError(f"Duplicate question id: {qid}")
        seen_question_ids.add(qid)
        criterion_id = _text(item.get("criterion_id", ""), f"questions[{i - 1}].criterion_id")
        if criterion_id not in criterion_ids:
            raise ValueError(f"Question {qid} refers to unknown criterion_id {criterion_id!r}")
        source = _as_dict(item.get("source"), f"questions[{i - 1}].source")
        source_type = str(source.get("type", "")).strip().lower()
        source_ref = str(source.get("ref", "")).strip()
        if source_type == "jd" and source_ref not in jd_ids:
            raise ValueError(f"Question {qid} references unknown JD id {source_ref!r}")
        if source_type == "resume" and source_ref not in resume_ids:
            raise ValueError(f"Question {qid} references unknown resume claim id {source_ref!r}")
        if source_type not in {"jd", "resume"}:
            raise ValueError(f"Question {qid} source.type must be 'jd' or 'resume'")
        probes = item.get("probes", [])
        if not isinstance(probes, list):
            probes = []
        normalized.append({
            "id": qid,
            "text": _text(item.get("text", ""), f"questions[{i - 1}].text"),
            "criterion_id": criterion_id,
            "source": {"type": source_type, "ref": source_ref},
            "probes": [str(p).strip() for p in probes[:2] if str(p).strip()],
        })

    covered = {q["criterion_id"] for q in normalized}
    missing = criterion_ids - covered
    if missing:
        raise ValueError("Question plan does not cover rubric criteria: " + ", ".join(sorted(missing)))
    return {"questions": normalized}
