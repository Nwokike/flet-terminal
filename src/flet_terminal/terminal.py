from typing import Any, Optional
import flet as ft
from flet.controls.base_control import control
from flet.data_channel import DataChannelOpenEvent, DataChannel

__all__ = ["Terminal"]


@control("FletTerminal")
class Terminal(ft.LayoutControl):
    """
    Native GPU-accelerated Terminal control for Flet using xterm.dart.
    Provides full xterm.js feature parity across Windows, Linux, macOS, Android, and Web.
    """

    scrollback: Optional[int] = 10000
    font_family: Optional[str] = "JetBrains Mono"
    font_size: Optional[float] = 13.0
    cursor_blink: Optional[bool] = True
    cursor_style: Optional[str] = "block"  # "block", "underline", "bar"
    theme: Optional[dict[str, Any]] = None
    read_only: Optional[bool] = False
    auto_focus: Optional[bool] = True

    # Sticky modifier key states (synced bidirectionally with Dart)
    ctrl_active: Optional[bool] = False
    alt_active: Optional[bool] = False

    # Standard Flet event handlers
    on_data: Optional[ft.ControlEventHandler] = None
    on_resize: Optional[ft.ControlEventHandler] = None
    on_modifier_reset: Optional[ft.ControlEventHandler] = None
    on_title_change: Optional[ft.ControlEventHandler] = None
    on_bell: Optional[ft.ControlEventHandler] = None
    on_selection_change: Optional[ft.ControlEventHandler] = None

    # Internal channel setup handler
    on_data_channel_open: Optional[ft.EventHandler[DataChannelOpenEvent]] = None

    def init(self):
        self._channel: Optional[DataChannel] = None
        self._on_bytes_handler = None
        if self.on_data_channel_open is None:
            self.on_data_channel_open = self._handle_data_channel_open
        self._on_unmount_callback = None

    def _handle_data_channel_open(self, e: DataChannelOpenEvent):
        if e.channel_name == "pty" or not self._channel:
            self._channel = self.get_data_channel(e.channel_id)
            if self._on_bytes_handler:
                self._channel.on_bytes(self._on_bytes_handler)

    def set_on_bytes(self, handler):
        """Registers a callback for raw bytes pushed from Dart to Python."""
        self._on_bytes_handler = handler
        if self._channel:
            self._channel.on_bytes(handler)

    def send_bytes(self, payload: bytes):
        """Sends raw bytes from Python to Dart (writing to terminal canvas)."""
        if self._channel:
            self._channel.send(payload)
        else:
            self.write(payload)

    def will_unmount(self):
        """Disposes resources and sockets when the terminal control is removed from tree."""
        super().will_unmount()
        if self._on_unmount_callback:
            try:
                self._on_unmount_callback()
            except Exception:
                pass

    async def write_async(self, data: str | bytes):
        """Writes text or escape sequences to the terminal via Flet method invocation."""
        payload = data if isinstance(data, str) else data.decode("utf-8", errors="ignore")
        await self._invoke_method("write", {"data": payload})

    def write(self, data: str | bytes):
        """Synchronous wrapper for write_async."""
        self.page.run_task(self.write_async, data)

    async def clear_async(self):
        """Clears the terminal scrollback and buffer."""
        await self._invoke_method("clear")

    def clear(self):
        """Synchronous wrapper for clear_async."""
        self.page.run_task(self.clear_async)

    async def focus_async(self):
        """Requests keyboard focus on the terminal."""
        await self._invoke_method("focus")

    def focus(self):
        """Synchronous wrapper for focus_async."""
        self.page.run_task(self.focus_async)

    async def search_async(self, query: str):
        """Searches for text within the terminal scrollback ring buffer."""
        await self._invoke_method("search", {"query": query})

    def search(self, query: str):
        """Synchronous wrapper for search_async."""
        self.page.run_task(self.search_async, query)

    async def clear_selection_async(self):
        """Clears any active text selection in the terminal."""
        await self._invoke_method("clear_selection")

    def clear_selection(self):
        """Synchronous wrapper for clear_selection_async."""
        self.page.run_task(self.clear_selection_async)

    async def select_all_async(self):
        """Selects all text currently in the terminal buffer and scrollback."""
        await self._invoke_method("select_all")

    def select_all(self):
        """Synchronous wrapper for select_all_async."""
        self.page.run_task(self.select_all_async)
