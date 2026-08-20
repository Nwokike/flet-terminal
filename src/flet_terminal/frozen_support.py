"""Imperative updates for controls living inside a declarative Flet tree."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

__all__ = ["thaw"]


@contextmanager
def thaw(control: Any) -> Iterator[None]:
    """Temporarily lift Flet's declarative "frozen" flag from a control.

    Controls that are part of a ``@ft.component`` render tree are stamped
    ``_frozen`` by Flet's object patcher, after which property assignment and
    ``update()`` on them raise ``RuntimeError("Frozen controls cannot be
    updated.")``. Flet performs this exact delete/restore dance internally
    (``base_control._before_update_safe``); this helper lets host apps mutate
    long-lived controls (terminal, key bar, search bar) in place instead of
    forcing a re-render of the owning component.
    """
    if control is None:
        yield
        return
    prev = getattr(control, "_frozen", None)
    if prev is not None:
        object.__delattr__(control, "_frozen")
    try:
        yield
    finally:
        if prev is not None:
            object.__setattr__(control, "_frozen", prev)
