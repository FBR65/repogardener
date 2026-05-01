"""Content generators — produce descriptions, topics, and READMEs via LLM."""
import json
from repogardener.llm import LLMClient

SYSTEM_DESC = (
    "You are a technical writer for GitHub profiles. "
    "Write a single-sentence description (under 350 characters) that clearly states what the repository does. "
    "Do NOT include markdown, emojis, or quotation marks. Output plain text only."
)

SYSTEM_TOPICS = (
    "You are a GitHub maintainer. "
    "Output ONLY a comma-separated list of 2-10 lowercase topics (no emojis, no quotes). "
    "Use standard GitHub topics: language names, frameworks, purpose keywords, tool types. "
    "Example: 'python, cli, automation, devtools'"
)

SYSTEM_README = (
    "You are a technical writer. "
    "Write a minimal but professional README.md in Markdown format. "
    "Include: title (# Name), short description, Installation, Usage, and License sections. "
    "Keep it concise (~50-200 words). Do NOT include badges."
)


def generate_description(llm: LLMClient, repo_name: str, docstrings: list,
                         languages: list, deps: dict) -> str:
    """Generate a one-sentence description for a repo."""
    context = _build_context(repo_name, docstrings, languages, deps)
    prompt = f"Repository: {repo_name}\n{context}\n\nWrite a one-sentence description:"
    result = llm.chat(prompt, system=SYSTEM_DESC, temperature=0.3)
    return result.strip()[:350]


def generate_topics(llm: LLMClient, repo_name: str, description: str,
                    languages: list, deps: dict) -> list:
    """Generate a list of topics (max 20)."""
    dep_names = ", ".join(sorted(deps.get("runtime", [])))
    prompt = (
        f"Repository: {repo_name}\n"
        f"Languages: {', '.join(languages) if languages else 'unknown'}\n"
        f"Description: {description}\n"
        f"Dependencies: {dep_names}\n"
        f"\nSuggest topics:"
    )
    result = llm.chat(prompt, system=SYSTEM_TOPICS, temperature=0.3)
    topics = [t.strip().lower() for t in result.split(",") if t.strip()]
    return topics[:20]


def generate_readme(llm: LLMClient, repo_name: str, docstrings: list,
                    languages: list, deps: dict, topics: list) -> str:
    """Generate a README.md for a repo without one."""
    context = _build_context(repo_name, docstrings, languages, deps)
    prompt = (
        f"Repository: {repo_name}\n"
        f"Topics: {', '.join(topics)}\n"
        f"{context}\n\nWrite a README.md:"
    )
    return llm.chat(prompt, system=SYSTEM_README, temperature=0.4)


def _build_context(repo_name, docstrings, languages, deps):
    """Build context string from analysis results."""
    parts = [f"Languages: {', '.join(languages) if languages else 'unknown'}"]
    dep_names = sorted(deps.get("runtime", []))
    if dep_names:
        parts.append(f"Dependencies: {', '.join(dep_names)}")
    if docstrings:
        parts.append("Key code:")
        for ds in docstrings[:5]:
            mod = ds.get("module", "")
            funcs = [f[0] for f in ds.get("functions", [])]
            parts.append(f"  - {ds['file']}: {mod[:80]}")
            if funcs:
                parts.append(f"    Functions: {', '.join(funcs[:5])}")
    return "\n".join(parts)
