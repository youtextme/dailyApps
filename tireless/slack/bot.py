"""Slack ingress for dailyApps — stateful, parallel (max 20), thread-aware."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from tireless.config import MAX_PARALLEL_SESSIONS, SlackConfig
from tireless.llm.client import LocalLLM, get_llm
from tireless.loops.engine import ObjectiveLoopEngine
from tireless.models import Session, SessionStatus
from tireless.session_store import SessionStore, get_store

log = logging.getLogger(__name__)


class SlackBot:
    """
    Message handling:
    - New top-level message → new session + objective loops
    - Thread reply → reload prior session context and iterate
    - Cap concurrent RUNNING sessions at MAX_PARALLEL_SESSIONS (default 20)
    """

    def __init__(
        self,
        config: SlackConfig | None = None,
        store: SessionStore | None = None,
        llm: LocalLLM | None = None,
        *,
        dry_run: bool = False,
    ) -> None:
        self.config = config or SlackConfig.from_env()
        self.store = store or get_store()
        self.llm = llm or get_llm()
        self.dry_run = dry_run
        self._executor = ThreadPoolExecutor(max_workers=MAX_PARALLEL_SESSIONS)
        self._lock = threading.Lock()
        self._app = None
        self._posted: list[dict[str, Any]] = []  # for tests / dry-run

    def handle_message(
        self,
        *,
        channel: str,
        user: str,
        text: str,
        ts: str,
        thread_ts: str | None = None,
    ) -> Session | None:
        text = (text or "").strip()
        if not text:
            return None

        # Ignore bot's own messages if tagged
        if text.startswith("*Loop ") and "·" in text:
            return None

        parent_ts = thread_ts or ts
        existing = self.store.find_for_message(channel, thread_ts, ts)

        if existing and thread_ts and thread_ts != ts:
            # Follow-up in thread — reload context
            self._post(channel, parent_ts, "Saw the follow-up — reloading the earlier session context.")
            fut = self._executor.submit(self._run_feedback, existing.id, text)
            fut.add_done_callback(self._log_future)
            return existing

        # New root message
        if self.store.active_count() >= MAX_PARALLEL_SESSIONS:
            self._post(
                channel,
                parent_ts,
                f"At capacity ({MAX_PARALLEL_SESSIONS} parallel runs). Try again in a bit.",
            )
            return None

        session = Session(
            channel=channel,
            thread_ts=parent_ts,
            user_id=user,
            root_prompt=text,
            status=SessionStatus.ACKED,
        )
        self.store.save(session)
        self._post(
            channel,
            parent_ts,
            "Read your message — starting the objective loop (stateful, not a one-shot).",
        )
        fut = self._executor.submit(self._run_new, session.id)
        fut.add_done_callback(self._log_future)
        return session

    def _run_new(self, session_id: str) -> None:
        session = self.store.get(session_id)
        if not session:
            return
        engine = ObjectiveLoopEngine(
            store=self.store,
            llm=self.llm,
            notify=lambda s, msg: self._post(s.channel, s.thread_ts, msg),
        )
        engine.start(session)

    def _run_feedback(self, session_id: str, feedback: str) -> None:
        session = self.store.get(session_id)
        if not session:
            return
        engine = ObjectiveLoopEngine(
            store=self.store,
            llm=self.llm,
            notify=lambda s, msg: self._post(s.channel, s.thread_ts, msg),
        )
        engine.continue_with_feedback(session, feedback)

    def _post(self, channel: str, thread_ts: str, text: str) -> None:
        payload = {"channel": channel, "thread_ts": thread_ts, "text": text}
        self._posted.append(payload)
        if self.dry_run or not self.config.configured:
            log.info("[slack-dry] %s", payload)
            return
        try:
            from slack_sdk import WebClient

            client = WebClient(token=self.config.bot_token)
            client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=text)
        except Exception as exc:  # noqa: BLE001
            log.warning("slack post failed: %s", exc)

    def _log_future(self, fut) -> None:
        exc = fut.exception()
        if exc:
            log.error("worker failed: %s", exc)

    def serve(self) -> None:
        """Socket Mode server (requires SLACK_BOT_TOKEN + SLACK_APP_TOKEN)."""
        if not self.config.configured:
            raise SystemExit(
                "Slack is not configured. Set SLACK_BOT_TOKEN and SLACK_APP_TOKEN "
                "(Socket Mode) or use --run-prompt for local loops."
            )
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler

        app = App(token=self.config.bot_token, signing_secret=self.config.signing_secret or None)
        bot = self

        @app.event("message")
        def on_message(event, say):  # noqa: ANN001
            if event.get("subtype") or event.get("bot_id"):
                return
            bot.handle_message(
                channel=event.get("channel", ""),
                user=event.get("user", ""),
                text=event.get("text", ""),
                ts=event.get("ts", ""),
                thread_ts=event.get("thread_ts"),
            )

        self._app = app
        log.info("Starting Slack Socket Mode bot for dailyApps…")
        SocketModeHandler(app, self.config.app_token).start()


def create_bot(*, dry_run: bool = False) -> SlackBot:
    return SlackBot(dry_run=dry_run)
