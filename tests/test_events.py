"""Event surface: ShortcutEvent shape and typed-event resolution.

Flet 1.0 resolves the concrete event class for an `on_*` handler from the
control's annotations at runtime; if annotations ever degrade to strings
(PEP 563) the resolver silently falls back and per-handler fields like
`ShortcutEvent.shortcut` stop being populated. These tests pin that contract.
"""

from flet.controls.control_event import Event, get_event_field_type

from flet_terminal import ShortcutEvent, Terminal


def test_shortcut_event_shape():
    t = Terminal()
    e = ShortcutEvent(name="shortcut", control=t, shortcut="toggle_search")
    assert e.shortcut == "toggle_search"
    assert e.name == "shortcut"
    assert e.control is t
    assert e.data is None


def test_shortcut_event_defaults():
    e = ShortcutEvent(name="shortcut", control=None)
    assert e.shortcut == ""


def test_shortcut_event_is_a_flet_event():
    assert issubclass(ShortcutEvent, Event)


def test_annotations_are_real_objects_not_strings():
    # Regression guard: PEP 563 would turn these into strings and break
    # flet's field-type resolution.
    annotations = ShortcutEvent.__annotations__
    assert annotations["shortcut"] is str


def test_typed_event_resolution_on_shortcut_handler():
    t = Terminal()
    resolved = get_event_field_type(t, "on_shortcut")
    assert resolved is ShortcutEvent


def test_terminal_event_handlers_are_plain_control_handlers():
    # on_data/on_resize etc. stay untyped (ControlEvent); only on_shortcut and
    # on_data_channel_open carry dedicated event classes.
    t = Terminal()
    resolved = get_event_field_type(t, "on_data")
    assert resolved is not ShortcutEvent
