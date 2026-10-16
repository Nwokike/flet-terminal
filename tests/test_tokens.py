"""Design tokens: exact values shared by the bar, buttons, and settings menu."""

from flet_terminal.tokens import (
    BTN_FONT_SIZE,
    BTN_HEIGHT,
    COLOR_ACTIVE_BG,
    COLOR_ACTIVE_FG,
    COLOR_BORDER,
    COLOR_INACTIVE_BG,
    COLOR_INACTIVE_FG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
)


def test_token_values():
    assert SPACE_XS == 2
    assert SPACE_SM == 4
    assert SPACE_MD == 8
    assert BTN_HEIGHT == 28
    assert BTN_FONT_SIZE == 11
    assert COLOR_ACTIVE_BG == "#8BE9FD"
    assert COLOR_ACTIVE_FG == "#1E1E1E"
    assert COLOR_INACTIVE_BG == "#313244"
    assert COLOR_INACTIVE_FG == "#CDD6F4"
    assert COLOR_BORDER == "#45475A"
