# flet-terminal

Native GPU-accelerated Terminal control for Flet (`ft.LayoutControl`) powered by [`xterm.dart`](https://pub.dev/packages/xterm). Exposes a high-throughput, low-latency terminal canvas with zero-copy binary streaming via Flet `DataChannel`s.

---

## 🚀 Test the Demo Studio App right now
Want to try the live terminal demo, high-speed ring buffer stress tests, and Termux virtual accessory keys before integrating?  
Download the pre-built multi-platform binaries from our latest release:  
👉 **[Download Latest Release (Android APKs, Windows Portable Zip, Linux Bundle & Web PWA)](https://github.com/Nwokike/flet-terminal/releases/latest)**

---

## 📦 Installation

```bash
pip install flet-terminal
```

*(Note: Requires Flet >= 0.80.0)*

---

## 💻 Quick Start & Integration

`flet-terminal` wraps Flutter's `xterm.dart` widget in a reusable Flet control (`Terminal`). Drop it directly into your page layout (`Row`, `Column`, `Container`, or `Tabs`) just like any other Flet widget:

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

    # 2. Handle user keyboard input (send to local PTY, SSH, or serial port)
    def handle_keyboard(e):
        # e.data contains keystrokes typed by the user inside the terminal canvas
        terminal.write(f"You typed: {e.data}\r\n")

    terminal.on_data = handle_keyboard

    # 3. Add to page inside a SafeArea (respects mobile notches and status bars)
    page.add(
        ft.SafeArea(
            ft.Container(
                content=terminal,
                expand=True,
                bgcolor="#1e1e2e",
                border_radius=8,
            )
        )
    )

    # 4. Write VT100/ANSI sequences directly from Python
    terminal.write("\x1b[1;32mWelcome to flet-terminal!\x1b[0m\r\n$ ")


ft.run(main)
```

---

## ✨ Key Features & Mobile Capabilities

- **⚡ Zero-Copy Binary Streaming (`send_bytes`)**: High-throughput Flet `DataChannel` bridge eliminates base64/JSON encoding overhead, rendering 10,000+ lines in milliseconds without UI stutter.
- **🎨 Full VT100/ANSI Support**: True RGB colors, bold/italic formatting, alternate screen buffers (`htop`/`vim` mode), window titles (`OSC 0`), and bell notifications (`\a`).
- **📱 Termux-Style Virtual Accessory Bar**: Built-in awareness for mobile soft keyboards (Android/iOS) with tactile virtual accessory keys (`ESC`, `TAB`, `CTRL+C`, `↑`, `↓`, `←`, `→`, `|`, `/`, `-`, `~`, `CLR`).
- **🛡️ Safe Area & Responsive Toolbar**: Automatically respects OS status bars, camera cutouts, and bottom navigation bars across Desktop, Android, and Web sandboxes.

---

## 📚 Architecture & Research Documentation

Detailed architectural notes, design comparisons, and execution walkthroughs are preserved in the `docs/` directory:
- 📑 **[Implementation Plan](docs/implementation_plan.md)**: Technical architecture, DataChannel bridging, and PTY lifecycle management.
- 📑 **[xterm.dart vs Alacritty Comparison](docs/xterm_comparison_research.md)**: Why `xterm.dart` (`qt.TerminalView`) was chosen over native Alacritty/PTY wrappers for universal cross-platform rendering.
- 📑 **[Flet Extension Architecture Research](docs/flet_extensions_research.md)**: Deep dive into Flet `LayoutControl` lifecycle (`did_mount`, `invoke_method`, and event handlers).
- 📑 **[Modularization & Packaging Plan](docs/modularization_plan.md)**: Project directory structure, wheel builds, and multi-platform CI pipelines.
- 📑 **[Development Walkthrough](docs/walkthrough.md)**: Step-by-step summary of bug fixes, lifecycle race synchronization, and verification results.

---

## 📄 License
MIT License
