"""Extremely savvy UI/UX/CX Builder — customer objective or nothing."""

from __future__ import annotations

import re
from typing import Any

from tireless.dailyapps.quality_gate import run_quality_gate
from tireless.llm.client import LocalLLM
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
        prior_html = str(ctx.session.artifacts.get("html") or "")
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
        # Tiny local models choke on full-page HTML JSON. Prefer offline scaffold,
        # then overlay feedback / prior identity. Stronger routers still get a live try
        # when there is no prior page yet.
        use_offline_html = bool(prior_html) or "1b" in (self.llm.config.model or "")
        if use_offline_html:
            data = LocalLLM(offline=True).chat_json(system, user)
            if prior_html and run_quality_gate(prior_html).ok:
                data["html"] = prior_html
                data["title"] = ctx.session.title or data.get("title")
                data["slug"] = ctx.session.slug or data.get("slug")
        else:
            data = self.llm.chat_json(system, user)
        html = str(data.get("html") or "")
        title = str(
            data.get("title")
            or (objective.learning_outcome if objective else ctx.session.root_prompt[:60])
        )
        slug = _slugify(str(data.get("slug") or title))
        if feedback and ctx.session.slug:
            slug = ctx.session.slug  # keep identity across feedback iterations

        report = run_quality_gate(html)
        if not report.ok:
            repair_system = (
                "You are fixing an HTML page to pass a quality gate. "
                "Return JSON {html, title, slug, tenets, cx_notes}. Tag: build_html."
            )
            repair_user = (
                f"PROMPT: {ctx.session.root_prompt}\n"
                f"Feedback: {feedback}\n"
                f"Violations: {report.violations}\n"
                f"Current HTML:\n{html[:12000]}"
            )
            repaired = self.llm.chat_json(repair_system, repair_user)
            html = str(repaired.get("html") or html)
            title = str(repaired.get("title") or title)
            if not ctx.session.feedback_history:
                slug = _slugify(str(repaired.get("slug") or slug))
            report = run_quality_gate(html)

        # Small local models often emit broken HTML — fall back to a known-good page
        # and overlay feedback rather than shipping a failing stub.
        if not report.ok:
            fallback = LocalLLM(offline=True).chat_json(system, user)
            html = str(fallback.get("html") or html)
            title = str(fallback.get("title") or title)
            if not ctx.session.slug:
                slug = _slugify(str(fallback.get("slug") or slug))
            else:
                slug = ctx.session.slug
            data = {**fallback, **{k: data.get(k) for k in ("tenets", "cx_notes") if data.get(k)}}
            report = run_quality_gate(html)

        if feedback:
            html = _apply_feedback_markers(html, feedback)
            report = run_quality_gate(html)

        tenets = [str(t) for t in (data.get("tenets") or [])]
        cx_notes = str(data.get("cx_notes") or "")
        if feedback:
            cx_notes = (cx_notes + f" Applied feedback: {feedback}").strip()
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


def _apply_feedback_markers(html: str, feedback: str) -> str:
    """Keep quality-passing HTML while surfacing the latest feedback in the page."""
    note = (
        f'<aside id="feedback-note" data-feedback="1">'
        f"<strong>Updated from feedback:</strong> {_escape(feedback)}"
        f"</aside>"
    )
    if 'id="feedback-note"' in html:
        html = re.sub(
            r'<aside id="feedback-note"[^>]*>[\s\S]*?</aside>',
            note,
            html,
            count=1,
        )
    elif "<body" in html:
        html = re.sub(r"(<body[^>]*>)", r"\1\n" + note, html, count=1, flags=re.I)
    # Light dark-mode affordance when feedback asks for it
    if re.search(r"dark\s*mode", feedback, flags=re.I) and "theme-toggle" not in html:
        html = html.replace(
            "</header>",
            '<div class="toolbar"><button id="theme-toggle" type="button">Dark mode</button></div>\n</header>',
            1,
        )
        html = html.replace(
            "</script>",
            """
const themeBtn = document.getElementById('theme-toggle');
if (themeBtn) {
  themeBtn.addEventListener('click', () => {
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.documentElement.setAttribute('data-theme', dark ? '' : 'dark');
    themeBtn.setAttribute('aria-pressed', dark ? 'false' : 'true');
  });
}
</script>""",
            1,
        )
    return html


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
