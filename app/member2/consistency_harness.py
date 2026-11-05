"""Run P5 three times on a fixed transcript and report score spread.

Usage from ai03-backend: python -m app.member2.consistency_harness
Requires a configured real LLM provider. It is intentionally not part of startup.
"""
import json
from statistics import mean
from .assessor import assess_interview

RUBRIC = {"criteria": [{"id": "technical", "name": "Technical fundamentals", "weight": 1.0,
    "what_good_looks_like": "Explains a relevant technical decision", "anchors": {"1": "No evidence", "3": "Adequate", "5": "Specific and well reasoned"}}]}
TRANSCRIPT = [
    {"turn_id": "t1", "speaker": "interviewer", "kind": "question", "text": "Describe a technical project."},
    {"turn_id": "t2", "speaker": "candidate", "kind": "answer", "text": "I built a Python API and added tests to catch invalid inputs."},
]

if __name__ == "__main__":
    results = [assess_interview(RUBRIC, TRANSCRIPT) for _ in range(3)]
    scores = []
    for result in results:
        row = next((x for x in result.get("criteria", []) if x.get("criterion_id") == "technical"), {})
        scores.append(row.get("score"))
    numeric = [x for x in scores if isinstance(x, (int, float))]
    report = {"runs": 3, "scores": scores, "score_spread": max(numeric) - min(numeric) if numeric else None,
              "mean_score": mean(numeric) if numeric else None,
              "note": "This is a small consistency smoke test, not a statistically meaningful validation."}
    print(json.dumps(report, indent=2))
