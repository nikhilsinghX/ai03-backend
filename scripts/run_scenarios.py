"""Runs the 5 scripted scenarios against the interview logic and writes docs/results.md.
Usage (from ai03-backend, venv active):  python scripts/run_scenarios.py
Works in mock mode (no key) and with a real key. Numbers are measured, not claimed."""
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import llm  # noqa: E402
from app.scenario_runner import run_all  # noqa: E402

res = run_all()
mode = "MOCK (no API key: rule-based follow-ups, placeholder scores)" if llm.is_mock() else f"REAL LLM ({llm.provider()})"
lines = [f"# Measured results", "", f"Generated {datetime.now():%Y-%m-%d %H:%M} | mode: **{mode}**", "",
         "| Scenario | Done | Qs | Follow-ups | Max/Q | Rephrases | Quotes shown/verified | Criteria w/o evidence | Rubric summary | Median turn ms | Gold check |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
for name, r in res.items():
    lines.append(f"| {name} | {'yes' if r['completed'] else 'NO'} | {r['questions']} | {r['followups']} | {r['max_followups_per_question']} | {r['rephrases']} | "
                 f"{r['quotes_shown']}/{r['quotes_verified']} | {r['null_scores']}/{r['criteria']} | {r['overall'] if r['overall'] is not None else 'n/a'} | {r['median_turn_ms']} | "
                 f"{'PASS' if not r['failed'] else 'FAIL: ' + '; '.join(r['failed'])} |")
det = sum(r["detail_followups"] for r in res.values()); spec = sum(r["specific_followups"] for r in res.values())
lines += ["", f"Follow-up specificity: {spec} of {det} detail follow-ups quote a phrase from the candidate's previous answer.",
          f"Evidence validity: {sum(r['quotes_verified'] for r in res.values())} of {sum(r['quotes_shown'] for r in res.values())} displayed quotes passed the verifier.", ""]
if llm.is_mock():
    lines += ["**Not measured in mock mode:** score separation between strong and weak candidates (placeholder scores are all 3), "
              "scoring consistency across 3 runs (use `python -m app.member2.consistency_harness` with a real key), question relevance ratings, "
              "and real LLM turn latency. Run this script again with an API key to fill these in.", ""]
out = ROOT.parent / "docs" / "results.md"
out.parent.mkdir(exist_ok=True)
out.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
print(f"\nWrote {out}")
sys.exit(1 if any(r["failed"] for r in res.values()) else 0)
