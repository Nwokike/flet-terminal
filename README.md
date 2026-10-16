# flet-terminal

[![pypi](https://img.shields.io/pypi/v/flet-terminal.svg)](https://pypi.python.org/pypi/flet-terminal)
[![python](https://img.shields.io/badge/python-%3E%3D3.10-%2334D058)](https://pypi.org/project/flet-terminal)
[![license](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/Nwokike/flet-terminal/blob/main/LICENSE)

Native GPU-accelerated terminal control for [Flet](https://flet.dev) apps.

A 1:1 wrapping of the [xterm.dart](https://pub.dev/packages/xterm) terminal engine, in the same architecture as [flet-ads](https://pypi.org/project/flet-ads/). One `uv add flet-terminal` covers Windows, Linux, macOS, Android and Web — no Python dependencies beyond `flet` (CI-verified on Flet 1.0.0 through the latest 1.0.x).

The control is view-only by design: it renders and streams bytes over a `DataChannel`; *your* app owns the child process (a local pty, an SSH/WebSocket session, anything). That separation is what makes the same package work in a desktop demo, in [CollabShell](https://github.com/Nwokike/CollabShell) (remote Colab pty), and in local-proot mobile apps.

## Test it without an account

Every release builds the demo app for every platform. Sideload or unpack any of them and every button is live:

| Variant | Download | Notes |
| :--- | :---: | :--- |
| 📱 **ARM64** (most phones/TVs) | [**app-arm64-v8a-release.apk**](https://github.com/Nwokike/flet-terminal/releases/latest/download/app-arm64-v8a-release.apk) | Modern 64-bit Android devices — grab this one unless you know otherwise |
| 📱 **ARMv7** (older phones) | [**app-armeabi-v7a-release.apk**](https://github.com/Nwokike/flet-terminal/releases/latest/download/app-armeabi-v7a-release.apk) | Legacy 32-bit Android devices |
| 💻 **x86_64** (emulators/ChromeOS) | [**app-x86_64-release.apk**](https://github.com/Nwokike/flet-terminal/releases/latest/download/app-x86_64-release.apk) | Android emulators & Chromebooks |
| 🪟 **Windows** | [**FletTerminal_windows_x64.zip**](https://github.com/Nwokike/flet-terminal/releases/latest/download/FletTerminal_windows_x64.zip) | Portable zip |
| 🐧 **Linux** | [**FletTerminal_linux_x86_64.tar.gz**](https://github.com/Nwokike/flet-terminal/releases/latest/download/FletTerminal_linux_x86_64.tar.gz) | Universal tarball |

Plain `flet run` launches the prebuilt client without the extension's Dart half — the terminal needs a built app (an artifact above, or `flet build <platform>`).

## Platform Support

| Platform | Windows | Linux | macOS | Android | iOS | Web |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Supported | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

The control itself is pure Dart rendering (xterm.dart), so it runs wherever Flet runs. The demo app's local-pty service uses POSIX `openpty` (Windows demo uses WinPTY transport); mobile hosts own their own process/session layer.

## Usage

```bash
uv add flet-terminal
```

The recommended entry point is the `MobileTerminal` composite — terminal + search bar + virtual extra-keys bar with sticky CTRL/ALT and zoom/settings:

```python
import flet as ft
from flet_terminal import MobileTerminal, BUILTIN_THEMES


@ft.component
def App():
    page = ft.context.page
    mt, _ = ft.use_state(lambda: MobileTerminal(
        show_extra_keys=True,
        show_search=False,
        scrollback=10000,
        font_family="JetBrains Mono",
        theme=BUILTIN_THEMES["JetBrains Dark"],
    ))

    # Your process layer: forward terminal bytes to a pty/SSH/kernel here.
    mt.set_on_bytes(lambda payload: mt.send_bytes(payload))

    return ft.Column(controls=[mt], spacing=0, expand=True)


def main(page: ft.Page):
    page.title = "My Terminal"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.render(App)


ft.run(main)
```

`MobileTerminal` constructs anywhere — inside a component tree, in a plain `main()`, or from a background task; no renderer context needed.

For just the viewport, use `Terminal` directly:

```python
import flet as ft
from flet_terminal import Terminal, BUILTIN_THEMES


def main(page: ft.Page):
    term = Terminal(scrollback=10000, theme=BUILTIN_THEMES["Dracula"], expand=True)

    def on_terminal_input(data: bytes):
        term.send_bytes(data)  # echo / forward to your process layer

    term.set_on_bytes(on_terminal_input)
    page.add(term)
    term.write("\x1b[1;32mWelcome to FletTerminal!\x1b[0m\r\n> ")


ft.run(main)
```

## Controls

### `Terminal` Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `scrollback` | `int \| None` | `10000` | Maximum number of scrollback lines retained in the ring buffer. |
| `font_family` | `str \| None` | `"JetBrains Mono"` | Monospace font family for rendering text. |
| `font_size` | `float \| None` | `11.0` | Font point size. |
| `cursor_blink` | `bool \| None` | `True` | Whether the terminal cursor blinks (real Dart-side timer). |
| `cursor_style` | `str \| None` | `"block"` | Cursor shape: `"block"`, `"underline"`, or `"bar"`. |
| `theme` | `dict \| None` | `None` | Dictionary mapping ANSI color keys to hex colors. |
| `read_only` | `bool \| None` | `False` | When `True`, disables user keyboard input (output still renders). |
| `auto_focus` | `bool \| None` | `True` | Automatically focuses the terminal when mounted. |
| `ctrl_active` / `alt_active` | `bool \| None` | `False` | Sticky modifier states, synced bidirectionally with Dart. |

### `Terminal` Methods

| Method | Arguments | Description |
| :--- | :--- | :--- |
| `send_bytes(payload)` | `bytes` | Sends binary data over the DataChannel to the terminal canvas (queued until the channel opens). |
| `send_input(payload)` | `bytes` | Local loopback to the registered `set_on_bytes` handler (virtual-key path). |
| `write(data)` | `str \| bytes` | Writes text or escape sequences to the terminal. |
| `clear()` | — | Clears the scrollback and visible screen buffer. |
| `focus()` | — | Requests keyboard focus. |
| `search(query, start, direction)` | `str, int, str` | Highlights/selects matches in the scrollback; total count arrives via `on_selection_change`. |
| `get_selection_async()` | — | Returns the current selection text (or `None` when not ready — request/response call, never queued). |
| `select_all()` / `clear_selection()` | — | Selection helpers. |
| `paste()` / `paste_async()` | — | Reads the clipboard on the Dart side and feeds it over the channel/data event. |

### Event handlers

| Event | Handler | Description |
| :--- | :--- | :--- |
| `on_data` | `Callable[[ft.ControlEvent], None]` | String-based terminal input (fallback path when no DataChannel handler matches). |
| `on_resize` | `Callable[[ft.ControlEvent], None]` | Dimensions changed. Event `data` is JSON `{"cols": int, "rows": int}` — forward it as `TIOCSWINSZ` to your pty. |
| `on_modifier_reset` | `Callable[[ft.ControlEvent], None]` | A sticky modifier was consumed by a hardware keystroke. |
| `on_title_change` | `Callable[[ft.ControlEvent], None]` | OSC 0/2 title sequence received. |
| `on_bell` | `Callable[[ft.ControlEvent], None]` | Bell character (`\a` / `0x07`) received. |
| `on_selection_change` | `Callable[[ft.ControlEvent], None]` | Selection updated, or search results reported (`{"query","found","count","index"}`). |
| `on_copy` | `Callable[[ft.ControlEvent], None]` | Text copied (secondary-tap or `copy_selection`). |
| `on_mount` | `Callable[[ft.ControlEvent], None]` | Dart view (re)created — replay your scrollback here. |
| `on_shortcut` | `Callable[[ShortcutEvent], None]` | Built-in host shortcut consumed pre-PTY; `e.shortcut` carries the machine name. Active only when a handler is set. |
| `on_data_channel_open` | internal | Wires the `pty` DataChannel; self-installed. |

#### Built-in shortcuts (`on_shortcut`)

| Combination | `e.shortcut` value |
| :--- | :--- |
| `Ctrl/Cmd+Shift+T` | `new_terminal` |
| `Ctrl/Cmd+Shift+W` | `close_terminal` |
| `Ctrl/Cmd+Shift+1 .. 9` | `switch_terminal_1` .. `switch_terminal_9` |
| `Ctrl/Cmd+Shift+F` | `toggle_search` |
| `Ctrl/Cmd+Shift+L` | `clear` |
| `Ctrl/Cmd+Shift+C` / `+V` | `copy` / `paste` |
| `Ctrl/Cmd+Shift+=` / `-` / `0` | `zoom_in` / `zoom_out` / `zoom_reset` |
| `Ctrl/Cmd+PageUp` / `PageDown` | `prev_terminal` / `next_terminal` |
| `F1` | `help` |

### `MobileTerminal` Additional Methods & Properties

| Member | Description |
| :--- | :--- |
| `set_theme(name)` | Switch to a built-in theme by name (unknown names are a no-op). |
| `set_cursor_style(style)` / `toggle_cursor_blink()` | Cursor appearance controls. |
| `zoom_in(step=1.0)` / `zoom_out(step=1.0)` / `reset_zoom()` | Font-size controls (floor 6.0 px). |
| `toggle_search()` / `show_search` | Built-in search bar visibility. |
| `copy_selection()` / `paste()` / `select_all()` / `clear_selection()` | Clipboard & selection helpers. |
| `send_bytes` / `send_input` / `write` / `clear` / `focus` / `search` / `set_on_bytes` | Forwarded from `Terminal`. |
| `ready` / `pending_count` / `clear_pending()` / `flush()` | DataChannel queue introspection (0 pending after reconnect? replay or drop). |
| `set_on_unmount(callback)` | Fired when the Dart view is torn down. |
| `font_size` / `cursor_blink` / `cursor_style` / `theme_name` | Read-only state mirrors (`theme_name` is `None` for custom palettes). |
| `ctrl_active` / `alt_active` | Sticky modifier state (settable; buttons repaint automatically). |

### `ExtraKeysBar` Constructor

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `on_send_payload` | `Callable[[bytes], None]` | required | Called with the final byte payload after modifier processing. |
| `on_modifier_change` | `Callable[[bool, bool], None]` | required | Called with `(ctrl, alt)` when sticky state changes. |
| `show_settings` | `bool` | `True` | Show the gear-icon settings popup. |
| `on_set_theme` / `on_set_cursor` / `on_toggle_blink` / `on_toggle_search` | callbacks | `None` | Settings-menu callbacks. |
| `on_copy` / `on_paste` / `on_select_all` / `on_clear` | callbacks | `None` | Clipboard/buffer callbacks. |
| `keys` | `list[tuple[str, bytes \| None]]` | `DEFAULT_EXTRA_KEYS` | Custom key layout. A `None` payload marks a sticky modifier (CTRL/ALT). |

The default layout: `ESC`, `TAB`, `CTRL`, `ALT`, `↑ ↓ ← →`, `- / | ~ ^`. Sticky CTRL transforms `a`→`\x01` (case-folded via `code−96`/`code−64`); sticky ALT prefixes `ESC` — the mirror of the Dart-side hardware-key transform.

## Configuration

`Ctrl/Alt` stickiness, themes, zoom, cursor and the search bar are all reachable from the gear menu (`show_settings=True`) and mirrored in the corresponding Python API above — pick whichever layer your app prefers.

## Limitations

- **View-only by design.** No spawn/pty API: the package renders bytes and reports events; your app owns the process (local `pty.openpty`, remote WebSocket, kernel client…). The channel is named `pty` for transport reasons only.
- **Built-in themes are plain ANSI dictionaries.** Dart accepts extra keys (`brightBlack`…`brightWhite`, `searchHit*`) that fall back to the default theme; the four `BUILTIN_THEMES` ship exactly twelve keys each.
- **`get_selection_async` never queues** (request/response): it returns `None` while the Dart view is not ready — retry after `on_mount`.
- **Search is linear over the scrollback** (xterm has no index); the match counter reflects the Dart-side count.

## Example

The standalone demo (all artifacts above) lives at [`examples/flet_terminal_example`](examples/flet_terminal_example) — a full `MobileTerminal` + local-pty app, cross-platform.

## Frozen-Control Support

Flet 1.0's declarative renderer stamps `_frozen = True` on component-rendered controls. Imperative mutations then raise `RuntimeError: Frozen controls cannot be updated.` `flet_terminal` handles this internally via `thaw()`; all `MobileTerminal`/`ExtraKeysBar`/`TerminalSearchBar` mutations already use it — no extra wrapping needed by consumers. If you build your own long-lived controls in a declarative tree, the pattern is:

```python
from flet_terminal.frozen_support import thaw

with thaw(some_control):
    some_control.style = new_style
    some_control.update()
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
