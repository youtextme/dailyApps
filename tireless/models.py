"""Shared models for stateful dailyApps processing."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class SessionStatus(str, Enum):
    ACKED = "acked"
    RUNNING = "running"
    WAITING_FEEDBACK = "waiting_feedback"
    COMPLETED = "completed"
    FAILED = "failed"


class StateStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class RoleName(str, Enum):
    LOOP_BUILDER = "loop_builder"
    OKR_CREATOR = "okr_creator"
    BARBARA_MINTO = "barbara_minto"
    UX_CX_BUILDER = "ux_cx_builder"
    SLACK_COMMUNICATOR = "slack_communicator"
    TEST_ENGINEER = "test_engineer"
    QUALITY_GATE = "quality_gate"


class ExitCriterion(BaseModel):
    """Objective, checkable condition — not a vibe check."""

    id: str = Field(default_factory=new_id)
    description: str
    check_kind: str  # e.g. has_okr, mece_complete, html_interactive, quality_pass, tests_pass
    params: dict[str, Any] = Field(default_factory=dict)
    met: bool = False
    evidence: str = ""


class LoopPlan(BaseModel):
    """One engineered loop with real exit criteria."""

    index: int
    name: str
    purpose: str
    owner_role: RoleName
    exit_criteria: list[ExitCriterion] = Field(default_factory=list)
    status: StateStatus = StateStatus.PENDING
    summary: str = ""
    artifacts: dict[str, Any] = Field(default_factory=dict)


class ProcessingState(BaseModel):
    """A reportable unit of progress (Slack gets one update per state end)."""

    id: str = Field(default_factory=new_id)
    loop_index: int
    name: str
    role: RoleName
    status: StateStatus = StateStatus.PENDING
    started_at: datetime | None = None
    ended_at: datetime | None = None
    slack_blurb: str = ""  # <= ~15 words
    detail_path: str = ""  # local or gist relative path
    output_preview: str = ""


class KeyResult(BaseModel):
    description: str
    metric: str
    target: str
    verification: str


class ObjectiveSpec(BaseModel):
    """Loop-1 product: what the user is actually trying to achieve."""

    end_goal: str
    target_customer: str
    success_definition: str
    non_goals: list[str] = Field(default_factory=list)
    key_results: list[KeyResult] = Field(default_factory=list)
    learning_outcome: str = ""  # e.g. "a page a kid can read and fully learn XYZ"


class ResearchAtom(BaseModel):
    """MECE research unit — mutually exclusive slice of knowledge."""

    topic: str
    question: str
    findings: str
    gaps_remaining: list[str] = Field(default_factory=list)
    sufficient_for_objective: bool = False


class TestCase(BaseModel):
    name: str
    kind: str  # unit | integration | production | cx
    steps: list[str]
    expected: str
    result: str = "pending"
    evidence: str = ""


class BuildGist(BaseModel):
    """Customer-facing build narrative (not a random test dump)."""

    title: str
    objectives: list[str]
    building_tenets: list[str]
    loops_run: list[str]
    unit_tests: list[TestCase] = Field(default_factory=list)
    integration_tests: list[TestCase] = Field(default_factory=list)
    production_tests: list[TestCase] = Field(default_factory=list)
    cx_evolution: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    app_url: str = ""
    markdown: str = ""
    url: str = ""  # GitHub gist or local file URL
    local_path: str = ""


class Session(BaseModel):
    """Stateful processing session — not a stateless prompt."""

    id: str = Field(default_factory=new_id)
    objective_id: str = Field(default_factory=new_id)
    channel: str = ""
    thread_ts: str = ""
    user_id: str = ""
    root_prompt: str
    status: SessionStatus = SessionStatus.ACKED
    loops: list[LoopPlan] = Field(default_factory=list)
    states: list[ProcessingState] = Field(default_factory=list)
    objective: ObjectiveSpec | None = None
    research: list[ResearchAtom] = Field(default_factory=list)
    slug: str = ""
    title: str = ""
    app_path: str = ""
    app_url: str = ""
    gist: BuildGist | None = None
    context_digest: str = ""  # reloaded on thread follow-ups
    feedback_history: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    def touch(self) -> None:
        self.updated_at = utcnow()

    def append_feedback(self, text: str) -> None:
        self.feedback_history.append(text)
        self.touch()

    def current_loop(self) -> LoopPlan | None:
        for loop in self.loops:
            if loop.status in {StateStatus.PENDING, StateStatus.RUNNING}:
                return loop
        return None
