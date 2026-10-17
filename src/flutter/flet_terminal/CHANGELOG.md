# 0.4.2

- **Soft-keyboard fix (owner-tested gaps):** the resize event payload now carries `bottom_inset` (the keyboard's height), so an app can reserve that space and keep the virtual extra-keys bar ABOVE the keyboard instead of behind it. Payload is backward compatible (`cols`/`rows` unchanged; `bottom_inset` is a new key).
- **Demo app aligned with the CollabShell integration** (the owner's reference implementation): it now wires `on_data` in addition to `set_on_bytes` — soft-keyboard characters on Android arrive on the string "data" event, not only the binary DataChannel, which is why letters didn't come through while delete did. `auto_focus=False` (desktop clicks focus; mobile no longer force-pops the keyboard).

# 0.4.1

- **Restored: reactive CTRL/ALT painting.** 0.4.0 replaced the `@ft.component`/`@ft.observable` modifier buttons with imperative `refresh_buttons()` repaints — a regression: the toggles stopped repainting in real component trees. The reactive `ModifierKey` mechanism is back, identical to 0.3.9; `ExtraKeysBar.refresh_buttons()` stays as a compatibility no-op because the `ModifierState` observable drives every repaint (taps, payload consumption, resets, setter assignments).
- **Construct-anywhere kept**: creating `MobileTerminal`/`ExtraKeysBar` outside a renderer context still never raises — in that case the modifier components are created inside a throwaway `Renderer().with_context()` (the README-documented pattern) and subscribe normally once the tree renders.
- `Terminal._mark_dart_ready()` keeps the detached-control tolerance (flush stays safe headless).
- Demo app: platform-aware default shell (`$SHELL` → `/system/bin/sh` on Android → `/bin/bash` → `/bin/sh`), `TERM` seeded for the child, and `pywinpty` added for the Windows engine — the demo is now usable on Android, Windows and Linux.

# 0.4.0

- **`MobileTerminal` now constructs anywhere.** The CTRL/ALT toggles no longer instantiate an `@ft.component` child eagerly, so construction outside an active renderer context (plain `main()`, background tasks, imperative code) no longer raises `RuntimeError: No current renderer is set`. The modifier "lights" repaint imperatively via the new `ExtraKeysBar.refresh_buttons()` — which also fixes the latent `AttributeError` raised by the `MobileTerminal.ctrl_active`/`alt_active` setters in 0.3.9.
- **Flush is genuinely safe anywhere**: `Terminal._mark_dart_ready()` tolerates detached controls (no page) instead of raising — `MobileTerminal.flush()` works headless.
- **House-extension standard**: MIT license metadata (`license`/`license-files`), `requires-python >=3.10`, bare `flet` dependency (the compat matrix is the contract — Flet 1.0.0+), narrow Dart package-data (`pubspec.yaml` + `lib/**` only), `__version__` export, `.fvmrc`, `.github/scripts/sync_versions.py`.
- **Contract test suite** (85 tests): exports, prop defaults, queue semantics, event typing, extra-key byte table, modifier transforms, MobileTerminal regressions, theme pins, search stepping, frozen-support contract.
- **CI**: `compat.yml` (Flet 1.0.0/1.0.1/1.0.4/latest × Python 3.10/3.14 + Dart analyze/test on Flutter 3.44.8), quality gate in `build-all.yml`, version-sync step in `publish.yml`, and an unsigned split-per-ABI demo APK published with every release.

# 0.3.9

- Targets **Flet 1.0.1**: Python floor `flet>=1.0.1`, Dart pubspec `flet: ^1.0.0`.
- Fixed pending-write flush — Flet 1.0's `run_task` rejects sync callables, so queued `send_bytes` writes were re-queued forever.
- One shared `Clipboard` service instead of registering a new instance on every copy.
- New `MobileTerminal` API: `on_mount` property, `ready`, `pending_count`, `clear_pending()`, `flush()`, `set_on_unmount()` — consumers no longer need `_terminal` internals.
- Search bar `border_color` → `border=OutlineInputBorder` and example SnackBar `duration` → `ft.Duration` (both deprecated/changed in Flet 1.0).

# 0.3.8

- **Host keyboard shortcuts, leak-free.** `Terminal`/`MobileTerminal` gain an `on_shortcut` event. Built-in combos are consumed on the Dart side via xterm's `onKeyEvent` hook — the highest-priority stage of xterm's key pipeline — so they never reach the PTY. Enabled only when `on_shortcut` is set; without a handler all keys flow to the terminal untouched.
- Combo set: `Ctrl/Cmd+Shift+T` (new_terminal), `+W` (close_terminal), `+1..9` (switch_terminal_N), `+F` (toggle_search), `+L` (clear), `+C` (copy), `+V` (paste), `+=` (zoom_in), `+-` (zoom_out), `+0` (zoom_reset), `Ctrl/Cmd+PageUp/PageDown` (prev/next_terminal), `F1` (help).
- New `ShortcutEvent` payload (`.shortcut` carries the machine name) exported from the package root.

# 0.2.2

- Updated default font size from 13px to 11px.
- Re-ordered virtual extra keys so arrow keys (`↑`, `↓`, `←`, `→`) come immediately after `ALT`.
- Hidden search bar by default (`show_search=False`), toggleable via settings menu.
- Intuitive collapse toggle button arrow states (`ARROW_DROP_UP` when open, `ARROW_DROP_DOWN` when collapsed).

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
