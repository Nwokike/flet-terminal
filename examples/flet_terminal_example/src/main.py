"""Root FletTerminal Demo Application setup and lifecycle manager."""
# ruff: noqa: E402

from __future__ import annotations
import json
import os
import sys

_cur_dir = os.path.dirname(os.path.abspath(__file__))
if _cur_dir not in sys.path:
    sys.path.insert(0, _cur_dir)

import flet as ft
from flet_terminal import MobileTerminal, BUILTIN_THEMES
from pty_service import PTYService
from demo_engine import DemoEngine
from ui_helpers import build_demo_appbar


def main(page: ft.Page):
    page.title = "FletTerminal Demo"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = "#12121A"

    mt = MobileTerminal(
        show_extra_keys=True,
        show_search=False,
        show_settings=True,
        scrollback=10000,
        font_family="JetBrains Mono",
        font_size=13.0,
        cursor_style="block",
        cursor_blink=True,
        theme=BUILTIN_THEMES["JetBrains Dark"],
        auto_focus=True,
    )

    def on_pty_output(data: bytes):
        mt.send_bytes(data)

    def on_pty_error(msg: str):
        page.show_dialog(
            ft.SnackBar(ft.Text(f"⚠️ {msg}"), bgcolor="#F38BA8", duration=2500)
        )

    pty_service = PTYService(on_output=on_pty_output, on_error=on_pty_error)
    demo_engine = DemoEngine(write_fn=mt.send_bytes, clear_fn=mt.clear)

    def handle_terminal_bytes(payload: bytes):
        if pty_service.active_engine in ("Local OS PTY", "Android Local Shell"):
            pty_service.write(payload)
        else:
            demo_engine.handle_input(payload)

    mt.set_on_bytes(handle_terminal_bytes)

    def handle_resize(e):
        try:
            data = json.loads(e.data)
            cols = int(data.get("cols", 80))
            rows = int(data.get("rows", 24))
            pty_service.resize(cols, rows)
        except Exception:
            pass

    mt.on_resize = handle_resize

    def switch_engine(engine_name: str):
        mt.clear()
        if engine_name in ("Local OS PTY", "Android Local Shell"):
            pty_service.start_session(engine_name)
        else:
            pty_service.stop_session()
            pty_service.active_engine = "ANSI Demo Engine"
            demo_engine.start()
        page.update()

    def run_matrix():
        switch_engine("ANSI Demo Engine")
        demo_engine._execute_command("matrix")

    def run_stress():
        switch_engine("ANSI Demo Engine")
        demo_engine._execute_command("stress")

    def run_alt_screen():
        mt.write("\x1b[?1049h\x1b[H\x1b[2J")
        mt.write(
            "\x1b[1;36m=== FletTerminal Alternate Screen Buffer Simulation ===\x1b[0m\r\n"
        )
        mt.write("Press Ctrl+L or type 'clear' to exit alternate screen.\r\n")

    appbar = build_demo_appbar(
        page=page,
        mt=mt,
        available_engines=PTYService.available_engines(),
        active_engine=pty_service.active_engine,
        on_switch_engine=switch_engine,
        on_run_matrix=run_matrix,
        on_run_stress=run_stress,
        on_run_alt_screen=run_alt_screen,
    )

    page.add(
        ft.SafeArea(content=ft.Column(controls=[appbar, mt], spacing=0, expand=True))
    )

    # Start initial session once mounted
    switch_engine(pty_service.active_engine)


ft.run(main)
