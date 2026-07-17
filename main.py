"""Root entrypoint for FletTerminal Cross-Platform Studio.

Forwards directly to `examples/flet_terminal_example/src/main.py` for easy testing with `flet run` or `flet build`.
"""

import flet as ft
from examples.flet_terminal_example.src.main import main

if __name__ == "__main__":
    ft.run(main)
