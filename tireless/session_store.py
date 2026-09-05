"""Persistent stateful sessions keyed by Slack thread."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from tireless.config import SESSIONS_DIR, ensure_dirs
from tireless.models import Session, SessionStatus


class SessionStore:
    """File-backed session store with in-memory index for concurrency caps."""

    def __init__(self, root: Path | None = None) -> None:
        ensure_dirs()
        self.root = root or SESSIONS_DIR
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._by_thread: dict[str, str] = {}
        self._load_index()

    def _thread_key(self, channel: str, thread_ts: str) -> str:
        return f"{channel}:{thread_ts}"

    def _path(self, session_id: str) -> Path:
        return self.root / f"{session_id}.json"

    def _load_index(self) -> None:
        for path in self.root.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                channel = data.get("channel") or ""
                thread_ts = data.get("thread_ts") or ""
                if channel and thread_ts:
                    self._by_thread[self._thread_key(channel, thread_ts)] = data["id"]
            except Exception:  # noqa: BLE001
                continue

    def save(self, session: Session) -> Session:
        with self._lock:
            session.touch()
            self._path(session.id).write_text(
                session.model_dump_json(indent=2),
                encoding="utf-8",
            )
            if session.channel and session.thread_ts:
                self._by_thread[self._thread_key(session.channel, session.thread_ts)] = session.id
            return session

    def get(self, session_id: str) -> Session | None:
        path = self._path(session_id)
        if not path.exists():
            return None
        return Session.model_validate_json(path.read_text(encoding="utf-8"))

    def get_by_thread(self, channel: str, thread_ts: str) -> Session | None:
        with self._lock:
            sid = self._by_thread.get(self._thread_key(channel, thread_ts))
        if not sid:
            # thread_ts for a reply is the parent; also try exact
            return None
        return self.get(sid)

    def find_for_message(self, channel: str, thread_ts: str | None, ts: str) -> Session | None:
        """Reload session for a thread reply; root messages create new sessions elsewhere."""
        if thread_ts and thread_ts != ts:
            found = self.get_by_thread(channel, thread_ts)
            if found:
                return found
        return self.get_by_thread(channel, ts)

    def active_count(self) -> int:
        with self._lock:
            count = 0
            for sid in set(self._by_thread.values()):
                session = self.get(sid)
                if session and session.status in {SessionStatus.ACKED, SessionStatus.RUNNING}:
                    count += 1
            return count

    def list_sessions(self) -> list[Session]:
        sessions: list[Session] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                sessions.append(Session.model_validate_json(path.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                continue
        return sessions


_STORE: SessionStore | None = None


def get_store() -> SessionStore:
    global _STORE
    if _STORE is None:
        _STORE = SessionStore()
    return _STORE
