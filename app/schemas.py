from __future__ import annotations
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

DISCLAIMER = "Assessment to support a human reviewer. Not a hiring decision."


class Criterion(BaseModel):
    id: str
    name: str
    description: str
    weight: float = 1.0
    # score anchors: {"1": "...", "3": "...", "5": "..."}
    anchors: Dict[str, str] = Field(default_factory=dict)


class Rubric(BaseModel):
    role_title: str
    criteria: List[Criterion]


class SessionCreate(BaseModel):
    jd_text: str
    resume_text: str


class Source(BaseModel):
    type: Literal["jd", "resume"] = "jd"
    ref: str = ""


class Question(BaseModel):
    id: str
    text: str
    criterion_id: str
    source: Source = Field(default_factory=Source)
    probes: List[str] = Field(default_factory=list)


class Turn(BaseModel):
    idx: int
    speaker: Literal["agent", "candidate"]
    text: str
    criterion_id: Optional[str] = None
    kind: Literal["main", "followup", "closing", "answer"] = "main"
    reason: Optional[str] = None       # why the agent asked this (shown in the UI)
    question_id: Optional[str] = None


class AnswerIn(BaseModel):
    text: str


class Evidence(BaseModel):
    turn_id: int
    quote: str


class CriterionScore(BaseModel):
    criterion_id: str
    score: Optional[int] = Field(default=None, ge=1, le=5)  # None = insufficient evidence
    confidence: Literal["low", "med", "high"] = "low"
    rationale: str = ""
    evidence_quotes: List[str] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)  # filled by the verifier


class HumanReview(BaseModel):
    topic: str
    why: str


class Assessment(BaseModel):
    scores: List[CriterionScore]
    overall: Optional[float] = None     # weighted "rubric summary" over scored criteria only
    summary: str = ""
    flags: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    needs_human_review: List[HumanReview] = Field(default_factory=list)
    suggested_human_questions: List[str] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER


class Session(BaseModel):
    id: str
    state: Literal["CREATED", "RUBRIC_READY", "IN_INTERVIEW", "COMPLETE"] = "CREATED"
    jd_text: str
    resume_text: str
    rubric: Optional[Rubric] = None
    # first question per criterion (kept for older clients); full plan is `questions`
    plan: Dict[str, str] = Field(default_factory=dict)
    questions: List[Question] = Field(default_factory=list)
    turns: List[Turn] = Field(default_factory=list)
    q_pos: int = 0             # index of the current planned question
    followups_used: int = 0    # follow-ups used on the current question
    started_at: Optional[float] = None
    assessment: Optional[Assessment] = None
    consent_given: bool = False
