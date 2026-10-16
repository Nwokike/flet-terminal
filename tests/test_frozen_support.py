"""frozen_support: the thaw/control_update contract for declarative trees."""

from types import SimpleNamespace

import pytest

from flet_terminal.frozen_support import control_update, thaw


def test_thaw_lifts_and_restores_frozen_flag():
    control = SimpleNamespace()
    control._frozen = 1
    with thaw(control):
        assert getattr(control, "_frozen", None) is None
    assert control._frozen == 1


def test_thaw_tolerates_none():
    with thaw(None):
        pass  # no-op by design (optional-control call sites)


def test_thaw_restores_even_on_exception():
    control = SimpleNamespace()
    control._frozen = 2
    with pytest.raises(ValueError):
        with thaw(control):
            raise ValueError("boom")
    assert control._frozen == 2


def test_thaw_on_unfrozen_control_is_a_noop():
    control = SimpleNamespace()
    with thaw(control):
        pass
    assert not hasattr(control, "_frozen")


def test_control_update_rejects_frozen_control():
    control = SimpleNamespace()
    control._frozen = 1
    with pytest.raises(RuntimeError):
        control_update(control)


def test_control_update_tolerates_none():
    control_update(None)  # no-op by design


def test_control_update_without_page_does_not_raise():
    control = SimpleNamespace()
    control_update(control)  # detached: logs a warning, returns None


def test_sanctioned_pattern_assignment_inside_thaw():
    # The documented usage: property assignment AND control_update together
    # inside a single thaw block.
    control = SimpleNamespace(_frozen=1)
    with thaw(control):
        control.value = "updated"
        control_update(control)
    assert control.value == "updated"
    assert control._frozen == 1
