"""Run an end-to-end fictional demo of Person 2's P1-P5 components.

Run from the interviewlens-ai project folder after copying the files into it:
    python run_person2_demo.py
This calls the configured LLM several times and may use API quota.
"""
import json

from .analyzer import analyze_answer
from .assessor import assess_interview
from .pipeline import extract_requirements, generate_rubric, plan_questions

SAMPLE_JD = """
Role: AI/ML Intern
Required: Python, basic machine learning, data cleaning, train/test split, model evaluation.
Responsibilities: build small ML experiments, compare a baseline with an improved model, explain results,
write readable code, and document limitations. Preferred: scikit-learn and experience with classification.
""".strip()

SAMPLE_RESUME = """
Fictional student project: Built a Python text classifier using scikit-learn. Cleaned a text dataset,
compared logistic regression with a Naive Bayes baseline, and reported F1 score. F1 improved from 0.72 to 0.81
after correcting a preprocessing issue. Worked with two classmates and wrote an evaluation script.
""".strip()


def main():
    requirements = extract_requirements(SAMPLE_JD, SAMPLE_RESUME)
    print("\n=== P1 REQUIREMENTS ===")
    print(json.dumps(requirements, indent=2, ensure_ascii=False))

    rubric = generate_rubric(requirements)
    print("\n=== P2 RUBRIC ===")
    print(json.dumps(rubric, indent=2, ensure_ascii=False))

    plan = plan_questions(requirements, rubric)
    print("\n=== P3 QUESTION PLAN ===")
    print(json.dumps(plan, indent=2, ensure_ascii=False))

    first_question = plan["questions"][0]
    criterion = next(c for c in rubric["criteria"] if c["id"] == first_question["criterion_id"])
    sample_answer = (
        "I used Python and scikit-learn to build a text classifier. I compared logistic regression with a Naive Bayes baseline, "
        "then corrected a preprocessing issue. I measured F1 score on the held-out set; it increased from 0.72 to 0.81."
    )
    analysis = analyze_answer(
        question=first_question,
        answer=sample_answer,
        criterion=criterion,
        follow_up_count=0,
        resume_claims=requirements["resume_claims"],
    )
    print("\n=== P4 ANSWER ANALYSIS ===")
    print(json.dumps(analysis, indent=2, ensure_ascii=False))

    transcript = [
        {"turn_id": 1, "speaker": "ai", "kind": "question", "question_id": first_question["id"], "text": first_question["text"]},
        {"turn_id": 2, "speaker": "candidate", "kind": "answer", "question_id": first_question["id"], "text": sample_answer},
    ]
    assessment = assess_interview(rubric, transcript)
    print("\n=== P5 VERIFIED ASSESSMENT ===")
    print(json.dumps(assessment, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
