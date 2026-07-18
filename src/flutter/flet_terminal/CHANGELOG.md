# 0.2.0

- UI redesign: compact AppBar toolbar, SubmenuButton settings/demos, responsive layout.
- Search: now visibly selects the match and reports count via `on_selection_change`.
- Readiness signal simplified (`did_mount` + `data_channel_open` + `before_event`).
- `send_bytes` fallback buffers binary data instead of corrupting through string protocol.
- `search()` accepts optional `start` parameter for stepping through matches.
- Android: basic subprocess shell engine (`ls`, `cd`, `cat`, `echo`, `grep`).
- Web: GitHub Pages deployment (live demo).
- Docs consolidated into single comprehensive README.

# 0.1.0

- Initial release of `flet-terminal` native GPU-accelerated terminal control.
- Full `xterm.js` feature parity: search, clipboard selection, title changes (`OSC 0/2`), audio/visual bell (`\a`).
- High-throughput binary `DataChannel` streaming (`send_bytes` / `on_bytes`).
- Sticky soft-keyboard modifiers (`CTRL`, `ALT`).
