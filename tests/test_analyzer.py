"""Tests for the AST analyzer module."""
import pytest
from pathlib import Path

from repogardener.analyzer import (
    detect_project_type,
    extract_docstrings,
    extract_all_docstrings,
    parse_dependencies,
)


# ── detect_project_type ─────────────────────────────────────────

def test_detect_python_project(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'")
    (tmp_path / "setup.py").touch()
    result = detect_project_type(tmp_path)
    assert "python" in result["languages"]
    assert "pyproject.toml" in result["build_files"]
    assert "setup.py" in result["build_files"]


def test_detect_javascript_project(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    result = detect_project_type(tmp_path)
    assert "javascript" in result["languages"]
    assert "package.json" in result["build_files"]


def test_detect_mixed_project(tmp_path):
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "package.json").write_text("{}")
    result = detect_project_type(tmp_path)
    assert "python" in result["languages"]
    assert "javascript" in result["languages"]


def test_detect_has_readme(tmp_path):
    (tmp_path / "README.md").write_text("# Hello")
    result = detect_project_type(tmp_path)
    assert result["has_readme"] is True


def test_detect_no_readme(tmp_path):
    result = detect_project_type(tmp_path)
    assert result["has_readme"] is False


def test_detect_rust_project(tmp_path):
    (tmp_path / "Cargo.toml").touch()
    result = detect_project_type(tmp_path)
    assert "rust" in result["languages"]


def test_detect_go_project(tmp_path):
    (tmp_path / "go.mod").touch()
    result = detect_project_type(tmp_path)
    assert "go" in result["languages"]


def test_detect_empty_project(tmp_path):
    result = detect_project_type(tmp_path)
    assert result["languages"] == []
    assert result["build_files"] == []


def test_detect_from_extensions(tmp_path):
    """Non-build-file languages detected via source files."""
    # Create a .rs file to detect Rust even without Cargo.toml
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.rs").write_text("fn main() {}")
    (tmp_path / "README.md").touch()
    result = detect_project_type(tmp_path)
    # rust should be detected from file extensions
    assert "rust" in result["languages"]
    assert result["has_readme"] is True


def test_detect_docker_file(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM python:3.11")
    result = detect_project_type(tmp_path)
    assert "docker" in result["languages"]


# ── extract_docstrings ──────────────────────────────────────────

def test_extract_module_docstring(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text('"""Module doc."""\n\ndef foo():\n    """Foo doc."""\n    pass\n')
    result = extract_docstrings(f)
    assert result["module"] == "Module doc."
    assert len(result["functions"]) == 1
    assert result["functions"][0] == ("foo", "Foo doc.")


def test_extract_class_docstring(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text('class MyClass:\n    """Class doc."""\n    pass\n')
    result = extract_docstrings(f)
    assert len(result["classes"]) == 1
    assert result["classes"][0] == ("MyClass", "Class doc.")


def test_extract_no_docstrings(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text('x = 1\n')
    result = extract_docstrings(f)
    assert result["module"] is None
    assert result["classes"] == []
    assert result["functions"] == []


def test_extract_syntax_error_file(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text("this is not valid python @@@")
    result = extract_docstrings(f)
    # Should return empty result, not crash
    assert result["module"] is None
    assert result["classes"] == []
    assert result["functions"] == []


# ── extract_all_docstrings ──────────────────────────────────────

def test_extract_all_docstrings(tmp_path):
    (tmp_path / "a.py").write_text('"""Module A."""\ndef foo():\n    """Foo."""\n    pass\n')
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text('"""Module B."""\n')
    results = extract_all_docstrings(tmp_path)
    assert len(results) == 2
    files = [r["file"] for r in results]
    assert "a.py" in files
    assert "sub/b.py" in files


def test_extract_all_skips_venv(tmp_path):
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.py").write_text('"""Should skip."""\n')
    (tmp_path / "main.py").write_text('"""Main."""\n')
    results = extract_all_docstrings(tmp_path)
    assert len(results) == 1
    assert results[0]["file"] == "main.py"


# ── parse_dependencies ──────────────────────────────────────────

def test_parse_pyproject_deps(tmp_path):
    (tmp_path / "pyproject.toml").write_text("""
[project]
dependencies = ["click>=8.0", "requests"]
[project.optional-dependencies]
dev = ["pytest", "ruff"]
""")
    result = parse_dependencies(tmp_path)
    assert result["source_file"] == "pyproject.toml"
    assert "click>=8.0" in result["runtime"]
    assert "requests" in result["runtime"]
    assert "pytest" in result["dev"]
    assert "ruff" in result["dev"]


def test_parse_requirements_txt(tmp_path):
    (tmp_path / "requirements.txt").write_text("click>=8.0\nrequests\n# comment\n\nflask\n")
    result = parse_dependencies(tmp_path)
    assert "click>=8.0" in result["runtime"]
    assert "requests" in result["runtime"]
    assert "flask" in result["runtime"]
    assert "# comment" not in result["runtime"]


def test_parse_package_json(tmp_path):
    (tmp_path / "package.json").write_text('''{
  "dependencies": {"express": "^4.18.0", "lodash": "4.17.21"},
  "devDependencies": {"jest": "29.0.0"}
}''')
    result = parse_dependencies(tmp_path)
    assert result["source_file"] == "package.json"
    assert "express ^4.18.0" in result["runtime"]
    assert "lodash 4.17.21" in result["runtime"]
    assert "jest 29.0.0" in result["dev"]


def test_parse_no_dependency_files(tmp_path):
    result = parse_dependencies(tmp_path)
    assert result["runtime"] == []
    assert result["dev"] == []
    assert result["source_file"] is None
