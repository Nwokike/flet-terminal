# flet-terminal

[![PyPI](https://img.shields.io/pypi/v/flet-terminal)](https://pypi.org/project/flet-terminal/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/flet-terminal)](https://pypi.org/project/flet-terminal/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Live Demo](https://img.shields.io/badge/demo-github_pages-blue)](https://nwokike.github.io/flet-terminal/)

Native GPU-accelerated Terminal control for [Flet](https://flet.dev) (`ft.LayoutControl`),
powered by [`xterm.dart`](https://pub.dev/packages/xterm). Exposes a high-throughput,
low-latency terminal canvas with zero-copy binary streaming via Flet `DataChannel`s.

> **🌐 [Live Web Demo](https://nwokike.github.io/flet-terminal/) — try it in your browser instantly.**

---

## Installation

Add `flet-terminal` to your Flet project:

```bash
# pip
pip install flet-terminal

# uv
uv add flet-terminal
```

Or add to `pyproject.toml`:

```toml
[project]
dependencies = [
    "flet-terminal",
    "flet>=0.86.0",
]
```

Requires **Flet >= 0.86.0**.

---

## Quick start — add terminal to your Flet app

```python
import flet as ft
from flet_terminal import Terminal


def main(page: ft.Page):
    # 1. Instantiate the Terminal widget
    terminal = Terminal(
        font_size=13.0,
        cursor_style="block",
        cursor_blink=True,
        theme={"background": "#1e1e2e", "foreground": "#cdd6f4"},
    )

    # 2. Handle keystrokes (send to PTY, SSH, serial port…)
    def handle_data(e):
        terminal.write(f"You typed: {e.data}\r\n")

    terminal.on_data = handle_data

    # 3. Add to your page layout
    page.add(
        ft.SafeArea(
            ft.Container(content=terminal, expand=True, bgcolor="#1e1e2e",
                         border_radius=8)
        )
    )

    # 4. Write VT100/ANSI sequences directly from Python
    terminal.write("\x1b[1;32mWelcome to flet-terminal!\x1b[0m\r\n$ ")


ft.run(main)
```

---

## Multi-platform demo binaries

Want to try the full Studio app (with PTY integration, stress tests, Termux-style
virtual keys) before integrating into your own project?

| Platform | Download | Engine |
| :------- | :------: | :----- |
| 📱 **Android (ARM64)** | [fletterminalstudio-arm64-v8a.apk](https://github.com/Nwokike/flet-terminal/releases/latest/download/fletterminalstudio-arm64-v8a.apk) | Basic Shell / Demo |
| 📱 **Android (ARMv7)** | [fletterminalstudio-armeabi-v7a.apk](https://github.com/Nwokike/flet-terminal/releases/latest/download/fletterminalstudio-armeabi-v7a.apk) | Basic Shell / Demo |
| 📱 **Android (x86_64)** | [fletterminalstudio-x86_64.apk](https://github.com/Nwokike/flet-terminal/releases/latest/download/fletterminalstudio-x86_64.apk) | Basic Shell / Demo |
| 🖥️ **Windows portable** | [FletTerminalStudio_0.2.0_windows_x64.zip](https://github.com/Nwokike/flet-terminal/releases/latest/download/FletTerminalStudio_0.2.0_windows_x64.zip) | Local PTY / Demo |
| 🐧 **Linux standalone** | [FletTerminalStudio_0.2.0_linux_x86_64.tar.gz](https://github.com/Nwokike/flet-terminal/releases/latest/download/FletTerminalStudio_0.2.0_linux_x86_64.tar.gz) | Local PTY / Demo |

### Engine availability by platform

| Platform | Real shell (`bash`/`powershell`) | Basic shell (`ls`, `cd`) | Demo Engine |
| :------- | :-------------------------------: | :----------------------: | :---------: |
| Linux / macOS | ✅ Local PTY | — | ✅ |
| Windows | ✅ ConPTY | — | ✅ |
| Android | ❌ (SELinux blocks PTY) | ✅ `subprocess.Popen` | ✅ |
| Web (PWA) | ❌ (sandbox) | ❌ | ✅ |

---

## Why flet-terminal

- **Cross-platform**: Windows, Linux, macOS, Android, iOS, and Web from one Python control.
- **Zero-copy binary streaming**: PTY bytes travel over a dedicated Flet `DataChannel`
  (`send_bytes` / `on_bytes`), bypassing MsgPack/JSON encoding overhead.
- **Full VT100/ANSI support**: true RGB colors, bold/italic, alternate screen buffers
  (`htop` / `vim` mode), OSC 0/2 window titles, and bell (`\a`).
- **Termux-style virtual accessory bar**: tactile soft-key buttons (`ESC`, `TAB`,
  `CTRL`, `ALT`, arrows, symbols) with sticky modifier toggles for mobile keyboards.

---

## API Reference

### Constructor properties

All standard `LayoutControl` properties are available (`width`, `height`, `expand`,
`opacity`, `tooltip`, `left`, `top`, `right`, `bottom`, `rotate`, `scale`, …).

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `scrollback` | `int \| None` | `10000` | Max lines retained in the ring buffer. |
| `font_family` | `str \| None` | `"JetBrains Mono"` | Terminal typeface. |
| `font_size` | `float \| None` | `13.0` | Base font size in px. |
| `cursor_blink` | `bool \| None` | `True` | Whether the cursor blinks. |
| `cursor_style` | `str \| None` | `"block"` | One of `"block"`, `"underline"`, `"bar"`. |
| `theme` | `dict \| None` | `None` | Color map (see [Theming](#theming)). |
| `read_only` | `bool \| None` | `False` | Disable keyboard input. |
| `auto_focus` | `bool \| None` | `True` | Grab focus when mounted. |
| `ctrl_active` | `bool \| None` | `False` | Sticky CTRL modifier (synced with Dart). |
| `alt_active` | `bool \| None` | `False` | Sticky ALT modifier (synced with Dart). |

#### Theming

`theme` accepts a dict of color keys. Unknown keys are ignored; missing keys
fall back to xterm defaults.

```python
terminal.theme = {
    "background": "#1E1E2E",
    "foreground": "#CDD6F4",
    "cursor": "#F5E0DC",
    "selection": "#585B70",
    "black": "#45475A", "red": "#F38BA8", "green": "#A6E3A1",
    "yellow": "#F9E2AF", "blue": "#89B4FA", "magenta": "#F5C2E7",
    "cyan": "#94E2D5", "white": "#BAC2DE",
}
```

### Events

Bind handlers by setting `terminal.on_<event>`:

| Event | Handler | Payload |
|-------|---------|---------|
| `on_data` | `ControlEventHandler` | Keystrokes typed in the canvas (`e.data`). |
| `on_resize` | `ControlEventHandler` | `{"cols": int, "rows": int}` (JSON string). |
| `on_title_change` | `ControlEventHandler` | New window title (OSC 0/2). |
| `on_bell` | `ControlEventHandler` | Bell (`\a`) — empty payload. |
| `on_modifier_reset` | `ControlEventHandler` | Fired when a sticky CTRL/ALT modifier auto-resets after a keystroke. |
| `on_selection_change` | `ControlEventHandler` | Result of `search()`: `{"query", "found", "count", "index"}`. |

### Methods

| Method | Description |
|--------|-------------|
| `write(data)` / `write_async(data)` | Send text or escape sequences to the terminal. |
| `clear()` / `clear_async()` | Clear scrollback + visible buffer. |
| `focus()` / `focus_async()` | Request keyboard focus. |
| `search(query, start=0)` / `search_async(...)` | Find `query` in buffer, selects the match, reports count via `on_selection_change`. |
| `clear_selection()` / `clear_selection_async()` | Clear active text selection. |
| `select_all()` / `select_all_async()` | Select all buffer text. |
| `send_bytes(payload)` | Send **raw bytes** over the `DataChannel` (binary-safe). |
| `set_on_bytes(handler)` | Register callback for raw bytes from Dart → Python (e.g. feed a local PTY). |

### Data flow

```
Keyboard ── on_data ──▶ Python ── send_bytes ──▶ DataChannel ──▶ xterm.dart
   ▲                                                              │
   └───────── on_bytes (set_on_bytes) ◀───────────────────────────┘
```

---

## Using with a real shell

### Linux / macOS (POSIX PTY)

The extension doesn't manage PTY lifecycle — that's your app's job. Connect
`on_data` and the data channel to a `pty` session:

```python
import os, pty, threading

master_fd, slave_fd = pty.openpty()
pid = os.fork()
if pid == 0:  # child
    os.setsid()
    os.dup2(slave_fd, 0); os.dup2(slave_fd, 1); os.dup2(slave_fd, 2)
    os.execv("/bin/bash", ["bash", "-l"])
else:  # parent
    os.close(slave_fd)
    terminal.on_data = lambda e: os.write(master_fd, e.data.encode())
    terminal.set_on_bytes(lambda b: terminal.send_bytes(b))
    def reader():
        while data := os.read(master_fd, 4096):
            terminal.send_bytes(data)
    threading.Thread(target=reader, daemon=True).start()
```

### Windows (ConPTY via `pywinpty`)

```python
import winpty
proc = winpty.PtyProcess.spawn("powershell.exe")
terminal.on_data = lambda e: proc.write(e.data)
terminal.set_on_bytes(lambda b: terminal.send_bytes(b))
def reader():
    while data := proc.read():
        terminal.send_bytes(data.encode())
threading.Thread(target=reader, daemon=True).start()
```

### Android (Basic shell via `subprocess`)

On Android, `fork()` and PTY are blocked by SELinux. A basic shell using
`subprocess.Popen` pipes is available for `ls`, `cd`, `cat`, `echo`, `grep` —
full-screen apps (`vim`, `htop`) won't work without a PTY.

```python
import subprocess, threading, signal

proc = subprocess.Popen(
    ["sh"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    env={**os.environ, "TERM": "xterm-256color"},
)

def handle_data(e):
    data = e.data.encode()
    if data == b"\x03":              # Ctrl+C
        proc.send_signal(signal.SIGINT)
    elif data == b"\x04":            # Ctrl+D
        proc.stdin.close()
    else:
        proc.stdin.write(data)
        proc.stdin.flush()

terminal.on_data = handle_data
terminal.set_on_bytes(lambda b: terminal.send_bytes(b))

def reader():
    while proc.poll() is None:
        data = proc.stdout.read(4096)
        if not data: break
        terminal.send_bytes(data)

threading.Thread(target=reader, daemon=True).start()
```

---

## Key features

### Virtual accessory keys (Termux-style)

The Studio app ships a toolbar of soft-key buttons (`ESC`, `TAB`, `CTRL`, `ALT`,
arrow keys, `-`, `/`, `|`, `~`) with sticky modifier toggles. When `CTRL` is
active, the next letter keystroke becomes a control code (`A` → `\x01`). `ALT`
prefixes the next keystroke with `\x1b`. Modifiers auto-reset after use.

### DataChannel streaming

For high-throughput data (PTY I/O, log tailing), Flet's `DataChannel` provides a
zero-copy binary pipe that bypasses the MsgPack control protocol entirely.
`send_bytes()` and `set_on_bytes()` use this path.

### Search

`terminal.search(query)` scans the ring buffer, selects the first match (visible
via the selection color), and reports the match count via `on_selection_change`.
Call `search(query, start=...)` to step through successive matches.

---

## Android note

Android does not allow `os.fork()` or PTY creation for regular (non-root) apps
due to SELinux policies. The pre-built demo APK defaults to a basic pipe-backed
shell (`sh` via `subprocess.Popen`) which supports `ls`, `cd`, `cat`, `echo`,
`grep`, and similar commands. For a full-featured terminal on Android, consider:

- **Termux** — install Termux from F-Droid for a native PTY-powered shell.
- **Remote SSH** — bundle an SSH client and connect to a remote server.
- **Root** — on rooted devices, `fork()` and PTY both work.

---

## License

[MIT License](LICENSE)
