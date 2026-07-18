"""FletTerminal Cross-Platform Test App & Demo Demo.

Tests FletTerminal across Web, Linux, Windows, and Android with built-in
VT100/ANSI stress testing engines and local OS PTY integration (`bash` / `PowerShell`).
"""

import json
import os
import signal
import struct
import subprocess
import sys
import threading
import time
import flet as ft
from flet_terminal import MobileTerminal

# Try importing POSIX pty (Linux/macOS desktop/server only)
try:
    if sys.platform in ("emscripten", "wasi", "win32", "android"):
        HAS_POSIX_PTY = False
    else:
        import fcntl
        import pty
        import termios

        # Verify openpty actually works in this environment (in case of sandboxed OS)
        try:
            _m, _s = pty.openpty()
            os.close(_m)
            os.close(_s)
            HAS_POSIX_PTY = True
        except OSError:
            HAS_POSIX_PTY = False
except ImportError:
    HAS_POSIX_PTY = False

# Try importing Windows ConPTY (pywinpty)
try:
    if sys.platform in ("emscripten", "wasi"):
        HAS_WIN_PTY = False
    else:
        import winpty

        HAS_WIN_PTY = True
except ImportError:
    HAS_WIN_PTY = False

# Android can use subprocess pipes for a basic shell (no PTY, so no
# job control or fullscreen apps, but ls/cd/cat/echo/grep all work).
HAS_ANDROID_SUBPROCESS = sys.platform == "android"

