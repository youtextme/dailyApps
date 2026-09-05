"""Slack Communicator — short trust-building status, details in links."""

from __future__ import annotations

from typing import Any

from tireless.models import RoleName
from tireless.roles.base import Role, RoleContext


class SlackCommunicator(Role):
    name = RoleName.SLACK_COMMUNICATOR
    charter = (
        "You communicate what is going on in a simple, casual way. "
        "The reader should feel real work is happening and trust that the right "
        "things are being done — without drowning in detail. "
        "Prefer a ~15 word explanation plus a link for anyone who wants more. "
        "Never dump long essays into Slack."
    )

    def blurb_for_state(self, state_name: str, summary: str, link: str = "") -> str:
        system = (
            f"You are the Slack Communicator.\n{self.charter}\n"
            "Return JSON {blurb, trust_line}. blurb <= 15 words. Tag slack_blurb."
        )
        user = f"State ended: {state_name}\nSummary: {summary}\nLink: {link}"
        data = self.llm.chat_json(system, user)
        blurb = str(data.get("blurb") or summary)
        words = blurb.split()
        if len(words) > 18:
            blurb = " ".join(words[:15]) + "…"
        if link:
            return f"{blurb}\n{link}"
        return blurb

    def act(self, ctx: RoleContext) -> dict[str, Any]:
        app_url = ctx.session.app_url or ctx.session.artifacts.get("app_url", "")
        gist_url = ""
        if ctx.session.gist:
            gist_url = ctx.session.gist.url or ctx.session.gist.local_path
        blurb = self.blurb_for_state(
            "ship_and_narrate",
            f"Shipped {ctx.session.title or ctx.session.slug}",
            gist_url or app_url,
        )
        final = (
            f"{blurb}\n"
            f"App: {app_url}\n"
            f"Build notes: {gist_url}"
        )
        ctx.session.artifacts["final_slack_message"] = final
        return {
            "app_url": app_url,
            "gist_url": gist_url,
            "gist_path": ctx.session.gist.local_path if ctx.session.gist else "",
            "message": final,
        }
