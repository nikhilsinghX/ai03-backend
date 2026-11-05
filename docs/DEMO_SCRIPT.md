# Demo script (about 5 minutes)

Before: run `run-backend.bat`, open http://127.0.0.1:8000 in Chrome, headset on, hotspot ready. Use fictional data only. Candidate answers are in `ai03-backend/sample_data/scripted_answers.json`.

1. **Problem (30 s).** Say it is an AI that supports human reviewers.
2. **Setup (45 s).** Load sample data, generate. Show the rubric (1/3/5 anchors) and a résumé-linked question with its source tag.
3. **Consent (15 s).** Start is locked until the box is ticked.
4. **Interview (2 min).** Strong answer to question 1: no follow-up. Then the vague answer "I made a project.": show the follow-up and the *Why this follow-up?* reason, and the coverage meter. Say "I don't know" once to show no pressure.
5. **Report (1 min).** Click a quote: it jumps to the exact transcript turn. Point at n/a criteria, gaps, human-review list and suggested questions.
6. **Safety and limits (30 s).** Human decides; mock mode vs real model; speech errors.

Fallbacks: type if speech fails; use the hotspot if Wi-Fi fails; Reset between runs; keep a screen recording as backup.
