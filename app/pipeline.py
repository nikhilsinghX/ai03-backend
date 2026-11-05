"""AI steps: rubric, question plan, follow-up decision, assessment.
PROMPTS live here (Member 2). MOCK mode keeps everything working without an API key, and every
real-LLM step falls back to a safe rule-based answer if the call fails, so the demo never dead-ends."""
import re
from typing import List, Optional, Tuple

from . import llm
from .report import says_dont_know
from .schemas import Assessment, Criterion, CriterionScore, Question, Rubric, Source, Turn

SAFETY = (
    "Judge ONLY job-related skills. Never use or infer age, gender, religion, "
    "caste, nationality, appearance, accent, voice, or any personal/demographic trait."
)

RUBRIC_SYSTEM = (
    "You design interview rubrics. " + SAFETY +
    ' Output JSON: {"role_title": str, "criteria": [{"id": short_snake_case, "name": str, '
    '"description": str, "weight": number (percentages, sum 100), "anchors": {"1": str, "3": str, "5": str}}]}. '
    "Produce 4-6 job-related criteria drawn from the job description."
)

PLAN_SYSTEM = (
    "You plan an interview. Write 6-8 questions. Every criterion gets at least one question and at "
    "least 2 questions are grounded in specific resume claims. " + SAFETY +
    ' Output JSON: {"questions": [{"id": "q1", "text": str, "criterion_id": str, '
    '"source": {"type": "jd" or "resume", "ref": "short quote of the JD line or resume claim"}, '
    '"probes": [str]}]}.'
)

FOLLOWUP_SYSTEM = (
    "You are an AI interviewer deciding whether to probe deeper. " + SAFETY +
    " Policy: no concrete example -> ask for one specific project or situation; example without an "
    "outcome or number -> ask how it was measured; vague ownership ('we did') -> ask what they "
    "personally did; a claim that conflicts with the resume -> ask neutrally to clarify, never accuse; "
    "a strong specific answer -> at most one deeper probe (trade-off or failure case) if followups_used is 0, "
    "else move on; off-topic or empty -> rephrase once politely; the candidate says they do not know -> "
    "needs_followup=false. Write ONE short spoken question (max 25 words) that refers to a specific detail "
    "from the answer. Never reveal scores. "
    'Output JSON: {"needs_followup": bool, "question": str, "reason": str}. '
    "'reason' is ONE short sentence telling the reviewer what was missing in the answer."
)

ASSESS_SYSTEM = (
    "You score a finished interview against the rubric, for a HUMAN reviewer. " + SAFETY +
    " Every score MUST cite 1-2 verbatim quotes copied exactly from CANDIDATE turns. If there is no "
    "supporting quote, set score to null. Never give a hire/reject verdict. "
    'Output JSON: {"scores": [{"criterion_id": str, "score": 1-5 or null, "confidence": "low"|"med"|"high", '
    '"rationale": str, "evidence_quotes": [str]}], "summary": str}.'
)


# ---------- Default rubric (PDF Appendix C, AI/ML Intern) ----------
def default_rubric(jd: str = "") -> Rubric:
    first = jd.strip().splitlines()[0].lstrip("# ").strip() if jd.strip() else "Role"
    spec = [
        ("fundamentals", "Technical fundamentals", 25, "Explains core ML and Python concepts correctly, with trade-offs.",
         "Cannot explain basic ML or Python concepts asked about", "Explains core concepts correctly with minor gaps",
         "Explains accurately with trade-offs and edge cases"),
        ("project_ownership", "Project depth and ownership", 25, "Specific problem, personal contribution and a measured outcome.",
         "No concrete project, or cannot say what they did themselves", "Describes a project and their role, limited outcome detail",
         "Specific problem, personal contribution, decisions made and a measured outcome"),
        ("problem_solving", "Problem solving and reasoning", 20, "Clear step-by-step approach that considers failure cases.",
         "No structured approach to a new problem", "Reasonable approach, misses some considerations",
         "Clear step-by-step approach, tests assumptions, considers failure cases"),
        ("communication", "Communication clarity", 15, "Well-structured, specific answers (judged on content only).",
         "Answer is hard to follow or does not address the question", "Mostly clear, somewhat unstructured",
         "Well-structured, specific, directly answers the question (judged on content only)"),
        ("learning", "Learning agility and collaboration", 15, "Concrete examples of learning fast and working in a team.",
         "No examples of learning or working with others", "Some examples, limited reflection",
         "Concrete examples of learning fast, receiving feedback, working in a team"),
    ]
    return Rubric(role_title=first, criteria=[
        Criterion(id=i, name=n, description=d, weight=w, anchors={"1": a1, "3": a3, "5": a5})
        for i, n, w, d, a1, a3, a5 in spec])


def _normalize_weights(r: Rubric) -> Rubric:
    ws = [max(0.0, float(c.weight or 0)) for c in r.criteria]
    total = sum(ws)
    pct = [round(w * 100 / total) for w in ws] if total > 0 else [round(100 / len(ws))] * len(ws)
    pct[-1] += 100 - sum(pct)
    for c, p in zip(r.criteria, pct):
        c.weight = float(p)
    return r


