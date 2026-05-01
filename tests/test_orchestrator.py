"""Tests for pipeline orchestrator."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from repogardener.orchestrator import run_pipeline
from repogardener.state import StateTracker


@patch("repogardener.orchestrator.list_repos")
@patch("repogardener.orchestrator.GithubClient")
def test_run_pipeline_returns_results_and_report(mock_client_cls, mock_list):
    """Pipeline returns (results, report) tuple."""
    mock_list.return_value = [
        {"name": "repo1", "full_name": "FBR65/repo1", "fork": False, "archived": False,
         "description": None, "topics": []},
    ]
    mock_client_cls.return_value = MagicMock()

    results, report = run_pipeline("FBR65", dry_run=True, state_file=None)
    assert isinstance(results, list)
    assert "RepoGardener Report" in report
    assert len(results) == 1


@patch("repogardener.orchestrator.list_repos")
@patch("repogardener.orchestrator.GithubClient")
def test_run_pipeline_skips_forks_and_archived(mock_client_cls, mock_list):
    """Forks and archived repos are filtered out."""
    mock_list.return_value = [
        {"name": "active", "full_name": "FBR65/active", "fork": False, "archived": False,
         "description": "x", "topics": ["python"]},
        {"name": "forked", "full_name": "FBR65/forked", "fork": True, "archived": False,
         "description": "x", "topics": []},
        {"name": "old", "full_name": "FBR65/old", "fork": False, "archived": True,
         "description": "x", "topics": []},
    ]
    mock_client_cls.return_value = MagicMock()

    results, report = run_pipeline("FBR65", dry_run=True, state_file=None)
    assert len(results) == 1
    assert results[0]["name"] == "active"


@patch("repogardener.orchestrator.list_repos")
@patch("repogardener.orchestrator.GithubClient")
def test_run_pipeline_respects_state_already_applied(mock_client_cls, mock_list, tmp_path):
    """Repos with state already applied are skipped."""
    state_file = tmp_path / "state.json"
    # Pre-seed state: description was already applied
    StateTracker(state_file).mark_applied("repo1", "description", "already has this")
    StateTracker(state_file).save()

    mock_list.return_value = [
        {"name": "repo1", "full_name": "FBR65/repo1", "fork": False, "archived": False,
         "description": "already has this", "topics": ["python"]},
    ]
    mock_client_cls.return_value = MagicMock()

    results, report = run_pipeline("FBR65", dry_run=True, state_file=state_file)
    # Description already matches applied state → no change
    assert results[0]["has_changes"] is False


@patch("repogardener.orchestrator.list_repos")
@patch("repogardener.orchestrator.GithubClient")
def test_run_pipeline_user_modified_respected(mock_client_cls, mock_list, tmp_path):
    """User-modified fields are not overwritten."""
    state_file = tmp_path / "state.json"
    # Pre-seed: we applied "generated desc" earlier
    StateTracker(state_file).mark_applied("repo1", "description", "generated desc")
    StateTracker(state_file).save()

    # User changed it on GitHub to their own text
    mock_list.return_value = [
        {"name": "repo1", "full_name": "FBR65/repo1", "fork": False, "archived": False,
         "description": "User wrote this manually", "topics": ["python"]},  # != "generated desc"
    ]
    mock_client_cls.return_value = MagicMock()

    results, report = run_pipeline("FBR65", dry_run=True, state_file=state_file)
    # Should NOT propose a new description — user owns it now
    assert "new_description" not in results[0]

