from .schemas import validate_rubric, validate_question_plan
from .verify import verify_assessment


def _rubric():
    return {"criteria": [
        {"id": f"c{i}", "name": f"Criterion {i}", "weight": 1,
         "anchors": {"1": "Low", "3": "Meets", "5": "Strong"}}
        for i in range(1, 5)
    ]}


def test_rubric_weights_normalize_and_anchors_required():
    result = validate_rubric(_rubric())
    assert len(result["criteria"]) == 4
    assert round(sum(x["weight"] for x in result["criteria"]), 6) == 1


def test_question_plan_requires_6_to_8_and_coverage():
    req = {"requirements": [{"id": "JD1", "text": "Python"}], "resume_claims": [{"claim_id": "RES1", "claim": "Built app"}]}
    rubric = _rubric()
    qs = [{"id": f"q{i}", "text": f"Explain example {i}", "criterion_id": f"c{((i-1)%4)+1}",
           "source": {"type": "resume" if i <= 2 else "jd", "ref": "RES1" if i <= 2 else "JD1"}, "probes": []}
          for i in range(1, 7)]
    out = validate_question_plan({"questions": qs}, req, rubric)
    assert len(out["questions"]) == 6
