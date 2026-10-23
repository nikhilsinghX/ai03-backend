
from assessor import assess_interview

# Keep the rubric and transcript identical across all 3 runs.
rubric = {
    "criteria": [
        {
            "id": "technical_fundamentals",
            "name": "Technical fundamentals",
            "weight": 0.25,
            "what_good_looks_like": "Explains technical choices accurately.",
            "anchors": {
                "1": "Cannot explain the technical approach.",
                "3": "Explains the basic approach correctly.",
                "5": "Explains choices, trade-offs, and edge cases."
            }
        },
        {
            "id": "project_ownership",
            "name": "Project ownership",
            "weight": 0.25,
            "what_good_looks_like": "Clearly explains personal contribution.",
            "anchors": {
                "1": "Cannot identify personal contribution.",
                "3": "Describes their role with some detail.",
                "5": "Clearly explains personal work and decisions."
            }
        },
        {
            "id": "problem_solving",
            "name": "Problem solving",
            "weight": 0.25,
            "what_good_looks_like": "Describes a problem and solution.",
            "anchors": {
                "1": "No clear problem-solving approach.",
                "3": "Describes a reasonable solution.",
                "5": "Explains debugging, reasoning, and trade-offs."
            }
        },
        {
            "id": "evaluation",
            "name": "Model evaluation",
            "weight": 0.25,
            "what_good_looks_like": "Explains the evaluation method and outcome.",
            "anchors": {
                "1": "No meaningful evaluation described.",
                "3": "Describes a metric and result.",
                "5": "Explains the metric, test method, and limitations."
            }
        }
    ]
}

transcript = [
    {
        "turn_id": 1,
        "speaker": "ai",
        "kind": "question",
        "question_id": "Q1",
        "text": "Describe an ML project, your contribution, and how you evaluated it."
    },
    {
        "turn_id": 2,
        "speaker": "candidate",
        "kind": "answer",
        "question_id": "Q1",
        "text": (
            "I built a Python text classifier using scikit-learn. "
            "I cleaned the dataset, split it into training and test sets, "
            "and compared logistic regression with a Naive Bayes baseline. "
            "After fixing a preprocessing bug, the F1 score on the held-out "
            "test set improved from 0.72 to 0.81. I wrote the evaluation "
            "script and documented the limitations."
        )
    }
]

results = []

for run_number in range(1, 4):
    print(f"\nRunning assessment {run_number}/3...")

    result = assess_interview(rubric, transcript)
    results.append(result)

    for item in result["criteria"]:
        print(
            f"  {item['criterion_id']}: "
            f"score={item['score']}, "
            f"verified_quotes={len(item['evidence'])}"
        )

print("\n=== CONSISTENCY REPORT ===")

for criterion in rubric["criteria"]:
    criterion_id = criterion["id"]

    scores = [
        item["score"]
        for result in results
        for item in result["criteria"]
        if item["criterion_id"] == criterion_id
    ]

    valid_scores = [score for score in scores if score is not None]

    print(f"\n{criterion_id}")
    print(f"Scores across runs: {scores}")

    if len(valid_scores) >= 2:
        spread = max(valid_scores) - min(valid_scores)
        print(f"Score spread: {spread}")

        if spread <= 1:
            print("Consistency target met (spread <= 1).")
        else:
            print("Consistency target NOT met (spread > 1).")
    else:
        print(
            "Insufficient verified scores to compare. "
            "Review the evidence and rerun if appropriate."
        )

print("\nAssessment runs completed.")
