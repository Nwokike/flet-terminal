> **APK size:** this example builds a small APK because it sets `[tool.flet.android].legacy_packaging = true` (native libs deflate). If your own app's APK is ~2x large for its deps, add that flag.

# FletTerminal Cross-Platform Demo & Example

This folder contains the official multi-engine test harness and example app for [`flet-terminal`](https://github.com/Nwokike/flet-terminal).

## Building Across Platforms (`flet build`)

From inside this folder (`examples/flet_terminal_example`), run `flet build` for any target platform:

```bash
# Web
flet build web -v

# Linux Desktop Bundle & Portable tar.gz
flet build linux -v

# Windows Desktop .exe
flet build windows -v

# Android APK (split per ABI or universal)
flet build apk --split-per-abi -v
```

## Running Locally

```bash
uv run flet run
```
