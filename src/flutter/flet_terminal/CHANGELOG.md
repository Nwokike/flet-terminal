# 0.2.1

- `Terminal.write()` and `write_async()` automatically route over the binary `DataChannel` (`pty`) fast-path whenever available, providing zero-latency output streaming for all applications.
- Built-in Zoom control: `MobileTerminal` now includes `zoom_in()`, `zoom_out()`, and `reset_zoom()` methods. The `ExtraKeysBar` settings menu features a one-line interactive font size row (`Font Size: 13px [ - ] [ + ] [ ↺ ]`) plus individual zoom menu items.
- Dynamic Checkmarks (`checked=True`): All options in the `ExtraKeysBar` settings menu (`Theme Presets`, `Cursor Style`, `Cursor Blink`, `Search Bar`) now display visual checkmarks indicating exactly what is currently selected, and dynamically check/uncheck whenever options are changed.

# 0.2.0

- `MobileTerminal` — new bundled wrapper with collapsible extra-keys bar, search, and settings popup (theme/cursor/blink) built-in.
- All `Terminal` properties and methods forwarded through `MobileTerminal` for drop-in compatibility.
- UI redesign: compact AppBar toolbar, SubmenuButton settings/demos, responsive layout.
- Search: now visibly selects the match and reports count via `on_selection_change`.
- Readiness signal simplified (`did_mount` + `data_channel_open` + `before_event`).
- `send_bytes` fallback buffers binary data instead of corrupting through string protocol.
- `search()` accepts optional `start` parameter for stepping through matches.

# 0.1.0

- Initial release of `flet-terminal` native GPU-accelerated terminal control.
- Full `xterm.js` feature parity: search, clipboard selection, title changes (`OSC 0/2`), audio/visual bell (`\a`).
- High-throughput binary `DataChannel` streaming (`send_bytes` / `on_bytes`).
- Sticky soft-keyboard modifiers (`CTRL`, `ALT`).
