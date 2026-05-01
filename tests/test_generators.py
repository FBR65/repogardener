"""Tests for content generators (description, topics, README)."""
import pytest
from unittest.mock import MagicMock

from repogardener.generators import (
    generate_description,
    generate_topics,
    generate_readme,
)


class FakeLLM:
    """Simple fake that returns a canned response."""
    def __init__(self, response=""):
        self.response = response
        self.calls = []

    def chat(self, prompt, system="", temperature=0.3):
        self.calls.append({"prompt": prompt, "system": system})
        return self.response


def test_generate_description():
    llm = FakeLLM("A command-line tool for managing GitHub repositories.")
    docstrings = [
        {"file": "cli.py", "module": "CLI entry point.", "functions": [("main", "Entry point.")]}
    ]
    result = generate_description(llm, "my-repo", docstrings, ["python"], {"runtime": ["click"]})
    assert result == "A command-line tool for managing GitHub repositories."
    assert len(llm.calls) == 1


def test_generate_description_truncates():
    """Description should be capped at 350 chars (GitHub limit)."""
    long_response = "X" * 400
    llm = FakeLLM(long_response)
    result = generate_description(llm, "repo", [], ["python"], {"runtime": []})
    assert len(result) <= 350
    assert result == "X" * 350


def test_generate_topics():
    llm = FakeLLM("python, cli, automation, devtools, github-api, git")
    result = generate_topics(llm, "my-repo", "A CLI tool", ["python"], {"runtime": ["click"]})
    assert len(result) > 0
    assert len(result) <= 20
    assert "python" in result
    assert "cli" in result
    assert all(isinstance(t, str) for t in result)


def test_generate_topics_returns_max_20():
    """GitHub topic limit is 20."""
    many = ", ".join(f"topic-{i}" for i in range(30))
    llm = FakeLLM(many)
    result = generate_topics(llm, "repo", "desc", ["python"], {"runtime": []})
    assert len(result) <= 20


def test_generate_readme():
    llm = FakeLLM("# My Repo\n\nA test README.\n")
    docstrings = [{"file": "main.py", "module": "Main module.", "functions": [("run", "Run it.")]}]
    result = generate_readme(llm, "my-repo", docstrings, ["python"], {"runtime": ["click"]}, ["cli", "python"])
    assert "# My Repo" in result
    assert len(llm.calls) == 1


def test_generate_readme_no_docstrings():
    """Should handle repos with no Python files."""
    llm = FakeLLM("# Empty Repo\n\nMinimal README.\n")
    result = generate_readme(llm, "empty", [], ["shell"], {"runtime": []}, [])
    assert len(result) > 0
