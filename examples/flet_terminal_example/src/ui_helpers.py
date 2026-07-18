"""UI Helpers — constructs appbar, engine selector, demo actions, and top-level navigation."""

from __future__ import annotations
from typing import Any, Callable
import flet as ft

__all__ = ["build_demo_appbar"]


def build_demo_appbar(
    page: ft.Page,
    mt: Any,
    available_engines: list[str],
    active_engine: str,
    on_switch_engine: Callable[[str], None],
    on_run_matrix: Callable[[], None],
    on_run_stress: Callable[[], None],
    on_run_alt_screen: Callable[[], None],
) -> ft.AppBar:
    """Build the responsive header bar with engine dropdown, demos, and zoom controls."""

    # Engine dropdown or badge
    if len(available_engines) > 1:
        engine_ctl = ft.Dropdown(
            value=active_engine,
            options=[ft.DropdownOption(k) for k in available_engines],
            width=170,
            text_size=11,
            height=32,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=0),
            on_select=lambda e: on_switch_engine(e.control.value),
        )
    else:
        engine_ctl = ft.Container(
            content=ft.Text(
                "VT100 Demo", size=11, weight=ft.FontWeight.BOLD, color="#A6E3A1"
            ),
            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            bgcolor="#313244",
            border_radius=4,
        )

    # Demos popup
    demos_popup = ft.PopupMenuButton(
        icon=ft.Icons.VIEW_LIST,
        icon_size=20,
        tooltip="Demos",
        style=ft.ButtonStyle(padding=4, visual_density=ft.VisualDensity.COMPACT),
        items=[
            ft.PopupMenuItem(
                content=ft.Text("ANSI Color & Style Matrix"),
                on_click=lambda e: on_run_matrix(),
            ),
            ft.PopupMenuItem(
                content=ft.Text("10,000 Line Stress Test"),
                on_click=lambda e: on_run_stress(),
            ),
            ft.PopupMenuItem(
                content=ft.Text("Alternate Screen Simulation"),
                on_click=lambda e: on_run_alt_screen(),
            ),
        ],
    )

    # Zoom controls
    zoom_in_btn = ft.IconButton(
        icon=ft.Icons.ZOOM_IN,
        icon_size=18,
        tooltip="Zoom In",
        style=ft.ButtonStyle(padding=2, visual_density=ft.VisualDensity.COMPACT),
        on_click=lambda e: _change_font_size(page, mt, 1.0),
    )
    zoom_out_btn = ft.IconButton(
        icon=ft.Icons.ZOOM_OUT,
        icon_size=18,
        tooltip="Zoom Out",
        style=ft.ButtonStyle(padding=2, visual_density=ft.VisualDensity.COMPACT),
        on_click=lambda e: _change_font_size(page, mt, -1.0),
    )

    return ft.AppBar(
        leading=engine_ctl,
        leading_width=180,
        toolbar_height=48,
        adaptive=True,
        bgcolor="#181825",
        actions=[demos_popup, zoom_out_btn, zoom_in_btn],
        actions_padding=ft.Padding.only(right=8),
    )


def _change_font_size(page: ft.Page, mt: Any, delta: float):
    new_size = max(8.0, min(36.0, (mt._terminal.font_size or 13.0) + delta))
    mt._terminal.font_size = new_size
    mt._terminal.update()

    page.overlay = [c for c in page.overlay if not isinstance(c, ft.SnackBar)]
    sb = ft.SnackBar(
        content=ft.Text(f"Font Size: {int(new_size)}px"),
        bgcolor="#313244",
        duration=1000,
        open=True,
    )
    page.overlay.append(sb)
    page.update()
