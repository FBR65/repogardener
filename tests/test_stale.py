"""Tests for stale dependency detector."""
import pytest
from unittest.mock import patch, MagicMock

from repogardener.stale import check_pypi, find_stale_deps, StaleDep


class FakeUrlopen:
    """Minimal mock for urllib.request.urlopen."""
    def __init__(self, data):
        self._data = data

    def read(self):
        import json
        return json.dumps(self._data).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_check_pypi_returns_version():
    fake_data = {"info": {"version": "2.0.0"}}
    with patch("repogardener.stale.urllib.request.urlopen", return_value=FakeUrlopen(fake_data)):
        result = check_pypi("requests")
    assert result == "2.0.0"


def test_check_pypi_handles_error():
    with patch("repogardener.stale.urllib.request.urlopen", side_effect=Exception("network error")):
        result = check_pypi("nonexistent-package-xyz")
    assert result is None


def test_find_stale_no_deps():
    result = find_stale_deps([])
    assert result == []


def test_find_stale_bad_input():
    """Malformed dep strings should not crash."""
    result = find_stale_deps(["not a valid dep string @@@@"])
    assert result == []


def test_find_stale_no_stale():
    """When latest version satisfies specifier, no stale deps."""
    fake_pypi = {"info": {"version": "2.0.0"}}
    with patch("repogardener.stale.urllib.request.urlopen", return_value=FakeUrlopen(fake_pypi)):
        result = find_stale_deps(["requests>=1.0.0"])
    # 2.0.0 should satisfy >=1.0.0, so no stale
    assert result == []


def test_find_stale_major_gap():
    """When latest is far outside specifier, flag stale."""
    fake_pypi = {"info": {"version": "5.0.0"}}
    with patch("repogardener.stale.urllib.request.urlopen", return_value=FakeUrlopen(fake_pypi)):
        result = find_stale_deps(["requests<2"])
    # 5.0.0 does NOT satisfy <2, should flag
    assert len(result) == 1
    assert result[0].name == "requests"
    assert result[0].latest == "5.0.0"


def test_staledep_dataclass():
    sd = StaleDep("click", ">=7.0", "8.1.0", 30)
    assert sd.name == "click"
    assert sd.current == ">=7.0"
    assert sd.latest == "8.1.0"
    assert sd.days_behind == 30
