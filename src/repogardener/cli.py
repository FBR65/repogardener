"""CLI entry point for RepoGardener."""
import click
from pathlib import Path

from repogardener.auth import GithubClient
from repogardener.scanner import list_repos, repo_summary, clone_all
from repogardener.orchestrator import run_pipeline


@click.group()
@click.version_option(version="0.1.0", prog_name="repogardener")
def main():
    """RepoGardener — automate GitHub profile maintenance."""


@main.command()
def status():
    """Check RepoGardener status."""
    click.echo("RepoGardener v0.1.0 ready.")


@main.command()
@click.option("--username", default="FBR65", help="GitHub username")
@click.option("--include-private", is_flag=True)
def list(username, include_private):
    """List all repos with their current state."""
    client = GithubClient()
    repos = list_repos(client, username, include_private)
    for repo in repos:
        s = repo_summary(repo)
        desc = s["description"] or "(no description)"
        topics = ", ".join(s["topics"]) if s["topics"] else "(no topics)"
        click.echo(f"{s['name']:40} | {s['language'] or '?':10} | {desc[:60]}")
        click.echo(f"  topics: {topics}")


@main.command()
@click.option("--workspace", default="repos", help="Clone destination directory")
@click.option("--include-forks/--skip-forks", default=False)
@click.option("--include-archived/--skip-archived", default=False)
def clone(workspace, include_forks, include_archived):
    """Shallow-clone all repos."""
    client = GithubClient()
    repos = list_repos(client, "FBR65")
    paths = clone_all(repos, Path(workspace),
                      skip_forks=not include_forks,
                      skip_archived=not include_archived)
    click.echo(f"Cloned {len(paths)} repos to {workspace}/")


@main.command()
@click.option("--dry-run/--apply", default=True, help="Dry-run (default) or apply changes")
@click.option("--workspace", default="repos", help="Repo clone workspace")
@click.option("--username", default="FBR65", help="GitHub username")
@click.option("--output", default="reports/report.md", help="Report output path")
def run(dry_run, workspace, username, output):
    """Run the full RepoGardener pipeline."""
    results, report = run_pipeline(
        username, dry_run=dry_run, workspace=Path(workspace)
    )
    # Save report
    Path(output).parent.mkdir(exist_ok=True, parents=True)
    Path(output).write_text(report)
    click.echo(report)
    if dry_run:
        changes = sum(1 for r in results if r["has_changes"])
        click.echo(f"\nDry-run complete. {changes} repos have changes.")
        click.echo(f"Report saved: {output}")
    else:
        click.echo(f"\nChanges applied. Report saved: {output}")


@main.command()
@click.option("--workspace", default="repos", help="Repo clone workspace")
@click.option("--output", default="reports/report.md", help="Report output path")
@click.option("--username", default="FBR65", help="GitHub username")
def report(workspace, output, username):
    """Analyze all repos and generate a dry-run report (alias for 'run --dry-run')."""
    results, report = run_pipeline(
        username, dry_run=True, workspace=Path(workspace)
    )
    Path(output).parent.mkdir(exist_ok=True, parents=True)
    Path(output).write_text(report)
    click.echo(report)
    changes = sum(1 for r in results if r["has_changes"])
    click.echo(f"\nReport complete. {changes} repos have changes.")
    click.echo(f"Report saved: {output}")
