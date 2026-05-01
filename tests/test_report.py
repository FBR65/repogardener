"""Tests for report generator."""
import pytest
from pathlib import Path
from repogardener.report import generate_report


def test_generate_report_empty():
    """Empty actions list produces minimal report."""
    result = generate_report([])
    assert "RepoGardener Report" in result
    assert "0 repos" in result
    assert "0 repos have pending changes" in result


def test_generate_report_with_changes():
    """Report shows pending changes correctly."""
    actions = [
        {
            "name": "test-repo",
            "full_name": "FBR65/test-repo",
            "current_description": None,
            "current_topics": [],
            "has_changes": True,
            "new_description": "A test repository",
            "new_topics": ["python", "cli"],
            "languages": ["python"],
        },
        {
            "name": "unchanged",
            "full_name": "FBR65/unchanged",
            "current_description": "Already has description",
            "current_topics": ["python"],
            "has_changes": False,
        },
    ]
    result = generate_report(actions)
    assert "2 repos" in result
    assert "1 repos have pending changes" in result
    assert "test-repo" in result
    assert "unchanged" in result
    assert "A test repository" in result
    assert "python" in result
    assert "cli" in result


def test_generate_report_saves_to_file(tmp_path):
    """Report can be saved to a file."""
    output = tmp_path / "report.md"
    actions = [{"name": "x", "has_changes": False}]
    result = generate_report(actions, output_path=str(output))
    assert output.exists()
    assert "RepoGardener Report" in output.read_text()
    assert "RepoGardener Report" in result


def test_generate_report_with_stale_deps():
    """Stale deps column shows warnings."""
    actions = [
        {
            "name": "old-project",
            "has_changes": True,
            "stale_deps": [("requests", ">=2.20", "2.32", 200), ("flask", ">=2.0", "3.1", 150)],
        }
    ]
    result = generate_report(actions)
    assert "⚠️" in result
    assert "old-project" in result
