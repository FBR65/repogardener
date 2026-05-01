"""Stale dependency detector — check Python deps against PyPI for outdated versions."""
import json
import urllib.request
from dataclasses import dataclass

# Use stdlib packaging if available (Python 3.8+); skip if not
try:
    from packaging.requirements import Requirement
    from packaging.version import Version
except ImportError:
    Requirement = None
    Version = None


@dataclass
class StaleDep:
    name: str
    current: str
    latest: str
    days_behind: int


def check_pypi(package_name: str) -> str | None:
    """Get latest version from PyPI JSON API."""
    try:
        url = f"https://pypi.org/pypi/{package_name}/json"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())["info"]["version"]
    except Exception:
        return None


def find_stale_deps(deps: list[str]) -> list[StaleDep]:
    """Check list of dependency strings against PyPI."""
    stale = []
    for dep_str in deps:
        if Requirement is None:
            continue
        try:
            req = Requirement(dep_str.strip())
            name = req.name
        except Exception:
            continue
        latest = check_pypi(name)
        if not latest:
            continue
        # Parse specifiers for min version
        if req.specifier:
            try:
                if not req.specifier.contains(latest):
                    stale.append(StaleDep(
                        name=name,
                        current=str(req.specifier),
                        latest=latest,
                        days_behind=-1  # indeterminate without release date
                    ))
            except Exception:
                pass
    return stale
