"""Version-of-record sync: pyproject == __init__.__version__ == pubspec.

The regex parsing (instead of tomllib) keeps this test runnable on the 3.10
compat-matrix leg.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    assert match, "no [project].version in pyproject.toml"
    return match.group(1)


def _init_version() -> str:
    text = (ROOT / "src" / "flet_terminal" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"', text, re.MULTILINE)
    assert match, "no __version__ in flet_terminal/__init__.py"
    return match.group(1)


def _pubspec_version() -> str:
    text = (ROOT / "src" / "flutter" / "flet_terminal" / "pubspec.yaml").read_text(
        encoding="utf-8"
    )
    match = re.search(r"^version: (.+)$", text, re.MULTILINE)
    assert match, "no version: line in pubspec.yaml"
    return match.group(1).strip()


def test_versions_are_in_sync():
    versions = {
        "pyproject.toml": _pyproject_version(),
        "flet_terminal/__init__.py": _init_version(),
        "pubspec.yaml": _pubspec_version(),
    }
    assert len(set(versions.values())) == 1, (
        f"version drift across files: {versions} — run "
        f"`uv run python .github/scripts/sync_versions.py`"
    )


def test_runtime_version_matches_files():
    import flet_terminal

    assert flet_terminal.__version__ == _pyproject_version()
