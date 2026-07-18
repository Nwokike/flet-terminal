"""FletTerminal Cross-Platform Test App & Demo Studio.

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

# Android can use subprocess pipes for a basic shell (no PTY, so no
# job control or fullscreen apps, but ls/cd/cat/echo/grep all work).
HAS_ANDROID_SUBPROCESS = sys.platform == "android"

# Width below which the toolbar collapses secondary actions into the overflow menu.
COMPACT_THRESHOLD = 720

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
    page.title = "FletTerminal Studio"
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

    # Modifier key state (Termux-style toggles)
    ctrl_active = False
    alt_active = False

    # Search state — last match offset + pointer for stepping through matches.
    search_idx = -1
    search_query = ""
    _match_offset = -1

    # ─── Terminal ───────────────────────────────────────────────
    terminal = Terminal(
        expand=True,
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
        page.show_snack_bar(
            ft.SnackBar(
                ft.Text("🔔 Terminal Bell Triggered! (\\a)"),
                bgcolor="#F38BA8",
                duration=1500,
            )
        )

    terminal.on_title_change = handle_title_change
    terminal.on_bell = handle_bell

    # ─── Incoming bytes from Dart widget ────────────────────────
    def handle_terminal_bytes(payload: bytes):
        nonlocal pty_master_fd, pty_process, android_proc, ctrl_active, alt_active
        if ctrl_active and len(payload) == 1:
            code = payload[0]
            if 97 <= code <= 122:  # a-z
                payload = bytes([code - 96])
            elif 65 <= code <= 90:  # A-Z
                payload = bytes([code - 64])
            ctrl_active = False
            _update_modifier_buttons()
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
                            terminal.send_bytes(data)
                        except OSError:
                            break

                threading.Thread(target=read_loop, daemon=True).start()
        except (OSError, AttributeError, Exception) as ex:
            page.show_snack_bar(
                ft.SnackBar(
                    ft.Text(
                        f"⚠️ Local PTY failed to start: {ex}. Reverting to Demo Engine."
                    ),
                    bgcolor="#F38BA8",
                )
            )
            active_engine = "ANSI Demo Engine"
            stop_pty()
            terminal.clear()
            terminal.write(
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
                            terminal.send_bytes(data.encode("utf-8", errors="ignore"))
                        except Exception:
                            break

                threading.Thread(target=read_loop, daemon=True).start()
            except Exception as ex:
                page.show_snack_bar(
                    ft.SnackBar(
                        ft.Text(
                            f"⚠️ WinPTY failed to start: {ex}. Reverting to Demo Engine."
                        ),
                        bgcolor="#F38BA8",
                    )
                )
                active_engine = "ANSI Demo Engine"
                stop_pty()
                terminal.clear()
                terminal.write(
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
                        terminal.send_bytes(data)
                    except Exception:
                        break

            threading.Thread(target=read_loop, daemon=True).start()
        except Exception as ex:
            page.show_snack_bar(
                ft.SnackBar(
                    ft.Text(
                        f"⚠️ Android shell failed to start: {ex}. Reverting to Demo Engine."
                    ),
                    bgcolor="#F38BA8",
                )
            )
            active_engine = "ANSI Demo Engine"
            stop_pty()
            terminal.clear()
            terminal.write(
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
                page.show_snack_bar(
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
            terminal.clear()
            stop_pty()
            if HAS_POSIX_PTY:
                start_posix_pty()
            elif HAS_WIN_PTY:
                start_win_pty()
        elif selected == "Android Local Shell":
            active_engine = "Android Local Shell"
            terminal.clear()
            stop_pty()
            start_android_shell()
        else:
            active_engine = "ANSI Demo Engine"
            stop_pty()
            terminal.clear()
            terminal.write("\x1b[32m[Demo Shell]>\x1b[0m ")
        page.update()

    # ─── Demo engines ───────────────────────────────────────────
    def run_ansi_matrix(e):
        terminal.write(
            "\r\n\x1b[1;33m--- ANSI Color & Formatting Matrix ---\x1b[0m\r\n"
        )
        terminal.write(
            "Styles: \x1b[1mBold\x1b[0m | \x1b[3mItalic\x1b[0m | \x1b[4mUnderline\x1b[0m | \x1b[7mInvert\x1b[0m\r\n"
        )
        for i in range(8):
            terminal.write(
                f"\x1b[3{i}mNormal {i}\x1b[0m  \x1b[1;3{i}mBright {i}\x1b[0m  \x1b[4{i};30m Bg {i} \x1b[0m\r\n"
            )
        terminal.write("\x1b[32m[Demo Shell]>\x1b[0m ")

    def run_stress_test(e):
        terminal.write(
            "\r\n\x1b[1;35m--- Starting 10,000 Line High-Throughput Stress Test ---\x1b[0m\r\n"
        )
        for i in range(1, 10001):
            color = 30 + (i % 7)
            terminal.write(
                f"\x1b[{color}m[Stress Benchmark] Log Entry #{i:05d}: FletTerminal ring-buffer memory throughput validation check.\x1b[0m\r\n"
            )
        terminal.write(
            "\x1b[1;32m--- Stress Test Completed Successfully! Check scrollback ring buffer. ---\x1b[0m\r\n\x1b[32m[Demo Shell]>\x1b[0m "
        )

    def run_alternate_screen_test(e):
        terminal.write("\x1b[?1049h\x1b[H\x1b[2J")
        terminal.write(
            "\x1b[1;36m╔══════════════════════════════════════════════════════════════════════════════╗\r\n"
        )
        terminal.write(
            "║       FletTerminal Alternate Screen Buffer Simulation (htop / vim mode)      ║\r\n"
        )
        terminal.write(
            "╠══════════════════════════════════════════════════════════════════════════════╣\r\n"
        )
        terminal.write(
            "║  CPU1 [|||||||||||||||||||||||||||||||||||||||||||          76.4%]           ║\r\n"
        )
        terminal.write(
            "║  CPU2 [||||||||||||||||||||||||||||                         42.1%]           ║\r\n"
        )
        terminal.write(
            "║  Mem  [|||||||||||||||||||||||||||||||||||||||||||||||||    3.8G/8.0G]       ║\r\n"
        )
        terminal.write(
            "║                                                                              ║\r\n"
        )
        terminal.write(
            "║  Notice how live terminal state is isolated inside alternate buffer (\\x1b[?1049h).  ║\r\n"
        )
        terminal.write(
            "║  Pressing Exit below sends \\x1b[?1049l to restore primary scrollback seamlessly! ║\r\n"
        )
        terminal.write(
            "╚══════════════════════════════════════════════════════════════════════════════╝\r\n"
        )

        def restore_screen():
            time.sleep(3.5)
            terminal.write("\x1b[?1049l\r\n\x1b[32m[Demo Shell]>\x1b[0m ")

        threading.Thread(target=restore_screen, daemon=True).start()

    def trigger_osc_bell(e):
        terminal.write("\x1b]0;OSC 0 Title Update Test\a")
        terminal.write("\a")
        terminal.write(
            "\r\n\x1b[33mSent window title change (OSC 0) and bell notification (\\a)!\x1b[0m\r\n\x1b[32m[Demo Shell]>\x1b[0m "
        )

    # ─── Appearance controls ────────────────────────────────────
    def change_cursor_style(e):
        terminal.cursor_style = e.control.value.lower()
        terminal.update()

    def toggle_cursor_blink(e):
        terminal.cursor_blink = not terminal.cursor_blink
        terminal.update()

    def zoom_in(e):
        terminal.font_size += 1.0
        terminal.update()

    def zoom_out(e):
        if terminal.font_size > 8.0:
            terminal.font_size -= 1.0
            terminal.update()

    # ─── Functional search (Dart selects the match; Python reports count) ──
    def handle_selection_change(e):
        nonlocal _match_offset
        try:
            data = json.loads(e.data)
        except Exception:
            return
        query = data.get("query", "")
        found = data.get("found", False)
        count = data.get("count", 0)
        index = data.get("index", -1)
        if found:
            _match_offset = index
        if not found:
            page.show_snack_bar(
                ft.SnackBar(
                    ft.Text(f'🔍 No matches for "{query}"'),
                    bgcolor="#313244",
                    duration=1500,
                )
            )
        else:
            label = search_idx + 1 if (query == search_query and search_idx >= 0) else 1
            page.show_snack_bar(
                ft.SnackBar(
                    ft.Text(f'🔍 {label} of {count} matches for "{query}"'),
                    bgcolor="#313244",
                    duration=1500,
                )
            )

    terminal.on_selection_change = handle_selection_change

    def do_search(e):
        """Fresh search from the top; selects the first match."""
        nonlocal search_query, search_idx
        q = search_field.value or ""
        if not q:
            return
        search_query = q
        search_idx = 0
        terminal.search(q, start=0)

    def do_search_next(e):
        """Step to the next match (triggered by Enter in the search field)."""
        nonlocal search_query, search_idx
        q = search_field.value or ""
        if not q:
            return
        if q != search_query:
            search_query = q
            search_idx = 0
            terminal.search(q, start=0)
            return
        search_idx += 1
        # `start` resumes scanning just past the previous match offset.
        terminal.search(q, start=_last_match_offset() + 1)

    def _last_match_offset() -> int:
        # The most recent match offset is tracked when the Dart event arrives.
        return _match_offset

    # ─── Modifier toggle buttons (CTRL / ALT) ───────────────────
    btn_ctrl = ft.IconButton(
        icon=ft.Icons.KEYBOARD_CONTROL,
        icon_size=16,
        tooltip="CTRL",
        selected=ctrl_active,
        selected_icon=ft.Icons.KEYBOARD_CONTROL,
        style=ft.ButtonStyle(padding=4, visual_density=ft.VisualDensity.COMPACT),
        on_click=lambda e: _toggle_ctrl(),
    )
    btn_alt = ft.IconButton(
        icon=ft.Icons.ALT_ROUTE,
        icon_size=16,
        tooltip="ALT",
        selected=alt_active,
        selected_icon=ft.Icons.ALT_ROUTE,
        style=ft.ButtonStyle(padding=4, visual_density=ft.VisualDensity.COMPACT),
        on_click=lambda e: _toggle_alt(),
    )

    def _toggle_ctrl():
        nonlocal ctrl_active
        ctrl_active = not ctrl_active
        btn_ctrl.selected = ctrl_active
        _update_modifier_buttons()

    def _toggle_alt():
        nonlocal alt_active
        alt_active = not alt_active
        btn_alt.selected = alt_active
        _update_modifier_buttons()

    def _update_modifier_buttons():
        btn_ctrl.selected = ctrl_active
        btn_alt.selected = alt_active
        page.update()

    # ─── Extra (Termux-style) keys bar ──────────────────────────
    def send_virtual_key(payload: bytes):
        handle_terminal_bytes(payload)

    def _make_key_btn(label, payload, bg="#313244"):
        return ft.Button(
            content=ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color="#CDD6F4"),
            height=34,
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=10, vertical=2),
                bgcolor=bg,
                visual_density=ft.VisualDensity.COMPACT,
            ),
            on_click=lambda e, p=payload: send_virtual_key(p),
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

    # Subtle horizontal scroll affordance for the extra-keys strip.
    scroll_hint = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    expand=True,
                    height=2,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.center_left,
                        end=ft.alignment.center_right,
                        colors=["#45475A", "#18182500"],
                    ),
                ),
                ft.Container(
                    expand=True,
                    height=2,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.center_right,
                        end=ft.alignment.center_left,
                        colors=["#45475A", "#18182500"],
                    ),
                ),
            ],
        ),
        padding=ft.padding.only(left=6, right=6, bottom=2),
    )

    def toggle_extra_keys(e):
        extra_keys_bar.visible = not extra_keys_bar.visible
        scroll_hint.visible = extra_keys_bar.visible
        # Reflect open/closed state on the keyboard toggle button.
        for c in (kb_toggle,):
            c.selected = extra_keys_bar.visible
        page.update()

    # ─── Search field (inline on wide screens) ──────────────────
    search_field = ft.TextField(
        hint_text="Search…",
        height=34,
        width=150,
        text_size=12,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=2),
        bgcolor="#1E1E2E",
        border_color="#45475A",
        on_submit=do_search_next,  # Enter steps to the next match
    )
    search_btn = ft.IconButton(
        icon=ft.Icons.SEARCH,
        icon_size=18,
        tooltip="Search",
        style=ft.ButtonStyle(padding=4, visual_density=ft.VisualDensity.COMPACT),
        on_click=do_search,
    )
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
    kb_toggle = ft.IconButton(
        icon=ft.Icons.KEYBOARD,
        icon_size=18,
        tooltip="Virtual Keys",
        selected=extra_keys_bar.visible,
        selected_icon=ft.Icons.KEYBOARD,
        style=ft.ButtonStyle(padding=4, visual_density=ft.VisualDensity.COMPACT),
        on_click=toggle_extra_keys,
    )

    # ─── Overflow menus (SubmenuButton = real nested submenus) ──
    def _theme_submenu():
        return ft.SubmenuButton(
            content=ft.Text("Theme"),
            controls=[
                ft.MenuItemButton(
                    content=ft.Text("Dracula"),
                    leading_icon=ft.Icon(
                        ft.Icons.CHECK, visible=active_theme_name == "Dracula"
                    ),
                    on_click=lambda e: change_theme("Dracula"),
                ),
                ft.MenuItemButton(
                    content=ft.Text("JetBrains Dark"),
                    leading_icon=ft.Icon(
                        ft.Icons.CHECK, visible=active_theme_name == "JetBrains Dark"
                    ),
                    on_click=lambda e: change_theme("JetBrains Dark"),
                ),
                ft.MenuItemButton(
                    content=ft.Text("Matrix Green"),
                    leading_icon=ft.Icon(
                        ft.Icons.CHECK, visible=active_theme_name == "Matrix Green"
                    ),
                    on_click=lambda e: change_theme("Matrix Green"),
                ),
            ],
        )

    def _cursor_submenu():
        cur = terminal.cursor_style or "block"
        return ft.SubmenuButton(
            content=ft.Text("Cursor"),
            controls=[
                ft.MenuItemButton(
                    content=ft.Text("Block"),
                    leading_icon=ft.Icon(ft.Icons.CHECK, visible=cur == "block"),
                    on_click=lambda e: change_cursor_type("block"),
                ),
                ft.MenuItemButton(
                    content=ft.Text("Underline"),
                    leading_icon=ft.Icon(ft.Icons.CHECK, visible=cur == "underline"),
                    on_click=lambda e: change_cursor_type("underline"),
                ),
                ft.MenuItemButton(
                    content=ft.Text("Bar"),
                    leading_icon=ft.Icon(ft.Icons.CHECK, visible=cur == "bar"),
                    on_click=lambda e: change_cursor_type("bar"),
                ),
            ],
        )

    def change_theme(name):
        nonlocal active_theme_name
        active_theme_name = name
        terminal.theme = THEMES[name]
        terminal.update()

    def change_cursor_type(style):
        terminal.cursor_style = style
        terminal.update()

    settings_menu = ft.SubmenuButton(
        content=ft.Text("Settings"),
        controls=[
            _theme_submenu(),
            _cursor_submenu(),
            ft.MenuItemButton(
                content=ft.Text("Toggle Cursor Blink"),
                leading_icon=ft.Icon(
                    ft.Icons.CHECK, visible=bool(terminal.cursor_blink)
                ),
                on_click=lambda e: toggle_cursor_blink(e),
            ),
        ],
    )

    demos_menu = ft.SubmenuButton(
        content=ft.Text("Demos"),
        controls=[
            ft.MenuItemButton(
                content=ft.Text("🎨 Color Matrix"), on_click=run_ansi_matrix
            ),
            ft.MenuItemButton(
                content=ft.Text("🚀 10k Stress Test"), on_click=run_stress_test
            ),
            ft.MenuItemButton(
                content=ft.Text("🖥️ Alt Screen"), on_click=run_alternate_screen_test
            ),
            ft.MenuItemButton(
                content=ft.Text("🔔 Bell & Title"), on_click=trigger_osc_bell
            ),
        ],
    )

    # Kebab overflow: hosts the controls that are inline on wide screens but
    # would crowd a phone — Search and Zoom. Demos/Settings stay as compact
    # SubmenuButtons (they fit even on narrow toolbars).
    def build_overflow():
        return ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            icon_size=20,
            tooltip="More",
            style=ft.ButtonStyle(padding=4, visual_density=ft.VisualDensity.COMPACT),
            items=[
                ft.PopupMenuItem(
                    content=ft.Text("Search"), on_click=lambda e: search_field.focus()
                ),
                ft.PopupMenuItem(content=ft.Text("Zoom In"), on_click=zoom_in),
                ft.PopupMenuItem(content=ft.Text("Zoom Out"), on_click=zoom_out),
            ],
        )

    # ─── AppBar (compact, adaptive, always present) ────────────
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
        content_padding=ft.padding.symmetric(horizontal=8, vertical=0),
        dense=True,
        on_select=switch_engine,
    )

    def build_appbar():
        wide = (page.width or 0) >= COMPACT_THRESHOLD
        actions: list[ft.Control] = []
        if HAS_POSIX_PTY or HAS_WIN_PTY or HAS_ANDROID_SUBPROCESS:
            actions.append(engine_dropdown)
        else:
            actions.append(
                ft.Container(
                    content=ft.Text(
                        "VT100 Demo",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color="#A6E3A1",
                    ),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    bgcolor="#313244",
                    border_radius=4,
                )
            )

        # Demos + Settings are always reachable as compact SubmenuButtons.
        actions.extend([demos_menu, settings_menu, kb_toggle])
        if wide:
            # Wide: everything inline for one-tap access.
            actions.extend([search_field, search_btn, zoom_out_btn, zoom_in_btn])
        else:
            # Narrow: tuck Search + Zoom into the kebab to keep the row short.
            actions.append(build_overflow())

        return ft.AppBar(
            title=ft.Text(
                "FletTerminal", size=14, weight=ft.FontWeight.BOLD, color="#CDD6F4"
            ),
            center_title=False,
            toolbar_height=48,
            leading_width=40,
            adaptive=True,
            bgcolor="#181825",
            actions=actions,
            actions_padding=ft.padding.only(right=8),
        )

    appbar = build_appbar()

    # ─── Layout ─────────────────────────────────────────────────
    page.add(
        ft.SafeArea(
            content=ft.Column(
                controls=[
                    appbar,
                    terminal,
                    extra_keys_bar,
                    scroll_hint,
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
        )
    )

    # Rebuild the AppBar responsively only when the wide/narrow state flips,
    # to avoid re-parenting controls on every resize tick.
    _last_wide = (page.width or 0) >= COMPACT_THRESHOLD

    def on_resize(e):
        nonlocal appbar, _last_wide
        wide = (page.width or 0) >= COMPACT_THRESHOLD
        if wide == _last_wide:
            return
        _last_wide = wide
        new_bar = build_appbar()
        col = page.controls[0].content
        col.controls[0] = new_bar
        appbar = new_bar
        page.update()

    page.on_resize = on_resize

    if active_engine == "Local OS PTY":
        if HAS_POSIX_PTY:
            start_posix_pty()
        elif HAS_WIN_PTY:
            start_win_pty()
    elif active_engine == "Android Local Shell":
        start_android_shell()
    else:
        terminal.write("\x1b[32m[Demo Shell]>\x1b[0m ")


if __name__ == "__main__":
    ft.run(main)