def generate_rubric(jd: str) -> Rubric:
    if llm.is_mock():
        return default_rubric(jd)
    try:
        r = Rubric(**llm.call_json(RUBRIC_SYSTEM, f"JOB DESCRIPTION:\n{jd}"))
        ids = [c.id for c in r.criteria]
        if not 4 <= len(r.criteria) <= 6 or len(set(ids)) != len(ids):
            raise ValueError("rubric must have 4-6 criteria with unique ids")
        if any(not all(k in c.anchors for k in ("1", "3", "5")) for c in r.criteria):
            raise ValueError("each criterion needs anchors 1, 3 and 5")
        return _normalize_weights(r)
    except Exception as e:  # noqa: BLE001
        print(f"[pipeline] rubric fallback: {e}")
        return default_rubric(jd)


# ---------- Question plan (6-8 questions, each tagged with criterion and source) ----------
_CLAIM_WORDS = ("built", "project", "led", "developed", "classifier", "chatbot", "model", "team", "hackathon", "intern", "research")
_TEMPLATES = {
    "fundamentals": "How would you decide between a simple model and a complex one when you have a small dataset?",
    "problem_solving": "A model that worked well suddenly gets worse on new data. How would you investigate?",
    "communication": "Explain overfitting to a teammate who is not technical.",
    "learning": "Tell me about a time you had to learn something new quickly, or acted on feedback.",
}


def _claims(resume: str, limit: int = 3) -> List[str]:
    parts = re.split(r"[\n;]|\.\s", resume or "")
    out = []
    for p in parts:
        p = re.sub(r"^(projects?|experience|skills|education)\s*:\s*", "", p.strip(), flags=re.I).strip(" .-•")
        if 15 <= len(p) <= 160:
            out.append(p)
    out.sort(key=lambda p: 0 if any(w in p.lower() for w in _CLAIM_WORDS) else 1)  # stable: keeps order otherwise
    return out[:limit]


def _jd_ref(jd: str, c: Criterion) -> str:
    lines = [l.strip().lstrip("# ").strip() for l in (jd or "").splitlines() if l.strip()]
    words = [w for w in re.findall(r"[a-z]+", c.name.lower()) if len(w) > 3]
    for l in lines:
        if any(w in l.lower() for w in words):
            return l[:90]
    return lines[0][:90] if lines else "Job description"


def _mock_plan(rubric: Rubric, resume: str, jd: str = "") -> List[Question]:
    claims = _claims(resume)
    crits = rubric.criteria
    qs: List[Question] = []
    used = 0
    for c in crits:
        if c.id == "project_ownership" and claims:
            claim = claims[0]; used = 1
            text = f'Tell me about this from your résumé: "{claim}". What problem were you solving, and what did you personally build?'
            src = Source(type="resume", ref=claim)
        else:
            text = _TEMPLATES.get(c.id) or f"Give a concrete example that shows {c.name.lower()}: the situation, what you personally did, and the result."
            src = Source(type="jd", ref=_jd_ref(jd, c))
        qs.append(Question(id="", text=text, criterion_id=c.id, source=src,
                           probes=["Ask for one specific example", "Ask how the result was measured"]))
    target = min(8, max(6, len(crits) + 2))
    k = 0
    for claim in claims[used:]:
        if len(qs) >= target:
            break
        c = crits[(k * 2) % len(crits)]; k += 1
        qs.append(Question(id="", criterion_id=c.id, source=Source(type="resume", ref=claim),
                           text=f'Your résumé says "{claim}". What was the hardest decision you made there, and what would you change now?',
                           probes=["Ask what they personally decided"]))
    while len(qs) < target:  # JD-grounded extras
        c = crits[(k * 2 + 1) % len(crits)]; k += 1
        ref = _jd_ref(jd, c)
        qs.append(Question(id="", criterion_id=c.id, source=Source(type="jd", ref=ref),
                           text=f'The job description mentions "{ref}". How would you apply {c.name.lower()} in your first month?',
                           probes=["Ask for a past example"]))
    order = {c.id: i for i, c in enumerate(crits)}
    qs.sort(key=lambda q: order[q.criterion_id])  # stable: grouped by criterion
    for i, q in enumerate(qs):
        q.id = f"q{i + 1}"
    return qs


def _validate_plan(data, rubric: Rubric, resume: str, jd: str) -> List[Question]:
    ids = {c.id for c in rubric.criteria}
    qs = []
    for item in (data.get("questions") if isinstance(data, dict) else data) or []:
        try:
            q = Question(**item)
        except Exception:  # noqa: BLE001
            continue
        if q.criterion_id in ids and q.text.strip():
            qs.append(q)
    qs = qs[:8]
    fallback = _mock_plan(rubric, resume, jd)
    for c in rubric.criteria:  # every criterion needs a question
        if not any(q.criterion_id == c.id for q in qs):
            qs.append(next(f for f in fallback if f.criterion_id == c.id))
    for f in fallback:  # pad up to 6
        if len(qs) >= 6:
            break
        if all(f.text != q.text for q in qs):
            qs.append(f)
    qs = qs[:8]
    order = {c.id: i for i, c in enumerate(rubric.criteria)}
    qs.sort(key=lambda q: order[q.criterion_id])
    for i, q in enumerate(qs):
        q.id = f"q{i + 1}"
    return qs


