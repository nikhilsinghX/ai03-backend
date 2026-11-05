# Plan (PDF) vs build: who owns what, and what is done

## Must-have
| ID | Item | Status |
|---|---|---|
| M1 | Paste or upload JD + résumé, load sample | Done (.txt/.md upload, no PDF) |
| M2 | Rubric 4-6 criteria, 1/3/5 anchors, editable (default = Appendix C) | Done |
| M3 | 6-8 questions, each tagged with criterion and JD/résumé source | Done |
| M4 | Consent, opening line says it is an AI, adaptive follow-ups (max 2), written policy | Done |
| M5 | Voice in/out in Chrome with typed fallback | Built; test in Chrome on your machine |
| M6 | Live transcript with turn IDs | Done |
| M7 | Assessment: scores or n/a, verified quotes, strengths, gaps, human-review, suggested questions, disclaimer | Done |
| M8 | "Why this follow-up" reason in the UI | Done |
| M9 | Printable report + JSON export | Done |

## By member
| Member | Done | Not done |
|---|---|---|
| 1 Backend | API, state machine (caps, coverage, time limit), SQLite, consent gate, provider switch (Anthropic/Groq/OpenAI), timeout, latency log, fallbacks, single port, run scripts | Authentication |
| 2 AI | Prompts, follow-up policy, verifier with turn IDs, P1-P5 modules + contract tests | Wiring P1-P5 into the live flow; 3-run consistency and prompt tuning need a real key |
| 3 Frontend | All screens, voice + typed, reason panel, coverage meter, report with clickable quotes, human decision, print, JSON, upload | Whisper fallback; second-candidate side-by-side view |
| 4 Data/QA/Demo | 3 resumes, 5 scripted scenarios, gold checks, runner, measured results.md (mock), SAFETY, LIMITATIONS, README, demo script, checklist, 7-slide deck | Real-key metrics, rehearsals, backup demo video |

## Should / stretch
Rubric edit before interview: done. Suggested human-round questions: done. Second candidate: scripted (strong vs vague) but no side-by-side view. Quote-verified count badge: done. Résumé-vs-answer inconsistency flag, Hindi/English, Whisper, candidate feedback, n8n email: not done.
