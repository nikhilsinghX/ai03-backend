# Test checklist (tick before every rehearsal)

Automated (ai03-backend, venv active): `python -m pytest -q` and `python -m pytest app/member2 -q`; then `python scripts/run_scenarios.py` (all 5 gold checks PASS).

- [ ] App opens at http://127.0.0.1:8000 and shows Backend online
- [ ] Load sample works; rubric (5 criteria) and 6-8 questions with source tags appear
- [ ] Upload a .txt file into the JD box works
- [ ] Start is locked until consent is ticked; first spoken line says it is an AI interviewer
- [ ] "I made a project." triggers a follow-up and the reason panel updates; never more than 2 per question
- [ ] "I don't know" gets no follow-up and appears under needs human review
- [ ] Interview ends with a closing line; report opens
- [ ] Every quote click jumps to the right transcript turn
- [ ] A criterion without a verified quote shows n/a and "Insufficient verified evidence"
- [ ] Reviewer decision needs a reason; Export JSON and Print work
- [ ] Reset returns to Setup; a second run works
- [ ] Typed fallback works with the mic blocked
- [ ] Restart the server mid-session: GET /sessions/{id} still returns it
- [ ] Stop the internet / use a wrong API key: the interview still runs (fallbacks)
- [ ] 1080p projector check
