"""Pipeline orchestrator — wire scanner → analyzer → generator → publisher into one run.

State-aware: every field change is checked against a persistent ledger before
applying, preventing redundant edits or overwriting user-made changes.
"""

from pathlib import Path

from repogardener.auth import GithubClient
from repogardener.scanner import list_repos, clone_all
from repogardener.analyzer import detect_project_type, extract_all_docstrings, parse_dependencies
from repogardener.llm import LLMClient
from repogardener.generators import generate_description, generate_topics, generate_readme
from repogardener.stale import find_stale_deps
from repogardener.report import generate_report
from repogardener.publisher import update_repo, upsert_readme
from repogardener.state import StateTracker

DEFAULT_STATE_FILE = Path("data/state.json")


def run_pipeline(
    username: str = "FBR65",
    dry_run: bool = True,
    workspace: Path | None = None,
    skip_clone: bool = False,
    state_file: Path | None = DEFAULT_STATE_FILE,
) -> tuple[list[dict], str]:
    """Run the full RepoGardener pipeline.

    Args:
        username: GitHub username to scan.
        dry_run: If True, only analyze and report; don't push to GitHub.
        workspace: Directory to clone repos into (optional, needed for analysis).
        skip_clone: If True, assume repos are already cloned in workspace.
        state_file: Path to state.json ledger for preventing repeated edits.

    Returns:
        Tuple of (list of action dicts, markdown report string).
    """
    client = GithubClient()
    llm = LLMClient()  # uses defaults from llm.py
    tracker = StateTracker(state_file)

    # 1. Scan
    print(f"🔍 Scanning repos for {username}...")
    repos = list_repos(client, username, include_private=False)
    print(f"   Found {len(repos)} repos")

    # Filter: skip forks, archived
    repos = [r for r in repos if not r.get("fork") and not r.get("archived")]
    print(f"   {len(repos)} actionable (non-fork, non-archived)")

    # 2. Clone (if workspace provided and not skipped)
    if workspace and not skip_clone:
        paths = clone_all(repos, workspace)
        print(f"   Cloned {len(paths)} repos to {workspace}")

    # 3. Analyze & Generate per repo
    results: list[dict] = []
    skipped_state: list[str] = []
    for repo in repos:
        name = repo["name"]
        full_name = repo["full_name"]
        repo_dir = workspace / name if workspace else None
        cur_desc = repo.get("description") or ""
        cur_topics = repo.get("topics", [])

        result: dict = {
            "name": name,
            "full_name": full_name,
            "current_description": repo.get("description"),
            "current_topics": cur_topics,
            "has_changes": False,
        }

        if repo_dir and repo_dir.exists():
            # Analyze
            pt = detect_project_type(repo_dir)
            result["languages"] = pt["languages"]
            result["has_readme"] = pt["has_readme"]
            docs = extract_all_docstrings(repo_dir)
            deps = parse_dependencies(repo_dir)
            result["deps"] = deps

            # ── Description ──────────────────────────────────────
            if not cur_desc or len(cur_desc) < 5:
                ok, reason = tracker.should_apply(name, "description", cur_desc or None, "")
                if ok:
                    try:
                        new_desc = generate_description(
                            llm, name, docs, pt["languages"], deps
                        )
                        result["new_description"] = new_desc
                        result["has_changes"] = True
                        print(f"   📝 {name}: description {reason}")
                    except Exception as e:
                        print(f"   ⚠️  description gen failed for {name}: {e}")
                else:
                    skipped_state.append(f"description({name}): {reason}")
                    print(f"   ⏭️  {name}: description skipped ({reason})")

            # ── Topics ───────────────────────────────────────────
            if not cur_topics:
                ok, reason = tracker.should_apply(name, "topics", None, "")
                if ok:
                    try:
                        new_topics = generate_topics(
                            llm, name, result.get("new_description", cur_desc),
                            pt["languages"], deps
                        )
                        result["new_topics"] = new_topics
                        result["has_changes"] = True
                        print(f"   🏷️  {name}: topics {reason}")
                    except Exception as e:
                        print(f"   ⚠️  topics gen failed for {name}: {e}")
                else:
                    skipped_state.append(f"topics({name}): {reason}")
                    print(f"   ⏭️  {name}: topics skipped ({reason})")

            # ── Stale deps (always fresh, not state-tracked) ─────
            try:
                stale = find_stale_deps(deps.get("runtime", []))
                if stale:
                    result["stale_deps"] = stale
                    result["has_changes"] = True
            except Exception as e:
                print(f"   ⚠️  stale check failed for {name}: {e}")

            # ── README ───────────────────────────────────────────
            if not pt["has_readme"] and (docs or deps.get("runtime")):
                ok, reason = tracker.should_apply(name, "readme", None, "")
                if ok:
                    try:
                        readme = generate_readme(
                            llm, name, docs, pt["languages"], deps,
                            result.get("new_topics", [])
                        )
                        result["new_readme"] = readme
                        result["has_changes"] = True
                        print(f"   📖 {name}: README {reason}")
                    except Exception as e:
                        print(f"   ⚠️  README gen failed for {name}: {e}")
                else:
                    skipped_state.append(f"readme({name}): {reason}")
                    print(f"   ⏭️  {name}: README skipped ({reason})")

        results.append(result)

    # ── State summary ───────────────────────────────────────────
    print(f"\n📊 State ledger: {len(tracker.get_summary())} repos tracked")

    # 4. Generate report
    report_text = generate_report(results)

    # 5. Apply if not dry-run
    if not dry_run:
        print(f"\n🚀 Applying changes to GitHub...")
        updated = 0
        for r in results:
            if not r["has_changes"]:
                continue
            name = r["name"]
            # Need at least description or topics to update
            desc = r.get("new_description")
            topics = r.get("new_topics")
            if desc or topics:
                ok = update_repo(client, r["full_name"], description=desc, topics=topics)
                if not ok:
                    continue
                # Mark state
                if desc:
                    tracker.mark_applied(name, "description", desc)
                if topics:
                    tracker.mark_applied(name, "topics", ", ".join(sorted(topics)))
            # README
            readme = r.get("new_readme")
            if readme:
                upsert_readme(client, r["full_name"], readme)
                tracker.mark_applied(name, "readme", readme)
            updated += 1
        tracker.save()
        print(f"   Applied changes to {updated} repos.")
        print(f"   State saved to {tracker.state_file}")

    print(f"✅ {'Dry-run' if dry_run else 'Run'} complete.")
    return results, report_text
