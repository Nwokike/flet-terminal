"""App — the declarative Flet 0.86 root component for the FletTerminal demo.

`DemoState` is an @ft.observable model; the terminal and PTY service are
created once per mount (use_state factory) and torn down on unmount.
Terminal settings live in a floating action button that mirrors the
ExtraKeysBar settings menu (themes, cursor, zoom, blink, search, clipboard).
"""

from __future__ import annotations

import json
import threading
import time

import flet as ft
from pty_service import PTYService
from ui_helpers import build_demo_appbar

from flet_terminal import BUILTIN_THEMES, MobileTerminal


@ft.observable
class DemoState:
    """Observable demo state; mutations re-render the App component."""

    def __init__(self):
        self.engines: list[str] = PTYService.available_engines()
        self.active_engine: str = PTYService.get_default_engine()
        # Terminal settings (drive the FAB menu checkmarks)
        self.theme: str = "JetBrains Dark"
        self.cursor: str = "block"
        self.blink: bool = True
        self.search: bool = False


def _make_resize_handler(pty: PTYService):
    def handle_resize(e):
        try:
            data = json.loads(e.data)
            pty.resize(int(data.get("cols", 80)), int(data.get("rows", 24)))
        except ValueError:
            # Malformed resize payload — the PTY keeps its last size.
            pass

    return handle_resize


def _make_bundle(page: ft.Page):
    """Create the long-lived terminal + PTY pair (runs once per mount).

    Every handler is wired before the controls enter the component tree.
    Settings live in the app-level FAB, so the keys-bar gear is hidden.
    """
    mt = MobileTerminal(
        show_extra_keys=True,
        show_search=False,
        show_settings=False,
        scrollback=10000,
        font_family="JetBrains Mono",
        cursor_style="block",
        cursor_blink=True,
        theme=BUILTIN_THEMES["JetBrains Dark"],
        auto_focus=True,
    )

    pty = PTYService(
        on_output=mt.send_bytes,
        on_error=lambda msg: page.show_dialog(
            ft.SnackBar(ft.Text(f"⚠️ {msg}"), bgcolor="#F38BA8", duration=2500)
        ),
    )
    mt.set_on_bytes(pty.write)
    mt.on_resize = _make_resize_handler(pty)
    return mt, pty


def _header(label: str) -> ft.PopupMenuItem:
    return ft.PopupMenuItem(
        content=ft.Text(label, weight=ft.FontWeight.BOLD), disabled=True
    )


def _item(
    label: str,
    icon,
    on_click,
    checked: bool | None = None,
) -> ft.PopupMenuItem:
    return ft.PopupMenuItem(
        content=ft.Text(label), icon=icon, on_click=on_click, checked=checked
    )


