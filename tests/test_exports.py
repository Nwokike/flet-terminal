"""The public export surface: exact names, importability, and version marker."""

import re

import flet_terminal

EXPECTED_ALL = [
    "BUILTIN_THEMES",
    "DEFAULT_EXTRA_KEYS",
    "ExtraKeysBar",
    "MobileTerminal",
    "ShortcutEvent",
    "Terminal",
    "TerminalSearchBar",
    "get_theme",
]


def test_all_is_exact():
    assert sorted(flet_terminal.__all__) == sorted(EXPECTED_ALL)


def test_every_export_is_importable():
    for name in EXPECTED_ALL:
        assert hasattr(flet_terminal, name), f"missing export: {name}"


def test_version_marker():
    assert re.fullmatch(r"\d+\.\d+\.\d+", flet_terminal.__version__), (
        f"unexpected version format: {flet_terminal.__version__!r}"
    )


def test_root_classes_resolve_to_package_modules():
    from flet_terminal.extra_keys import ExtraKeysBar
    from flet_terminal.mobile_terminal import MobileTerminal
    from flet_terminal.terminal import Terminal

    assert flet_terminal.Terminal is Terminal
    assert flet_terminal.MobileTerminal is MobileTerminal
    assert flet_terminal.ExtraKeysBar is ExtraKeysBar
