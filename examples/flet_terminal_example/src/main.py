"""FletTerminal Cross-Platform Test App & Demo Studio.

Tests FletTerminal across Web, Linux, Windows, and Android with built-in
VT100/ANSI stress testing engines and local OS PTY integration (`bash` / `PowerShell`).
"""

import json
import os
import struct
import sys
import threading
import time
import flet as ft
from flet_terminal import Terminal

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


def main(page: ft.Page):
    page.title = "FletTerminal Studio - Cross-Platform Multi-Engine Harness"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = "#12121A"

    # Themes definitions
    themes = {
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

    active_theme_name = "JetBrains Dark"

    # Terminal instance
    terminal = Terminal(
        expand=True,
        scrollback=10000,
        font_family="JetBrains Mono",
        font_size=13.0,
        cursor_style="block",
        cursor_blink=True,
        theme=themes[active_theme_name],
        auto_focus=True,
    )

    default_engine = "Local OS PTY" if (HAS_POSIX_PTY or HAS_WIN_PTY) else "ANSI Demo Engine"
    active_engine = default_engine
    pty_master_fd = None
    pty_process = None

    # Status Bar indicators
    title_status_text = ft.Text("📌 Title: FletTerminal", size=11, color="#89B4FA")

    # Event handlers from terminal
    def handle_title_change(e):
        title_status_text.value = f"📌 Title: {e.data}"
        page.update()

    def handle_bell(e):
        page.show_dialog(ft.SnackBar(ft.Text("🔔 Terminal Bell Triggered! (\a)"), bgcolor="#F38BA8", duration=1500))

    terminal.on_title_change = handle_title_change
    terminal.on_bell = handle_bell

    # Handle incoming bytes from Dart widget
    def handle_terminal_bytes(payload: bytes):
        nonlocal pty_master_fd, pty_process
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
        else:
            # Interactive Demo Engine response
            text = payload.decode("utf-8", errors="ignore")
            if text == "\r":
                terminal.send_bytes(b"\r\n\x1b[32m[Demo Shell]>\x1b[0m ")
            elif text == "\x03":  # Ctrl+C
                terminal.send_bytes(b"^C\r\n\x1b[32m[Demo Shell]>\x1b[0m ")
            else:
                # Echo typed characters
                terminal.send_bytes(payload)

    terminal.set_on_bytes(handle_terminal_bytes)

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

    terminal.on_resize = handle_resize

    # PTY setup and cleanup functions
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
                            terminal.send_bytes(data)
                        except OSError:
                            break

                threading.Thread(target=read_loop, daemon=True).start()
        except (OSError, AttributeError, Exception) as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"⚠️ Local PTY failed to start: {ex}. Reverting to Demo Engine."), bgcolor="#F38BA8"))
            active_engine = "ANSI Demo Engine"
            stop_pty()
            terminal.clear()
            terminal.write(f"\r\n\x1b[1;31m[PTY Error]\x1b[0m Local OS PTY is not available in this environment ({ex}).\r\nSwitched to ANSI VT100 Demo Engine.\r\n\x1b[32m[Demo Shell]>\x1b[0m ")
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
                            terminal.send_bytes(data.encode("utf-8", errors="ignore"))
                        except Exception:
                            break

                threading.Thread(target=read_loop, daemon=True).start()
            except Exception as ex:
                page.show_dialog(ft.SnackBar(ft.Text(f"⚠️ WinPTY failed to start: {ex}. Reverting to Demo Engine."), bgcolor="#F38BA8"))
                active_engine = "ANSI Demo Engine"
                stop_pty()
                terminal.clear()
                terminal.write(f"\r\n\x1b[1;31m[PTY Error]\x1b[0m WinPTY is not available ({ex}).\r\nSwitched to ANSI VT100 Demo Engine.\r\n\x1b[32m[Demo Shell]>\x1b[0m ")
                page.update()

    def stop_pty():
        nonlocal pty_master_fd, pty_process
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

    # Engine switching logic
    def switch_engine(e):
        nonlocal active_engine
        selected = e.control.value
        if selected == "Local OS PTY":
            if not HAS_POSIX_PTY and not HAS_WIN_PTY:
                page.show_dialog(ft.SnackBar(ft.Text("⚠️ Local PTY is unavailable on Web/Android sandbox or unconfigured OS."), bgcolor="#F38BA8"))
                e.control.value = "ANSI Demo Engine"
                page.update()
                return
            active_engine = "Local OS PTY"
            terminal.clear()
            stop_pty()
            if HAS_POSIX_PTY:
                start_posix_pty()
            elif HAS_WIN_PTY:
                start_win_pty()
        else:
            active_engine = "ANSI Demo Engine"
            stop_pty()
            terminal.clear()
            terminal.write("\x1b[1;36m=== FletTerminal VT100/ANSI Demo Engine Active ===\x1b[0m\r\nType commands or use test buttons above.\r\n\x1b[32m[Demo Shell]>\x1b[0m ")
        page.update()

    # Test Button actions for Demo Engine
    def run_ansi_matrix(e):
        terminal.write("\r\n\x1b[1;33m--- ANSI Color & Formatting Matrix ---\x1b[0m\r\n")
        terminal.write("Styles: \x1b[1mBold\x1b[0m | \x1b[3mItalic\x1b[0m | \x1b[4mUnderline\x1b[0m | \x1b[7mInvert\x1b[0m\r\n")
        for i in range(8):
            terminal.write(f"\x1b[3{i}mNormal {i}\x1b[0m  \x1b[1;3{i}mBright {i}\x1b[0m  \x1b[4{i};30m Bg {i} \x1b[0m\r\n")
        terminal.write("\x1b[32m[Demo Shell]>\x1b[0m ")

    def run_stress_test(e):
        terminal.write("\r\n\x1b[1;35m--- Starting 10,000 Line High-Throughput Stress Test ---\x1b[0m\r\n")
        for i in range(1, 10001):
            color = 30 + (i % 7)
            terminal.write(f"\x1b[{color}m[Stress Benchmark] Log Entry #{i:05d}: FletTerminal ring-buffer memory throughput validation check.\x1b[0m\r\n")
        terminal.write("\x1b[1;32m--- Stress Test Completed Successfully! Check scrollback ring buffer. ---\x1b[0m\r\n\x1b[32m[Demo Shell]>\x1b[0m ")

    def run_alternate_screen_test(e):
        terminal.write("\x1b[?1049h\x1b[H\x1b[2J")  # Switch to alt buffer & clear
        terminal.write("\x1b[1;36m╔══════════════════════════════════════════════════════════════════════════════╗\r\n")
        terminal.write("║       FletTerminal Alternate Screen Buffer Simulation (htop / vim mode)      ║\r\n")
        terminal.write("╠══════════════════════════════════════════════════════════════════════════════╣\r\n")
        terminal.write("║  CPU1 [|||||||||||||||||||||||||||||||||||||||||||          76.4%]           ║\r\n")
        terminal.write("║  CPU2 [||||||||||||||||||||||||||||                         42.1%]           ║\r\n")
        terminal.write("║  Mem  [|||||||||||||||||||||||||||||||||||||||||||||||||    3.8G/8.0G]       ║\r\n")
        terminal.write("║                                                                              ║\r\n")
        terminal.write("║  Notice how live terminal state is isolated inside alternate buffer (\x1b[?1049h).  ║\r\n")
        terminal.write("║  Pressing Exit below sends \x1b[?1049l to restore primary scrollback seamlessly! ║\r\n")
        terminal.write("╚══════════════════════════════════════════════════════════════════════════════╝\r\n")
        
        def restore_screen():
            time.sleep(3.5)
            terminal.write("\x1b[?1049l\r\n\x1b[32m[Demo Shell]>\x1b[0m ")
            
        threading.Thread(target=restore_screen, daemon=True).start()

    def trigger_osc_bell(e):
        terminal.write("\x1b]0;OSC 0 Title Update Test\a")
        terminal.write("\a")  # Bell
        terminal.write("\r\n\x1b[33mSent window title change (OSC 0) and bell notification (\a)!\x1b[0m\r\n\x1b[32m[Demo Shell]>\x1b[0m ")

    # Accessory Controls
    def change_cursor_style(e):
        terminal.cursor_style = e.control.value.lower()
        terminal.update()

    def toggle_cursor_blink(e):
        terminal.cursor_blink = e.control.value
        terminal.update()

    def change_theme(e):
        nonlocal active_theme_name
        active_theme_name = e.control.value
        terminal.theme = themes[active_theme_name]
        terminal.update()

    def zoom_in(e):
        terminal.font_size += 1.0
        terminal.update()

    def zoom_out(e):
        if terminal.font_size > 8.0:
            terminal.font_size -= 1.0
            terminal.update()

    # Search Bar handler
    search_field = ft.TextField(
        hint_text="Search in scrollback...",
        height=32,
        text_size=12,
        content_padding=ft.Padding(10, 4, 10, 4),
        expand=True,
        bgcolor="#1E1E2E",
        border_color="#45475A",
    )

    def do_search(e):
        if search_field.value:
            terminal.search(search_field.value)

    toolbar_controls = []
    if HAS_POSIX_PTY or HAS_WIN_PTY:
        toolbar_controls.extend([
            ft.Text("Engine:", size=11, color="#BAC2DE"),
            ft.Dropdown(
                options=[
                    ft.dropdown.Option("ANSI Demo Engine"),
                    ft.dropdown.Option("Local OS PTY"),
                ],
                value=active_engine,
                height=26,
                width=135,
                text_size=11,
                content_padding=ft.Padding(8, 0, 8, 0),
                on_select=switch_engine,
            ),
            ft.Container(width=2),
        ])
    else:
        toolbar_controls.extend([
            ft.Container(
                content=ft.Row(
                    [ft.Icon(ft.Icons.TERMINAL, size=14, color="#A6E3A1"), ft.Text("VT100 Demo", size=11, weight=ft.FontWeight.BOLD, color="#A6E3A1")],
                    spacing=4,
                ),
                padding=ft.Padding(6, 2, 6, 2),
                bgcolor="#313244",
                border_radius=4,
            ),
            ft.Container(width=2),
        ])

    toolbar_controls.extend([
        ft.Text("Theme:", size=11, color="#BAC2DE"),
        ft.Dropdown(
            options=[ft.dropdown.Option(k) for k in themes.keys()],
            value=active_theme_name,
            height=26,
            width=115,
            text_size=11,
            content_padding=ft.Padding(8, 0, 8, 0),
            on_select=change_theme,
        ),
        ft.Container(width=2),
        ft.Text("Cursor:", size=11, color="#BAC2DE"),
        ft.Dropdown(
            options=[
                ft.dropdown.Option("Block"),
                ft.dropdown.Option("Underline"),
                ft.dropdown.Option("Bar"),
            ],
            value="Block",
            height=26,
            width=90,
            text_size=11,
            content_padding=ft.Padding(8, 0, 8, 0),
            on_select=change_cursor_style,
        ),
        ft.Checkbox(label="Blink", value=True, on_change=toggle_cursor_blink, scale=0.75),
        ft.Container(width=2),
        ft.IconButton(ft.Icons.ZOOM_OUT, icon_size=16, tooltip="Zoom Out", on_click=zoom_out),
        ft.IconButton(ft.Icons.ZOOM_IN, icon_size=16, tooltip="Zoom In", on_click=zoom_in),
        ft.Container(width=2),
        search_field,
        ft.IconButton(ft.Icons.SEARCH, icon_size=16, tooltip="Search", on_click=do_search),
        ft.Container(width=2),
        ft.PopupMenuButton(
            tooltip="Run Demos & Benchmarks",
            content=ft.Container(
                content=ft.Row(
                    [ft.Icon(ft.Icons.AUTO_AWESOME, size=14, color="#F9E2AF"), ft.Text("Demos", size=11, color="#F9E2AF")],
                    spacing=4,
                ),
                padding=ft.Padding(6, 4, 6, 4),
                bgcolor="#313244",
                border_radius=4,
            ),
            items=[
                ft.PopupMenuItem(content=ft.Text("🎨 Color Matrix", size=11), on_click=run_ansi_matrix),
                ft.PopupMenuItem(content=ft.Text("🚀 10k Line Stress", size=11), on_click=run_stress_test),
                ft.PopupMenuItem(content=ft.Text("🖥️ Alt Screen (htop)", size=11), on_click=run_alternate_screen_test),
                ft.PopupMenuItem(content=ft.Text("🔔 Bell & Title", size=11), on_click=trigger_osc_bell),
            ],
        ),
        ft.Container(width=4),
        title_status_text,
    ])

    toolbar = ft.Container(
        content=ft.Row(
            controls=toolbar_controls,
            scroll=ft.ScrollMode.ADAPTIVE,
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(8, 4, 8, 4),
        bgcolor="#181825",
        border=ft.Border.only(bottom=ft.BorderSide(1, "#313244")),
    )

    page.add(
        ft.SafeArea(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        toolbar,
                        terminal,
                    ],
                    spacing=0,
                    expand=True,
                ),
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
    else:
        terminal.write("\x1b[32m[Demo Shell]>\x1b[0m ")


if __name__ == "__main__":
    ft.run(main)
