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
        atoms = _atoms_from_payload(data)
        if not _mece_ready(atoms):
            # Tiny local models often return incomplete MECE — use structured offline research.
            from tireless.llm.client import LocalLLM

            offline = LocalLLM(offline=True).chat_json(system, user)
            atoms = _atoms_from_payload(offline)

        for atom in atoms:
            if atom.findings and not atom.gaps_remaining:
                atom.sufficient_for_objective = True

        ctx.session.research = atoms
        ctx.session.artifacts["research_atoms"] = [a.model_dump() for a in atoms]
        ctx.session.context_digest += f" Research atoms={len(atoms)}."
        return {
            "atoms": [a.model_dump() for a in atoms],
        }


def _atoms_from_payload(data: dict) -> list[ResearchAtom]:
    return [
        ResearchAtom(
            topic=str(a.get("topic") or "topic"),
            question=str(a.get("question") or ""),
            findings=str(a.get("findings") or ""),
            gaps_remaining=[str(g) for g in (a.get("gaps_remaining") or [])],
            sufficient_for_objective=bool(a.get("sufficient_for_objective")),
        )
        for a in (data.get("atoms") or [])
    ]


def _mece_ready(atoms: list[ResearchAtom]) -> bool:
    if len(atoms) < 2:
        return False
    return all(a.findings and (a.sufficient_for_objective or not a.gaps_remaining) for a in atoms)
