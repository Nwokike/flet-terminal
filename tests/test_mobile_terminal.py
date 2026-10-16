"""MobileTerminal: the M1 regression suite plus the forwarded-consumer contract.

The two regressions this file pins:
1. ``MobileTerminal()`` constructs with NO active renderer context (the 0.3.9
   ExtraKeysBar composed an ``@ft.component`` child eagerly, raising
   ``RuntimeError: No current renderer is set`` — hit on-device).
2. ``ctrl_active``/``alt_active`` setters no longer call a nonexistent
   ``ExtraKeysBar.refresh_buttons`` (latent ``AttributeError`` in 0.3.9).

Everything after that locks the surface CollabShell (the shipped consumer)
uses: constructor kwargs, method forwards, event setters, and the search
router.
"""

import json
from types import SimpleNamespace

from flet_terminal import BUILTIN_THEMES, MobileTerminal


# ─── Regression 1 + 2 ───────────────────────────────────────────────────────


def test_constructs_without_renderer_context_regression():
    # Bare construction, no @ft.component tree, no Renderer context.
    mt = MobileTerminal()
    assert mt is not None
    assert mt._keys_bar is not None


def test_ctrl_alt_setters_do_not_raise_regression():
    mt = MobileTerminal()
    mt.ctrl_active = True
    assert mt.ctrl_active is True
    assert mt._terminal.ctrl_active is True
    assert mt._keys_bar.ctrl_active is True

    mt.alt_active = True
    assert mt.alt_active is True
    assert mt._keys_bar.alt_active is True

    mt.ctrl_active = False
    mt.alt_active = False
    assert mt.ctrl_active is False
    assert mt.alt_active is False
    assert mt._keys_bar.ctrl_active is False
    assert mt._keys_bar.alt_active is False


# ─── Constructor variants ───────────────────────────────────────────────────


def test_constructor_variants():
    no_bar = MobileTerminal(show_extra_keys=False, show_search=True)
    assert no_bar._keys_bar is None
    assert no_bar.show_search is True

    with_bar = MobileTerminal(show_extra_keys=True, show_search=False)
    assert with_bar._keys_bar is not None
    assert with_bar.show_search is False


def test_constructor_kwargs_reach_terminal():
    mt = MobileTerminal(
        scrollback=5000,
        font_family="monospace",
        font_size=13.5,
        cursor_blink=False,
        cursor_style="bar",
        read_only=True,
        auto_focus=False,
    )
    assert mt._terminal.scrollback == 5000
    assert mt._terminal.font_family == "monospace"
    assert mt.font_size == 13.5
    assert mt.cursor_blink is False
    assert mt.cursor_style == "bar"
    assert mt._terminal.read_only is True
    assert mt._terminal.auto_focus is False


def test_theme_defaults_to_jetbrains_dark():
    mt = MobileTerminal()
    assert mt._terminal.theme == BUILTIN_THEMES["JetBrains Dark"]
    assert mt.theme_name == "JetBrains Dark"
    assert mt._keys_bar.active_theme == "JetBrains Dark"


def test_theme_name_none_for_custom_palette():
    custom = {k: v for k, v in BUILTIN_THEMES["Dracula"].items()}
    custom["background"] = "#010203"
    mt = MobileTerminal(theme=custom)
    assert mt.theme_name is None


# ─── Byte flow forwards ─────────────────────────────────────────────────────


def test_send_bytes_queues_on_terminal():
    mt = MobileTerminal()
    mt.send_bytes(b"payload")
    assert mt.pending_count == 1


def test_send_input_loops_back_to_host_handler():
    mt = MobileTerminal()
    got: list[bytes] = []
    mt.set_on_bytes(got.append)
    mt.send_input(b"\x1b[A")
    assert got == [b"\x1b[A"]


def test_ready_pending_clear_flush_contract():
    mt = MobileTerminal()
    assert mt.ready is False
    mt.send_bytes(b"a")
    mt.send_bytes(b"b")
    assert mt.pending_count == 2
    mt.flush()  # idempotent + safe while detached
    assert mt.pending_count == 2
    mt.clear_pending()
    assert mt.pending_count == 0


def test_set_on_unmount_fires_via_terminal_will_unmount():
    mt = MobileTerminal()
    fired: list[int] = []
    mt.set_on_unmount(lambda: fired.append(1))
    mt._terminal.will_unmount()
    assert fired == [1]


# ─── Search bar wiring ──────────────────────────────────────────────────────


