"""Runs the strong and the vague fictional candidate through a RUNNING server (over HTTP).

Usage (server running):  python scripts/demo_run.py [http://127.0.0.1:8000]
In mock mode every score is 3, so no separation is expected. Use a real key for a real check.
"""
import json
import sys
import urllib.request
from pathlib import Path

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
DATA = Path(__file__).resolve().parents[1] / "sample_data"
JD = (DATA / "jd_ml_intern.md").read_text(encoding="utf-8")
ANSWERS = json.loads((DATA / "scripted_answers.json").read_text(encoding="utf-8"))


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def run(name, resume_file, answers):
    resume = (DATA / "resumes" / resume_file).read_text(encoding="utf-8")
    sid = call("POST", "/api/session", {"jd_text": JD, "resume_text": resume})["session_id"]
    call("POST", f"/api/session/{sid}/consent", {})
    call("POST", f"/api/session/{sid}/start", {})
    followups = 0
    for i in range(80):
        r = call("POST", f"/api/session/{sid}/answer", {"text": answers[i % len(answers)]})
        followups += r["kind"] == "follow_up"
        if r["done"]:
            break
    else:
        raise SystemExit(f"{name}: interview never finished")
    a = call("GET", f"/api/session/{sid}/assessment")
    scores = [s["score"] for s in a["scores"]]
    verified = sum(len(s["evidence_quotes"]) for s in a["scores"])
    print(f"{name:7} session={sid} summary={a['overall']} scores={scores} follow-ups={followups} verified quotes={verified} flags={len(a['flags'])}")
    return a["overall"]


if __name__ == "__main__":
    mock = call("GET", "/health")["mock_llm"]
    strong = run("strong", "strong.md", ANSWERS["strong"])
    weak = run("vague", "mismatch.md", ANSWERS["vague"])
    if mock:
        print("mock mode: no score separation expected")
    elif strong is not None and weak is not None:
        print(f"score gap (strong - vague) = {round(strong - weak, 2)}")
