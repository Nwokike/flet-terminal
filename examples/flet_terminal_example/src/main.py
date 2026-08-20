"""Root Flet Terminal Application — declarative Flet 0.86 entry point.

The app is a single `@ft.component` tree rendered via `page.render(App)`;
all UI state lives in the `DemoState` observable in `app.py`.
"""

from __future__ import annotations

import os
import sys

_cur_dir = os.path.dirname(os.path.abspath(__file__))
if _cur_dir not in sys.path:
    sys.path.insert(0, _cur_dir)

import flet as ft
from app import App


def main(page: ft.Page):
    page.title = "Flet Terminal"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = "#12121A"
    page.render(App)


ft.run(main)
