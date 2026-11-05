import os

for _k in ("ANTHROPIC_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"):
    os.environ[_k] = ""  # force mock mode

from app.scenario_runner import run_all  # noqa: E402

RESULTS = run_all()


def _assert(name):
    r = RESULTS[name]
    assert not r["failed"], f"{name}: {r['failed']}"


def test_strong_candidate_gets_no_followups_and_full_evidence():
    _assert("strong")


def test_average_candidate_gets_followups():
    _assert("average")


def test_vague_candidate_followups_capped_at_two():
    _assert("vague")


def test_evasive_candidate_is_rephrased_once_then_moved_on():
    _assert("evasive")


def test_idk_candidate_is_not_pressured_and_is_flagged():
    _assert("idk")


def test_followups_reference_the_candidates_answer():
    detail = sum(r["detail_followups"] for r in RESULTS.values())
    specific = sum(r["specific_followups"] for r in RESULTS.values())
    assert detail and specific == detail
