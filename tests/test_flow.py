import os
import tempfile

for _k in ("ANTHROPIC_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"):
    os.environ[_k] = ""  # force mock mode
os.environ["DB_PATH"] = os.path.join(tempfile.gettempdir(), "interviewlens_test.db")

from fastapi.testclient import TestClient
from app.main import app
from app.verify import quote_in_transcript
from app.schemas import Turn

c = TestClient(app)
JD = "# AI/ML Intern\nNeeds Python, ML basics, teamwork."
LONG = " ".join(["word"] * 40)


def run_to_end(sid, text=LONG):
    for _ in range(60):
        r = c.post(f"/sessions/{sid}/answer", json={"text": text}).json()
        if r["done"]:
            return r
    raise AssertionError("interview never finished")


def test_full_flow():
    s = c.post("/sessions", json={"jd_text": JD, "resume_text": "I built a RAG bot."}).json()
    sid = s["id"]
    assert s["state"] == "RUBRIC_READY" and len(s["rubric"]["criteria"]) >= 4
    assert c.post(f"/sessions/{sid}/start").status_code == 403
    assert c.post(f"/sessions/{sid}/consent").status_code == 200
    r = c.post(f"/sessions/{sid}/start").json()
    assert r["turn"]["kind"] == "main"
    # short answer -> follow-up
    r = c.post(f"/sessions/{sid}/answer", json={"text": "short"}).json()
    assert r["turn"]["kind"] == "followup"
    # long answers -> advance until done
    for _ in range(20):
        r = c.post(f"/sessions/{sid}/answer", json={"text": LONG}).json()
        if r["done"]:
            break
    assert r["done"]
    a = c.get(f"/sessions/{sid}/assessment").json()
    assert len(a["scores"]) >= 4


def test_cannot_start_twice():
    sid = c.post("/sessions", json={"jd_text": JD, "resume_text": "x"}).json()["id"]
    c.post(f"/sessions/{sid}/consent")
    c.post(f"/sessions/{sid}/start")
    assert c.post(f"/sessions/{sid}/start").status_code == 409


def test_verify_quote():
    turns = [Turn(idx=0, speaker="candidate", text="I used FastAPI and Postgres for the backend.")]
    assert quote_in_transcript("used FastAPI and Postgres", turns)
    assert not quote_in_transcript("I led a team of fifty engineers", turns)


def test_api_aliases_and_consent_gate():
    created = c.post("/api/session", json={"jd_text": JD, "resume_text": "I built a RAG bot."})
    assert created.status_code == 200
    sid = created.json()["session_id"]
    assert c.post(f"/api/session/{sid}/rubric").status_code == 200
    assert len(c.post(f"/api/session/{sid}/plan").json()["questions"]) >= 4
    assert c.post(f"/api/session/{sid}/start").status_code == 403
    assert c.post(f"/api/session/{sid}/consent").status_code == 200
    assert c.post(f"/api/session/{sid}/start").status_code == 200
    transcript = c.get(f"/api/session/{sid}/transcript").json()["turns"]
    assert transcript and "turn_id" in transcript[0]


def test_frontend_is_served_on_same_port():
    response = c.get("/")
    assert response.status_code == 200
    assert "InterviewLens" in response.text
    js = c.get("/js/api.js")
    assert js.status_code == 200
    assert "const API_BASE = window.API_BASE || '';" in js.text


def test_api_interview_transcript_and_assessment():
    created = c.post("/api/session", json={"jd_text": JD, "resume_text": "Built a fictional search prototype."})
    sid = created.json()["session_id"]
    c.post(f"/api/session/{sid}/consent")
    started = c.post(f"/api/session/{sid}/start")
    assert started.status_code == 200
    assert started.json()["turn"]["speaker"] == "agent"
    result = None
    for _ in range(20):
        result = c.post(f"/api/session/{sid}/answer", json={"text": LONG})
        assert result.status_code == 200
        if result.json()["done"]:
            break
    assert result and result.json()["done"] is True
    transcript = c.get(f"/api/session/{sid}/transcript").json()["turns"]
    assert any(t["speaker"] == "candidate" for t in transcript)
    assert all("turn_id" in t for t in transcript)
    assessment = c.get(f"/api/session/{sid}/assessment")
    assert assessment.status_code == 200
    assert "scores" in assessment.json()
    assert c.get("/").status_code == 200


