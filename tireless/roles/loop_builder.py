"""Loop Builder — engineers loops with real exit criteria, not prompt theater."""

from __future__ import annotations

from typing import Any

from tireless.models import ExitCriterion, LoopPlan, RoleName, StateStatus
from tireless.roles.base import Role, RoleContext


class LoopBuilder(Role):
    name = RoleName.LOOP_BUILDER
    charter = (
        "You achieve outcomes with loops, not one-shot prompts. "
        "Loop 1 must set the stage: define every later loop, what each state means, "
        "how completion is proven, and how status updates should be read. "
        "Every loop has objective exit criteria that can fail. "
        "Reject fake validations and hallucinated acknowledgements."
    )

    def act(self, ctx: RoleContext) -> dict[str, Any]:
        system = (
            f"You are the Loop Builder.\n{self.charter}\n"
            "Return JSON with key 'loops' (array) and 'stage_notes' (string). "
            "Each loop: index, name, purpose, owner_role "
            "(okr_creator|barbara_minto|ux_cx_builder|test_engineer|slack_communicator|loop_builder), "
            "exit_criteria: [{description, check_kind, params?}]."
        )
        user = (
            f"PROMPT: {ctx.session.root_prompt}\n"
            f"Feedback: {ctx.session.feedback_history}\n"
            f"Context digest: {ctx.session.context_digest}\n"
            "Design the loop plan. Loop 1 must be objective understanding / OKRs. "
            "Later loops build, validate, and ship."
        )
        data = self.llm.chat_json(system, user)
        loops = [_to_loop(item) for item in data.get("loops") or []]
        if not loops:
            raise RuntimeError("Loop Builder produced no loops")
        # Ensure loop 1 is present and stage-setting
        if loops[0].index != 1:
            for i, loop in enumerate(loops, start=1):
                loop.index = i
        ctx.session.loops = loops
        ctx.session.artifacts["stage_notes"] = data.get("stage_notes", "")
        ctx.session.context_digest = (
            f"Stage set by Loop Builder. {data.get('stage_notes','')} "
            f"Loops: " + "; ".join(f"{l.index}:{l.name}" for l in loops)
        )
        return {
            "loops": [l.model_dump() for l in loops],
            "stage_notes": data.get("stage_notes", ""),
        }


def _to_loop(item: dict[str, Any]) -> LoopPlan:
    role_raw = str(item.get("owner_role") or "loop_builder")
    try:
        role = RoleName(role_raw)
    except ValueError:
        role = RoleName.LOOP_BUILDER
    criteria = [
        ExitCriterion(
            description=str(c.get("description") or "unspecified"),
            check_kind=str(c.get("check_kind") or "manual"),
            params=dict(c.get("params") or {}),
        )
        for c in (item.get("exit_criteria") or [])
    ]
    return LoopPlan(
        index=int(item.get("index") or 0),
        name=str(item.get("name") or "loop"),
        purpose=str(item.get("purpose") or ""),
        owner_role=role,
        exit_criteria=criteria,
        status=StateStatus.PENDING,
    )
