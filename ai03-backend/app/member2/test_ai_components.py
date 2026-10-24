"""Fast unit tests for Person 2 code. These tests do not call the LLM API."""
import pytest

from .analyzer import analyze_answer
from .schemas import validate_rubric
from .verify import verify_assessment


def sample_rubric():
    return {"criteria": [
        {"id": "technical", "name": "Technical", "weight": 0.25, "what_good_looks_like": "Correct, job-related technical reasoning", "anchors": {"1": "Incorrect or absent", "3": "Mostly correct", "5": "Correct with trade-offs"}},
        {"id": "ownership", "name": "Ownership", "weight": 0.25, "what_good_looks_like": "Explains own work", "anchors": {"1": "No own contribution", "3": "Some own contribution", "5": "Specific ownership and decisions"}},
        {"id": "problem_solving", "name": "Problem solving", "weight": 0.25, "what_good_looks_like": "Structured problem solving", "anchors": {"1": "No approach", "3": "Reasonable approach", "5": "Tests assumptions and trade-offs"}},
        {"id": "outcomes", "name": "Outcomes", "weight": 0.25, "what_good_looks_like": "Explains measurable outcome", "anchors": {"1": "No outcome", "3": "Outcome described", "5": "Outcome measured and contextualized"}},
    ]}


def test_rubric_weights_are_normalized():
    rubric = sample_rubric()
    rubric["criteria"][0]["weight"] = 25
    rubric["criteria"][1]["weight"] = 25
    rubric["criteria"][2]["weight"] = 25
    rubric["criteria"][3]["weight"] = 25
    result = validate_rubric(rubric)
    assert sum(x["weight"] for x in result["criteria"]) == pytest.approx(1.0)


def test_unverified_quote_is_removed_and_score_withheld():
    rubric = sample_rubric()
    transcript = [{"turn_id": 1, "speaker": "candidate", "kind": "answer", "text": "I used Python and scikit-learn."}]
    assessment = {"criteria": [
        {"criterion_id": "technical", "score": 5, "confidence": "high", "evidence": [{"turn_id": 1, "quote": "I am an expert in everything."}], "rationale": "Unsupported"}
    ]}
    result = verify_assessment(assessment, rubric, transcript)
    tech = next(x for x in result["criteria"] if x["criterion_id"] == "technical")
    assert tech["score"] is None
    assert tech["evidence"] == []


def test_verified_quote_keeps_score():
    rubric = sample_rubric()
    transcript = [{"turn_id": 2, "speaker": "candidate", "kind": "answer", "text": "I used Python and scikit-learn to train the model."}]
    assessment = {"criteria": [
        {"criterion_id": "technical", "score": 4, "confidence": "medium", "evidence": [{"turn_id": 2, "quote": "I used Python and scikit-learn"}], "rationale": "Names relevant tools."}
    ]}
    result = verify_assessment(assessment, rubric, transcript)
    tech = next(x for x in result["criteria"] if x["criterion_id"] == "technical")
    assert tech["score"] == 4
    assert len(tech["evidence"]) == 1


def test_two_followups_always_forces_next_without_api_call():
    result = analyze_answer(
        question={"id": "Q1", "text": "Describe a project."},
        answer="I built a classifier.",
        criterion={"id": "technical", "anchors": {"1": "low", "3": "mid", "5": "high"}},
        follow_up_count=2,
    )
    assert result["decision"] == "NEXT"
    assert result["utterance"] == ""
