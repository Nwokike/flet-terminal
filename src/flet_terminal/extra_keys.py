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
        on_toggle_search: Callable[[], None] | None = None,
        keys: list[tuple[str, bytes | None]] | None = None,
    ):
        self._on_send_payload = on_send_payload
        self._on_modifier_change = on_modifier_change
        self._on_set_theme = on_set_theme
        self._on_set_cursor = on_set_cursor
        self._on_toggle_blink = on_toggle_blink
        self._on_toggle_search = on_toggle_search
        self._keys = keys or DEFAULT_EXTRA_KEYS

        self.ctrl_active = False
        self.alt_active = False
        self._collapsed = False

        self.active_theme = "JetBrains Dark"
        self.active_cursor = "block"
        self.active_blink = True
        self.active_search = True
        self.current_font_size = 13.0
        self.default_font_size = 13.0
        self._on_zoom_in: Callable[[], None] | None = None
        self._on_zoom_out: Callable[[], None] | None = None
        self._on_zoom_reset: Callable[[], None] | None = None

        self._btn_ctrl: ft.Button | None = None
        self._btn_alt: ft.Button | None = None

        self._toggle_btn = ft.IconButton(
            icon=ft.Icons.ARROW_DROP_DOWN,
            icon_size=20,
            tooltip="Hide keys",
            style=ft.ButtonStyle(padding=2, visual_density=ft.VisualDensity.COMPACT),
            on_click=self._on_toggle_collapse,
        )

        key_controls: list[ft.Control] = []
        if show_settings:
            key_controls.append(self._build_settings_menu())

        for label, payload in self._keys:
            key_controls.append(self._make_key_btn(label, payload))

        self._keys_row = ft.Row(
            controls=key_controls,
            spacing=SPACE_XS,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self._expanded_row = ft.Row(
            controls=[
                self._toggle_btn,
                self._keys_row,
            ],
            spacing=2,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self._collapsed_view = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(expand=True),
                    self._toggle_btn,
                    ft.Container(expand=True),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_click=self._on_toggle_collapse,
            ink=True,
            tooltip="Click anywhere to show keys",
        )

        super().__init__(
            content=self._expanded_row,
            padding=ft.Padding(4, 1, 4, 1),
            bgcolor="#181825",
        )

    def _get_settings_menu_items(self) -> list[ft.Control]:
        """Return the refreshed list of items with current checkmarks and font size."""
        return [
            ft.PopupMenuItem(
                content=ft.Text("Theme Presets", weight=ft.FontWeight.BOLD),
                disabled=True,
            ),
            ft.PopupMenuItem(
                content=ft.Text("Dracula"),
                checked=self.active_theme == "Dracula",
                on_click=lambda e: (
                    self._on_set_theme("Dracula") if self._on_set_theme else None
                ),
            ),
            ft.PopupMenuItem(
                content=ft.Text("JetBrains Dark"),
                checked=self.active_theme == "JetBrains Dark",
                on_click=lambda e: (
                    self._on_set_theme("JetBrains Dark") if self._on_set_theme else None
                ),
            ),
            ft.PopupMenuItem(
                content=ft.Text("Matrix Green"),
                checked=self.active_theme == "Matrix Green",
                on_click=lambda e: (
                    self._on_set_theme("Matrix Green") if self._on_set_theme else None
                ),
            ),
            ft.PopupMenuItem(),
            ft.PopupMenuItem(
                content=ft.Text("Cursor Style", weight=ft.FontWeight.BOLD),
                disabled=True,
            ),
            ft.PopupMenuItem(
                content=ft.Text("Block"),
                checked=self.active_cursor == "block",
                on_click=lambda e: (
                    self._on_set_cursor("block") if self._on_set_cursor else None
                ),
            ),
            ft.PopupMenuItem(
                content=ft.Text("Underline"),
                checked=self.active_cursor == "underline",
                on_click=lambda e: (
                    self._on_set_cursor("underline") if self._on_set_cursor else None
                ),
            ),
            ft.PopupMenuItem(
                content=ft.Text("Bar"),
                checked=self.active_cursor == "bar",
                on_click=lambda e: (
                    self._on_set_cursor("bar") if self._on_set_cursor else None
                ),
            ),
            ft.PopupMenuItem(),
            ft.PopupMenuItem(
                content=ft.Text("Font Size / Zoom", weight=ft.FontWeight.BOLD),
                disabled=True,
            ),
            ft.PopupMenuItem(
                content=ft.Row(
                    controls=[
                        ft.Text(
                            f"Font Size: {int(self.current_font_size)}px",
                            expand=True,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                            icon_size=18,
                            tooltip="Zoom Out",
                            style=ft.ButtonStyle(
                                padding=0, visual_density=ft.VisualDensity.COMPACT
                            ),
                            on_click=lambda e: (
                                self._on_zoom_out() if self._on_zoom_out else None
                            ),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                            icon_size=18,
                            tooltip="Zoom In",
                            style=ft.ButtonStyle(
                                padding=0, visual_density=ft.VisualDensity.COMPACT
                            ),
                            on_click=lambda e: (
                                self._on_zoom_in() if self._on_zoom_in else None
                            ),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.RESTART_ALT,
                            icon_size=18,
                            tooltip="Reset Zoom",
                            style=ft.ButtonStyle(
                                padding=0, visual_density=ft.VisualDensity.COMPACT
                            ),
                            on_click=lambda e: (
                                self._on_zoom_reset() if self._on_zoom_reset else None
                            ),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
            ),
            ft.PopupMenuItem(
                content=ft.Text("Zoom In (+)"),
                on_click=lambda e: self._on_zoom_in() if self._on_zoom_in else None,
            ),
            ft.PopupMenuItem(
                content=ft.Text("Zoom Out (-)"),
                on_click=lambda e: self._on_zoom_out() if self._on_zoom_out else None,
            ),
            ft.PopupMenuItem(
                content=ft.Text(f"Reset Zoom ({int(self.default_font_size)}px)"),
                on_click=lambda e: (
                    self._on_zoom_reset() if self._on_zoom_reset else None
                ),
            ),
            ft.PopupMenuItem(),
            ft.PopupMenuItem(
                content=ft.Text("Toggle Options", weight=ft.FontWeight.BOLD),
                disabled=True,
            ),
            ft.PopupMenuItem(
                content=ft.Text("Cursor Blink"),
                checked=self.active_blink,
                on_click=lambda e: (
                    self._on_toggle_blink() if self._on_toggle_blink else None
                ),
            ),
            ft.PopupMenuItem(
                content=ft.Text("Search Bar"),
                checked=self.active_search,
                on_click=lambda e: (
                    self._on_toggle_search() if self._on_toggle_search else None
                ),
            ),
        ]

    def _build_settings_menu(self) -> ft.PopupMenuButton:
        self._settings_menu = ft.PopupMenuButton(
            icon=ft.Icons.SETTINGS,
            icon_size=16,
            tooltip="Terminal Settings",
            style=ft.ButtonStyle(padding=2, visual_density=ft.VisualDensity.COMPACT),
            items=self._get_settings_menu_items(),
        )
        return self._settings_menu

    def update_settings_menu(self):
        """Refresh the items and checkmarks inside the settings menu."""
        if hasattr(self, "_settings_menu") and self._settings_menu:
            self._settings_menu.items = self._get_settings_menu_items()
            try:
                if self._settings_menu.page:
                    self._settings_menu.update()
                elif self.page:
                    self.update()
            except RuntimeError:
                pass

    def _make_key_btn(self, label: str, payload: bytes | None) -> ft.Control:
        if payload is None:
            is_ctrl = label == "CTRL"
            btn = ft.Button(
                content=ft.Text(label, size=BTN_FONT_SIZE, weight=ft.FontWeight.BOLD),
                height=BTN_HEIGHT,
                style=self._get_modifier_style(
                    self.ctrl_active if is_ctrl else self.alt_active
                ),
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
            if self._btn_ctrl.page:
                self._btn_ctrl.update()
        if self._btn_alt:
            self._btn_alt.style = self._get_modifier_style(self.alt_active)
            if self._btn_alt.page:
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
            self._toggle_btn.icon = ft.Icons.ARROW_DROP_UP
            self._toggle_btn.tooltip = "Show keys"
            self.content = self._collapsed_view
        else:
            self._toggle_btn.icon = ft.Icons.ARROW_DROP_DOWN
            self._toggle_btn.tooltip = "Hide keys"
            self.content = self._expanded_row
        self.update()
