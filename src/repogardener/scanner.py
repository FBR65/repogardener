"""GitHub repository scanner — list, analyze, clone repos."""
import json
import urllib.request
import urllib.error
import subprocess
from pathlib import Path

from repogardener.auth import GithubClient

API_BASE = "https://api.github.com"
WORKSPACE = Path.cwd() / "repos"


def list_repos(client: GithubClient, username: str, include_private=False) -> list[dict]:
    """Fetch all repos for a user with pagination."""
    repos = []
    page = 1
    while True:
        url = f"{API_BASE}/users/{username}/repos?per_page=100&page={page}&sort=updated"
        if include_private:
            url += "&type=all"
        req = urllib.request.Request(url, headers=client.headers)
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                if not data:
                    break
                repos.extend(data)
                page += 1
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"GitHub API error: {e.code} {e.reason}")
    return repos


def repo_summary(repo: dict) -> dict:
    """Extract key fields from a repo object."""
    return {
        "name": repo["name"],
        "full_name": repo["full_name"],
        "description": repo.get("description"),
        "topics": repo.get("topics", []),
        "language": repo.get("language"),
        "default_branch": repo.get("default_branch", "master"),
        "clone_url": repo.get("clone_url"),
        "pushed_at": repo.get("pushed_at"),
        "archived": repo.get("archived", False),
        "fork": repo.get("fork", False),
        "has_readme": False,
        "has_pyproject": False,
    }


def clone_all(repos: list[dict], workspace: Path = None, skip_forks=True,
              skip_archived=True) -> list[Path]:
    """Shallow-clone repos into workspace. Returns list of repo dirs."""
    ws = workspace or WORKSPACE
    ws.mkdir(exist_ok=True, parents=True)
    cloned = []
    for repo in repos:
        if skip_forks and repo.get("fork", False):
            continue
        if skip_archived and repo.get("archived", False):
            continue
        dest = ws / repo["name"]
        if dest.exists():
            subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"],
                           capture_output=True, timeout=30)
        else:
            clone_url = repo.get("clone_url")
            if not clone_url:
                continue
            subprocess.run([
                "git", "clone", "--depth", "1",
                clone_url, str(dest)
            ], capture_output=True, timeout=60)
        cloned.append(dest)
    return cloned
