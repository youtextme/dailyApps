"""CLI entrypoints for dailyApps / tireless."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from tireless.config import ensure_dirs
from tireless.llm.client import LocalLLM
from tireless.loops.engine import ObjectiveLoopEngine
from tireless.models import Session, SessionStatus
from tireless.session_store import SessionStore, get_store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tireless", description="dailyApps stateful loop engine")
    parser.add_argument("--setup-dailyapps", action="store_true", help="Create data dirs and verify layout")
    parser.add_argument("--serve-slack-bot", action="store_true", help="Run Slack Socket Mode bot")
    parser.add_argument("--dailyapps-live-tests", action="store_true", help="Run package live/self tests")
    parser.add_argument("--run-prompt", type=str, default="", help="Run one prompt through the loop engine (local)")
    parser.add_argument("--feedback", type=str, default="", help="Feedback for an existing --session-id")
    parser.add_argument("--session-id", type=str, default="", help="Session id for feedback continuation")
    parser.add_argument("--offline", action="store_true", help="Force offline LLM fallbacks")
    parser.add_argument("--data-dir", type=str, default="", help="Override TIRELESS_DATA_DIR")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.data_dir:
        import os

        os.environ["TIRELESS_DATA_DIR"] = args.data_dir

    ensure_dirs()

    if args.setup_dailyapps:
        return cmd_setup()
    if args.dailyapps_live_tests:
        return cmd_live_tests(offline=args.offline)
    if args.serve_slack_bot:
        return cmd_serve_slack(offline=args.offline)
    if args.feedback and args.session_id:
        return cmd_feedback(args.session_id, args.feedback, offline=args.offline)
    if args.run_prompt:
        return cmd_run_prompt(args.run_prompt, offline=args.offline)

    parser.print_help()
    return 0


def cmd_setup() -> int:
    from tireless.config import APPS_DIR, GISTS_DIR, REPO_ROOT, SESSIONS_DIR, TEMPLATES_DIR
    from tireless.dailyapps.catalog import refresh_catalog

    ensure_dirs()
    APPS_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    refresh_catalog(REPO_ROOT)
    print("dailyApps setup OK")
    print(f"  repo:      {REPO_ROOT}")
    print(f"  apps:      {APPS_DIR}")
    print(f"  sessions:  {SESSIONS_DIR}")
    print(f"  gists:     {GISTS_DIR}")
    return 0


def cmd_serve_slack(*, offline: bool) -> int:
    from tireless.slack.bot import SlackBot

    llm = LocalLLM(offline=offline)
    bot = SlackBot(llm=llm, dry_run=False)
    bot.serve()
    return 0


def cmd_run_prompt(prompt: str, *, offline: bool) -> int:
    store = get_store()
    llm = LocalLLM(offline=offline)
    messages: list[str] = []

    def notify(session: Session, msg: str) -> None:
        messages.append(msg)
        print(f"[state] {msg}\n")

    session = Session(root_prompt=prompt, channel="local", thread_ts="local")
    store.save(session)
    engine = ObjectiveLoopEngine(store=store, llm=llm, notify=notify)
    session = engine.start(session)
    print("---")
    print(f"session:   {session.id}")
    print(f"objective: {session.objective_id}")
    print(f"status:    {session.status.value}")
    print(f"app:       {session.app_url}")
    if session.gist:
        print(f"gist:      {session.gist.url or session.gist.local_path}")
    if session.error:
        print(f"error:     {session.error[:500]}")
        return 1
    return 0


def cmd_feedback(session_id: str, feedback: str, *, offline: bool) -> int:
    store = get_store()
    session = store.get(session_id)
    if not session:
        print(f"session not found: {session_id}", file=sys.stderr)
        return 1
    llm = LocalLLM(offline=offline)

    def notify(session: Session, msg: str) -> None:
        print(f"[state] {msg}\n")

    engine = ObjectiveLoopEngine(store=store, llm=llm, notify=notify)
    session = engine.continue_with_feedback(session, feedback)
    print(f"status: {session.status.value}")
    print(f"app:    {session.app_url}")
    return 0 if session.status != SessionStatus.FAILED else 1


def cmd_live_tests(*, offline: bool) -> int:
    """Self-check used by --dailyapps-live-tests."""
    import os
    import tempfile

    from tireless.dailyapps.quality_gate import run_quality_gate
    from tireless.slack.bot import SlackBot
    import tireless.dailyapps.gist as gist_mod
    import tireless.dailyapps.shipper as shipper_mod

    failures = 0

    # quality gate rejects thin stub
    thin = "<!DOCTYPE html><html><body><h1>x</h1></body></html>"
    report = run_quality_gate(thin)
    if report.ok:
        print("FAIL: thin stub should not pass quality gate")
        failures += 1
    else:
        print("OK: quality gate rejects thin stub")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        os.environ["TIRELESS_DATA_DIR"] = tmp
        apps = tmp_path / "apps"
        gists = tmp_path / "gists"
        apps.mkdir()
        gists.mkdir()
        old_apps, old_gists = shipper_mod.APPS_DIR, gist_mod.GISTS_DIR
        shipper_mod.APPS_DIR = apps
        gist_mod.GISTS_DIR = gists
        try:
            store = SessionStore(root=tmp_path / "sessions")
            llm = LocalLLM(offline=True)
            bot = SlackBot(store=store, llm=llm, dry_run=True)
            session = bot.handle_message(
                channel="C1",
                user="U1",
                text="build a tip calculator that splits bills",
                ts="1.0",
            )
            assert session is not None
            bot._executor.shutdown(wait=True)
            session = store.get(session.id)
            assert session is not None
            if not session.app_url and not session.artifacts.get("html"):
                print(
                    f"FAIL: expected shipped app or html, status={session.status} "
                    f"err={(session.error or '')[:300]}"
                )
                failures += 1
            else:
                print(f"OK: loop run status={session.status.value} app={session.app_url}")

            bot2 = SlackBot(store=store, llm=llm, dry_run=True)
            bot2.handle_message(
                channel="C1",
                user="U1",
                text="make tip buttons larger and add dark mode",
                ts="2.0",
                thread_ts="1.0",
            )
            bot2._executor.shutdown(wait=True)
            session = store.get(session.id)
            assert session is not None
            if "make tip buttons larger" not in " ".join(session.feedback_history):
                print("FAIL: feedback not attached to reloaded session")
                failures += 1
            else:
                print("OK: thread feedback reloaded session context")
        finally:
            shipper_mod.APPS_DIR = old_apps
            gist_mod.GISTS_DIR = old_gists

    if failures:
        print(f"{failures} live test failure(s)")
        return 1
    print("dailyapps live tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
