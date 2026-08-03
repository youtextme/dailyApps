"""Stateful objective loop engine — loop engineering over prompt engineering."""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone
from typing import Callable

from tireless.dailyapps.gist import build_gist_markdown, persist_gist
from tireless.dailyapps.shipper import ship_session
from tireless.llm.client import LocalLLM, get_llm
from tireless.models import (
    ProcessingState,
    RoleName,
    Session,
    SessionStatus,
    StateStatus,
    utcnow,
)
from tireless.roles.base import RoleContext
from tireless.roles.registry import get_role
from tireless.roles.slack_communicator import SlackCommunicator
from tireless.session_store import SessionStore, get_store

log = logging.getLogger(__name__)

NotifyFn = Callable[[Session, str], None]


class ObjectiveLoopEngine:
    """
    Processing is stateful.

    Loop 1 (via Loop Builder + OKR Creator) sets the stage for all later loops:
    states, meaning of done, and how status updates should be read.
    Every completed state emits a short Slack update.
    """

    def __init__(
        self,
        store: SessionStore | None = None,
        llm: LocalLLM | None = None,
        notify: NotifyFn | None = None,
    ) -> None:
        self.store = store or get_store()
        self.llm = llm or get_llm()
        self.notify = notify or (lambda _session, _msg: None)

    def start(self, session: Session, *, resume: bool = False) -> Session:
        session.status = SessionStatus.RUNNING
        self.store.save(session)
        if not resume:
            self._emit(
                session,
                "Read your note — kicking off the objective loop now.",
            )
        try:
            self._ensure_stage(session)
            for loop in list(session.loops):
                if loop.status == StateStatus.DONE:
                    continue
                self._run_loop(session, loop.index)
            # After build/test loops, ship + gist if needed
            self._finalize(session)
            session.status = SessionStatus.WAITING_FEEDBACK
            self.store.save(session)
            final = session.artifacts.get("final_slack_message") or (
                f"Done. App: {session.app_url}"
            )
            self._emit(session, final)
        except Exception as exc:  # noqa: BLE001
            log.exception("session %s failed", session.id)
            session.status = SessionStatus.FAILED
            session.error = f"{exc}\n{traceback.format_exc()}"
            self.store.save(session)
            self._emit(session, "Hit a snag mid-loop — parked details in the session log.")
        return session

    def continue_with_feedback(self, session: Session, feedback: str) -> Session:
        """Reload prior session context and iterate — never a cold unknown prompt."""
        session.append_feedback(feedback)
        session.status = SessionStatus.RUNNING
        session.error = ""
        # Keep objective_id / slug / digest; reset later loops for rebuild
        session.context_digest = (
            f"Reloaded session {session.id} / objective {session.objective_id}. "
            f"Prior goal: {session.objective.end_goal if session.objective else session.root_prompt}. "
            f"New feedback: {feedback}"
        )
        self.store.save(session)
        self._emit(
            session,
            "Got the follow-up — reloading the same session context to iterate.",
        )

        # Re-stage lightly if loops missing; otherwise mark build/test/ship pending again
        if not session.loops:
            self._ensure_stage(session)
        else:
            for loop in session.loops:
                if loop.owner_role in {
                    RoleName.UX_CX_BUILDER,
                    RoleName.TEST_ENGINEER,
                    RoleName.SLACK_COMMUNICATOR,
                    RoleName.BARBARA_MINTO,
                }:
                    loop.status = StateStatus.PENDING
                    loop.summary = ""
        return self.start(session, resume=True)

    def _ensure_stage(self, session: Session) -> None:
        """Loop engineering entry: Loop Builder defines the whole plan first."""
        if session.loops:
            return
        self._run_role_state(
            session,
            loop_index=0,
            state_name="stage_setting",
            role_name=RoleName.LOOP_BUILDER,
            purpose="Set the stage: loops, states, exit criteria, status semantics",
        )
        if not session.loops:
            raise RuntimeError("Stage setting failed to produce loops")

    def _run_loop(self, session: Session, loop_index: int) -> None:
        loop = next(l for l in session.loops if l.index == loop_index)
        loop.status = StateStatus.RUNNING
        self.store.save(session)

        role_name = loop.owner_role
        artifacts = self._run_role_state(
            session,
            loop_index=loop.index,
            state_name=loop.name,
            role_name=role_name,
            purpose=loop.purpose,
        )

        # Special: after UX build, ship early so production tests can see files
        if role_name == RoleName.UX_CX_BUILDER and session.artifacts.get("html"):
            try:
                ship_info = ship_session(session)
                artifacts.update(ship_info)
                gist = persist_gist(session, build_gist_markdown(session))
                artifacts["gist_url"] = gist.url
                artifacts["gist_path"] = gist.local_path
            except Exception as exc:  # noqa: BLE001
                log.warning("ship after UX failed: %s", exc)
                artifacts["ship_error"] = str(exc)

        if role_name == RoleName.SLACK_COMMUNICATOR:
            if not session.app_url and session.artifacts.get("html"):
                ship_session(session)
            gist = persist_gist(session, build_gist_markdown(session))
            artifacts["gist_url"] = gist.url
            artifacts["gist_path"] = gist.local_path
            artifacts["app_url"] = session.app_url

        role = get_role(role_name, self.llm)
        checked = role.verify(loop.exit_criteria, {**session.artifacts, **artifacts})
        loop.exit_criteria = checked
        unmet = [c for c in checked if not c.met]
        if unmet and role_name != RoleName.LOOP_BUILDER:
            # One recovery attempt for the same role
            self._emit(
                session,
                f"Loop {loop.index} missed exit criteria — retrying once with evidence.",
            )
            artifacts = self._run_role_state(
                session,
                loop_index=loop.index,
                state_name=f"{loop.name}_retry",
                role_name=role_name,
                purpose=f"Retry: {loop.purpose}",
            )
            if role_name == RoleName.UX_CX_BUILDER and session.artifacts.get("html"):
                ship_session(session)
            checked = role.verify(loop.exit_criteria, {**session.artifacts, **artifacts})
            loop.exit_criteria = checked
            unmet = [c for c in checked if not c.met]

        loop.artifacts = artifacts
        if unmet:
            loop.status = StateStatus.FAILED
            loop.summary = "Failed exit criteria: " + "; ".join(c.description for c in unmet)
            self.store.save(session)
            raise RuntimeError(loop.summary)

        loop.status = StateStatus.DONE
        loop.summary = f"Completed with {len(checked)} exit criteria met"
        self.store.save(session)

    def _run_role_state(
        self,
        session: Session,
        *,
        loop_index: int,
        state_name: str,
        role_name: RoleName,
        purpose: str,
    ) -> dict:
        state = ProcessingState(
            loop_index=loop_index,
            name=state_name,
            role=role_name,
            status=StateStatus.RUNNING,
            started_at=utcnow(),
        )
        session.states.append(state)
        self.store.save(session)

        role = get_role(role_name, self.llm)
        ctx = RoleContext(session=session, llm=self.llm)
        # Consultative think step (behavior), then act
        _thought = role.think(ctx)
        session.artifacts.setdefault("thoughts", []).append(
            {"role": role_name.value, "state": state_name, "thought": _thought[:2000]}
        )
        artifacts = role.act(ctx) or {}
        session.artifacts.update({k: v for k, v in artifacts.items() if k != "html" or v})
        if "html" in artifacts:
            session.artifacts["html"] = artifacts["html"]

        communicator = SlackCommunicator(self.llm)
        link = ""
        if session.gist:
            link = session.gist.url or session.gist.local_path
        elif session.app_url:
            link = session.app_url
        blurb = communicator.blurb_for_state(state_name, purpose, link)
        state.slack_blurb = blurb
        state.output_preview = purpose
        state.status = StateStatus.DONE
        state.ended_at = datetime.now(timezone.utc)
        state.detail_path = link
        self.store.save(session)
        self._emit(session, f"*Loop {loop_index or 1} · {state_name}*\n{blurb}")
        return artifacts

    def _finalize(self, session: Session) -> None:
        if session.artifacts.get("html") and not session.app_url:
            ship_session(session)
        gist = persist_gist(session, build_gist_markdown(session))
        session.artifacts["gist_url"] = gist.url
        session.artifacts["gist_path"] = gist.local_path
        # Ensure communicator role produced a final message
        if not session.artifacts.get("final_slack_message"):
            msg = SlackCommunicator(self.llm).act(
                RoleContext(session=session, llm=self.llm)
            )
            session.artifacts["final_slack_message"] = msg.get("message", "")
        self.store.save(session)

    def _emit(self, session: Session, message: str) -> None:
        try:
            self.notify(session, message)
        except Exception as exc:  # noqa: BLE001
            log.warning("notify failed: %s", exc)
