"""MobileTerminal — Terminal with built-in extra-keys bar, search, and settings.

MobileTerminal is a ``ft.Column`` that bundles the bare :class:`~flet_terminal.Terminal`
control with a collapsible Termux-style virtual accessory bar (ESC, TAB, CTRL, ALT,
arrows, symbols), a compact search bar, and a settings popup (theme, cursor, blink).

Usage::

    from flet_terminal import MobileTerminal
    page.add(MobileTerminal(font_size=14))
"""

from __future__ import annotations

from typing import Any, Callable, Optional
import flet as ft
from flet_terminal.terminal import Terminal

__all__ = ["MobileTerminal"]

DEFAULT_EXTRA_KEYS: list[tuple[str, bytes | None]] = [
    ("ESC", b"\x1b"),
    ("TAB", b"\t"),
    ("CTRL", None),
    ("ALT", None),
    ("▲", b"\x1b[A"),
    ("▼", b"\x1b[B"),
    ("◀", b"\x1b[D"),
    ("▶", b"\x1b[C"),
    ("-", b"-"),
    ("/", b"/"),
    ("|", b"|"),
    ("~", b"~"),
]

BUILTIN_THEMES: dict[str, dict[str, str]] = {
    "Dracula": {
        "background": "#1E1F29",
        "foreground": "#F8F8F2",
        "cursor": "#FF79C6",
        "selection": "#44475A",
        "black": "#21222C",
        "red": "#FF5555",
        "green": "#50FA7B",
        "yellow": "#F1FA8C",
        "blue": "#BD93F9",
        "magenta": "#FF79C6",
        "cyan": "#8BE9FD",
        "white": "#F8F8F2",
    },
    "JetBrains Dark": {
        "background": "#1E1E2E",
        "foreground": "#CDD6F4",
        "cursor": "#F5E0DC",
        "selection": "#585B70",
        "black": "#45475A",
        "red": "#F38BA8",
        "green": "#A6E3A1",
        "yellow": "#F9E2AF",
        "blue": "#89B4FA",
        "magenta": "#F5C2E7",
        "cyan": "#94E2D5",
        "white": "#BAC2DE",
    },
    "Matrix Green": {
        "background": "#0D1117",
        "foreground": "#00FF66",
        "cursor": "#00FF66",
        "selection": "#163320",
        "black": "#0D1117",
        "red": "#FF5555",
        "green": "#00FF66",
        "yellow": "#FFFF00",
        "blue": "#0088FF",
        "magenta": "#FF00FF",
        "cyan": "#00FFFF",
        "white": "#FFFFFF",
    },
}


