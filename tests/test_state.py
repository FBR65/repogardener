"""Tests for state tracker — verhindert doppelte/konfliktäre Änderungen."""
import json
import hashlib
from pathlib import Path
from repogardener.state import StateTracker


def hash_value(val: str) -> str:
    return hashlib.sha256(val.strip().lower().encode()).hexdigest()


# ── should_apply ──────────────────────────────────────────────

def test_new_field_returns_true():
    """Neues Feld ohne State → apply."""
    st = StateTracker()
    ok, reason = st.should_apply("repo-a", "description", None, "A test repo")
    assert ok is True
    assert reason == "new"


def test_same_proposal_already_applied():
    """Exakt gleicher Vorschlag wie letztes Mal → skip."""
    st = StateTracker()
    st.mark_applied("repo-a", "description", "A test repo")
    ok, reason = st.should_apply("repo-a", "description", "A test repo", "A test repo")
    assert ok is False
    assert reason == "already_applied"


def test_current_unset_proposal_different():
    """Current=None, Proposal anders als letztes Mal → apply (weil current None)."""
    st = StateTracker()
    st.mark_applied("repo-a", "description", "Old desc")
    ok, reason = st.should_apply("repo-a", "description", None, "New desc")
    assert ok is True
    assert reason == "changed"


def test_user_modified_field():
    """User hat Feld auf GitHub geändert → warn, nicht überschreiben."""
    st = StateTracker()
    st.mark_applied("repo-a", "description", "Our generated desc")
    # current (von GitHub) ≠ was wir applied haben → user-modified
    ok, reason = st.should_apply(
        "repo-a", "description", "User changed this manually", "Better desc"
    )
    assert ok is False
    assert reason == "user_modified"


def test_current_matches_our_last_proposal_different():
    """User hat nichts geändert, aber unser neuer Vorschlag ist anders → apply."""
    st = StateTracker()
    st.mark_applied("repo-a", "description", "Old generated desc")
    ok, reason = st.should_apply(
        "repo-a", "description", "Old generated desc", "New better desc"
    )
    assert ok is True
    assert reason == "changed"


# ── Persistence ───────────────────────────────────────────────

def test_save_and_load(tmp_path):
    """State wird korrekt gespeichert und geladen."""
    state_file = tmp_path / "state.json"
    st = StateTracker(state_file)
    st.mark_applied("repo-a", "description", "Some desc")
    st.mark_applied("repo-a", "topics", "python, cli")
    st.save()

    # Neuer Tracker lädt den alten State
    st2 = StateTracker(state_file)
    ok, reason = st2.should_apply("repo-a", "description", "Some desc", "Some desc")
    assert ok is False
    assert reason == "already_applied"


def test_mark_applied_updates_state():
    """mark_applied überschreibt den vorherigen Wert."""
    st = StateTracker()
    st.mark_applied("repo-a", "description", "Version 1")
    st.mark_applied("repo-a", "description", "Version 2")
    ok, reason = st.should_apply("repo-a", "description", "Version 2", "Version 2")
    assert ok is False
    assert reason == "already_applied"


def test_get_summary():
    """get_summary liefert lesbare Statistik."""
    st = StateTracker()
    st.mark_applied("repo-a", "description", "desc-a")
    st.mark_applied("repo-a", "topics", "t1, t2")
    st.mark_applied("repo-b", "description", "desc-b")
    summary = st.get_summary()
    assert "repo-a" in summary
    assert "repo-b" in summary
    assert summary["repo-a"] == 2  # description + topics
