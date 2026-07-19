# flet-terminal

<p align="center">
  <a href="https://github.com/Nwokike/flet-terminal/releases/latest"><img src="https://img.shields.io/badge/Download-Flet%20Terminal-orange?style=for-the-badge&logo=github&logoColor=white" alt="Download Flet Terminal" /></a>
  <a href="https://pypi.org/project/flet-terminal/"><img src="https://img.shields.io/pypi/v/flet-terminal?style=for-the-badge&logo=pypi&logoColor=white" alt="PyPI" /></a>
  <img src="https://img.shields.io/badge/Built%20with-Flet%200.86-00B0FF?style=for-the-badge&logo=flutter&logoColor=white" alt="Flet" />
</p>

A native, GPU-accelerated terminal control for [Flet](https://flet.dev/), built on top of [xterm.dart](https://github.com/PangolinDesktop/xterm.dart). 

`flet-terminal` provides high-performance VT100/ANSI terminal emulation across **Windows, Linux, macOS, Android, and Web**, utilizing low-latency binary `DataChannel` streaming to render thousands of lines per second without UI freezing.

---

## Download Flet Terminal

Try the standalone **Flet Terminal** desktop application directly on your OS:

| Platform | Download | Notes |
| :---: | :---: | :--- |
| 🪟 **Windows (x64)** | [**FletTerminal_windows_x64.zip**](https://github.com/Nwokike/flet-terminal/releases/latest/download/FletTerminal_windows_x64.zip) | Portable Windows executable (`.exe`) |
| 🐧 **Linux (x86_64)** | [**FletTerminal_linux_x86_64.tar.gz**](https://github.com/Nwokike/flet-terminal/releases/latest/download/FletTerminal_linux_x86_64.tar.gz) | Universal Linux tarball (`tar -xzf`) |
| 📦 **All Releases** | [**View Releases Page**](https://github.com/Nwokike/flet-terminal/releases/latest) | Changelog and release notes |

---

## Features

- **High-Throughput Binary Streaming**: Routes terminal data over Flet `DataChannel` directly to the `xterm.dart` canvas, bypassing string/MsgPack serialization overhead.
- **Cross-Platform Compatibility**: Full feature parity across Desktop (`pty` / `winpty`), Mobile (`Android`), and Web (`WASM` / `Pyodide`).
- **Responsive Mobile Wrapper & Zoom Controls**: `MobileTerminal` includes `zoom_in()`, `zoom_out()`, `reset_zoom()`, and a customizable virtual accessory keyboard (`ESC`, `TAB`, `CTRL`, `ALT`, arrows) with sticky modifier toggles and collapsible state.
- **Dynamic Checkmarks & Built-in Themes**: Supports instant switching between built-in color schemes (`Dracula`, `JetBrains Dark`, `Matrix Green`), customizable font families (`JetBrains Mono`), cursor shapes (`block`, `underline`, `bar`), and cursor blink. Settings popup displays accurate checkmarks (`checked=True`) that dynamically tick as options change.
- **Interactive Search & Selection**: Built-in buffer search (`search`), scrollback control, and clipboard integration (`select_all`, `clear_selection`, right-click copy/paste).

---

## Installation

Install via `pip`:

```bash
pip install flet-terminal
```

Or using `uv`:

```bash
uv add flet-terminal
```

---

## Quickstart

### 1. Basic Terminal (`Terminal`)

```python
import flet as ft
from flet_terminal import Terminal, BUILTIN_THEMES

def main(page: ft.Page):
    page.theme_mode = ft.ThemeMode.DARK

    term = Terminal(
        scrollback=10000,
        font_family="JetBrains Mono",
        font_size=13.0,
        cursor_style="block",
        cursor_blink=True,
        theme=BUILTIN_THEMES["Dracula"],
        expand=True,
    )

    # Handle incoming bytes typed or pasted into the terminal
    def on_terminal_input(data: bytes):
        # Echo back or forward to a local OS shell / PTY process
        term.send_bytes(data)

    term.set_on_bytes(on_terminal_input)

    page.add(term)
    term.write("\x1b[1;32mWelcome to FletTerminal!\x1b[0m\r\n> ")

ft.run(main)
```

### 2. Responsive Mobile Wrapper (`MobileTerminal`)

`MobileTerminal` combines the core `Terminal` with a virtual extra-keys bar, sticky modifier buttons (`CTRL`, `ALT`), settings menu, and search bar:

```python
import flet as ft
from flet_terminal import MobileTerminal, BUILTIN_THEMES

def main(page: ft.Page):
    mt = MobileTerminal(
        show_extra_keys=True,
        show_search=True,
        show_settings=True,
        scrollback=10000,
        font_family="JetBrains Mono",
        font_size=13.0,
        theme=BUILTIN_THEMES["JetBrains Dark"],
        expand=True,
    )

    def on_bytes(payload: bytes):
        mt.send_bytes(payload)

    mt.set_on_bytes(on_bytes)
    page.add(mt)

ft.run(main)
```

---

## API Reference

### `Terminal` Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `scrollback` | `int` | `10000` | Maximum number of scrollback lines retained in the ring buffer. |
| `font_family` | `str` | `"JetBrains Mono"` | Monospace font family for rendering text. |
| `font_size` | `float` | `13.0` | Font point size. |
| `cursor_style` | `str` | `"block"` | Cursor shape (`"block"`, `"underline"`, or `"bar"`). |
| `cursor_blink` | `bool` | `True` | Whether the terminal cursor blinks continuously. |
| `theme` | `dict` | `None` | Dictionary mapping ANSI color keys to hex/int colors. |
| `read_only` | `bool` | `False` | When `True`, disables user keyboard input into the terminal canvas. |
| `auto_focus` | `bool` | `True` | Automatically focuses the terminal when mounted. |

### `Terminal` Methods

| Method | Arguments | Description |
| :--- | :--- | :--- |
| `send_bytes(payload)` | `bytes` | Sends binary data directly over the DataChannel to the terminal canvas. |
| `write(data)` | `str \| bytes` | Writes text or escape sequences to the terminal. |
| `clear()` | — | Clears the terminal scrollback and visible screen buffer. |
| `focus()` | — | Requests keyboard focus on the terminal control. |
| `search(query, start)` | `str, int` | Highlights and selects matching text in the scrollback buffer. |
| `select_all()` | — | Selects all text currently in the buffer. |
| `clear_selection()` | — | Clears any active selection. |

### `Terminal` Events

| Event | Handler | Description |
| :--- | :--- | :--- |
| `on_data` | `Callable[[ft.ControlEvent], None]` | Triggered when string-based text input occurs. |
| `on_resize` | `Callable[[ft.ControlEvent], None]` | Fired when dimensions change. Event `data` contains JSON `{"cols": int, "rows": int}`. |
| `on_title_change` | `Callable[[ft.ControlEvent], None]` | Triggered when OSC 0/2 title escape sequences are received. |
| `on_bell` | `Callable[[ft.ControlEvent], None]` | Triggered when the bell character (`\a` / `0x07`) is received. |
| `on_selection_change` | `Callable[[ft.ControlEvent], None]` | Fired when selection or search matches update. |

---

## Built-in Themes

You can import and pass built-in presets from `flet_terminal.themes`:

```python
from flet_terminal import BUILTIN_THEMES, get_theme

# Available: "Dracula", "JetBrains Dark", "Matrix Green"
my_theme = get_theme("Dracula")
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
