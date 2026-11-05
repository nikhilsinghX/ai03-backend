"""P5 assessment generation followed by mandatory code-based evidence verification."""
from __future__ import annotations

import json

from .llm_adapter import generate_json
from .prompts import P5_ASSESSOR_SYSTEM
from .verify import verify_assessment


def assess_interview(rubric: dict, transcript: list[dict]) -> dict:
    """Generate per-criterion assessment and return only quote-verified evidence."""
    if not isinstance(rubric, dict) or not isinstance(rubric.get("criteria"), list):
        raise ValueError("rubric must contain a criteria list")
    if not isinstance(transcript, list):
        raise ValueError("transcript must be a list of turn dictionaries")
    context = {"rubric": rubric, "transcript": transcript}
    raw_assessment = generate_json(P5_ASSESSOR_SYSTEM, json.dumps(context, ensure_ascii=False))
    return verify_assessment(raw_assessment, rubric, transcript)
