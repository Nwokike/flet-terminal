"""UI Helpers — constructs appbar, engine selector, demo actions, and top-level navigation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import flet as ft

__all__ = ["build_demo_appbar"]


def build_demo_appbar(
    mt: Any,
    available_engines: list[str],
    active_engine: str,
    on_switch_engine: Callable[[str], None],
    on_run_matrix: Callable[[], None],
    on_run_stress: Callable[[], None],
    on_run_alt_screen: Callable[[], None],
    on_toggle_search: Callable[[], None] | None = None,
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
        badge_text = (
            active_engine
            if active_engine
            else (available_engines[0] if available_engines else "Local Shell")
        )
        engine_ctl = ft.Container(
            content=ft.Text(
                badge_text, size=11, weight=ft.FontWeight.BOLD, color="#A6E3A1"
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
        on_click=lambda e: mt.zoom_in(),
    )
    zoom_out_btn = ft.IconButton(
        icon=ft.Icons.ZOOM_OUT,
        icon_size=18,
        tooltip="Zoom Out",
        style=ft.ButtonStyle(padding=2, visual_density=ft.VisualDensity.COMPACT),
        on_click=lambda e: mt.zoom_out(),
    )
    toggle_search_btn = ft.IconButton(
        icon=ft.Icons.SEARCH,
        icon_size=18,
        tooltip="Toggle Search Bar",
        style=ft.ButtonStyle(padding=2, visual_density=ft.VisualDensity.COMPACT),
        on_click=lambda e: (
            on_toggle_search() if on_toggle_search else mt.toggle_search()
        ),
    )

    return ft.AppBar(
        leading=engine_ctl,
        leading_width=180,
        toolbar_height=48,
        adaptive=True,
        bgcolor="#181825",
        actions=[demos_popup, toggle_search_btn, zoom_out_btn, zoom_in_btn],
        actions_padding=ft.Padding.only(right=8),
    )
