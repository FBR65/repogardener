"""Tests for GitHub authentication."""
import os
import pytest
from repogardener.auth import GithubClient, AuthError


def test_github_client_no_token_raises(monkeypatch):
    """When no token sources exist, AuthError is raised."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(AuthError, match="GITHUB_TOKEN"):
        GithubClient(env_file="/nonexistent/.env", credential_file="/nonexistent/.git-credentials")


def test_github_client_from_token():
    client = GithubClient(token="fake-token")
    assert client.token == "fake-token"
    assert "Authorization" in client.headers
    assert "token fake-token" in client.headers["Authorization"]


def test_github_client_headers_format():
    client = GithubClient(token="ghp_test123")
    headers = client.headers
    assert headers["Authorization"] == "token ghp_test123"
    assert headers["Accept"] == "application/vnd.github+json"


def test_github_client_from_env(monkeypatch):
    """Token is loaded from GITHUB_TOKEN env var."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_env_token")
    client = GithubClient(env_file="/nonexistent/.env", credential_file="/nonexistent/.git-credentials")
    assert client.token == "ghp_env_token"


def test_github_client_from_git_credentials(monkeypatch, tmp_path):
    """Token is extracted from ~/.git-credentials."""
    cred_file = tmp_path / ".git-credentials"
    cred_file.write_text("https://user:ghp_cred_token@github.com\n")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    client = GithubClient(env_file="/nonexistent/.env", credential_file=str(cred_file))
    assert client.token == "ghp_cred_token"
