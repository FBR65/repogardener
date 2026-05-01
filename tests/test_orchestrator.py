"""Tests for pipeline orchestrator."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from repogardener.orchestrator import run_pipeline
from repogardener.scanner import list_repos


@patch("repogardener.orchestrator.list_repos")
@patch("repogardener.orchestrator.GithubClient")
def test_run_pipeline_returns_results_and_report(mock_client_cls, mock_list):
    """Pipeline returns (results, report) tuple."""
    mock_list.return_value = [
        {"name": "repo1", "full_name": "FBR65/repo1", "fork": False, "archived": False,
         "description": None, "topics": []},
    ]
    mock_client_cls.return_value = MagicMock()

    results, report = run_pipeline("FBR65", dry_run=True)
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

    results, report = run_pipeline("FBR65", dry_run=True)
    assert len(results) == 1
    assert results[0]["name"] == "active"
