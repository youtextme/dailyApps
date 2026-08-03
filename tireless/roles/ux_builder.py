"""Extremely savvy UI/UX/CX Builder — customer objective or nothing."""

from __future__ import annotations

import re
from typing import Any

from tireless.dailyapps.quality_gate import run_quality_gate
from tireless.models import RoleName
from tireless.roles.base import Role, RoleContext


class UXCXBuilder(Role):
    name = RoleName.UX_CX_BUILDER
    charter = (
        "You build the page keeping one end goal: customer delight via meeting "
        "the customer objective — nothing else. Remove everything that delays "
        "the customer from meeting that objective (extra words, visual noise). "
        "At the same time the page must feel so delightful people want to share it. "
        "Everything is wired to help the target customer finish the job."
    )

    def act(self, ctx: RoleContext) -> dict[str, Any]:
        objective = ctx.session.objective
        feedback = ctx.session.feedback_history[-1] if ctx.session.feedback_history else ""
        system = (
            f"You are the Extremely savvy UI UX CX Builder.\n{self.charter}\n"
            "Return JSON with keys: title, slug, html, tenets[], cx_notes. "
            "html must be a full HTML document with doctype, viewport, expressive fonts "
            "(not Inter/Roboto), atmospheric background, interactive controls, and "
            "body data-dailyapps-ready=\"1\". "
            "Key the system tag build_html for tooling."
        )
        user = (
            f"PROMPT: {ctx.session.root_prompt}\n"
            f"Feedback: {feedback}\n"
            f"Objective: {objective.model_dump() if objective else None}\n"
            f"Research: {[a.model_dump() for a in ctx.session.research]}\n"
            "Build the page. If feedback exists, improve the prior intent rather than starting over."
        )
        data = self.llm.chat_json(system, user)
        html = str(data.get("html") or "")
        title = str(data.get("title") or (objective.learning_outcome if objective else ctx.session.root_prompt[:60]))
        slug = _slugify(str(data.get("slug") or title))
        if feedback and ctx.session.slug:
            slug = ctx.session.slug  # keep identity across feedback iterations

        # Apply quality gate; if fail, one repair pass with concrete violations
        report = run_quality_gate(html)
        if not report.ok:
            repair_system = (
                "You are fixing an HTML page to pass a quality gate. "
                "Return JSON {html, title, slug, tenets, cx_notes}. Tag: build_html."
            )
            repair_user = (
                f"PROMPT: {ctx.session.root_prompt}\n"
                f"Violations: {report.violations}\n"
                f"Current HTML:\n{html[:12000]}"
            )
            repaired = self.llm.chat_json(repair_system, repair_user)
            html = str(repaired.get("html") or html)
            title = str(repaired.get("title") or title)
            if not ctx.session.feedback_history:
                slug = _slugify(str(repaired.get("slug") or slug))
            report = run_quality_gate(html)

        tenets = [str(t) for t in (data.get("tenets") or [])]
        cx_notes = str(data.get("cx_notes") or "")
        ctx.session.title = title
        ctx.session.slug = slug
        ctx.session.artifacts["html"] = html
        ctx.session.artifacts["tenets"] = tenets
        ctx.session.artifacts["cx_notes"] = cx_notes
        ctx.session.artifacts["quality_score"] = report.score
        ctx.session.artifacts["quality_violations"] = report.violations
        return {
            "title": title,
            "slug": slug,
            "html": html,
            "tenets": tenets,
            "cx_notes": cx_notes,
            "quality_score": report.score,
            "quality_ok": report.ok,
        }


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug or "daily-app")[:80]
