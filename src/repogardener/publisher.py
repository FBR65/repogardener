"""GitHub API publisher — update description, topics, and README."""

import json
import base64
import urllib.request
import urllib.error

from repogardener.auth import GithubClient

API_BASE = "https://api.github.com"


def update_repo(
    client: GithubClient,
    full_name: str,
    description: str | None = None,
    topics: list[str] | None = None,
    homepage: str | None = None,
) -> bool:
    """Update repo metadata (description, topics, homepage).

    Returns True on success, False on failure.
    Does nothing (returns True) if no updates are supplied.
    """
    updated = False

    # --- description + homepage (PATCH /repos/:owner/:repo) ---
    body: dict = {}
    if description is not None:
        body["description"] = description[:350]
    if homepage is not None:
        body["homepage"] = homepage

    if body:
        url = f"{API_BASE}/repos/{full_name}"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={**client.headers, "Content-Type": "application/json"},
            method="PATCH",
        )
        try:
            urllib.request.urlopen(req)
            updated = True
        except urllib.error.HTTPError as e:
            print(f"  FAILED update description for {full_name}: {e.code}")
            return False

    # --- topics (PUT /repos/:owner/:repo/topics) ---
    if topics is not None:
        url = f"{API_BASE}/repos/{full_name}/topics"
        req = urllib.request.Request(
            url,
            data=json.dumps({"names": topics}).encode(),
            headers={
                **client.headers,
                "Content-Type": "application/json",
                "Accept": "application/vnd.github.mercy-preview+json",
            },
            method="PUT",
        )
        try:
            urllib.request.urlopen(req)
            updated = True
        except urllib.error.HTTPError as e:
            print(f"  FAILED update topics for {full_name}: {e.code}")
            return False

    # If nothing was supplied, it's still "success" (no-op)
    if not body and topics is None:
        return True

    return updated


def upsert_readme(
    client: GithubClient,
    full_name: str,
    content: str,
    branch: str = "main",
    message: str = "docs: update README via RepoGardener",
) -> bool:
    """Create or update README.md via GitHub Contents API.

    Returns True on success, False on failure.
    """
    path = "README.md"
    url = f"{API_BASE}/repos/{full_name}/contents/{path}"

    body: dict = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "branch": branch,
    }

    # Check if README already exists to get its SHA for an update
    try:
        req = urllib.request.Request(f"{url}?ref={branch}", headers=client.headers)
        with urllib.request.urlopen(req) as resp:
            existing = json.loads(resp.read().decode())
            body["sha"] = existing["sha"]
    except urllib.error.HTTPError:
        pass  # File doesn't exist yet — create new

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={**client.headers, "Content-Type": "application/json"},
        method="PUT",
    )
    try:
        urllib.request.urlopen(req)
        return True
    except urllib.error.HTTPError as e:
        print(f"  FAILED README for {full_name}: {e.code}")
        return False
