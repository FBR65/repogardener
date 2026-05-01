"""Tests for the GitHub API publisher."""
import json
import pytest
from unittest.mock import patch, MagicMock

from repogardener.publisher import update_repo, upsert_readme
from repogardener.auth import GithubClient


class FakeGithubClient:
    """Client that returns predictable responses."""
    def __init__(self, token=None):
        self.token = token or "test-token"
        self.headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json"}

    @classmethod
    def from_token(cls, token):
        return cls(token)


def test_update_repo_description():
    client = FakeGithubClient("token")
    with patch("repogardener.publisher.urllib.request.urlopen") as mock_urlopen:
        update_repo(client, "user/repo", description="A test repo")
        call_args = mock_urlopen.call_args[0][0]
        assert call_args.get_method() == "PATCH"
        assert "/repos/user/repo" in call_args.get_full_url()


def test_update_repo_topics():
    client = FakeGithubClient("token")
    with patch("repogardener.publisher.urllib.request.urlopen") as mock_urlopen:
        update_repo(client, "user/repo", topics=["python", "cli"])
        call_args = mock_urlopen.call_args[0][0]
        assert call_args.get_method() == "PUT"
        assert "/topics" in call_args.get_full_url()
        body = json.loads(call_args.data)
        assert body["names"] == ["python", "cli"]


def test_update_repo_truncates_description():
    client = FakeGithubClient("token")
    with patch("repogardener.publisher.urllib.request.urlopen") as mock_urlopen:
        update_repo(client, "user/repo", description="X" * 400)
        call_args = mock_urlopen.call_args[0][0]
        body = json.loads(call_args.data)
        assert len(body["description"]) <= 350


def test_update_repo_noop_when_nothing_to_update():
    client = FakeGithubClient("token")
    with patch("repogardener.publisher.urllib.request.urlopen") as mock_urlopen:
        result = update_repo(client, "user/repo")
    assert result is True  # nothing to do = success
    mock_urlopen.assert_not_called()


def test_upsert_readme_create():
    client = FakeGithubClient("token")
    with patch("repogardener.publisher.urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"sha": "abc123"}).encode()
        mock_urlopen.side_effect = [
            _http_error(404),  # README not found
            mock_resp,
        ]
        result = upsert_readme(client, "user/repo", "# Hello\n\nContent.")
        assert result is True


def test_upsert_readme_update():
    """When README exists, include SHA for update."""
    client = FakeGithubClient("token")
    with patch("repogardener.publisher.urllib.request.urlopen") as mock_urlopen:
        mock_get = MagicMock()
        mock_get.read.return_value = json.dumps({"sha": "abc123"}).encode()
        mock_get.__enter__.return_value = mock_get  # context-manager chain
        mock_put = MagicMock()
        mock_put.__enter__.return_value = mock_put
        mock_urlopen.side_effect = [mock_get, mock_put]
        result = upsert_readme(client, "user/repo", "# Updated\n\nContent.")
        assert result is True
        # Verify SHA was included in PUT body
        put_req = mock_urlopen.call_args_list[1][0][0]
        body = json.loads(put_req.data)
        assert body["sha"] == "abc123"


def _http_error(code):
    from urllib.error import HTTPError
    from io import BytesIO
    return HTTPError("http://fake", code, "Error", {}, BytesIO(b""))
