
"""P5 assessment generation with evidence verification."""

from __future__ import annotations

import json

from llm import generate_json
from prompts import P5_ASSESSOR_SYSTEM
from verify import verify_assessment


def assess_interview(rubric: dict, transcript: list[dict]) -> dict:
    """Generate an assessment and verify its evidence quotes."""

    if not isinstance(rubric, dict) or not isinstance(
        rubric.get("criteria"), list
    ):
        raise ValueError("rubric must contain a criteria list")

    if not isinstance(transcript, list):
        raise ValueError("transcript must be a list of turn dictionaries")

    context = {
        "rubric": rubric,
        "transcript": transcript,
    }

    raw_assessment = generate_json(
        P5_ASSESSOR_SYSTEM,
        json.dumps(context, ensure_ascii=False),
    )

    # Temporary debugging: inspect project ownership before verification.
    for row in raw_assessment.get("criteria", []):
        if row.get("criterion_id") == "project_ownership":
            print("\n--- RAW PROJECT OWNERSHIP ---")
            print(json.dumps(row, indent=2, ensure_ascii=False))

    # Keep this return inside the function.
    return verify_assessment(raw_assessment, rubric, transcript)
