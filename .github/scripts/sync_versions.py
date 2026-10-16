"""Keep the Python package version and the Dart plugin version in lockstep.

The version of record is ``[project].version`` in the root ``pyproject.toml``.
This script propagates it to:

* ``src/flutter/flet_terminal/pubspec.yaml`` (``version:``)
* ``src/flet_terminal/__init__.py`` (``__version__ = "..."``)

Run from the repository root::

    uv run python .github/scripts/sync_versions.py           # propagate
    uv run python .github/scripts/sync_versions.py --check   # CI gate (exit 1 on drift)

Wired into ``publish.yml`` (before ``uv build``) so a wheel can never ship a
version that disagrees with the Dart payload, and into ``build-all.yml``'s
quality job in ``--check`` mode. Mirrors the flet-notifications tool of the
same name.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

VERSION_RE = re.compile(r'^version = "([^"]+)"', re.MULTILINE)

PUBSPEC = ROOT / "src" / "flutter" / "flet_terminal" / "pubspec.yaml"
INIT = ROOT / "src" / "flet_terminal" / "__init__.py"


def read_pyproject_version() -> str:
    match = VERSION_RE.search((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if not match:
        sys.exit("sync_versions: no [project].version found in pyproject.toml")
    return match.group(1)


def sync_pubspec(version: str, check: bool) -> str:
    text = PUBSPEC.read_text(encoding="utf-8")
    updated, count = re.subn(
        r"^version: .*$", f"version: {version}", text, count=1, flags=re.MULTILINE
    )
    if count == 0:
        sys.exit("sync_versions: no `version:` line found in pubspec.yaml")
    if updated != text:
        if check:
            return f"DRIFT: pubspec.yaml != {version}"
        PUBSPEC.write_text(updated, encoding="utf-8")
        return f"pubspec.yaml -> {version}"
    return f"pubspec.yaml already at {version}"


def sync_init(version: str, check: bool) -> str:
    text = INIT.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'^__version__ = ".*"$',
        f'__version__ = "{version}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count == 0:
        sys.exit("sync_versions: no __version__ assignment found in __init__.py")
    if updated != text:
        if check:
            return f"DRIFT: __init__.py != {version}"
        INIT.write_text(updated, encoding="utf-8")
        return f"__init__.py -> {version}"
    return f"__init__.py already at {version}"


def main() -> None:
    check = "--check" in sys.argv[1:]
    version = read_pyproject_version()
    results = (sync_pubspec(version, check), sync_init(version, check))
    drift = [line for line in results if line.startswith("DRIFT")]
    for line in results:
        print(f"sync_versions: {line}")
    if drift:
        sys.exit(1)


if __name__ == "__main__":
    main()
