"""Role behaviors: think → act → verify exit criteria."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from tireless.llm.client import LocalLLM
from tireless.models import ExitCriterion, RoleName, Session


@dataclass
class RoleContext:
    session: Session
    llm: LocalLLM
    notify: Callable[[str, str], None] = field(default=lambda _blurb, _detail: None)
    extras: dict[str, Any] = field(default_factory=dict)


class Role(ABC):
    """A recruited consultant with a stable *behavior*, not a static checklist."""

    name: RoleName
    charter: str

    def __init__(self, llm: LocalLLM) -> None:
        self.llm = llm

    def think(self, ctx: RoleContext) -> str:
        """Form a working mental model before acting."""
        system = (
            f"You are the {self.name.value} consultant.\n"
            f"Behavior charter:\n{self.charter}\n"
            "Think in plain language. Do not invent fake certainty. "
            "Name what you know, what you don't, and what must be true to exit."
        )
        user = (
            f"Objective id: {ctx.session.objective_id}\n"
            f"Root prompt: {ctx.session.root_prompt}\n"
            f"Feedback history: {ctx.session.feedback_history}\n"
            f"Context digest: {ctx.session.context_digest}\n"
            f"Current objective spec: {ctx.session.objective.model_dump() if ctx.session.objective else None}\n"
            "What are you trying to accomplish in this turn, and what would prove it?"
        )
        return self.llm.chat(system, user, temperature=0.2)

    @abstractmethod
    def act(self, ctx: RoleContext) -> dict[str, Any]:
        """Produce artifacts that move the session forward."""

    def verify(self, criteria: list[ExitCriterion], artifacts: dict[str, Any]) -> list[ExitCriterion]:
        """Mark criteria met/unmet with evidence. Subclasses may override."""
        updated: list[ExitCriterion] = []
        for c in criteria:
            met, evidence = self._default_check(c, artifacts)
            updated.append(c.model_copy(update={"met": met, "evidence": evidence}))
        return updated

    def _default_check(self, c: ExitCriterion, artifacts: dict[str, Any]) -> tuple[bool, str]:
        kind = c.check_kind
        if kind == "has_end_goal":
            goal = (artifacts.get("end_goal") or "").strip()
            return (len(goal) > 10, goal[:160] or "missing end_goal")
        if kind == "has_okrs":
            krs = artifacts.get("key_results") or []
            need = int((c.params or {}).get("min", 2))
            return (len(krs) >= need, f"{len(krs)} key results")
        if kind == "mece_complete":
            atoms = artifacts.get("atoms") or []
            ok = bool(atoms) and all(a.get("sufficient_for_objective") for a in atoms)
            return (ok, f"{len(atoms)} research atoms")
        if kind == "quality_pass":
            score = float(artifacts.get("quality_score") or 0)
            return (score >= 80, f"score={score}")
        if kind == "tests_pass":
            tests = artifacts.get("all_tests") or []
            if not tests:
                return False, "no tests"
            failed = [t for t in tests if t.get("result") != "pass"]
            return (not failed, f"pass={len(tests)-len(failed)}/{len(tests)}")
        if kind == "shipped":
            ok = bool(artifacts.get("app_url")) and bool(artifacts.get("gist_url") or artifacts.get("gist_path"))
            return (ok, f"app={artifacts.get('app_url')} gist={artifacts.get('gist_url') or artifacts.get('gist_path')}")
        # Unknown criteria require explicit evidence flag
        return (bool(artifacts.get(f"criterion_{c.id}")), artifacts.get("evidence", ""))