def _started(resume="x"):
    sid = c.post("/sessions", json={"jd_text": JD, "resume_text": resume}).json()["id"]
    c.post(f"/sessions/{sid}/consent")
    c.post(f"/sessions/{sid}/start")
    return sid


def test_session_persists_in_sqlite():
    sid = _started()
    s = c.get(f"/sessions/{sid}").json()  # re-read from the database, not from memory
    assert s["state"] == "IN_INTERVIEW" and s["consent_given"] and len(s["turns"]) == 1


def test_max_two_followups_per_question():
    sid = _started()
    ans = "I built a small model and it worked well for us"  # no outcome, no example
    kinds = [c.post(f"/sessions/{sid}/answer", json={"text": ans}).json()["turn"]["kind"] for _ in range(3)]
    assert kinds == ["followup", "followup", "main"]


def test_api_answer_has_reason_and_coverage():
    sid = _started()
    r = c.post(f"/api/session/{sid}/answer", json={"text": "short"}).json()
    assert r["kind"] == "follow_up" and r["reason"]
    assert r["coverage"]["total"] >= 4 and 0 <= r["coverage"]["percent"] <= 100


def test_empty_answer_rejected():
    sid = _started()
    assert c.post(f"/sessions/{sid}/answer", json={"text": "   "}).status_code == 422


def test_unverifiable_scores_are_capped_and_flagged():
    sid = _started()
    for _ in range(40):
        if c.post(f"/sessions/{sid}/answer", json={"text": "ok"}).json()["done"]:
            break
    a = c.get(f"/sessions/{sid}/assessment").json()  # "ok" is too short to verify as a quote
    assert all(x["score"] is None for x in a["scores"]) and a["flags"]
    assert a["overall"] is None and a["needs_human_review"] and a["suggested_human_questions"]


def test_finish_early_still_gives_assessment():
    sid = _started()
    c.post(f"/sessions/{sid}/answer", json={"text": LONG})
    assert c.post(f"/api/session/{sid}/finish").status_code == 200


def test_first_turn_says_it_is_an_ai_and_plan_has_6_to_8_tagged_questions():
    sid = new_session_for_plan()
    s = c.get(f"/sessions/{sid}").json()
    assert 6 <= len(s["questions"]) <= 8
    assert {q["criterion_id"] for q in s["questions"]} == {x["id"] for x in s["rubric"]["criteria"]}
    assert all(q["source"]["type"] in ("jd", "resume") and q["source"]["ref"] for q in s["questions"])
    c.post(f"/sessions/{sid}/consent")
    first = c.post(f"/sessions/{sid}/start").json()["turn"]
    assert "AI interviewer" in first["text"] and first["reason"]


def new_session_for_plan():
    return c.post("/sessions", json={"jd_text": JD, "resume_text": "Built a RAG chatbot with FastAPI. Led a 4-person hackathon team."}).json()["id"]


def test_dont_know_gets_no_followup_and_is_flagged_for_the_human():
    sid = _started()
    r = c.post(f"/sessions/{sid}/answer", json={"text": "I don't know."}).json()
    assert r["turn"]["kind"] == "main"  # no follow-up pressure
    run_to_end(sid, text="I don't know.")
    a = c.get(f"/sessions/{sid}/assessment").json()
    assert any("did not know" in x["why"] for x in a["needs_human_review"])


def test_assessment_has_disclaimer_and_no_hire_decision_field():
    sid = _started()
    run_to_end(sid)
    a = c.get(f"/sessions/{sid}/assessment").json()
    assert "human reviewer" in a["disclaimer"] and not any(k in a for k in ("hire", "decision", "recommendation"))
    assert a["overall"] is not None and a["strengths"] is not None


def test_edit_rubric_replans_questions():
    sid = c.post("/sessions", json={"jd_text": JD, "resume_text": "Built a RAG chatbot with FastAPI."}).json()["id"]
    s = c.get(f"/sessions/{sid}").json()
    s["rubric"]["criteria"] = s["rubric"]["criteria"][:4]
    out = c.put(f"/sessions/{sid}/rubric", json=s["rubric"]).json()
    assert len(out["rubric"]["criteria"]) == 4 and all(q["criterion_id"] in {x["id"] for x in out["rubric"]["criteria"]} for q in out["questions"])
