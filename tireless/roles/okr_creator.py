"""Objective & Key Results Creator — turns vague asks into real objectives."""

from __future__ import annotations

from typing import Any

from tireless.models import KeyResult, ObjectiveSpec, RoleName
from tireless.roles.base import Role, RoleContext


class OKRCreator(Role):
    name = RoleName.OKR_CREATOR
    charter = (
        "You research what the user meant — and what they did not mean — "
        "then rewrite the ask into a crisp objective, key results, and criteria. "
        "Prefer end states a person can experience (e.g. a page a kid can read "
        "and fully learn XYZ) over feature laundry lists."
    )

    def act(self, ctx: RoleContext) -> dict[str, Any]:
        system = (
            f"You are the Objective & Key Results Creator.\n{self.charter}\n"
            "Return JSON: end_goal, target_customer, success_definition, non_goals[], "
            "learning_outcome, key_results[{description, metric, target, verification}]."
        )
        user = (
            f"PROMPT: {ctx.session.root_prompt}\n"
            f"Feedback: {ctx.session.feedback_history}\n"
            f"Prior objective: {ctx.session.objective.model_dump() if ctx.session.objective else None}\n"
            "Enhance this into the objective the user is truly trying to achieve."
        )
        data = self.llm.chat_json(system, user)
        krs = [
            KeyResult(
                description=str(k.get("description") or ""),
                metric=str(k.get("metric") or ""),
                target=str(k.get("target") or ""),
                verification=str(k.get("verification") or ""),
            )
            for k in (data.get("key_results") or [])
        ]
        objective = ObjectiveSpec(
            end_goal=str(data.get("end_goal") or ctx.session.root_prompt),
            target_customer=str(data.get("target_customer") or "end user"),
            success_definition=str(data.get("success_definition") or ""),
            non_goals=[str(x) for x in (data.get("non_goals") or [])],
            key_results=krs,
            learning_outcome=str(data.get("learning_outcome") or ""),
        )
        ctx.session.objective = objective
        ctx.session.title = objective.learning_outcome or objective.end_goal[:80]
        ctx.session.context_digest = (
            f"Objective: {objective.end_goal}. "
            f"Success: {objective.success_definition}. "
            f"KRs: {len(objective.key_results)}."
        )
        return {
            "end_goal": objective.end_goal,
            "key_results": [k.model_dump() for k in krs],
            "objective": objective.model_dump(),
        }
