"""Barbara Minto Researcher — MECE mental models, not answer-first research."""

from __future__ import annotations

from typing import Any

from tireless.models import ResearchAtom, RoleName
from tireless.roles.base import Role, RoleContext


class BarbaraMintoResearcher(Role):
    name = RoleName.BARBARA_MINTO
    charter = (
        "You do not research with the end answer already decided. "
        "You build the right mental model, ask what information is sufficient "
        "to meet the user's objective, and what you still do not know. "
        "Slice research into mutually exclusive atoms that together are exhaustive (MECE)."
    )

    def act(self, ctx: RoleContext) -> dict[str, Any]:
        objective = ctx.session.objective
        system = (
            f"You are the Barbara Minto Researcher.\n{self.charter}\n"
            "Return JSON: atoms[{topic, question, findings, gaps_remaining[], sufficient_for_objective}]."
            " Atoms must be mutually exclusive and collectively cover the objective."
        )
        user = (
            f"PROMPT: {ctx.session.root_prompt}\n"
            f"Objective: {objective.model_dump() if objective else None}\n"
            "Research what must be known. Flag remaining gaps honestly."
        )
        data = self.llm.chat_json(system, user)
        atoms = [
            ResearchAtom(
                topic=str(a.get("topic") or "topic"),
                question=str(a.get("question") or ""),
                findings=str(a.get("findings") or ""),
                gaps_remaining=[str(g) for g in (a.get("gaps_remaining") or [])],
                sufficient_for_objective=bool(a.get("sufficient_for_objective")),
            )
            for a in (data.get("atoms") or [])
        ]
        # If the model left gaps, mark insufficient unless findings exist
        for atom in atoms:
            if atom.gaps_remaining:
                atom.sufficient_for_objective = False
        # For offline/local builds, allow proceeding when findings exist and gaps empty
        if atoms and all(a.findings and not a.gaps_remaining for a in atoms):
            for atom in atoms:
                atom.sufficient_for_objective = True

        ctx.session.research = atoms
        ctx.session.artifacts["research_atoms"] = [a.model_dump() for a in atoms]
        ctx.session.context_digest += f" Research atoms={len(atoms)}."
        return {
            "atoms": [a.model_dump() for a in atoms],
        }
