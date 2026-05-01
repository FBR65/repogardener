"""Tests for GitHub scanner functionality."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from repogardener.scanner import list_repos, repo_summary, clone_all


class FakeResponse:
    """Minimal mock for urllib response."""
    def __init__(self, data, code=200):
        self._data = json.dumps(data).encode()
        self.code = code

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_repo_summary_extracts_key_fields():
    repo = {
        "name": "test-repo",
        "full_name": "FBR65/test-repo",
        "description": "A test repo",
        "topics": ["python", "cli"],
        "language": "Python",
        "default_branch": "master",
        "clone_url": "https://github.com/FBR65/test-repo.git",
        "pushed_at": "2026-01-01T00:00:00Z",
        "archived": False,
        "fork": False,
    }
    result = repo_summary(repo)
    assert result["name"] == "test-repo"
    assert result["full_name"] == "FBR65/test-repo"
    assert result["description"] == "A test repo"
    assert result["topics"] == ["python", "cli"]
    assert result["language"] == "Python"
    assert result["default_branch"] == "master"
    assert result["clone_url"] == "https://github.com/FBR65/test-repo.git"
    assert result["pushed_at"] == "2026-01-01T00:00:00Z"
    assert result["archived"] is False
    assert result["fork"] is False


def test_repo_summary_handles_missing_fields():
    repo = {"name": "minimal", "full_name": "FBR65/minimal"}
    result = repo_summary(repo)
    assert result["name"] == "minimal"
    assert result["description"] is None
    assert result["topics"] == []
    assert result["language"] is None


# ── clone_all tests ──────────────────────────────────────────────

SAMPLE_REPO = {
    "name": "my-project",
    "clone_url": "https://github.com/FBR65/my-project.git",
    "fork": False,
    "archived": False,
}
FORK_REPO = {
    **SAMPLE_REPO,
    "name": "forked-project",
    "fork": True,
    "archived": False,
}
ARCHIVED_REPO = {
    **SAMPLE_REPO,
    "name": "old-project",
    "fork": False,
    "archived": True,
}
NO_URL_REPO = {
    "name": "no-url-project",
    "fork": False,
    "archived": False,
}


def test_clone_all_skips_forks(tmp_path):
    """Forks should be skipped when skip_forks=True."""
    repos = [FORK_REPO, SAMPLE_REPO]
    with patch("repogardener.scanner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = clone_all(repos, workspace=tmp_path, skip_forks=True)
    assert len(result) == 1
    assert result[0].name == "my-project"


def test_clone_all_skips_archived(tmp_path):
    """Archived repos should be skipped when skip_archived=True."""
    repos = [ARCHIVED_REPO, SAMPLE_REPO]
    with patch("repogardener.scanner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = clone_all(repos, workspace=tmp_path, skip_archived=True)
    assert len(result) == 1
    assert result[0].name == "my-project"


def test_clone_all_includes_forks_when_enabled(tmp_path):
    """Forks should be included when skip_forks=False."""
    repos = [FORK_REPO, SAMPLE_REPO]
    with patch("repogardener.scanner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = clone_all(repos, workspace=tmp_path, skip_forks=False)
    assert len(result) == 2


def test_clone_all_skips_no_clone_url(tmp_path):
    """Repos without a clone_url should be skipped."""
    repos = [NO_URL_REPO, SAMPLE_REPO]
    with patch("repogardener.scanner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = clone_all(repos, workspace=tmp_path, skip_forks=False)
    assert len(result) == 1
    assert result[0].name == "my-project"


def test_clone_all_runs_git_clone(tmp_path):
    """Verify the git clone command is invoked with expected args."""
    repos = [SAMPLE_REPO]
    with patch("repogardener.scanner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        clone_all(repos, workspace=tmp_path)
    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert "clone" in call_args
    assert "--depth" in call_args
    assert "1" in call_args
    assert SAMPLE_REPO["clone_url"] in call_args


def test_clone_all_pulls_existing_repo(tmp_path):
    """Existing repos should trigger git pull, not git clone."""
    dest = tmp_path / SAMPLE_REPO["name"]
    dest.mkdir()
    repos = [SAMPLE_REPO]
    with patch("repogardener.scanner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        clone_all(repos, workspace=tmp_path, skip_forks=False)
    call_args = mock_run.call_args[0][0]
    assert "pull" in call_args
    assert "clone" not in call_args


def test_clone_all_creates_workspace(tmp_path):
    """Workspace directory should be created if it doesn't exist."""
    ws = tmp_path / "not-yet-created"
    repos = [SAMPLE_REPO]
    with patch("repogardener.scanner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        clone_all(repos, workspace=ws)
    assert ws.exists()