THEMES = {
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

CURSOR_STYLES = ["block", "underline", "bar"]


def main(page: ft.Page):
    page.title = "Terminal Demo"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = "#12121A"
    page.theme = ft.Theme(color_scheme_seed="#89B4FA")

    active_theme_name = "JetBrains Dark"
    active_engine = (
        "Android Local Shell"
        if HAS_ANDROID_SUBPROCESS
        else "Local OS PTY"
        if (HAS_POSIX_PTY or HAS_WIN_PTY)
        else "ANSI Demo Engine"
    )
    pty_master_fd = None
    pty_process = None
    android_proc = None

    mt = MobileTerminal(
        show_extra_keys=True,
        show_search=True,
        scrollback=10000,
        font_family="JetBrains Mono",
        font_size=13.0,
        cursor_style="block",
        cursor_blink=True,
        theme=THEMES[active_theme_name],
        auto_focus=True,
    )

    # ─── Event handlers from terminal ───────────────────────────
    def handle_title_change(e):
        page.update()

    def handle_bell(e):
        page.show_dialog(
            ft.SnackBar(
                ft.Text("🔔 Terminal Bell Triggered! (\\a)"),
                bgcolor="#F38BA8",
                duration=1500,
            )
        )

    mt.on_title_change = handle_title_change
    mt.on_bell = handle_bell

    # ─── Incoming bytes from Dart widget ────────────────────────
    def handle_terminal_bytes(payload: bytes):
        nonlocal pty_master_fd, pty_process, android_proc
        if mt.ctrl_active and len(payload) == 1:
            code = payload[0]
            if 97 <= code <= 122:
                payload = bytes([code - 96])
            elif 65 <= code <= 90:
                payload = bytes([code - 64])
            mt.ctrl_active = False
        if mt.alt_active:
            payload = b"\x1b" + payload
            mt.alt_active = False

        if active_engine == "Local OS PTY":
            if HAS_POSIX_PTY and pty_master_fd is not None:
                try:
                    os.write(pty_master_fd, payload)
                except OSError:
                    pass
            elif HAS_WIN_PTY and pty_process is not None:
                try:
                    pty_process.write(payload.decode("utf-8", errors="ignore"))
                except Exception:
                    pass
        elif active_engine == "Android Local Shell":
            if android_proc is not None and android_proc.poll() is None:
                try:
                    if payload == b"\x03":
                        android_proc.send_signal(signal.SIGINT)
                    elif payload == b"\x04":
                        android_proc.stdin.close()
                    elif payload == b"\x1b":
                        pass  # Escape on its own — do nothing
                    else:
                        android_proc.stdin.write(payload)
                        android_proc.stdin.flush()
                except Exception:
                    pass
        else:
            text = payload.decode("utf-8", errors="ignore")
            if text == "\r":
                mt.send_bytes(b"\r\n\x1b[32m[Demo Shell]>\x1b[0m ")
            elif text == "\x03":  # Ctrl+C
                mt.send_bytes(b"^C\r\n\x1b[32m[Demo Shell]>\x1b[0m ")
            elif text == "\x0c":  # Ctrl+L
                mt.clear()
                mt.write("\x1b[32m[Demo Shell]>\x1b[0m ")
            elif text == "\x04":  # Ctrl+D
                mt.send_bytes(b"exit\r\n\x1b[32m[Demo Shell]>\x1b[0m ")
            elif text == "\t":
                mt.send_bytes(b"  ")
            elif text == "\x1b":
                mt.send_bytes(b"^[")
            elif payload in (b"\x1b[A", b"\x1b[B", b"\x1b[C", b"\x1b[D"):
                mt.send_bytes(payload)
            else:
                mt.send_bytes(payload)

    mt.set_on_bytes(handle_terminal_bytes)

    def handle_resize(e):
        try:
            data = json.loads(e.data)
            cols = int(data.get("cols", 80))
            rows = int(data.get("rows", 24))
            if active_engine == "Local OS PTY":
                if pty_master_fd is not None and HAS_POSIX_PTY:
                    winsize = struct.pack("HHHH", rows, cols, 0, 0)
                    fcntl.ioctl(pty_master_fd, termios.TIOCSWINSZ, winsize)
                elif HAS_WIN_PTY and pty_process is not None and cols > 0 and rows > 0:
                    pty_process.set_size(cols, rows)
        except Exception as ex:
            print(f"[Resize Error] {ex}")

    mt.on_resize = handle_resize

    # ─── PTY setup/teardown ─────────────────────────────────────
    def start_posix_pty():
        nonlocal pty_master_fd, active_engine
        try:
            master_fd, slave_fd = pty.openpty()
            pid = os.fork()
            if pid == 0:
                os.setsid()
                os.dup2(slave_fd, 0)
                os.dup2(slave_fd, 1)
                os.dup2(slave_fd, 2)
                if slave_fd > 2:
                    os.close(slave_fd)
                os.close(master_fd)
                shell = os.environ.get("SHELL", "/bin/bash")
                os.execv(shell, [shell, "-l"])
            else:
                os.close(slave_fd)
                pty_master_fd = master_fd

                def read_loop():
                    while pty_master_fd == master_fd:
                        try:
                            data = os.read(master_fd, 4096)
                            if not data:
                                break
                            mt.send_bytes(data)
                        except OSError:
                            break

                threading.Thread(target=read_loop, daemon=True).start()
        except (OSError, AttributeError, Exception) as ex:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(
                        f"⚠️ Local PTY failed to start: {ex}. Reverting to Demo Engine."
                    ),
                    bgcolor="#F38BA8",
                )
            )
            active_engine = "ANSI Demo Engine"
            stop_pty()
            mt.clear()
            mt.write(
                f"\r\n\x1b[1;31m[PTY Error]\x1b[0m Local OS PTY is not available in this environment ({ex}).\r\nSwitched to ANSI VT100 Demo Engine.\r\n\x1b[32m[Demo Shell]>\x1b[0m "
            )
            page.update()

    def start_win_pty():
        nonlocal pty_process, active_engine
        if HAS_WIN_PTY:
            try:
                pty_process = winpty.PtyProcess.spawn("powershell.exe")

                def read_loop():
                    while pty_process is not None:
                        try:
                            data = pty_process.read()
                            if not data or pty_process.isalive() is False:
                                break
                            mt.send_bytes(data.encode("utf-8", errors="ignore"))
                        except Exception:
                            break

                threading.Thread(target=read_loop, daemon=True).start()
            except Exception as ex:
                page.show_dialog(
                    ft.SnackBar(
                        ft.Text(
                            f"⚠️ WinPTY failed to start: {ex}. Reverting to Demo Engine."
                        ),
                        bgcolor="#F38BA8",
                    )
                )
                active_engine = "ANSI Demo Engine"
                stop_pty()
                mt.clear()
                mt.write(
                    f"\r\n\x1b[1;31m[PTY Error]\x1b[0m WinPTY is not available ({ex}).\r\nSwitched to ANSI VT100 Demo Engine.\r\n\x1b[32m[Demo Shell]>\x1b[0m "
                )
                page.update()

    def start_android_shell():
        """Starts `sh` via subprocess pipes on Android.
        No PTY means no job control or fullscreen apps (vim/htop won't work),
        but ls, cd, cat, echo, grep, and similar commands work fine."""
        nonlocal android_proc, active_engine
        try:
            android_proc = subprocess.Popen(
                ["sh"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env={**os.environ, "TERM": "xterm-256color"},
            )

            def read_loop():
                while android_proc is not None and android_proc.poll() is None:
                    try:
                        data = android_proc.stdout.read(4096)
                        if not data:
                            break
                        mt.send_bytes(data)
                    except Exception:
                        break

            threading.Thread(target=read_loop, daemon=True).start()
        except Exception as ex:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(
                        f"⚠️ Android shell failed to start: {ex}. Reverting to Demo Engine."
                    ),
                    bgcolor="#F38BA8",
                )
            )
            active_engine = "ANSI Demo Engine"
            stop_pty()
            mt.clear()
            mt.write(
                f"\r\n\x1b[1;31m[Shell Error]\x1b[0m Android shell unavailable ({ex}).\r\nSwitched to ANSI VT100 Demo Engine.\r\n\x1b[32m[Demo Shell]>\x1b[0m "
            )
            page.update()

    def stop_pty():
        nonlocal pty_master_fd, pty_process, android_proc
        if pty_master_fd is not None:
            try:
                os.close(pty_master_fd)
            except Exception:
                pass
            pty_master_fd = None
        if pty_process is not None:
            try:
                pty_process.close()
            except Exception:
                pass
            pty_process = None
        if android_proc is not None:
            try:
                android_proc.terminate()
                android_proc.wait(timeout=2)
            except Exception:
                try:
                    android_proc.kill()
                except Exception:
                    pass
            android_proc = None

    # ─── Engine switching ───────────────────────────────────────
    def switch_engine(e):
        nonlocal active_engine
        selected = e.control.value
        if selected == "Local OS PTY":
            if not HAS_POSIX_PTY and not HAS_WIN_PTY:
                page.show_dialog(
                    ft.SnackBar(
                        ft.Text(
                            "⚠️ Local PTY is unavailable on Web/Android sandbox or unconfigured OS."
                        ),
                        bgcolor="#F38BA8",
                    )
                )
                e.control.value = active_engine
                page.update()
                return
            active_engine = "Local OS PTY"
            mt.clear()
            stop_pty()
            if HAS_POSIX_PTY:
                start_posix_pty()
            elif HAS_WIN_PTY:
                start_win_pty()
        elif selected == "Android Local Shell":
            active_engine = "Android Local Shell"
            mt.clear()
            stop_pty()
            start_android_shell()
        else:
            active_engine = "ANSI Demo Engine"
            stop_pty()
            mt.clear()
            mt.write("\x1b[32m[Demo Shell]>\x1b[0m ")
        page.update()

    # ─── Demo engines ───────────────────────────────────────────
    def run_ansi_matrix(e):
        mt.write("\r\n\x1b[1;33m--- ANSI Color & Formatting Matrix ---\x1b[0m\r\n")
        mt.write(
            "Styles: \x1b[1mBold\x1b[0m | \x1b[3mItalic\x1b[0m | \x1b[4mUnderline\x1b[0m | \x1b[7mInvert\x1b[0m\r\n"
        )
        for i in range(8):
            mt.write(
                f"\x1b[3{i}mNormal {i}\x1b[0m  \x1b[1;3{i}mBright {i}\x1b[0m  \x1b[4{i};30m Bg {i} \x1b[0m\r\n"
            )
        mt.write("\x1b[32m[Demo Shell]>\x1b[0m ")

    def run_stress_test(e):
        mt.write(
            "\r\n\x1b[1;35m--- Starting 10,000 Line High-Throughput Stress Test ---\x1b[0m\r\n"
        )
        for i in range(1, 10001):
            color = 30 + (i % 7)
            mt.write(
                f"\x1b[{color}m[Stress Benchmark] Log Entry #{i:05d}: FletTerminal ring-buffer memory throughput validation check.\x1b[0m\r\n"
            )
        mt.write(
            "\x1b[1;32m--- Stress Test Completed Successfully! Check scrollback ring buffer. ---\x1b[0m\r\n\x1b[32m[Demo Shell]>\x1b[0m "
        )

    def run_alternate_screen_test(e):
        mt.write("\x1b[?1049h\x1b[H\x1b[2J")
        mt.write(
            "\x1b[1;36m╔══════════════════════════════════════════════════════════════════════════════╗\r\n"
        )
        mt.write(
            "║       FletTerminal Alternate Screen Buffer Simulation (htop / vim mode)      ║\r\n"
        )
        mt.write(
            "╠══════════════════════════════════════════════════════════════════════════════╣\r\n"
        )
        mt.write(
            "║  CPU1 [|||||||||||||||||||||||||||||||||||||||||||          76.4%]           ║\r\n"
        )
        mt.write(
            "║  CPU2 [||||||||||||||||||||||||||||                         42.1%]           ║\r\n"
        )
        mt.write(
            "║  Mem  [|||||||||||||||||||||||||||||||||||||||||||||||||    3.8G/8.0G]       ║\r\n"
        )
        mt.write(
            "║                                                                              ║\r\n"
        )
        mt.write(
            "║  Notice how live terminal state is isolated inside alternate buffer (\\x1b[?1049h).  ║\r\n"
        )
        mt.write(
            "║  Pressing Exit below sends \\x1b[?1049l to restore primary scrollback seamlessly! ║\r\n"
        )
        mt.write(
            "╚══════════════════════════════════════════════════════════════════════════════╝\r\n"
        )

        def restore_screen():
            time.sleep(3.5)
            mt.write("\x1b[?1049l\r\n\x1b[32m[Demo Shell]>\x1b[0m ")

        threading.Thread(target=restore_screen, daemon=True).start()

    def trigger_osc_bell(e):
        mt.write("\x1b]0;OSC 0 Title Update Test\a")
        mt.write("\a")
        mt.write(
            "\r\n\x1b[33mSent window title change (OSC 0) and bell notification (\\a)!\x1b[0m\r\n\x1b[32m[Demo Shell]>\x1b[0m "
        )

    # ─── Appearance controls ────────────────────────────────────
    def change_cursor_style(e):
        mt.cursor_style = e.control.value.lower()
        mt.update()

    def toggle_cursor_blink(e):
        mt.cursor_blink = not mt.cursor_blink
        mt.update()

    def zoom_in(e):
        mt.font_size += 1.0
        mt.update()

    def zoom_out(e):
        if mt.font_size > 8.0:
            mt.font_size -= 1.0
            mt.update()

    # ─── AppBar controls ───────────────────────────────────────
    zoom_out_btn = ft.IconButton(
        icon=ft.Icons.ZOOM_OUT,
        icon_size=18,
        tooltip="Zoom Out",
        style=ft.ButtonStyle(padding=4, visual_density=ft.VisualDensity.COMPACT),
        on_click=zoom_out,
    )
    zoom_in_btn = ft.IconButton(
        icon=ft.Icons.ZOOM_IN,
        icon_size=18,
        tooltip="Zoom In",
        style=ft.ButtonStyle(padding=4, visual_density=ft.VisualDensity.COMPACT),
        on_click=zoom_in,
    )
    # ─── AppBar: engine selector (left), demos + search + zoom (right) ──
    #      Search disappears into kebab on narrow screens.
    engine_dropdown_options = [
        ft.dropdown.Option("ANSI Demo Engine"),
    ]
    if HAS_ANDROID_SUBPROCESS:
        engine_dropdown_options.append(ft.dropdown.Option("Android Local Shell"))
    if HAS_POSIX_PTY or HAS_WIN_PTY:
        engine_dropdown_options.append(ft.dropdown.Option("Local OS PTY"))

    engine_dropdown = ft.Dropdown(
        options=engine_dropdown_options,
        value=active_engine,
        height=34,
        width=150,
        text_size=12,
        content_padding=ft.Padding.symmetric(horizontal=8, vertical=0),
        dense=True,
        on_select=switch_engine,
    )

    demos_popup = ft.PopupMenuButton(
        icon=ft.Icons.VIEW_LIST,
        icon_size=20,
        tooltip="Demos",
        style=ft.ButtonStyle(padding=4, visual_density=ft.VisualDensity.COMPACT),
        items=[
            ft.PopupMenuItem(
                content=ft.Text("🎨 Color Matrix"), on_click=run_ansi_matrix
            ),
            ft.PopupMenuItem(
                content=ft.Text("🚀 10k Stress Test"), on_click=run_stress_test
            ),
            ft.PopupMenuItem(
                content=ft.Text("🖥️ Alt Screen"), on_click=run_alternate_screen_test
            ),
            ft.PopupMenuItem(
                content=ft.Text("🔔 Bell & Title"), on_click=trigger_osc_bell
            ),
        ],
    )

    # ─── Settings popup (gear icon in AppBar) ──────────────────
    def _settings_items():
        cur_theme = active_theme_name
        cur_cursor = mt.cursor_style or "block"
        blink = bool(mt.cursor_blink)

        def item(text):
            return ft.PopupMenuItem(
                content=ft.Text(text, size=11, weight=ft.FontWeight.BOLD), disabled=True
            )

        def clickable(text, active, handler):
            ctrls = [ft.Text(text, size=13), ft.Container(expand=True)]
            if active:
                ctrls.append(ft.Icon(ft.Icons.CHECK, size=16))
            return ft.PopupMenuItem(content=ft.Row(controls=ctrls), on_click=handler)

        return [
            item("Theme"),
            clickable(
                "Dracula", cur_theme == "Dracula", lambda e: _set_theme("Dracula")
            ),
            clickable(
                "JetBrains Dark",
                cur_theme == "JetBrains Dark",
                lambda e: _set_theme("JetBrains Dark"),
            ),
            clickable(
                "Matrix Green",
                cur_theme == "Matrix Green",
                lambda e: _set_theme("Matrix Green"),
            ),
            ft.PopupMenuItem(content=ft.Text("")),
            item("Cursor"),
            clickable("Block", cur_cursor == "block", lambda e: _set_cursor("block")),
            clickable(
                "Underline",
                cur_cursor == "underline",
                lambda e: _set_cursor("underline"),
            ),
            clickable("Bar", cur_cursor == "bar", lambda e: _set_cursor("bar")),
            ft.PopupMenuItem(content=ft.Text("")),
            clickable("Toggle Cursor Blink", blink, lambda e: _toggle_blink()),
        ]

    settings_popup = ft.PopupMenuButton(
        icon=ft.Icons.SETTINGS,
        icon_size=20,
        tooltip="Settings",
        style=ft.ButtonStyle(padding=4, visual_density=ft.VisualDensity.COMPACT),
        items=_settings_items(),
        on_open=lambda e: _refresh_settings(),
    )

    def _refresh_settings():
        settings_popup.items = _settings_items()
        settings_popup.update()

    def _set_theme(name):
        nonlocal active_theme_name
        active_theme_name = name
        mt.theme = THEMES[name]
        mt.update()
        page.show_dialog(
            ft.SnackBar(ft.Text(f"Theme: {name}"), bgcolor="#313244", duration=1200)
        )

    def _set_cursor(style):
        mt.cursor_style = style
        mt.update()
        page.show_dialog(
            ft.SnackBar(ft.Text(f"Cursor: {style}"), bgcolor="#313244", duration=1200)
        )

    def _toggle_blink():
        mt.cursor_blink = not mt.cursor_blink
        mt.update()
        state = "on" if mt.cursor_blink else "off"
        page.show_dialog(
            ft.SnackBar(ft.Text(f"Blink: {state}"), bgcolor="#313244", duration=1200)
        )

    # ─── AppBar ────────────────────────────────────────────────
    def build_appbar():
        if HAS_POSIX_PTY or HAS_WIN_PTY or HAS_ANDROID_SUBPROCESS:
            left = engine_dropdown
        else:
            left = ft.Container(
                content=ft.Text(
                    "VT100 Demo", size=11, weight=ft.FontWeight.BOLD, color="#A6E3A1"
                ),
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                bgcolor="#313244",
                border_radius=4,
            )

        right: list[ft.Control] = [
            demos_popup,
            settings_popup,
            zoom_out_btn,
            zoom_in_btn,
        ]

        return ft.AppBar(
            leading=left,
            leading_width=160,
            toolbar_height=48,
            adaptive=True,
            bgcolor="#181825",
            actions=right,
            actions_padding=ft.Padding.only(right=8),
        )

    appbar = build_appbar()

    # ─── Layout ─────────────────────────────────────────────────
    page.add(
        ft.SafeArea(
            content=ft.Column(
                controls=[
                    appbar,
                    mt,
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
        )
    )

    if active_engine == "Local OS PTY":
        if HAS_POSIX_PTY:
            start_posix_pty()
        elif HAS_WIN_PTY:
            start_win_pty()
    elif active_engine == "Android Local Shell":
        start_android_shell()
    else:
        mt.write("\x1b[32m[Demo Shell]>\x1b[0m ")


if __name__ == "__main__":
    ft.run(main)
