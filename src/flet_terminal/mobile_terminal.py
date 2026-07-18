"""MobileTerminal — composite responsive control combining Terminal, virtual keyboard bar, and search."""

from __future__ import annotations
from typing import Any, Callable
import flet as ft
from .terminal import Terminal
from .extra_keys import ExtraKeysBar, DEFAULT_EXTRA_KEYS
from .search_bar import TerminalSearchBar
from .themes import get_theme, BUILTIN_THEMES

__all__ = ["MobileTerminal"]


class MobileTerminal(ft.Column):
    """High-level terminal wrapper with responsive virtual extra keys, sticky modifiers, and search."""

    def __init__(
        self,
        show_extra_keys: bool = True,
        show_search: bool = True,
        show_settings: bool = True,
        scrollback: int = 10000,
        font_family: str = "JetBrains Mono",
        font_size: float = 13.0,
        cursor_blink: bool = True,
        cursor_style: str = "block",
        theme: dict[str, Any] | None = None,
        read_only: bool = False,
        auto_focus: bool = True,
        extra_keys: list[tuple[str, bytes | None]] | None = None,
        expand: bool | int = True,
    ):
        super().__init__(expand=expand, spacing=0)

        self._terminal = Terminal(
            scrollback=scrollback,
            font_family=font_family,
            font_size=font_size,
            cursor_blink=cursor_blink,
            cursor_style=cursor_style,
            theme=theme or BUILTIN_THEMES["JetBrains Dark"],
            read_only=read_only,
            auto_focus=auto_focus,
            expand=True,
        )

        self._search_bar: TerminalSearchBar | None = None
        if show_search:
            self._search_bar = TerminalSearchBar(on_search=self._terminal.search)

        self._keys_bar: ExtraKeysBar | None = None
        if show_extra_keys:
            self._keys_bar = ExtraKeysBar(
                on_send_payload=self._terminal.send_bytes,
                on_modifier_change=self._on_modifier_change,
                show_settings=show_settings,
                on_set_theme=self.set_theme,
                on_set_cursor=self.set_cursor_style,
                on_toggle_blink=self.toggle_cursor_blink,
                on_toggle_search=self.toggle_search,
                keys=extra_keys or DEFAULT_EXTRA_KEYS,
            )
            self._terminal.on_modifier_reset = lambda e: (
                self._keys_bar.reset_modifiers() if self._keys_bar else None
            )

        controls: list[ft.Control] = [self._terminal]
        if self._search_bar:
            controls.append(self._search_bar)
        if self._keys_bar:
            controls.append(self._keys_bar)

        self.controls = controls

    def _on_modifier_change(self, ctrl: bool, alt: bool):
        self._terminal.ctrl_active = ctrl
        self._terminal.alt_active = alt
        self._terminal.update()

    @property
    def show_search(self) -> bool:
        return self._search_bar.visible if self._search_bar else False

    @show_search.setter
    def show_search(self, val: bool):
        if not self._search_bar and val:
            self._search_bar = TerminalSearchBar(on_search=self._terminal.search)
            if self._keys_bar and self._keys_bar in self.controls:
                self.controls.insert(
                    self.controls.index(self._keys_bar), self._search_bar
                )
            else:
                self.controls.append(self._search_bar)
        if self._search_bar:
            self._search_bar.visible = val
            self.update()

    def toggle_search(self):
        """Toggle visibility of the search bar."""
        self.show_search = not self.show_search

    def set_theme(self, theme_name: str):
        """Switch the active terminal color theme by name."""
        preset = get_theme(theme_name)
        if preset:
            self._terminal.theme = preset
            self._terminal.update()

    def set_cursor_style(self, style: str):
        """Set cursor shape ('block', 'underline', 'bar')."""
        self._terminal.cursor_style = style
        self._terminal.update()

    def toggle_cursor_blink(self):
        """Toggle blinking animation for the cursor."""
        self._terminal.cursor_blink = not self._terminal.cursor_blink
        self._terminal.update()

    # ─── Forwarded Terminal Methods & Properties ───────────────────────────

    @property
    def ctrl_active(self) -> bool:
        return self._terminal.ctrl_active or False

    @ctrl_active.setter
    def ctrl_active(self, val: bool):
        self._terminal.ctrl_active = val
        if self._keys_bar:
            self._keys_bar.ctrl_active = val
            self._keys_bar.refresh_buttons()

    @property
    def alt_active(self) -> bool:
        return self._terminal.alt_active or False

    @alt_active.setter
    def alt_active(self, val: bool):
        self._terminal.alt_active = val
        if self._keys_bar:
            self._keys_bar.alt_active = val
            self._keys_bar.refresh_buttons()

    def send_bytes(self, payload: bytes):
        self._terminal.send_bytes(payload)

    def write(self, data: str | bytes):
        self._terminal.write(data)

    def clear(self):
        self._terminal.clear()

    def focus(self):
        self._terminal.focus()

    def search(self, query: str, start: int = 0):
        self._terminal.search(query, start)

    def clear_selection(self):
        self._terminal.clear_selection()

    def select_all(self):
        self._terminal.select_all()

    def set_on_bytes(self, handler: Callable[[bytes], None]):
        self._terminal.set_on_bytes(handler)

    # Forwarded event handler accessors
    @property
    def on_data(self):
        return self._terminal.on_data

    @on_data.setter
    def on_data(self, val):
        self._terminal.on_data = val

    @property
    def on_resize(self):
        return self._terminal.on_resize

    @on_resize.setter
    def on_resize(self, val):
        self._terminal.on_resize = val

    @property
    def on_title_change(self):
        return self._terminal.on_title_change

    @on_title_change.setter
    def on_title_change(self, val):
        self._terminal.on_title_change = val

    @property
    def on_bell(self):
        return self._terminal.on_bell

    @on_bell.setter
    def on_bell(self, val):
        self._terminal.on_bell = val

    @property
    def on_selection_change(self):
        return self._terminal.on_selection_change

    @on_selection_change.setter
    def on_selection_change(self, val):
        self._terminal.on_selection_change = val
