"""Root Flet Terminal Application setup and lifecycle manager."""
# ruff: noqa: E402

from __future__ import annotations
import json
import os
import sys

_cur_dir = os.path.dirname(os.path.abspath(__file__))
if _cur_dir not in sys.path:
    sys.path.insert(0, _cur_dir)

import time
import threading
import flet as ft
from flet_terminal import MobileTerminal, BUILTIN_THEMES
from pty_service import PTYService
from ui_helpers import build_demo_appbar


def main(page: ft.Page):
    page.title = "Flet Terminal"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = "#12121A"

    mt = MobileTerminal(
        show_extra_keys=True,
        show_search=False,
        show_settings=True,
        scrollback=10000,
        font_family="JetBrains Mono",
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
    mt.set_on_bytes(pty_service.write)

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
        pty_service.start_session(engine_name)
        page.update()

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
                    f"\x1b[32m{' '.join(['10'[((i + j) * 7) % 2] for j in range(40)])}\x1b[0m\r\n".encode(
                        "utf-8"
                    )
                )
                time.sleep(0.05)
            mt.send_bytes(b"\r\n\x1b[32mMatrix animation finished.\x1b[0m\r\n")

        threading.Thread(target=loop, daemon=True).start()

    def run_stress():
        mt.write("\r\n\x1b[33mGenerating 1000 lines throughput test...\x1b[0m\r\n")

        def loop():
            for i in range(1, 1001):
                mt.send_bytes(
                    f"\x1b[36m[LINE {i:04d}]\x1b[0m High-speed throughput test payload string...\r\n".encode(
                        "utf-8"
                    )
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
