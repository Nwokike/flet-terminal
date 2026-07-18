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
    page.title = "FletTerminal Studio"
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

    # Modifier key state (Termux-style toggles)
    ctrl_active = False
    alt_active = False

    # Event handlers from terminal
    def handle_title_change(e):
        page.update()

    def handle_bell(e):
        page.show_dialog(ft.SnackBar(ft.Text("🔔 Terminal Bell Triggered! (\\a)"), bgcolor="#F38BA8", duration=1500))

    terminal.on_title_change = handle_title_change
    terminal.on_bell = handle_bell

    # Handle incoming bytes from Dart widget
    def handle_terminal_bytes(payload: bytes):
        nonlocal pty_master_fd, pty_process, ctrl_active, alt_active
        # Apply CTRL modifier: convert a-z/A-Z to control codes
        if ctrl_active and len(payload) == 1:
            code = payload[0]
            if 97 <= code <= 122:  # a-z
                payload = bytes([code - 96])
            elif 65 <= code <= 90:  # A-Z
                payload = bytes([code - 64])
            ctrl_active = False
            _update_modifier_buttons()

        # Apply ALT modifier: prefix with ESC
        if alt_active:
            payload = b"\x1b" + payload
            alt_active = False
            _update_modifier_buttons()

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
            elif text == "\x0c":  # Ctrl+L
                terminal.clear()
                terminal.write("\x1b[32m[Demo Shell]>\x1b[0m ")
            elif text == "\x04":  # Ctrl+D
                terminal.send_bytes(b"exit\r\n\x1b[32m[Demo Shell]>\x1b[0m ")
            elif text == "\t":
                terminal.send_bytes(b"  ")
            elif text == "\x1b":
                terminal.send_bytes(b"^[")
            elif payload in (b"\x1b[A", b"\x1b[B", b"\x1b[C", b"\x1b[D"):
                terminal.send_bytes(payload)
            else:
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
            terminal.write("\x1b[32m[Demo Shell]>\x1b[0m ")
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
        terminal.write("║  Notice how live terminal state is isolated inside alternate buffer (\\x1b[?1049h).  ║\r\n")
        terminal.write("║  Pressing Exit below sends \\x1b[?1049l to restore primary scrollback seamlessly! ║\r\n")
        terminal.write("╚══════════════════════════════════════════════════════════════════════════════╝\r\n")
        
        def restore_screen():
            time.sleep(3.5)
            terminal.write("\x1b[?1049l\r\n\x1b[32m[Demo Shell]>\x1b[0m ")
            
        threading.Thread(target=restore_screen, daemon=True).start()

    def trigger_osc_bell(e):
        terminal.write("\x1b]0;OSC 0 Title Update Test\a")
        terminal.write("\a")  # Bell
        terminal.write("\r\n\x1b[33mSent window title change (OSC 0) and bell notification (\\a)!\x1b[0m\r\n\x1b[32m[Demo Shell]>\x1b[0m ")

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
        hint_text="Search...",
        height=30,
        text_size=11,
        content_padding=ft.Padding(8, 2, 8, 2),
        width=140,
        bgcolor="#1E1E2E",
        border_color="#45475A",
    )

    def do_search(e):
        if search_field.value:
            terminal.search(search_field.value)

    # ─── Build toolbar: only essential controls visible, rest in overflow menu ───

    # Engine selector (only on desktop)
    toolbar_controls = []
    if HAS_POSIX_PTY or HAS_WIN_PTY:
        toolbar_controls.append(
            ft.Dropdown(
                options=[
                    ft.dropdown.Option("ANSI Demo Engine"),
                    ft.dropdown.Option("Local OS PTY"),
                ],
                value=active_engine,
                height=30,
                width=140,
                text_size=11,
                content_padding=ft.Padding(8, 0, 8, 0),
                on_select=switch_engine,
            ),
        )
    else:
        toolbar_controls.append(
            ft.Container(
                content=ft.Text("VT100 Demo", size=11, weight=ft.FontWeight.BOLD, color="#A6E3A1"),
                padding=ft.Padding(8, 4, 8, 4),
                bgcolor="#313244",
                border_radius=4,
            ),
        )

    # Demos popup
    toolbar_controls.append(
        ft.PopupMenuButton(
            icon=ft.Icons.AUTO_AWESOME,
            icon_size=18,
            icon_color="#F9E2AF",
            tooltip="Demos",
            items=[
                ft.PopupMenuItem(content=ft.Text("🎨 Color Matrix"), on_click=run_ansi_matrix),
                ft.PopupMenuItem(content=ft.Text("🚀 10k Stress Test"), on_click=run_stress_test),
                ft.PopupMenuItem(content=ft.Text("🖥️ Alt Screen"), on_click=run_alternate_screen_test),
                ft.PopupMenuItem(content=ft.Text("🔔 Bell & Title"), on_click=trigger_osc_bell),
            ],
        ),
    )

    # Search inline
    toolbar_controls.extend([
        search_field,
        ft.IconButton(icon=ft.Icons.SEARCH, icon_size=16, tooltip="Search", on_click=do_search, style=ft.ButtonStyle(padding=0)),
    ])

    # Spacer to push settings to the right
    toolbar_controls.append(ft.Container(expand=True))

    # Zoom
    toolbar_controls.extend([
        ft.IconButton(icon=ft.Icons.ZOOM_OUT, icon_size=16, tooltip="Zoom Out", on_click=zoom_out, style=ft.ButtonStyle(padding=0)),
        ft.IconButton(icon=ft.Icons.ZOOM_IN, icon_size=16, tooltip="Zoom In", on_click=zoom_in, style=ft.ButtonStyle(padding=0)),
    ])

    # Settings overflow menu (theme, cursor, blink)
    toolbar_controls.append(
        ft.PopupMenuButton(
            icon=ft.Icons.SETTINGS,
            icon_size=18,
            tooltip="Settings",
            items=[
                ft.PopupMenuItem(content=ft.Text("Theme")),
                ft.PopupMenuItem(content=ft.Text("  Dracula"), on_click=lambda e: _set_theme("Dracula")),
                ft.PopupMenuItem(content=ft.Text("  JetBrains Dark"), on_click=lambda e: _set_theme("JetBrains Dark")),
                ft.PopupMenuItem(content=ft.Text("  Matrix Green"), on_click=lambda e: _set_theme("Matrix Green")),
                ft.PopupMenuItem(content=ft.Text("Cursor Style")),
                ft.PopupMenuItem(content=ft.Text("  Block"), on_click=lambda e: _set_cursor("block")),
                ft.PopupMenuItem(content=ft.Text("  Underline"), on_click=lambda e: _set_cursor("underline")),
                ft.PopupMenuItem(content=ft.Text("  Bar"), on_click=lambda e: _set_cursor("bar")),
                ft.PopupMenuItem(content=ft.Text("Toggle Cursor Blink"), on_click=lambda e: _toggle_blink()),
            ],
        ),
    )

    # Toggle extra keys bar
    toolbar_controls.append(
        ft.IconButton(icon=ft.Icons.KEYBOARD, icon_size=18, tooltip="Virtual Keys", on_click=lambda e: toggle_extra_keys(e), style=ft.ButtonStyle(padding=0)),
    )

    def _set_theme(name):
        nonlocal active_theme_name
        active_theme_name = name
        terminal.theme = themes[name]
        terminal.update()

    def _set_cursor(style):
        terminal.cursor_style = style
        terminal.update()

    def _toggle_blink():
        terminal.cursor_blink = not terminal.cursor_blink
        terminal.update()

    toolbar = ft.Container(
        content=ft.Row(
            controls=toolbar_controls,
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(6, 4, 6, 4),
        bgcolor="#181825",
        border=ft.Border.only(bottom=ft.BorderSide(1, "#313244")),
    )

    # ─── Termux-style extra keys bar with CTRL/ALT toggle modifiers ───

    def send_virtual_key(payload: bytes):
        handle_terminal_bytes(payload)

    # CTRL and ALT toggle buttons (refs for styling updates)
    btn_ctrl = ft.Button(
        "CTRL", height=32,
        style=ft.ButtonStyle(
            padding=ft.Padding(10, 2, 10, 2),
            bgcolor="#313244", color="#CDD6F4",
            text_style=ft.TextStyle(size=12, weight=ft.FontWeight.BOLD),
        ),
        on_click=lambda e: _toggle_ctrl(),
    )
    btn_alt = ft.Button(
        "ALT", height=32,
        style=ft.ButtonStyle(
            padding=ft.Padding(10, 2, 10, 2),
            bgcolor="#313244", color="#CDD6F4",
            text_style=ft.TextStyle(size=12, weight=ft.FontWeight.BOLD),
        ),
        on_click=lambda e: _toggle_alt(),
    )

    def _toggle_ctrl():
        nonlocal ctrl_active
        ctrl_active = not ctrl_active
        _update_modifier_buttons()

    def _toggle_alt():
        nonlocal alt_active
        alt_active = not alt_active
        _update_modifier_buttons()

    def _update_modifier_buttons():
        btn_ctrl.style = ft.ButtonStyle(
            padding=ft.Padding(10, 2, 10, 2),
            bgcolor="#8BE9FD" if ctrl_active else "#313244",
            color="#1E1E1E" if ctrl_active else "#CDD6F4",
            text_style=ft.TextStyle(size=12, weight=ft.FontWeight.BOLD),
        )
        btn_alt.style = ft.ButtonStyle(
            padding=ft.Padding(10, 2, 10, 2),
            bgcolor="#8BE9FD" if alt_active else "#313244",
            color="#1E1E1E" if alt_active else "#CDD6F4",
            text_style=ft.TextStyle(size=12, weight=ft.FontWeight.BOLD),
        )
        page.update()

    def _make_key_btn(label, payload, bg="#313244"):
        return ft.Button(
            label, height=32,
            style=ft.ButtonStyle(
                padding=ft.Padding(10, 2, 10, 2),
                bgcolor=bg, color="#CDD6F4",
                text_style=ft.TextStyle(size=12, weight=ft.FontWeight.BOLD),
            ),
            on_click=lambda e: send_virtual_key(payload),
        )

    extra_keys_bar = ft.Container(
        content=ft.Row(
            controls=[
                _make_key_btn("ESC", b"\x1b"),
                _make_key_btn("TAB", b"\t"),
                btn_ctrl,
                btn_alt,
                _make_key_btn("▲", b"\x1b[A", bg="#45475A"),
                _make_key_btn("▼", b"\x1b[B", bg="#45475A"),
                _make_key_btn("◀", b"\x1b[D", bg="#45475A"),
                _make_key_btn("▶", b"\x1b[C", bg="#45475A"),
                _make_key_btn("-", b"-"),
                _make_key_btn("/", b"/"),
                _make_key_btn("|", b"|"),
                _make_key_btn("~", b"~"),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(6, 4, 6, 4),
        bgcolor="#181825",
        border=ft.Border.only(top=ft.BorderSide(1, "#313244")),
    )

    def toggle_extra_keys(e):
        extra_keys_bar.visible = not extra_keys_bar.visible
        page.update()

    page.add(
        ft.SafeArea(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        toolbar,
                        terminal,
                        extra_keys_bar,
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
