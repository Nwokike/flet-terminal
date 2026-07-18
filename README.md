# flet-terminal

Native GPU-accelerated Terminal control for Flet (`ft.LayoutControl`) powered by [`xterm.dart`](https://pub.dev/packages/xterm). Exposes a high-throughput, low-latency terminal canvas with zero-copy binary streaming via Flet `DataChannel`s.

---

## 🚀 Multi-Platform Demo Studio Downloads

Want to try the live terminal demo, high-speed ring buffer stress tests, and Termux virtual accessory keys before integrating?  
Download the pre-built multi-platform binaries right now:

| Variant | Download Link | Notes |
| :--- | :---: | :--- |
| 📱 **ARM64** (most phones) | [**fletterminalstudio-arm64-v8a.apk**](https://github.com/Nwokike/flet-terminal/releases/latest/download/fletterminalstudio-arm64-v8a.apk) | Modern 64-bit Android devices |
| 📱 **ARMv7** (older phones) | [**fletterminalstudio-armeabi-v7a.apk**](https://github.com/Nwokike/flet-terminal/releases/latest/download/fletterminalstudio-armeabi-v7a.apk) | Legacy 32-bit Android devices |
| 💻 **x86_64** (emulators) | [**fletterminalstudio-x86_64.apk**](https://github.com/Nwokike/flet-terminal/releases/latest/download/fletterminalstudio-x86_64.apk) | Chromebooks & Android emulators |
| 🖥️ **Windows portable** | [**FletTerminalStudio_0.1.0_windows_x64.zip**](https://github.com/Nwokike/flet-terminal/releases/latest/download/FletTerminalStudio_0.1.0_windows_x64.zip) | Standalone portable executable (`.exe`) |
| 🐧 **Linux standalone** | [**FletTerminalStudio_0.1.0_linux_x86_64.tar.gz**](https://github.com/Nwokike/flet-terminal/releases/latest/download/FletTerminalStudio_0.1.0_linux_x86_64.tar.gz) | Pre-compiled Linux binary bundle |
| 🌐 **Web PWA** | [**FletTerminalStudio_0.1.0_web_pwa.zip**](https://github.com/Nwokike/flet-terminal/releases/latest/download/FletTerminalStudio_0.1.0_web_pwa.zip) | Static Web Assembly / Progressive Web App |

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

## 📄 License
[MIT License](LICENSE)
