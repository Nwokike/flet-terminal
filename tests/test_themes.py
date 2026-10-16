"""Built-in themes: exact names, exact key sets, pinned colors.

CollabShell (the shipped consumer) selects themes by name and reads these
dicts verbatim — name or key drift is a breaking change.
"""

from flet_terminal import BUILTIN_THEMES, get_theme

EXPECTED_NAMES = ["Dracula", "JetBrains Dark", "Matrix Green", "Colab Light"]

EXPECTED_KEYS = {
    "background",
    "foreground",
    "cursor",
    "selection",
    "black",
    "red",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "white",
}


def test_exact_theme_names():
    assert list(BUILTIN_THEMES.keys()) == EXPECTED_NAMES


def test_every_theme_has_exactly_the_twelve_keys():
    for name, palette in BUILTIN_THEMES.items():
        assert set(palette.keys()) == EXPECTED_KEYS, f"{name} key drift"


def test_pinned_palette_values():
    d = BUILTIN_THEMES["Dracula"]
    assert d["background"] == "#1E1F29"
    assert d["foreground"] == "#F8F8F2"
    assert d["cursor"] == "#FF79C6"

    j = BUILTIN_THEMES["JetBrains Dark"]
    assert j["background"] == "#1E1E2E"
    assert j["foreground"] == "#CDD6F4"
    assert j["selection"] == "#585B70"

    m = BUILTIN_THEMES["Matrix Green"]
    assert m["background"] == "#0D1117"
    assert m["green"] == "#00FF66"

    c = BUILTIN_THEMES["Colab Light"]
    assert c["background"] == "#FFFFFF"
    assert c["foreground"] == "#1F2430"


def test_get_theme_lookup():
    assert get_theme(None) is None
    assert get_theme("") is None
    assert get_theme("No Such Theme") is None
    assert get_theme("Dracula") == BUILTIN_THEMES["Dracula"]
    assert get_theme("Dracula") is BUILTIN_THEMES["Dracula"]
