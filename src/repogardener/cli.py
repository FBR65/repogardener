"""CLI entry point for RepoGardener."""
import click
from pathlib import Path

from repogardener.auth import GithubClient
from repogardener.scanner import list_repos, repo_summary, clone_all


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
