"""ExtraKeysBar: byte table, sticky-modifier transforms, and repaint plumbing.

Covers both M1 regression fixes:
* `refresh_buttons()` exists and repaints the CTRL/ALT toggles imperatively.
* construction is renderer-independent (plain buttons, no @ft.component).
"""

from flet_terminal import DEFAULT_EXTRA_KEYS, ExtraKeysBar

EXPECTED_KEYS = [
    ("ESC", b"\x1b"),
    ("TAB", b"\t"),
    ("CTRL", None),
    ("ALT", None),
    ("↑", b"\x1b[A"),
    ("↓", b"\x1b[B"),
    ("←", b"\x1b[D"),
    ("→", b"\x1b[C"),
    ("-", b"-"),
    ("/", b"/"),
    ("|", b"|"),
    ("~", b"~"),
    ("^", b"^"),
]


def _bar(**kwargs):
    sent: list[bytes] = []
    mods: list[tuple[bool, bool]] = []
    bar = ExtraKeysBar(
        on_send_payload=sent.append,
        on_modifier_change=lambda c, a: mods.append((c, a)),
        **kwargs,
    )
    return bar, sent, mods


def test_exact_default_byte_table():
    assert DEFAULT_EXTRA_KEYS == EXPECTED_KEYS


def test_constructs_without_any_renderer_context():
    bar, _, _ = _bar()
    assert bar is not None
    assert bar._btn_ctrl is not None
    assert bar._btn_alt is not None


def test_refresh_buttons_exists_and_repaints_state():
    bar, _, _ = _bar()
    # Two independent smoke paths: no-page (warns, stays local) must not raise.
    bar.refresh_buttons()
    bar.ctrl_active = True
    bar.refresh_buttons()
    assert bar.ctrl_active is True
    bar.alt_active = True
    bar.refresh_buttons()
    assert bar.alt_active is True


def test_property_setters_notify_and_sync_state():
    bar, _, _ = _bar()
    bar.ctrl_active = True
    assert bar._mods.ctrl is True
    bar.ctrl_active = False
    assert bar._mods.ctrl is False
    # Setters are silent by design (they reflect external state, they don't
    # report a user modulation).
    assert bar._mods.alt is False


def test_toggle_modifier_flips_and_notifies():
    bar, _, mods = _bar()
    bar._toggle_modifier(is_ctrl=True)
    assert bar._mods.ctrl is True
    assert mods == [(True, False)]
    bar._toggle_modifier(is_ctrl=True)
    assert bar._mods.ctrl is False
    assert mods == [(True, False), (False, False)]
    bar._toggle_modifier(is_ctrl=False)
    assert bar._mods.alt is True
    assert mods[-1] == (False, True)


def test_reset_modifiers_only_notifies_when_active():
    bar, _, mods = _bar()
    bar.reset_modifiers()
    assert mods == []
    bar._toggle_modifier(is_ctrl=True)
    mods.clear()
    bar.reset_modifiers()
    assert bar._mods.ctrl is False
    assert bar._mods.alt is False
    assert mods == [(False, False)]


def test_ctrl_transform_lowercase_and_uppercase():
    bar, sent, mods = _bar()
    bar.ctrl_active = True
    bar._send_payload(b"a")
    assert sent == [b"\x01"]
    assert bar.ctrl_active is False  # consumed
    assert mods[-1] == (False, False)

    bar.ctrl_active = True
    bar._send_payload(b"A")
    assert sent[-1] == b"\x01"


def test_ctrl_consumed_but_payload_untouched_for_non_letters():
    bar, sent, _ = _bar()
    bar.ctrl_active = True
    bar._send_payload(b"5")
    assert sent == [b"5"]
    assert bar.ctrl_active is False


def test_ctrl_not_consumed_for_multi_byte_payload():
    bar, sent, _ = _bar()
    bar.ctrl_active = True
    bar._send_payload(b"ab")
    assert sent == [b"ab"]
    assert bar.ctrl_active is True


def test_alt_prefixes_escape_and_is_consumed():
    bar, sent, mods = _bar()
    bar.alt_active = True
    bar._send_payload(b"x")
    assert sent == [b"\x1bx"]
    assert bar.alt_active is False
    assert mods[-1] == (False, False)


def test_ctrl_alt_combined():
    bar, sent, _ = _bar()
    bar.ctrl_active = True
    bar.alt_active = True
    bar._send_payload(b"c")
    assert sent == [b"\x1b\x03"]  # ALT ESC prefix + CTRL-C
    assert bar.ctrl_active is False
    assert bar.alt_active is False


def test_custom_key_layout_replaces_default():
    bar, _, _ = _bar(show_settings=False, keys=[("X", b"x")])
    assert len(bar._keys_row.controls) == 1


def test_settings_menu_built_with_checkmarks():
    bar, _, _ = _bar()

    def checked_texts(bar):
        items = bar._get_settings_menu_items()
        return [
            getattr(i.content, "value", "")
            for i in items
            if getattr(i, "checked", False)
        ]

    # Defaults: one theme + cursor blink + search bar.
    assert sorted(checked_texts(bar)) == [
        "Cursor Blink",
        "JetBrains Dark",
        "Search Bar",
    ]
    bar.active_theme = "Dracula"
    assert sorted(checked_texts(bar)) == ["Cursor Blink", "Dracula", "Search Bar"]


def test_update_settings_menu_is_safe_headless():
    bar, _, _ = _bar()
    bar.active_cursor = "bar"
    bar.update_settings_menu()  # no page: must not raise


def test_collapse_toggle_swaps_content():
    bar, _, _ = _bar()
    expanded = bar._expanded_row
    collapsed = bar._collapsed_view
    assert bar.content is expanded
    bar._on_toggle_collapse(None)
    assert bar.content is collapsed
    bar._on_toggle_collapse(None)
    assert bar.content is expanded
