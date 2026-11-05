# Measured results

Generated 2026-11-01 13:15 | mode: **MOCK (no API key: rule-based follow-ups, placeholder scores)**

| Scenario | Done | Qs | Follow-ups | Max/Q | Rephrases | Quotes shown/verified | Criteria w/o evidence | Rubric summary | Median turn ms | Gold check |
|---|---|---|---|---|---|---|---|---|---|---|
| strong | yes | 7 | 0 | 0 | 0 | 5/5 | 0/5 | 3.0 | 0.26 | PASS |
| average | yes | 7 | 7 | 2 | 0 | 5/5 | 0/5 | 3.0 | 0.24 | PASS |
| vague | yes | 7 | 7 | 2 | 0 | 5/5 | 0/5 | 3.0 | 0.22 | PASS |
| evasive | yes | 7 | 7 | 1 | 7 | 0/0 | 5/5 | n/a | 0.23 | PASS |
| idk | yes | 7 | 0 | 0 | 0 | 0/0 | 5/5 | n/a | 0.23 | PASS |

Follow-up specificity: 14 of 14 detail follow-ups quote a phrase from the candidate's previous answer.
Evidence validity: 15 of 15 displayed quotes passed the verifier.

**Not measured in mock mode:** score separation between strong and weak candidates (placeholder scores are all 3), scoring consistency across 3 runs (use `python -m app.member2.consistency_harness` with a real key), question relevance ratings, and real LLM turn latency. Run this script again with an API key to fill these in.