def plan_questions(rubric: Rubric, resume: str, jd: str = "") -> List[Question]:
    if not llm.is_mock():
        try:
            data = llm.call_json(PLAN_SYSTEM, f"RUBRIC:\n{rubric.model_dump_json()}\n\nJOB DESCRIPTION:\n{jd}\n\nRESUME:\n{resume}", max_tokens=2500)
            return _validate_plan(data, rubric, resume, jd)
        except Exception as e:  # noqa: BLE001
            print(f"[pipeline] plan fallback: {e}")
    return _mock_plan(rubric, resume, jd)


# ---------- Follow-up policy ----------
_OUTCOME = re.compile(r"\d|percent|%|accuracy|improv|reduc|increas|faster|saved|result", re.I)


def _hook(answer: str) -> str:
    return re.sub(r'["\u201c\u201d]', "", " ".join(answer.split()[:6]))


def _rule_followup(base_question: str, answer: str, used: int) -> Tuple[bool, str, str]:
    """Deterministic policy (also the fallback when the LLM is unavailable)."""
    words = answer.split()
    lower = answer.lower()
    if says_dont_know(answer):
        return False, "", ""  # mark gap, move on, no pressure
    if len(words) < 4:
        if used == 0:
            return (True, f"Let me rephrase the question: {base_question}",
                    "The answer was empty or off-topic, so the agent politely rephrases once before moving on.")
        return False, "", ""
    if len(words) >= 25:
        return False, "", ""
    kinds = []
    if re.search(r"\bwe\b", lower) and not re.search(r"\b(i|my|me)\b", lower):
        kinds.append("ownership")
    if not _OUTCOME.search(answer):
        kinds.append("metric")
    kinds.append("example")
    kind = kinds[min(used, len(kinds) - 1)]
    hook = _hook(answer)
    if kind == "ownership":
        return (True, f'You said "{hook}". Which part did you personally build or decide?',
                "The answer said 'we' without saying what the candidate personally did, so the follow-up asks about their own contribution.")
    if kind == "metric":
        return (True, f'You mentioned "{hook}". How did you measure whether it worked, or what changed?',
                "The answer had no measurable outcome, so the follow-up asks how the result was measured.")
    return (True, f'Could you give one specific project or situation behind "{hook}"?',
            "The answer was short and gave no concrete example, so the follow-up asks for one specific project or situation.")


def decide_followup(criterion: Criterion, question: str, answer: str, followups_used: int = 0,
                    base_question: Optional[str] = None) -> Tuple[bool, str, str]:
    base = base_question or question
    if llm.is_mock():
        return _rule_followup(base, answer, followups_used)
    if says_dont_know(answer):
        return False, "", ""
    try:
        data = llm.call_json(
            FOLLOWUP_SYSTEM,
            f"CRITERION: {criterion.model_dump_json()}\nQUESTION: {question}\nANSWER: {answer}\nFOLLOWUPS_USED: {followups_used}",
            max_tokens=400,
        )
        q = str(data.get("question", "")).strip()
        return bool(data.get("needs_followup")) and bool(q), q, str(data.get("reason", "")).strip()
    except Exception as e:  # noqa: BLE001
        print(f"[pipeline] follow-up fallback: {e}")
        return _rule_followup(base, answer, followups_used)


# ---------- Assessment ----------
def assess(rubric: Rubric, turns: List[Turn]) -> Assessment:
    if llm.is_mock():
        scores = []
        for c in rubric.criteria:
            answers = [t for t in turns if t.speaker == "candidate" and t.criterion_id == c.id
                       and len(t.text.split()) >= 4 and not says_dont_know(t.text)]
            quote = " ".join(answers[0].text.split()[:12]) if answers else ""
            scores.append(CriterionScore(criterion_id=c.id, score=3,
                                         rationale="Mock score for pipeline testing.",
                                         evidence_quotes=[quote] if quote else []))
        return Assessment(scores=scores, summary="Mock assessment.")
    transcript = "\n".join(f"[turn {t.idx}] {t.speaker.upper()}: {t.text}" for t in turns)
    try:
        data = llm.call_json(ASSESS_SYSTEM, f"RUBRIC:\n{rubric.model_dump_json()}\n\nTRANSCRIPT:\n{transcript}", max_tokens=2500)
        return Assessment(**data)
    except Exception as e:  # noqa: BLE001
        print(f"[pipeline] assessment fallback: {e}")
        return Assessment(
            scores=[CriterionScore(criterion_id=c.id, score=None, rationale="Automatic assessment unavailable (LLM error).")
                    for c in rubric.criteria],
            summary="Automatic assessment unavailable. Please review the transcript manually.",
            flags=["LLM unavailable during assessment: no scores were generated."])
