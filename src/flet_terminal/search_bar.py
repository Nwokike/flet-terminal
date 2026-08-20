"""TerminalSearchBar — compact search bar with match stepping and close."""

from __future__ import annotations

from typing import Callable

import flet as ft

from .frozen_support import thaw

__all__ = ["TerminalSearchBar"]


class TerminalSearchBar(ft.Container):
    """Search field with next/prev match stepping, match counter, and close.

    `on_search(query, start, direction)` drives the terminal search; the Dart
    side reports results through `on_selection_change` JSON which the host
    should forward via `report_result(found, count, index)` so the counter and
    stepping offsets stay in sync.
    """

    def __init__(
        self,
        on_search: Callable[[str, int, str], None],
        on_close: Callable[[], None] | None = None,
    ):
        self._on_search = on_search
        self._on_close = on_close
        self._last_index = -1
        self._count = 0

        self._search_field = ft.TextField(
            hint_text="Search buffer…",
            height=28,
            text_size=11,
            expand=True,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=0),
            bgcolor="#1E1E2E",
            border_color="#45475A",
            on_submit=lambda e: self.do_search(direction="next"),
        )
        self._counter = ft.Text(
            "",
            size=10,
            color="#A6ADC8",
        )
        self._counter.visible = False

        btn_style = ft.ButtonStyle(padding=2, visual_density=ft.VisualDensity.COMPACT)
        prev_btn = ft.IconButton(
            icon=ft.Icons.KEYBOARD_ARROW_UP_ROUNDED,
            icon_size=14,
            tooltip="Previous match",
            style=btn_style,
            on_click=lambda e: self.do_search(direction="prev"),
        )
        next_btn = ft.IconButton(
            icon=ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
            icon_size=14,
            tooltip="Next match",
            style=btn_style,
            on_click=lambda e: self.do_search(direction="next"),
        )
        close_btn = ft.IconButton(
            icon=ft.Icons.CLOSE_ROUNDED,
            icon_size=14,
            tooltip="Close search",
            style=btn_style,
            on_click=lambda e: self._handle_close(),
        )

        super().__init__(
            content=ft.Row(
                controls=[
                    self._search_field,
                    self._counter,
                    prev_btn,
                    next_btn,
                    close_btn,
                ],
                spacing=2,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(2, 1, 2, 1),
        )

    def do_search(self, direction: str = "next"):
        q = self._search_field.value or ""
        if not q:
            return
        if direction == "next":
            # Resume after the current match so repeated presses step forward.
            start = self._last_index + 1 if self._last_index >= 0 else 0
        else:
            start = self._last_index if self._last_index >= 0 else 0
        self._on_search(q, start, direction)

    def report_result(self, found: bool, count: int, index: int):
        """Update the match counter from the terminal's selection_change event."""
        self._count = count
        self._last_index = index if found else -1
        with thaw(self._counter):
            self._counter.value = (
                f"{count} found" if found and count > 0 else "No matches"
            )
            self._counter.visible = True
        try:
            if self.page:
                with thaw(self):
                    self.update()
        except RuntimeError:
            pass

    def _handle_close(self):
        with thaw(self._search_field):
            self._search_field.value = ""
        with thaw(self._counter):
            self._counter.visible = False
        self._last_index = -1
        self._count = 0
        if self._on_close:
            self._on_close()
