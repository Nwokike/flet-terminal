"""TerminalSearchBar — compact search bar component above the terminal grid."""

from __future__ import annotations
from typing import Callable
import flet as ft

__all__ = ["TerminalSearchBar"]


class TerminalSearchBar(ft.Container):
    """Compact search field and controls for terminal scrollback buffer querying."""

    def __init__(
        self,
        on_search: Callable[[str, int], None],
    ):
        self._on_search = on_search
        self._search_field = ft.TextField(
            hint_text="Search buffer…",
            height=28,
            text_size=11,
            expand=True,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=0),
            bgcolor="#1E1E2E",
            border_color="#45475A",
            on_submit=lambda e: self.do_search(start=0),
        )
        search_btn = ft.IconButton(
            icon=ft.Icons.SEARCH,
            icon_size=14,
            tooltip="Search",
            style=ft.ButtonStyle(padding=2, visual_density=ft.VisualDensity.COMPACT),
            on_click=lambda e: self.do_search(start=0),
        )
        super().__init__(
            content=ft.Row(
                controls=[self._search_field, search_btn],
                spacing=2,
            ),
            padding=ft.Padding(2, 1, 2, 1),
        )

    def do_search(self, start: int = 0):
        q = self._search_field.value or ""
        if q:
            self._on_search(q, start)
