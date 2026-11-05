# Known limitations

- **Mock mode is not an assessment.** With no API key every criterion gets a placeholder score of 3 (when a quote exists). It proves the flow, not scoring quality. Never use it for a real decision.
- **Real-model behaviour is not validated.** Rubric, question and follow-up quality, scoring consistency and strong-vs-weak separation have not been measured with a real model. Fill the gaps with `python scripts/run_scenarios.py` and `python -m app.member2.consistency_harness` once a key is set.
- **Follow-up policy in mock mode is rule-based** (answer length, "we" vs "I", outcome words, "I don't know"). It is deliberately simple and can be wrong; the real model uses the written policy prompt.
- **Member 2's full P1-P5 modules are not in the live flow.** They live in `app/member2/` with their own tests. The live flow uses `app/pipeline.py`, which has the same rules in a simpler shape.
- **Speech:** Chrome's recognition needs internet and often mishears names and technical words. The live transcript and typed fallback cover this. No Whisper fallback, no Hindi/English mixed answers.
- **Upload accepts .txt and .md only** (or paste). PDF résumés are not parsed.
- **No authentication.** Do not expose the server to the internet. Sessions are stored in a local SQLite file (`interviewlens.db`).
- The reviewer's decision recorded in the report lives in the open page and the exported JSON, not on the server.
- No ATS integration and no automatic hiring decision, by design.
