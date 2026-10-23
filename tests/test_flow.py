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
    c.post(f"/sessions/{sid}/start")
    assert c.post(f"/sessions/{sid}/start").status_code == 409


def test_verify_quote():
    turns = [Turn(idx=0, speaker="candidate", text="I used FastAPI and Postgres for the backend.")]
    assert quote_in_transcript("used FastAPI and Postgres", turns)
    assert not quote_in_transcript("I led a team of fifty engineers", turns)
