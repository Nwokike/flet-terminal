"""App — the declarative Flet 0.86 root component for the FletTerminal demo.

`DemoState` is an @ft.observable model; the terminal and PTY service are
created once per mount (use_state factory) and torn down on unmount.
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
    """
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

    pty = PTYService(
        on_output=mt.send_bytes,
        on_error=lambda msg: page.show_dialog(
            ft.SnackBar(ft.Text(f"⚠️ {msg}"), bgcolor="#F38BA8", duration=2500)
        ),
    )
    mt.set_on_bytes(pty.write)
    mt.on_resize = _make_resize_handler(pty)
    return mt, pty


@ft.component
def App() -> ft.Control:
    page = ft.context.page
    ds = ft.use_state(DemoState).value
    mt, pty = ft.use_state(lambda: _make_bundle(page)).value

    def switch_engine(engine_name: str):
        mt.clear()
        pty.start_session(engine_name)
        ds.active_engine = engine_name

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
    )

    return ft.SafeArea(
        content=ft.Column(controls=[appbar, mt], spacing=0, expand=True)
    )


__all__ = ["App", "DemoState"]
