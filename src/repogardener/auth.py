"""GitHub authentication with token auto-detection."""
import os
import re
from pathlib import Path


class AuthError(Exception):
    """Authentication-related error."""
    pass


class GithubClient:
    """GitHub API client with automatic token detection."""

    def __init__(self, token=None, env_file=None, credential_file=None):
        self.token = token or self._load_token(env_file=env_file, credential_file=credential_file)
        if not self.token:
            raise AuthError(
                "GITHUB_TOKEN not found. Set it via:\n"
                "  export GITHUB_TOKEN=ghp_...\n"
                "Or place it in ~/.hermes/.env as GITHUB_TOKEN=ghp_..."
            )

    @staticmethod
    def _load_token(env_file=None, credential_file=None):
        # 1. Environment variable
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token

        # 2. .env file
        env_path = Path(env_file if env_file is not None
                        else os.path.expanduser("~/.hermes/.env"))
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("GITHUB_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")

        # 3. git credential store
        cred_path = credential_file if credential_file is not None else \
            os.path.expanduser("~/.git-credentials")
        cred_file = Path(cred_path)
        if cred_file.exists():
            content = cred_file.read_text()
            for line in content.splitlines():
                if "github.com" in line:
                    m = re.search(r"https://[^:]+:([^@]+)@github", line)
                    if m:
                        return m.group(1)

        return None

    @property
    def headers(self):
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
        }
