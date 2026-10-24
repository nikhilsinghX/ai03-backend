import os
os.environ["ANTHROPIC_API_KEY"] = ""  # force mock mode

from fastapi.testclient import TestClient
from app.main import app
from app.verify import quote_in_transcript
from app.schemas import Turn

c = TestClient(app)
JD = "# AI/ML Intern\nNeeds Python, ML basics, teamwork."
LONG = " ".join(["word"] * 40)


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