class MobileTerminal(ft.Column):
    """Terminal with built-in virtual accessory keys, search, and settings.

    Parameters
    ----------
    show_extra_keys : bool, default=True
        Whether the extra-keys bar is shown.
    show_search : bool, default=True
        Whether the search bar is shown above the terminal.
    show_settings : bool, default=True
        Whether the settings gear icon is shown in the keys bar.
    extra_keys_visible : bool, default=True
        Whether the keys bar starts expanded (vs collapsed).
    extra_keys : list[(str, bytes|None)], optional
        Custom keys. ``None`` payload marks a sticky-modifier toggle.
    theme_name : str, optional
        One of ``"Dracula"``, ``"JetBrains Dark"``, ``"Matrix Green"``.
    **terminal_kwargs
        Forwarded to the underlying :class:`~flet_terminal.Terminal`.
    """

    def __init__(
        self,
        *,
        show_extra_keys: bool = True,
        show_search: bool = True,
        extra_keys_visible: bool = True,
        extra_keys: list[tuple[str, bytes | None]] | None = None,
        theme_name: str | None = None,
        **terminal_kwargs: Any,
    ):
        if theme_name is not None and "theme" not in terminal_kwargs:
            preset = BUILTIN_THEMES.get(theme_name)
            if preset is not None:
                terminal_kwargs["theme"] = preset

        terminal_kwargs.setdefault("expand", True)
        self._terminal = Terminal(**terminal_kwargs)
        self._extra_keys = list(extra_keys or DEFAULT_EXTRA_KEYS)
        self._keys_visible = extra_keys_visible
        self._keys_enabled = show_extra_keys
        self._ctrl_active: bool = False
        self._alt_active: bool = False

        # Sync internal modifier state when the terminal resets modifiers
        self._terminal.on_modifier_reset = lambda e: self._on_terminal_modifier_reset()

        self._search_bar = self._build_search_bar() if show_search else None
        self._keys_bar, self._keys_collapsed = self._build_keys_bars()

        controls: list[ft.Control] = []
        if self._search_bar is not None:
            controls.append(self._search_bar)
        controls.append(self._terminal)
        if self._keys_enabled:
            controls.append(self._keys_bar)
            controls.append(self._keys_collapsed)

        super().__init__(controls=controls, expand=True, spacing=0, tight=True)

        self._keys_bar.visible = self._keys_visible
        self._keys_collapsed.visible = not self._keys_visible

    # ── Search bar ────────────────────────────────────────────────────

    def _build_search_bar(self) -> ft.Container:
        self._search_field = ft.TextField(
            hint_text="Search…",
            height=28,
            text_size=11,
            expand=True,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=0),
            bgcolor="#1E1E2E",
            border_color="#45475A",
            on_submit=lambda e: self._do_search_next(),
        )
        search_btn = ft.IconButton(
            icon=ft.Icons.SEARCH,
            icon_size=14,
            tooltip="Search",
            style=ft.ButtonStyle(padding=2, visual_density=ft.VisualDensity.COMPACT),
            on_click=lambda e: self._do_search(),
        )
        return ft.Container(
            content=ft.Row(
                controls=[self._search_field, search_btn],
                spacing=2,
            ),
            padding=ft.Padding(2, 1, 2, 1),
        )

    def _on_terminal_modifier_reset(self):
        """Called when the Dart side auto-resets modifiers after a keystroke."""
        if self._ctrl_active or self._alt_active:
            self._ctrl_active = False
            self._alt_active = False
            self._refresh_modifier_buttons()

    def _do_search(self):
        q = self._search_field.value or ""
        if q:
            self._terminal.search(q, start=0)

    def _do_search_next(self):
        q = self._search_field.value or ""
        if q:
            # Step through matches by always searching from start=0;
            # the Dart side wraps to the first match when it hits the end.
            self._terminal.search(q, start=0)

    # ── Extra-keys bar ────────────────────────────────────────────────

    def _make_key_btn(
        self, label: str, payload: bytes | None, bg: str = "#313244"
    ) -> ft.Control:
        if payload is None:
            is_ctrl = label == "CTRL"
            btn = ft.Button(
                label,
                height=28,
                style=ft.ButtonStyle(
                    padding=ft.Padding.symmetric(horizontal=4, vertical=0),
                    bgcolor=bg,
                    color="#CDD6F4",
                    text_style=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD),
                    visual_density=ft.VisualDensity.COMPACT,
                    side=ft.BorderSide(width=0),
                ),
                on_click=lambda e, c=is_ctrl: self._toggle_modifier(c),
            )
            if is_ctrl:
                self._btn_ctrl = btn
            else:
                self._btn_alt = btn
            return btn
        return ft.Button(
            content=ft.Text(label, size=11, weight=ft.FontWeight.BOLD, color="#CDD6F4"),
            height=28,
            style=ft.ButtonStyle(
                padding=ft.Padding.symmetric(horizontal=3, vertical=0),
                bgcolor=bg,
                visual_density=ft.VisualDensity.COMPACT,
                side=ft.BorderSide(width=0),
            ),
            on_click=lambda e, p=payload: self._send_key_payload(p),
        )

    def _send_key_payload(self, payload: bytes):
        if self._ctrl_active and len(payload) == 1:
            code = payload[0]
            if 97 <= code <= 122:
                payload = bytes([code - 96])
            elif 65 <= code <= 90:
                payload = bytes([code - 64])
            self._ctrl_active = False
            self._refresh_modifier_buttons()
        if self._alt_active:
            payload = b"\x1b" + payload
            self._alt_active = False
            self._refresh_modifier_buttons()
        self._terminal.send_bytes(payload)

    def _toggle_modifier(self, is_ctrl: bool):
        if is_ctrl:
            self._ctrl_active = not self._ctrl_active
        else:
            self._alt_active = not self._alt_active
        self._refresh_modifier_buttons()

    def _refresh_modifier_buttons(self):
        shared = dict(
            padding=ft.Padding.symmetric(horizontal=4, vertical=0),
            text_style=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD),
            visual_density=ft.VisualDensity.COMPACT,
            side=ft.BorderSide(width=0),
        )
        self._btn_ctrl.style = ft.ButtonStyle(
            bgcolor="#8BE9FD" if self._ctrl_active else "#313244",
            color="#1E1E1E" if self._ctrl_active else "#CDD6F4",
            **shared,
        )
        self._btn_alt.style = ft.ButtonStyle(
            bgcolor="#8BE9FD" if self._alt_active else "#313244",
            color="#1E1E1E" if self._alt_active else "#CDD6F4",
            **shared,
        )
        self._btn_ctrl.update()
        self._btn_alt.update()
        self._terminal.ctrl_active = self._ctrl_active
        self._terminal.alt_active = self._alt_active
        if self.page:
            self.page.update()

    def _build_keys_bars(self) -> tuple[ft.Container, ft.Container]:
        self._btn_ctrl = None
        self._btn_alt = None
        key_controls: list[ft.Control] = [
            ft.IconButton(
                icon=ft.Icons.ARROW_DROP_DOWN,
                icon_size=20,
                tooltip="Hide keys",
                style=ft.ButtonStyle(
                    padding=2, visual_density=ft.VisualDensity.COMPACT
                ),
                on_click=lambda e: self._toggle_keys_bar(),
            ),
        ]
        for label, payload in self._extra_keys:
            key_controls.append(self._make_key_btn(label, payload))

        self._keys_row = ft.Row(
            controls=key_controls,
            scroll=ft.ScrollMode.ALWAYS,
            spacing=3,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        expanded = ft.Container(
            content=ft.Column(
                controls=[
                    self._keys_row,
                    ft.Container(
                        height=1,
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment.CENTER_LEFT,
                            end=ft.Alignment.CENTER_RIGHT,
                            colors=["#45475A80", "#18182500", "#18182500", "#45475A80"],
                        ),
                    ),
                ],
                spacing=0,
            ),
            padding=ft.Padding(4, 1, 4, 1),
            bgcolor="#181825",
            border=ft.Border.only(top=ft.BorderSide(1, "#313244")),
            visible=True,
        )
        collapsed = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.ARROW_DROP_UP,
                        icon_size=20,
                        tooltip="Show keys",
                        style=ft.ButtonStyle(
                            padding=2, visual_density=ft.VisualDensity.COMPACT
                        ),
                        on_click=lambda e: self._toggle_keys_bar(),
                    ),
                    ft.Container(expand=True),
                ],
            ),
            height=28,
            bgcolor="#181825",
            border=ft.Border.only(top=ft.BorderSide(1, "#313244")),
            visible=False,
        )
        return expanded, collapsed

    def _toggle_keys_bar(self):
        self._keys_visible = not self._keys_visible
        self._keys_bar.visible = self._keys_visible
        self._keys_collapsed.visible = not self._keys_visible
        if self.page:
            self.page.update()

    # ── Settings popup ───────────────────────────────────────────────

    # ── Forwarded Terminal properties ────────────────────────────────

    @property
    def terminal(self) -> Terminal:
        return self._terminal

    @property
    def scrollback(self) -> int | None:
        return self._terminal.scrollback

    @scrollback.setter
    def scrollback(self, v: int | None):
        self._terminal.scrollback = v

    @property
    def font_family(self) -> str | None:
        return self._terminal.font_family

    @font_family.setter
    def font_family(self, v: str | None):
        self._terminal.font_family = v
        self._terminal.update()

    @property
    def font_size(self) -> float | None:
        return self._terminal.font_size

    @font_size.setter
    def font_size(self, v: float | None):
        self._terminal.font_size = v
        self._terminal.update()

    @property
    def cursor_blink(self) -> bool | None:
        return self._terminal.cursor_blink

    @cursor_blink.setter
    def cursor_blink(self, v: bool | None):
        self._terminal.cursor_blink = v
        self._terminal.update()

    @property
    def cursor_style(self) -> str | None:
        return self._terminal.cursor_style

    @cursor_style.setter
    def cursor_style(self, v: str | None):
        self._terminal.cursor_style = v
        self._terminal.update()

    @property
    def theme(self) -> dict[str, Any] | None:
        return self._terminal.theme

    @theme.setter
    def theme(self, v: dict[str, Any] | None):
        self._terminal.theme = v
        self._terminal.update()

    @property
    def read_only(self) -> bool | None:
        return self._terminal.read_only

    @read_only.setter
    def read_only(self, v: bool | None):
        self._terminal.read_only = v

    @property
    def auto_focus(self) -> bool | None:
        return self._terminal.auto_focus

    @auto_focus.setter
    def auto_focus(self, v: bool | None):
        self._terminal.auto_focus = v

    @property
    def ctrl_active(self) -> bool | None:
        return self._ctrl_active

    @ctrl_active.setter
    def ctrl_active(self, v: bool | None):
        self._ctrl_active = bool(v)
        self._refresh_modifier_buttons()

    @property
    def alt_active(self) -> bool | None:
        return self._alt_active

    @alt_active.setter
    def alt_active(self, v: bool | None):
        self._alt_active = bool(v)
        self._refresh_modifier_buttons()

    # ── Forwarded events ─────────────────────────────────────────────

    @property
    def on_data(self) -> Optional[ft.ControlEventHandler]:
        return self._terminal.on_data

    @on_data.setter
    def on_data(self, h: Optional[ft.ControlEventHandler]):
        self._terminal.on_data = h

    @property
    def on_resize(self) -> Optional[ft.ControlEventHandler]:
        return self._terminal.on_resize

    @on_resize.setter
    def on_resize(self, h: Optional[ft.ControlEventHandler]):
        self._terminal.on_resize = h

    @property
    def on_modifier_reset(self) -> Optional[ft.ControlEventHandler]:
        return self._terminal.on_modifier_reset

    @on_modifier_reset.setter
    def on_modifier_reset(self, h: Optional[ft.ControlEventHandler]):
        self._terminal.on_modifier_reset = h

    @property
    def on_title_change(self) -> Optional[ft.ControlEventHandler]:
        return self._terminal.on_title_change

    @on_title_change.setter
    def on_title_change(self, h: Optional[ft.ControlEventHandler]):
        self._terminal.on_title_change = h

    @property
    def on_bell(self) -> Optional[ft.ControlEventHandler]:
        return self._terminal.on_bell

    @on_bell.setter
    def on_bell(self, h: Optional[ft.ControlEventHandler]):
        self._terminal.on_bell = h

    @property
    def on_selection_change(self) -> Optional[ft.ControlEventHandler]:
        return self._terminal.on_selection_change

    @on_selection_change.setter
    def on_selection_change(self, h: Optional[ft.ControlEventHandler]):
        self._terminal.on_selection_change = h

    # ── Forwarded methods ────────────────────────────────────────────

    def write(self, data: str | bytes):
        return self._terminal.write(data)

    def write_async(self, data: str | bytes):
        return self._terminal.write_async(data)

    def clear(self):
        return self._terminal.clear()

    def clear_async(self):
        return self._terminal.clear_async()

    def focus(self):
        return self._terminal.focus()

    def focus_async(self):
        return self._terminal.focus_async()

    def search(self, query: str, start: int = 0):
        return self._terminal.search(query, start)

    def search_async(self, query: str, start: int = 0):
        return self._terminal.search_async(query, start)

    def clear_selection(self):
        return self._terminal.clear_selection()

    def clear_selection_async(self):
        return self._terminal.clear_selection_async()

    def select_all(self):
        return self._terminal.select_all()

    def select_all_async(self):
        return self._terminal.select_all_async()

    def send_bytes(self, payload: bytes):
        return self._terminal.send_bytes(payload)

    def set_on_bytes(self, handler: Callable[[bytes], None]):
        return self._terminal.set_on_bytes(handler)
