# Welcome to FletTerminal

`flet-terminal` is a native GPU-accelerated terminal control for Flet, powered by Flutter's [`xterm.dart`](https://github.com/PangolinDesktop/xterm.dart).

It provides complete **`xterm.js` feature parity**, high-throughput zero-copy binary streaming via Flet `DataChannel`, and full cross-platform compatibility across **Windows, Linux, macOS, Android, and Web**.

## Key Features
- 🚀 **60fps GPU Hardware Acceleration** via Skia/Impeller graphics engine.
- 🌊 **Dedicated DataChannels** for ultra-fast, zero-copy binary streams (`send_bytes` / `on_bytes`).
- 🎨 **Full `ITheme` & Styling Parity**: Customizable foreground, background, 16 ANSI colors, cursor styles (`block`, `underline`, `bar`), and blinking.
- 📱 **Touch & Soft-Keyboard Friendly**: Built-in sticky modifier interceptors (`CTRL`, `ALT`) for mobile devices.
- 🔍 **Search & Selection**: Programmatic scrollback search (`terminal.search(query)`), clipboard selection, and ring-buffer retention up to 10,000+ lines.
- 🌐 **Backend Agnostic**: Works cleanly with local OS PTYs (`pty.openpty()` / `ConPTY`), SSH streams, or interactive Web/Mobile demos.

## Quick Start

```python
import flet as ft
from flet_terminal import Terminal

def main(page: ft.Page):
    terminal = Terminal(
        expand=True,
        scrollback=10000,
        font_family="JetBrains Mono",
        font_size=13.0,
        cursor_style="block",
        cursor_blink=True,
    )

    def handle_bytes(data: bytes):
        # Echo characters or forward to shell/backend
        terminal.send_bytes(data)

    terminal.set_on_bytes(handle_bytes)
    page.add(terminal)

ft.app(target=main)
```
