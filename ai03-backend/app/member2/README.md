# InterviewLens — Person 2 AI/Prompt Engineering Code (P1-P5)

These files use the working LLM wrapper you already have in `llm.py`. They expect its function signature to be:

```python
generate_json(system_prompt: str, user_prompt: str) -> dict
```

## Files

- `prompts.py`: Versioned system prompts for P1-P5.
- `schemas.py`: JSON contract validation and rubric weight normalization.
- `pipeline.py`: P1 `extract_requirements`, P2 `generate_rubric`, P3 `plan_questions`.
- `analyzer.py`: P4 `analyze_answer`, including the hard cap of two follow-ups.
- `assessor.py`: P5 `assess_interview`.
- `verify.py`: deterministic quote checking against candidate transcript turns. Scores without verified evidence become `null`.
- `test_ai_components.py`: unit tests; these do not require an API call.
- `run_person2_demo.py`: end-to-end fictional test; this does call the model several times.

## Add the files to your existing project

1. Make a backup of your current `pipeline.py` before replacing it. In PowerShell, from the project folder, run:
   `Copy-Item pipeline.py pipeline.py.backup -ErrorAction SilentlyContinue`
2. Extract/copy these files into `C:\Users\Shubhi\OneDrive\Desktop\Jaipur\interviewlens-ai`, next to `llm.py` and `.env`.
3. Keep your current `.env` and `llm.py`; do not replace either one.
4. Confirm `.env` has your own valid `GROQ_API_KEY` and `GROQ_MODEL` settings. Never share the key or commit `.env`.
5. Run the unit tests first:
   `python -m pytest test_ai_components.py -q`
6. Then run the LLM demo:
   `python run_person2_demo.py`

## Public function contracts to share with Person 1

- `extract_requirements(jd_text: str, resume_text: str = "") -> dict`
- `generate_rubric(requirements: dict) -> {"criteria": [...]}`
- `plan_questions(requirements: dict, rubric: dict) -> {"questions": [...]}`
- `analyze_answer(question: dict, answer: str, criterion: dict, follow_up_count: int = 0, resume_claims: list | None = None) -> dict`
- `assess_interview(rubric: dict, transcript: list[dict]) -> dict`
- `verify_assessment(assessment: dict, rubric: dict, transcript: list[dict]) -> dict`

## Important integration notes

- P1's detailed `requirements` IDs look like `JD1`, `JD2`; resume claim IDs look like `RES1`, `RES2`.
- P3 expects rubric criterion IDs to be stable and sources to reference those P1 IDs.
- Transcript turns should include `turn_id`, `speaker` (`ai` or `candidate`), `text`, `question_id`, and `kind` (`question`, `follow_up`, or `answer`).
- The verifier only accepts evidence quoted from candidate turns, never AI turns. If no quote verifies for a criterion, its score is withheld as `null`.
- Assessment is for a human reviewer only; it does not return a hire/reject decision.
- If your current `test_pipeline.py` assumes an older P1 JSON key structure, check it after copying. This version preserves common convenience keys such as `required_skills`, `nice_to_have_skills`, `qualifications`, `responsibilities`, and `resume_claims` alongside the detailed `requirements` list.