@ft.component
def App() -> ft.Control:
    page = ft.context.page
    ds, _ = ft.use_state(DemoState)
    bundle, _ = ft.use_state(lambda: _make_bundle(page))
    mt, pty = bundle

    def switch_engine(engine_name: str):
        mt.clear()
        pty.start_session(engine_name)
        ds.active_engine = engine_name

    def pick_theme(name: str):
        ds.theme = name
        mt.set_theme(name)

    def pick_cursor(style: str):
        ds.cursor = style
        mt.set_cursor_style(style)

    def zoom_in():
        mt.zoom_in()

    def zoom_out():
        mt.zoom_out()

    def zoom_reset():
        mt.reset_zoom()

    def toggle_blink():
        ds.blink = not ds.blink
        mt.toggle_cursor_blink()

    def toggle_search():
        ds.search = not ds.search
        mt.toggle_search()

    def run_matrix():
        mt.write("\r\n\x1b[32m=== ANSI Color & Style Matrix ===\x1b[0m\r\n")
        mt.write("\x1b[1mStandard & Bright ANSI Colors:\x1b[0m\r\n")
        for i in range(8):
            mt.write(f"\x1b[4{i}m   \x1b[0m ")
        mt.write("\r\n")
        for i in range(8):
            mt.write(f"\x1b[10{i}m   \x1b[0m ")
        mt.write("\r\n\x1b[32mStarting Matrix animation (3 seconds)...\x1b[0m\r\n")

        def loop():
            for i in range(30):
                mt.send_bytes(
                    f"\x1b[32m{' '.join(['10'[((i + j) * 7) % 2] for j in range(40)])}\x1b[0m\r\n".encode()
                )
                time.sleep(0.05)
            mt.send_bytes(b"\r\n\x1b[32mMatrix animation finished.\x1b[0m\r\n")

        threading.Thread(target=loop, daemon=True).start()

    def run_stress():
        mt.write("\r\n\x1b[33mGenerating 1000 lines throughput test...\x1b[0m\r\n")

        def loop():
            for i in range(1, 1001):
                mt.send_bytes(
                    f"\x1b[36m[LINE {i:04d}]\x1b[0m High-speed throughput test payload string...\r\n".encode()
                )
                time.sleep(0.001)
            mt.send_bytes(b"\r\n\x1b[33mThroughput test complete.\x1b[0m\r\n")

        threading.Thread(target=loop, daemon=True).start()

    def run_alt_screen():
        mt.write("\x1b[?1049h\x1b[H\x1b[2J")
        mt.write(
            "\x1b[1;36m=== FletTerminal Alternate Screen Buffer Simulation ===\x1b[0m\r\n"
        )
        mt.write("Press Ctrl+L or type 'clear' to exit alternate screen.\r\n")

    # Start the initial PTY session once mounted; stop it on unmount.
    ft.on_mounted(lambda: pty.start_session(ds.active_engine))
    ft.use_effect(lambda: None, [], cleanup=pty.stop_session)

    appbar = build_demo_appbar(
        mt=mt,
        available_engines=ds.engines,
        active_engine=ds.active_engine,
        on_switch_engine=switch_engine,
        on_run_matrix=run_matrix,
        on_run_stress=run_stress,
        on_run_alt_screen=run_alt_screen,
        on_toggle_search=toggle_search,
    )

    settings_items = [
        _header("Clipboard"),
        _item("Copy Selection", ft.Icons.COPY_ROUNDED, lambda e: mt.copy_selection()),
        _item("Paste", ft.Icons.CONTENT_PASTE_ROUNDED, lambda e: mt.paste()),
        _item("Select All", ft.Icons.SELECT_ALL_ROUNDED, lambda e: mt.select_all()),
        _item("Clear Terminal", ft.Icons.CLEAR_ALL_ROUNDED, lambda e: mt.clear()),
        ft.PopupMenuItem(),
        _header("Theme Presets"),
        _item(
            "Dracula",
            ft.Icons.PALETTE_ROUNDED,
            lambda e: pick_theme("Dracula"),
            ds.theme == "Dracula",
        ),
        _item(
            "JetBrains Dark",
            ft.Icons.PALETTE_ROUNDED,
            lambda e: pick_theme("JetBrains Dark"),
            ds.theme == "JetBrains Dark",
        ),
        _item(
            "Matrix Green",
            ft.Icons.PALETTE_ROUNDED,
            lambda e: pick_theme("Matrix Green"),
            ds.theme == "Matrix Green",
        ),
        _item(
            "Colab Light",
            ft.Icons.PALETTE_ROUNDED,
            lambda e: pick_theme("Colab Light"),
            ds.theme == "Colab Light",
        ),
        ft.PopupMenuItem(),
        _header("Cursor Style"),
        _item(
            "Block",
            ft.Icons.TEXT_FIELDS_ROUNDED,
            lambda e: pick_cursor("block"),
            ds.cursor == "block",
        ),
        _item(
            "Underline",
            ft.Icons.TEXT_FIELDS_ROUNDED,
            lambda e: pick_cursor("underline"),
            ds.cursor == "underline",
        ),
        _item(
            "Bar",
            ft.Icons.TEXT_FIELDS_ROUNDED,
            lambda e: pick_cursor("bar"),
            ds.cursor == "bar",
        ),
        ft.PopupMenuItem(),
        _header("Font Size / Zoom"),
        _item("Zoom In (+)", ft.Icons.ADD_ROUNDED, lambda e: zoom_in()),
        _item("Zoom Out (-)", ft.Icons.REMOVE_ROUNDED, lambda e: zoom_out()),
        _item("Reset Zoom (11px)", ft.Icons.FIT_SCREEN_ROUNDED, lambda e: zoom_reset()),
        ft.PopupMenuItem(),
        _header("Toggle Options"),
        _item(
            "Cursor Blink",
            ft.Icons.VISIBILITY_ROUNDED,
            lambda e: toggle_blink(),
            ds.blink,
        ),
        _item(
            "Search Bar", ft.Icons.SEARCH_ROUNDED, lambda e: toggle_search(), ds.search
        ),
    ]

    settings_fab = ft.FloatingActionButton(
        content=ft.PopupMenuButton(
            items=settings_items,
            icon=ft.Icons.SETTINGS_ROUNDED,
            icon_color=ft.Colors.WHITE,
            icon_size=20,
        ),
        bgcolor="#F97316",
        mini=True,
        tooltip="Terminal Settings",
        margin=ft.Padding(0, 0, 52, 16),
    )

    return ft.SafeArea(
        content=ft.Stack(
            controls=[
                ft.Column(controls=[appbar, mt], spacing=0, expand=True),
                settings_fab,
            ],
            alignment=ft.alignment.Alignment.BOTTOM_RIGHT,
            expand=True,
        )
    )


__all__ = ["App", "DemoState"]