def test_show_search_toggle_syncs_bar_and_menu():
    mt = MobileTerminal()
    assert mt.show_search is False
    assert mt._keys_bar.active_search is False

    mt.toggle_search()
    assert mt.show_search is True
    assert mt._search_bar.visible is True
    assert mt._keys_bar.active_search is True

    mt.toggle_search()
    assert mt.show_search is False


# ─── Theme / cursor / zoom controls ─────────────────────────────────────────


def test_set_theme_known_and_unknown():
    mt = MobileTerminal()
    mt.set_theme("Matrix Green")
    assert mt._terminal.theme == BUILTIN_THEMES["Matrix Green"]
    assert mt.theme_name == "Matrix Green"
    assert mt._keys_bar.active_theme == "Matrix Green"

    mt.set_theme("Does Not Exist")  # silent no-op
    assert mt.theme_name == "Matrix Green"


def test_set_cursor_style():
    mt = MobileTerminal()
    mt.set_cursor_style("underline")
    assert mt.cursor_style == "underline"
    assert mt._keys_bar.active_cursor == "underline"


def test_toggle_cursor_blink():
    mt = MobileTerminal()
    assert mt.cursor_blink is True
    mt.toggle_cursor_blink()
    assert mt.cursor_blink is False
    assert mt._keys_bar.active_blink is False


def test_zoom_in_out_reset_and_floor():
    mt = MobileTerminal(font_size=11.0)
    mt.zoom_in()
    mt.zoom_in()
    assert mt.font_size == 13.0
    mt.zoom_out(step=1.0)
    assert mt.font_size == 12.0
    for _ in range(20):
        mt.zoom_out(step=1.0)
    assert mt.font_size == 6.0  # floor
    mt.reset_zoom()
    assert mt.font_size == 11.0


def test_zoom_floor_noop_at_floor():
    mt = MobileTerminal(font_size=6.0)
    mt.zoom_out()
    assert mt.font_size == 6.0


# ─── Selection / clipboard router ───────────────────────────────────────────


def test_selection_router_keeps_internal_and_exposes_user_handler():
    mt = MobileTerminal()
    user_events: list = []
    handler = user_events.append
    mt.on_selection_change = handler
    # Getter returns the USER handler; the terminal still routes through ours.
    assert mt.on_selection_change is handler
    assert mt._terminal.on_selection_change == mt._internal_on_selection_change


def test_selection_router_feeds_search_counter_and_user_handler():
    mt = MobileTerminal()
    user_events: list = []
    mt.on_selection_change = user_events.append
    event = SimpleNamespace(
        data=json.dumps({"query": "x", "found": True, "count": 3, "index": 1})
    )
    mt._internal_on_selection_change(event)
    assert user_events == [event]
    assert mt._search_bar._counter.value == "3 found"
    assert mt._search_bar._counter.visible is True


def test_selection_router_ignores_non_search_events():
    mt = MobileTerminal()
    event = SimpleNamespace(data=json.dumps({"has_selection": True, "text": "hi"}))
    mt._internal_on_selection_change(event)  # must not raise or touch counter
    assert mt._search_bar._counter.visible is False


def test_selection_router_tolerates_bad_json():
    mt = MobileTerminal()
    mt._internal_on_selection_change(SimpleNamespace(data="{not json"))
    assert mt._search_bar._counter.visible is False


def test_copy_selection_headless_is_a_noop():
    mt = MobileTerminal()
    mt.copy_selection()  # no page: must return silently


# ─── Forwarded event setters ────────────────────────────────────────────────


def test_forwarded_event_setters_roundtrip():
    mt = MobileTerminal()
    for attr in (
        "on_data",
        "on_resize",
        "on_title_change",
        "on_bell",
        "on_mount",
        "on_copy",
        "on_shortcut",
    ):
        handler = lambda e: None  # noqa: E731
        setattr(mt, attr, handler)
        assert getattr(mt, attr) is handler


def test_forwarded_methods_exist_for_consumer_surface():
    mt = MobileTerminal()
    # Every method CollabShell calls must exist and be callable headless.
    for name in (
        "send_bytes",
        "send_input",
        "write",
        "clear",
        "focus",
        "search",
        "clear_selection",
        "select_all",
        "copy_selection",
        "paste",
        "set_on_bytes",
        "set_theme",
        "set_cursor_style",
        "toggle_cursor_blink",
        "toggle_search",
        "zoom_in",
        "zoom_out",
        "reset_zoom",
        "clear_pending",
        "flush",
        "set_on_unmount",
    ):
        assert callable(getattr(mt, name)), f"missing forward: {name}"
