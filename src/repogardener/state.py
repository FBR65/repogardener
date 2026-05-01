"""State tracker — prevents redundant or conflicting changes.

Guards every field change (description, topics, README) against
a persistent JSON ledger. Before applying, we check:
1. Did we already apply this exact proposal? → skip
2. Did the user manually edit the field since our last apply? → skip (warn)
3. Is the current value our own last proposal but we have a new one? → apply
4. Is the field currently empty/None? → apply (first time)
"""

import hashlib
import json
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class StateTracker:
    """Tracks what RepoGardener has applied to each repo+field.

    State ledger format:
    {
        "repo_name": {
            "description": "sha256_hash_of_applied_value",
            "topics": "sha256_hash_of_topics_json",
            "readme": "sha256_hash_of_readme_content"
        }
    }
    """

    state_file: Path | None = None
    _ledger: dict[str, dict[str, str]] = field(default_factory=dict)

    def __post_init__(self):
        if self.state_file and self.state_file.exists():
            self._ledger = json.loads(self.state_file.read_text())

    # ── Public API ────────────────────────────────────────────

    def should_apply(
        self, repo: str, field: str, current_value: str | None, proposed_value: str
    ) -> tuple[bool, str]:
        """Decide whether to apply a proposed change.

        Args:
            repo: Repository name (e.g. "hermes-agent")
            field: Field name ("description", "topics", "readme")
            current_value: Current value on GitHub (or None if unset)
            proposed_value: What we'd set it to

        Returns:
            (ok: bool, reason: str) — reason is one of:
                "new", "changed", "already_applied", "user_modified"
        """
        our_hash = self._hash(proposed_value)
        their_hash = self._hash(current_value) if current_value else None
        prev_hash = self._get_applied_hash(repo, field)

        # 1. Never applied anything before → apply
        if prev_hash is None:
            return True, "new"

        # 2. Exact same proposal we already applied → skip
        if our_hash == prev_hash:
            return False, "already_applied"

        # 3. User changed the field since our last apply → skip (guard user edits)
        if their_hash is not None and their_hash != prev_hash:
            return False, "user_modified"

        # 4. Our last proposal still stands on GitHub, but we have a better one → apply
        return True, "changed"

    def mark_applied(self, repo: str, field: str, value: str):
        """Record that we've applied this value to the repo+field."""
        self._ledger.setdefault(repo, {})[field] = self._hash(value)

    def save(self):
        """Persist ledger to disk."""
        if self.state_file:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps(self._ledger, indent=2))

    def get_summary(self) -> dict[str, int]:
        """Return count of applied fields per repo."""
        return {repo: len(fields) for repo, fields in self._ledger.items()}

    # ── Internals ─────────────────────────────────────────────

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.strip().lower().encode()).hexdigest()

    def _get_applied_hash(self, repo: str, field: str) -> str | None:
        return self._ledger.get(repo, {}).get(field)
