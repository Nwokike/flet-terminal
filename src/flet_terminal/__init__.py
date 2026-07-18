"""FletTerminal — GPU-accelerated Terminal control for Flet across Web, Desktop, and Mobile."""

from flet_terminal.terminal import Terminal
from flet_terminal.mobile_terminal import MobileTerminal
from flet_terminal.themes import BUILTIN_THEMES, get_theme
from flet_terminal.extra_keys import ExtraKeysBar, DEFAULT_EXTRA_KEYS
from flet_terminal.search_bar import TerminalSearchBar

__all__ = [
    "Terminal",
    "MobileTerminal",
    "BUILTIN_THEMES",
    "get_theme",
    "ExtraKeysBar",
    "DEFAULT_EXTRA_KEYS",
    "TerminalSearchBar",
]
