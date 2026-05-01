"""CLI entry point for RepoGardener."""
import click


@click.group()
@click.version_option(version="0.1.0", prog_name="repogardener")
def main():
    """RepoGardener — automate GitHub profile maintenance."""


@main.command()
def status():
    """Check RepoGardener status."""
    click.echo("RepoGardener v0.1.0 ready.")
