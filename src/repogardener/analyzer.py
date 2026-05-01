"""Repository analyzer — project type detection, docstring extraction, dependency parsing."""
import ast
import json
import tomllib
from pathlib import Path

PROJECT_SIGNATURES = {
    "python": ["pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "requirements.txt"],
    "javascript": ["package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"],
    "typescript": ["tsconfig.json"],
    "rust": ["Cargo.toml", "Cargo.lock"],
    "go": ["go.mod", "go.sum"],
    "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "ruby": ["Gemfile", "Rakefile"],
    "shell": [],
    "docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
}

EXTENSION_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".rs": "rust", ".go": "go", ".java": "java", ".rb": "ruby",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    ".md": "markdown", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".cfg": "ini", ".ini": "ini",
}


def detect_project_type(repo_dir: Path) -> dict:
    """Detect languages and build files in a repo directory."""
    result = {"languages": [], "build_files": [], "has_readme": False}

    # Check for README
    for readme_name in ("README.md", "README.rst", "README.txt", "README"):
        if (repo_dir / readme_name).exists():
            result["has_readme"] = True
            break

    # Check build files
    for lang, markers in PROJECT_SIGNATURES.items():
        for marker in markers:
            if (repo_dir / marker).exists():
                result["build_files"].append(marker)
                if lang not in result["languages"]:
                    result["languages"].append(lang)

    # Detect from file extensions (weighted)
    ext_counts = {}
    for f in repo_dir.rglob("*"):
        if f.is_file() and f.suffix in EXTENSION_MAP:
            lang = EXTENSION_MAP[f.suffix]
            ext_counts[lang] = ext_counts.get(lang, 0) + 1

    for lang, count in sorted(ext_counts.items(), key=lambda x: -x[1])[:3]:
        if lang not in result["languages"]:
            result["languages"].append(lang)

    return result


def extract_docstrings(py_file: Path) -> dict:
    """Extract all docstrings from a Python file."""
    result = {
        "module": None,
        "classes": [],
        "functions": [],
    }
    try:
        tree = ast.parse(py_file.read_text())
    except SyntaxError:
        return result

    result["module"] = ast.get_docstring(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node)
            if doc:
                result["classes"].append((node.name, doc))
        elif isinstance(node, ast.FunctionDef):
            doc = ast.get_docstring(node)
            if doc:
                result["functions"].append((node.name, doc))

    return result


def extract_all_docstrings(repo_dir: Path) -> list[dict]:
    """Collect docstrings from all .py files in repo."""
    results = []
    for py_file in repo_dir.rglob("*.py"):
        if ".venv" in py_file.parts or "__pycache__" in py_file.parts:
            continue
        docs = extract_docstrings(py_file)
        rel = py_file.relative_to(repo_dir)
        results.append({"file": str(rel), **docs})
    return results


def parse_dependencies(repo_dir: Path) -> dict:
    """Extract dependencies from known build files."""
    deps = {"runtime": [], "dev": [], "source_file": None}

    # pyproject.toml (PEP 621 or Poetry)
    pyproject = repo_dir / "pyproject.toml"
    if pyproject.exists():
        data = tomllib.loads(pyproject.read_text())
        project = data.get("project", {})
        deps["runtime"] = project.get("dependencies", [])
        deps["dev"] = project.get("optional-dependencies", {}).get("dev", [])
        # Poetry format
        poetry = data.get("tool", {}).get("poetry", {})
        if poetry:
            for name, spec in poetry.get("dependencies", {}).items():
                if name != "python":
                    deps["runtime"].append(f"{name} {spec}")
            for name, spec in poetry.get("group", {}).get("dev", {}).get("dependencies", {}).items():
                deps["dev"].append(f"{name} {spec}")
        deps["source_file"] = "pyproject.toml"

    # requirements.txt
    req_file = repo_dir / "requirements.txt"
    if req_file.exists():
        deps["runtime"].extend(
            line.strip() for line in req_file.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        )
        if not deps.get("source_file"):
            deps["source_file"] = "requirements.txt"

    # package.json
    pkg = repo_dir / "package.json"
    if pkg.exists():
        data = json.loads(pkg.read_text())
        deps["runtime"] = [f"{k} {v}" for k, v in data.get("dependencies", {}).items()]
        deps["dev"] = [f"{k} {v}" for k, v in data.get("devDependencies", {}).items()]
        if not deps.get("source_file"):
            deps["source_file"] = "package.json"

    return deps
