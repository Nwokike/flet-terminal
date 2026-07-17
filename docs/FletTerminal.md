# API Reference: `Terminal`

`Terminal` inherits from `ft.LayoutControl` and embeds the native `xterm.dart` canvas.

## Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `scrollback` | `int` | `10000` | Maximum number of lines retained in the scrollback ring buffer. |
| `font_family` | `str` | `"JetBrains Mono"` | Font family name used to render terminal characters. |
| `font_size` | `float` | `13.0` | Font size in points. |
| `cursor_style` | `str` | `"block"` | Cursor shape: `"block"`, `"underline"`, or `"bar"` (`"verticalBar"`). |
| `cursor_blink` | `bool` | `True` | Whether the cursor blinks continuously. |
| `theme` | `dict` | `None` | Dictionary specifying colors (matching `xterm.js` `ITheme` properties like `background`, `foreground`, `cursor`, `selection`, plus ANSI 0-15 palettes). |
| `read_only` | `bool` | `False` | When true, prevents user keyboard input. |
| `auto_focus` | `bool` | `True` | Automatically focuses the terminal canvas upon mounting. |
| `ctrl_active` | `bool` | `False` | Sticky `CTRL` key state for soft keyboards. |
| `alt_active` | `bool` | `False` | Sticky `ALT` (`ESC`) key state for soft keyboards. |

## Event Handlers

| Handler | Event Type | Description |
| :--- | :--- | :--- |
| `on_data` | `ControlEvent` | Fired when text/characters are typed (fallback when DataChannel is unused). |
| `on_resize` | `ControlEvent` | Fired when terminal grid dimensions change (`{"cols": width, "rows": height}`). |
| `on_modifier_reset`| `ControlEvent` | Fired when Dart automatically toggles sticky modifier states off after key press. |
| `on_title_change` | `ControlEvent` | Fired when an application sets the window title via `OSC 0/2` escape sequence. |
| `on_bell` | `ControlEvent` | Fired when the terminal receives an audio/visual bell (`\a`). |
| `on_selection_change` | `ControlEvent` | Fired when active text selection changes or a search query match is highlighted. |

## Methods

### `send_bytes(payload: bytes)`
Sends raw bytes directly over the high-throughput `DataChannel` to the Dart canvas.

### `set_on_bytes(handler: Callable[[bytes], None])`
Registers the callback invoked whenever raw bytes arrive from the Dart canvas (`DataChannel`).

### `write(data: str | bytes)` / `await write_async(data: str | bytes)`
Writes string or binary data to the terminal via Flet method invocation.

### `clear()` / `await clear_async()`
Clears the entire scrollback buffer and active canvas view.

### `focus()` / `await focus_async()`
Requests keyboard focus on the terminal control.

### `search(query: str)` / `await search_async(query: str)`
Searches for `query` inside the terminal scrollback ring buffer and highlights matches.

### `clear_selection()` / `await clear_selection_async()`
Clears any active highlighted text selection in the terminal.

### `select_all()` / `await select_all_async()`
Selects all text currently inside the visible grid and scrollback buffer.
