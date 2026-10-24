from __future__ import annotations
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


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


class Turn(BaseModel):
    idx: int
    speaker: Literal["agent", "candidate"]
    text: str
    criterion_id: Optional[str] = None
    kind: Literal["main", "followup", "closing", "answer"] = "main"


class AnswerIn(BaseModel):
    text: str


class CriterionScore(BaseModel):
    criterion_id: str
    score: int = Field(ge=1, le=5)
    rationale: str
    evidence_quotes: List[str] = Field(default_factory=list)


class Assessment(BaseModel):
    scores: List[CriterionScore]
    overall: float
    summary: str
    flags: List[str] = Field(default_factory=list)


class Session(BaseModel):
    id: str
    state: Literal["CREATED", "RUBRIC_READY", "IN_INTERVIEW", "COMPLETE"] = "CREATED"
    jd_text: str
    resume_text: str
    rubric: Optional[Rubric] = None
    # one main question per criterion, planned from rubric + resume
    plan: Dict[str, str] = Field(default_factory=dict)
    turns: List[Turn] = Field(default_factory=list)
    crit_pos: int = 0          # index of current criterion
    followups_used: int = 0    # follow-ups used on current criterion
    assessment: Optional[Assessment] = None
    consent_given: bool = False
