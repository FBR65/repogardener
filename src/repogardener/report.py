"""Report generator — preview all changes as a structured markdown report."""

from pathlib import Path


def generate_report(actions: list[dict], output_path: str | None = None) -> str:
    """Generate a markdown report of all proposed changes.

    Args:
        actions: List of action dicts, each with at least:
            - name: str
            - has_changes: bool
            Optionally: new_description, new_topics, new_readme, stale_deps,
            current_description, current_topics, languages
        output_path: If set, also write the report to this file.

    Returns:
        Markdown report string.
    """
    lines: list[str] = [
        "# 🌱 RepoGardener Report",
        "",
        f"**{len(actions)} repos analyzed**",
        "",
    ]
    changes = sum(1 for a in actions if a.get("has_changes"))
    lines.append(f"**{changes} repos have pending changes**")
    lines.append("")

    # Summary table
    lines.append("| Repo | Description | Topics | README | Stale Deps |")
    lines.append("|------|-------------|--------|--------|------------|")

    for a in actions:
        desc_flag = "✅" if a.get("new_description") else "—"
        topics_new = a.get("new_topics", [])
        topics_flag = f"✅ {len(topics_new)} new" if topics_new else "—"
        readme_flag = "✅" if a.get("new_readme") else "—"
        stale = a.get("stale_deps", [])
        stale_flag = f"⚠️ {len(stale)}" if stale else "—"
        lines.append(
            f"| `{a['name']}` | {desc_flag} | {topics_flag} | {readme_flag} | {stale_flag} |"
        )
    lines.append("")

    # Detail section for repos with changes
    for a in actions:
        if not a.get("has_changes"):
            continue
        lines.append(f"### {a['name']}")
        if a.get("new_description"):
            lines.append(f"**Description:** {a['new_description']}")
            lines.append("")
        if a.get("new_topics"):
            lines.append(f"**Topics:** `{'`, `'.join(a['new_topics'][:10])}`")
            lines.append("")
        if a.get("new_readme"):
            lines.append(f"**README:** generated ({len(a['new_readme'])} chars)")
            lines.append("")
        if a.get("stale_deps"):
            lines.append("**Stale dependencies:**")
            for sd in a["stale_deps"]:
                if isinstance(sd, (tuple, list)):
                    lines.append(f"  - `{sd[0]}`: {sd[1]} → {sd[2]}")
                else:
                    lines.append(f"  - `{sd.name}`: {sd.current} → {sd.latest}")
            lines.append("")

    report = "\n".join(lines)

    if output_path:
        Path(output_path).parent.mkdir(exist_ok=True, parents=True)
        Path(output_path).write_text(report)

    return report
