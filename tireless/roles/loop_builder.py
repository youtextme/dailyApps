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
        loops = _normalize_plan(loops, ctx.session.root_prompt)
        stage_notes = str(data.get("stage_notes") or "")
        if not stage_notes:
            stage_notes = (
                "Loop 1 sets the objective/OKRs and defines exit criteria for every later loop; "
                "Slack updates fire when each state ends."
            )
        ctx.session.loops = loops
        ctx.session.artifacts["stage_notes"] = stage_notes
        ctx.session.context_digest = (
            f"Stage set by Loop Builder. {stage_notes} "
            f"Loops: " + "; ".join(f"{l.index}:{l.name}" for l in loops)
        )
        return {
            "loops": [l.model_dump() for l in loops],
            "stage_notes": stage_notes,
        }


_REQUIRED = [
    (RoleName.OKR_CREATOR, "understand_objective", "Identify end goal, OKRs, success criteria", "has_okrs"),
    (RoleName.BARBARA_MINTO, "mece_research", "MECE research mental model for the objective", "mece_complete"),
    (RoleName.UX_CX_BUILDER, "build_delightful_app", "Build the page that meets the customer objective", "quality_pass"),
    (RoleName.TEST_ENGINEER, "real_validation", "Run unit/integration/production/CX tests with evidence", "tests_pass"),
    (RoleName.SLACK_COMMUNICATOR, "ship_and_narrate", "Ship app + gist; short Slack status + links", "shipped"),
]


def _to_loop(item: dict[str, Any]) -> LoopPlan:
    role_raw = str(item.get("owner_role") or "loop_builder").strip().lower().replace(" ", "_")
    aliases = {
        "okr": RoleName.OKR_CREATOR,
        "okrs": RoleName.OKR_CREATOR,
        "researcher": RoleName.BARBARA_MINTO,
        "minto": RoleName.BARBARA_MINTO,
        "ux": RoleName.UX_CX_BUILDER,
        "ui": RoleName.UX_CX_BUILDER,
        "builder": RoleName.UX_CX_BUILDER,
        "test": RoleName.TEST_ENGINEER,
        "qa": RoleName.TEST_ENGINEER,
        "slack": RoleName.SLACK_COMMUNICATOR,
        "comms": RoleName.SLACK_COMMUNICATOR,
    }
    try:
        role = RoleName(role_raw)
    except ValueError:
        role = aliases.get(role_raw, RoleName.LOOP_BUILDER)
        for key, mapped in aliases.items():
            if key in role_raw:
                role = mapped
                break
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


def _normalize_plan(loops: list[LoopPlan], prompt: str) -> list[LoopPlan]:
    """Guarantee the canonical consultative loop spine exists with real exit criteria."""
    by_role = {l.owner_role: l for l in loops if l.owner_role in {r for r, *_ in _REQUIRED}}
    normalized: list[LoopPlan] = []
    for i, (role, name, purpose, check) in enumerate(_REQUIRED, start=1):
        existing = by_role.get(role)
        if existing:
            if not existing.exit_criteria:
                existing.exit_criteria = [
                    ExitCriterion(description=f"Complete: {purpose}", check_kind=check)
                ]
            existing.index = i
            if role == RoleName.OKR_CREATOR and not any(
                c.check_kind == "has_end_goal" for c in existing.exit_criteria
            ):
                existing.exit_criteria.insert(
                    0,
                    ExitCriterion(description="Clear end goal", check_kind="has_end_goal"),
                )
            if role == RoleName.OKR_CREATOR:
                for c in existing.exit_criteria:
                    if c.check_kind == "has_okrs" and "min" not in c.params:
                        c.params["min"] = 2
            normalized.append(existing)
        else:
            criteria = [ExitCriterion(description=f"Complete: {purpose}", check_kind=check)]
            if role == RoleName.OKR_CREATOR:
                criteria = [
                    ExitCriterion(description="Clear end goal", check_kind="has_end_goal"),
                    ExitCriterion(
                        description="At least 2 measurable key results",
                        check_kind="has_okrs",
                        params={"min": 2},
                    ),
                ]
            normalized.append(
                LoopPlan(
                    index=i,
                    name=name,
                    purpose=f"{purpose} for: {prompt[:120]}",
                    owner_role=role,
                    exit_criteria=criteria,
                    status=StateStatus.PENDING,
                )
            )
    return normalized

