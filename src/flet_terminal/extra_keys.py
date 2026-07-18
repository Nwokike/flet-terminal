"""ExtraKeysBar — virtual accessory keyboard and settings toolbar for FletTerminal."""

from __future__ import annotations
from typing import Callable
import flet as ft
from .tokens import (
    BTN_HEIGHT,
    BTN_FONT_SIZE,
    COLOR_ACTIVE_BG,
    COLOR_ACTIVE_FG,
    COLOR_INACTIVE_BG,
    COLOR_INACTIVE_FG,
    SPACE_XS,
)

__all__ = ["DEFAULT_EXTRA_KEYS", "ExtraKeysBar"]

DEFAULT_EXTRA_KEYS: list[tuple[str, bytes | None]] = [
    ("ESC", b"\x1b"),
    ("TAB", b"\t"),
    ("CTRL", None),
    ("ALT", None),
    ("-", b"-"),
    ("/", b"/"),
    ("|", b"|"),
    ("~", b"~"),
    ("^", b"^"),
    ("↑", b"\x1b[A"),
    ("↓", b"\x1b[B"),
    ("←", b"\x1b[D"),
    ("→", b"\x1b[C"),
]


class ExtraKeysBar(ft.Container):
    """Virtual toolbar displaying quick keys, sticky modifier toggles, and settings."""

    def __init__(
        self,
        on_send_payload: Callable[[bytes], None],
        on_modifier_change: Callable[[bool, bool], None],
        show_settings: bool = True,
        on_set_theme: Callable[[str], None] | None = None,
        on_set_cursor: Callable[[str], None] | None = None,
        on_toggle_blink: Callable[[], None] | None = None,
        keys: list[tuple[str, bytes | None]] | None = None,
    ):
        self._on_send_payload = on_send_payload
        self._on_modifier_change = on_modifier_change
        self._on_set_theme = on_set_theme
        self._on_set_cursor = on_set_cursor
        self._on_toggle_blink = on_toggle_blink
        self._keys = keys or DEFAULT_EXTRA_KEYS

        self.ctrl_active = False
        self.alt_active = False
        self._collapsed = False

        self._btn_ctrl: ft.Button | None = None
        self._btn_alt: ft.Button | None = None

        self._toggle_btn = ft.IconButton(
            icon=ft.Icons.ARROW_DROP_DOWN,
            icon_size=16,
            tooltip="Collapse virtual keys",
            style=ft.ButtonStyle(padding=2, visual_density=ft.VisualDensity.COMPACT),
            on_click=self._on_toggle_collapse,
        )

        controls: list[ft.Control] = [self._toggle_btn]
        if show_settings:
            controls.append(self._build_settings_menu())

        for label, payload in self._keys:
            controls.append(self._make_key_btn(label, payload))

        self._keys_row = ft.Row(
            controls=controls,
            spacing=SPACE_XS,
            scroll=ft.ScrollMode.AUTO,
        )

        super().__init__(
            content=self._keys_row,
            padding=ft.Padding(4, 2, 4, 2),
            bgcolor="#1A1B26",
        )

    def _build_settings_menu(self) -> ft.PopupMenuButton:
        return ft.PopupMenuButton(
            icon=ft.Icons.SETTINGS,
            icon_size=16,
            tooltip="Terminal Settings",
            style=ft.ButtonStyle(padding=2, visual_density=ft.VisualDensity.COMPACT),
            items=[
                ft.PopupMenuItem(
                    content=ft.Text("Theme Presets", weight=ft.FontWeight.BOLD),
                    disabled=True,
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Dracula"),
                    on_click=lambda e: (
                        self._on_set_theme("Dracula") if self._on_set_theme else None
                    ),
                ),
                ft.PopupMenuItem(
                    content=ft.Text("JetBrains Dark"),
                    on_click=lambda e: (
                        self._on_set_theme("JetBrains Dark")
                        if self._on_set_theme
                        else None
                    ),
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Matrix Green"),
                    on_click=lambda e: (
                        self._on_set_theme("Matrix Green")
                        if self._on_set_theme
                        else None
                    ),
                ),
                ft.PopupMenuItem(),
                ft.PopupMenuItem(
                    content=ft.Text("Cursor Style", weight=ft.FontWeight.BOLD),
                    disabled=True,
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Block"),
                    on_click=lambda e: (
                        self._on_set_cursor("block") if self._on_set_cursor else None
                    ),
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Underline"),
                    on_click=lambda e: (
                        self._on_set_cursor("underline")
                        if self._on_set_cursor
                        else None
                    ),
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Bar"),
                    on_click=lambda e: (
                        self._on_set_cursor("bar") if self._on_set_cursor else None
                    ),
                ),
                ft.PopupMenuItem(),
                ft.PopupMenuItem(
                    content=ft.Text("Toggle Cursor Blink"),
                    on_click=lambda e: (
                        self._on_toggle_blink() if self._on_toggle_blink else None
                    ),
                ),
            ],
        )

    def _make_key_btn(self, label: str, payload: bytes | None) -> ft.Control:
        if payload is None:
            is_ctrl = label == "CTRL"
            btn = ft.Button(
                content=ft.Text(label, size=BTN_FONT_SIZE, weight=ft.FontWeight.BOLD),
                height=BTN_HEIGHT,
                style=self._get_modifier_style(False),
                on_click=lambda e, c=is_ctrl: self._toggle_modifier(c),
            )
            if is_ctrl:
                self._btn_ctrl = btn
            else:
                self._btn_alt = btn
            return btn

        return ft.Button(
            content=ft.Text(
                label,
                size=BTN_FONT_SIZE,
                weight=ft.FontWeight.BOLD,
                color=COLOR_INACTIVE_FG,
            ),
            height=BTN_HEIGHT,
            style=ft.ButtonStyle(
                padding=ft.Padding.symmetric(horizontal=6, vertical=0),
                bgcolor=COLOR_INACTIVE_BG,
                visual_density=ft.VisualDensity.COMPACT,
                side=ft.BorderSide(width=0),
            ),
            on_click=lambda e, p=payload: self._send_payload(p),
        )

    def _get_modifier_style(self, active: bool) -> ft.ButtonStyle:
        return ft.ButtonStyle(
            padding=ft.Padding.symmetric(horizontal=6, vertical=0),
            bgcolor=COLOR_ACTIVE_BG if active else COLOR_INACTIVE_BG,
            color=COLOR_ACTIVE_FG if active else COLOR_INACTIVE_FG,
            visual_density=ft.VisualDensity.COMPACT,
            side=ft.BorderSide(width=0),
        )

    def _toggle_modifier(self, is_ctrl: bool):
        if is_ctrl:
            self.ctrl_active = not self.ctrl_active
        else:
            self.alt_active = not self.alt_active
        self.refresh_buttons()
        self._on_modifier_change(self.ctrl_active, self.alt_active)

    def refresh_buttons(self):
        if self._btn_ctrl:
            self._btn_ctrl.style = self._get_modifier_style(self.ctrl_active)
            self._btn_ctrl.update()
        if self._btn_alt:
            self._btn_alt.style = self._get_modifier_style(self.alt_active)
            self._btn_alt.update()

    def reset_modifiers(self):
        if self.ctrl_active or self.alt_active:
            self.ctrl_active = False
            self.alt_active = False
            self.refresh_buttons()
            self._on_modifier_change(self.ctrl_active, self.alt_active)

    def _send_payload(self, payload: bytes):
        if self.ctrl_active and len(payload) == 1:
            code = payload[0]
            if 97 <= code <= 122:
                payload = bytes([code - 96])
            elif 65 <= code <= 90:
                payload = bytes([code - 64])
            self.ctrl_active = False
            self.refresh_buttons()
            self._on_modifier_change(self.ctrl_active, self.alt_active)
        if self.alt_active:
            payload = b"\x1b" + payload
            self.alt_active = False
            self.refresh_buttons()
            self._on_modifier_change(self.ctrl_active, self.alt_active)
        self._on_send_payload(payload)

    def _on_toggle_collapse(self, e):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._keys_row.controls = [self._toggle_btn]
            self._toggle_btn.icon = ft.Icons.KEYBOARD
            self._toggle_btn.tooltip = "Show virtual keys"
        else:
            controls: list[ft.Control] = [self._toggle_btn]
            if self._on_set_theme is not None:
                controls.append(self._build_settings_menu())
            for label, payload in self._keys:
                controls.append(self._make_key_btn(label, payload))
            self._keys_row.controls = controls
            self._toggle_btn.icon = ft.Icons.ARROW_DROP_DOWN
            self._toggle_btn.tooltip = "Collapse virtual keys"
            self.refresh_buttons()
        self.update()
