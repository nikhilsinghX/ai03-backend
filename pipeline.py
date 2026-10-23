"""P1-P3 pipeline functions for InterviewLens Person 2.

Uses the existing llm.py contract: generate_json(system_prompt, user_prompt) -> dict.
"""
from __future__ import annotations

import json
from typing import Any

from llm import generate_json
from prompts import P1_EXTRACTOR_SYSTEM, P2_RUBRIC_SYSTEM, P3_QUESTION_PLANNER_SYSTEM
from schemas import validate_requirements, validate_rubric, validate_question_plan


def extract_requirements(jd_text: str, resume_text: str = "") -> dict:
    """P1: extract explicit JD requirements and resume claims to explore."""
    if not isinstance(jd_text, str) or not jd_text.strip():
        raise ValueError("jd_text must contain the job description")
    if not isinstance(resume_text, str):
        raise ValueError("resume_text must be text")
    user_prompt = json.dumps({
        "job_description": jd_text.strip(),
        "resume": resume_text.strip(),
    }, ensure_ascii=False)
    raw = generate_json(P1_EXTRACTOR_SYSTEM, user_prompt)
    return validate_requirements(raw)


def generate_rubric(requirements: dict) -> dict:
    """P2: create 4-6 weighted, job-related rubric criteria with score anchors."""
    if not isinstance(requirements, dict) or not requirements.get("requirements"):
        raise ValueError("requirements must contain at least one extracted job requirement")
    user_prompt = json.dumps(requirements, ensure_ascii=False)
    raw = generate_json(P2_RUBRIC_SYSTEM, user_prompt)
    return validate_rubric(raw)


def plan_questions(requirements: dict, rubric: dict) -> dict:
    """P3: create 6-8 questions mapped to criteria and source IDs."""
    if not isinstance(requirements, dict) or not isinstance(rubric, dict):
        raise ValueError("requirements and rubric must be dictionaries")
    user_prompt = json.dumps({"requirements": requirements, "rubric": rubric}, ensure_ascii=False)
    raw = generate_json(P3_QUESTION_PLANNER_SYSTEM, user_prompt)
    return validate_question_plan(raw, requirements, rubric)
