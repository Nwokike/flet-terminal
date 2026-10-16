"""Terminal control: defaults, wire identity, and pending-write queue semantics."""

import asyncio

import flet as ft

from flet_terminal import Terminal


def test_control_type_and_base():
    t = Terminal()
    assert t._c == "FletTerminal"
    assert isinstance(t, ft.LayoutControl)


def test_default_props():
    t = Terminal()
    assert t.scrollback == 10000
    assert t.font_family == "JetBrains Mono"
    assert t.font_size == 11.0
    assert t.cursor_blink is True
    assert t.cursor_style == "block"
    assert t.theme is None
    assert t.read_only is False
    assert t.auto_focus is True
    assert t.ctrl_active is False
    assert t.alt_active is False


def test_default_events_none_except_channel_open():
    t = Terminal()
    assert t.on_data is None
    assert t.on_resize is None
    assert t.on_modifier_reset is None
    assert t.on_title_change is None
    assert t.on_bell is None
    assert t.on_selection_change is None
    assert t.on_copy is None
    assert t.on_mount is None
    assert t.on_shortcut is None
    # The channel-open handler self-installs so DataChannel wiring always works.
    assert t.on_data_channel_open is not None


def test_internal_state_initialized():
    t = Terminal()
    assert t._pending_writes == []
    assert t._dart_ready is False
    assert t._channel_ready is False
    assert t._channel is None


def test_send_bytes_queues_while_detached():
    t = Terminal()
    t.send_bytes(b"one")
    t.send_bytes(b"two")
    assert len(t._pending_writes) == 2
    fn, args = t._pending_writes[0]
    assert fn == t.send_bytes
    assert args == (b"one",)


def test_write_queues_async_variant_while_detached():
    t = Terminal()
    t.write("hello")
    t.write(b"bytes")
    assert len(t._pending_writes) == 2
    fn, args = t._pending_writes[0]
    assert fn == t.write_async
    assert args == ("hello",)
    fn2, args2 = t._pending_writes[1]
    assert fn2 == t.write_async
    assert args2 == (b"bytes",)


def test_method_wrappers_queue_when_detached():
    t = Terminal()
    t.clear()
    t.focus()
    t.search("needle", 3, "prev")
    t.clear_selection()
    t.select_all()
    t.paste()
    queued = [fn for fn, _ in t._pending_writes]
    assert queued == [
        t.clear_async,
        t.focus_async,
        t.search_async,
        t.clear_selection_async,
        t.select_all_async,
        t.paste_async,
    ]
    _, search_args = t._pending_writes[2]
    assert search_args == ("needle", 3, "prev")


def test_send_input_bypasses_dart_entirely():
    t = Terminal()
    received: list[bytes] = []
    t.set_on_bytes(received.append)
    t.send_input(b"\t")
    assert received == [b"\t"]
    # Local loopback only — nothing was queued for Dart.
    assert t._pending_writes == []


def test_send_input_without_handler_is_dropped_silently():
    t = Terminal()
    t.send_input(b"\x1b")  # no handler registered
    assert t._pending_writes == []


def test_get_selection_is_not_queued_and_returns_none_when_not_ready():
    t = Terminal()
    assert asyncio.run(t.get_selection_async()) is None
    assert t._pending_writes == []


def test_flush_requeues_while_detached_and_never_raises():
    t = Terminal()
    t.write("x")
    t._mark_dart_ready()  # flush() path on a detached control
    assert len(t._pending_writes) == 1
    assert t._dart_ready is True


def test_will_unmount_clears_queue_and_fires_callback():
    t = Terminal()
    fired: list[int] = []
    t._on_unmount_callback = lambda: fired.append(1)
    t.send_bytes(b"q")
    t.will_unmount()
    assert fired == [1]
    assert t._pending_writes == []
    assert t._dart_ready is False


def test_will_unmount_callback_exception_is_swallowed():
    t = Terminal()

    def boom():
        raise ValueError("callback bug")

    t._on_unmount_callback = boom
    t.will_unmount()  # must not raise


def test_set_on_bytes_rebinds_live_channel_only_when_present():
    t = Terminal()
    t.set_on_bytes(lambda b: None)
    assert t._on_bytes_handler is not None
    assert t._channel is None  # channel attaches later via data_channel_open


def test_props_roundtrip():
    # Plain dataclass props: the control stores whatever is set (the zoom
    # clamp logic lives in MobileTerminal).
    t = Terminal()
    t.font_size = 14.5
    t.scrollback = 5000
    t.read_only = True
    assert t.font_size == 14.5
    assert t.scrollback == 5000
    assert t.read_only is True
