"""When the LLM is configured but fails or returns junk, the interview must still work."""
import os

for _k in ("ANTHROPIC_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"):
    os.environ[_k] = ""

from app import llm, pipeline, scenario_runner  # noqa: E402


def _real_but_broken(monkeypatch, behaviour):
    monkeypatch.setattr(llm, "is_mock", lambda: False)
    monkeypatch.setattr(llm, "call_json", behaviour)


def _boom(*a, **k):
    raise RuntimeError("simulated timeout")


def test_every_step_falls_back_when_the_llm_times_out(monkeypatch):
    _real_but_broken(monkeypatch, _boom)
    jd, answers, _ = scenario_runner.load()
    r = scenario_runner.run_interview(jd, "Built a classifier. Led a hackathon team.", answers["average"])
    assert r["completed"] and r["questions"] >= 6 and r["followups"] >= 1  # rubric, plan, follow-ups all fell back


def test_assessment_failure_gives_no_scores_instead_of_a_crash(monkeypatch):
    _real_but_broken(monkeypatch, _boom)
    rubric = pipeline.default_rubric("# Role")
    a = pipeline.assess(rubric, [])
    assert all(s.score is None for s in a.scores) and a.flags


def test_junk_rubric_from_the_llm_is_rejected(monkeypatch):
    _real_but_broken(monkeypatch, lambda *a, **k: {"role_title": "x", "criteria": [{"id": "a", "name": "n", "description": "d"}]})
    assert len(pipeline.generate_rubric("# Role").criteria) == 5  # default rubric used


def test_good_llm_plan_is_validated_and_padded(monkeypatch):
    rubric = pipeline.default_rubric("# Role")
    plan = {"questions": [{"id": "x", "text": "Explain overfitting.", "criterion_id": "fundamentals",
                           "source": {"type": "jd", "ref": "ML basics"}}]}
    _real_but_broken(monkeypatch, lambda *a, **k: plan)
    qs = pipeline.plan_questions(rubric, "Built a chatbot with FastAPI project.", "# Role\nML basics")
    assert 6 <= len(qs) <= 8 and {q.criterion_id for q in qs} == {c.id for c in rubric.criteria}


def test_provider_switch_picks_the_key_that_exists(monkeypatch):
    for k in ("LLM_PROVIDER", "ANTHROPIC_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert llm.is_mock()
    monkeypatch.setenv("GROQ_API_KEY", "x")
    assert llm.provider() == "groq" and not llm.is_mock()
