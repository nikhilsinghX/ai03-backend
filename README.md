# InterviewLens — integrated single-port application

InterviewLens combines the existing Member 1 FastAPI interview flow, Member 2 P1–P5 prompt/validation/evidence-verification files, and Member 3 browser UI in one project. The browser UI and API are served by the same FastAPI process on **port 8000**.

## Windows quick start
1. Extract this ZIP to a normal folder, e.g. `D:\InterviewLens`.
2. Open that folder in File Explorer.
3. Double-click `run-backend.bat` (or run `./run-backend.bat` from PowerShell).
4. Open `http://127.0.0.1:8000`.
5. To use a real LLM, edit `ai03-backend\.env` and add your provider key. Without a key, the app intentionally runs in mock mode for UI/flow testing.

## What is included
- Member 1: FastAPI app, LLM wrapper, state machine, rubric/question flow, assessment route, API routes and same-process static frontend serving.
- Member 2: P1–P5 prompt set, JSON validation helpers, question/answer analysis, assessor, evidence quote verifier, demo script and contract tests under `ai03-backend/app/member2/`.
- Member 3: responsive frontend, transcript, voice input/speech synthesis where supported, typed-answer fallback, rubric review, consent gate, report and human review decision.
- Sample fictional JD/resume, safety and limitations notes.

## Important status notes
- The main interactive flow uses the integrated Member 1 pipeline; Member 2's full P1–P5 modules are included as package modules and can be tested/imported independently. They are not all wired into the live session-creation path yet because their structured outputs differ from the current UI's Pydantic data contract.
- The current session store is in-memory; sessions are lost when the server restarts. SQLite persistence is not implemented.
- Real-provider behavior depends on a valid provider key/model and has not been validated in this package build. Mock mode is for development and must not be used to make hiring decisions.
- Scores/evidence are advisory only. A human reviewer records the final decision (Hire / Do not hire / Hold). The application does not automatically hire or reject candidates.
- Voice features depend on browser support and microphone permission; typed input remains available.

## Tests
From `ai03-backend` with the virtual environment active:
`python -m pytest app/member2/test_contracts.py`

Run existing flow tests with:
`python -m pytest tests`

Member 2's three-run assessment consistency smoke test (requires a configured real provider):
`cd ai03-backend` then `python -m app.member2.consistency_harness`.
