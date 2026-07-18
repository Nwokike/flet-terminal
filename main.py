"""Root entrypoint for FletTerminal Cross-Platform Demo.

Forwards directly to `examples/flet_terminal_example/src/main.py` for easy testing with `flet run` or `flet build`.
"""
# ruff: noqa: E402

import sys
from pathlib import Path

_demo_dir = str(Path(__file__).parent / "examples" / "flet_terminal_example" / "src")
if _demo_dir not in sys.path:
    sys.path.insert(0, _demo_dir)

import flet as ft
from examples.flet_terminal_example.src.main import main

if __name__ == "__main__":
    ft.run(main)
