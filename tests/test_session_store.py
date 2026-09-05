from tireless.models import Session
from tireless.session_store import SessionStore


def test_thread_lookup_and_feedback(tmp_path):
    store = SessionStore(root=tmp_path)
    s = Session(root_prompt="build a quiz", channel="C", thread_ts="10.0")
    store.save(s)
    found = store.find_for_message("C", "10.0", "11.0")
    assert found is not None
    assert found.id == s.id
    found.append_feedback("add dark mode")
    store.save(found)
    again = store.get(s.id)
    assert again.feedback_history == ["add dark mode"]


def test_active_count(tmp_path):
    store = SessionStore(root=tmp_path)
    a = Session(root_prompt="a", channel="C", thread_ts="1")
    store.save(a)
    assert store.active_count() == 1
