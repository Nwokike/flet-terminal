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
    on_mount: Optional[ft.ControlEventHandler] = None

    # Internal channel setup handler
    on_data_channel_open: Optional[ft.EventHandler[DataChannelOpenEvent]] = None

    def init(self):
        self._channel: Optional[DataChannel] = None
        self._on_bytes_handler = None
        if self.on_data_channel_open is None:
            self.on_data_channel_open = self._handle_data_channel_open
        self._on_unmount_callback = None
        self._pending_writes: list[Any] = []
        self._dart_ready: bool = False
        self._channel_ready: bool = False

    def before_event(self, e: ft.ControlEvent):
        self._mark_dart_ready()
        return super().before_event(e)

    def _mark_dart_ready(self):
        if not self._dart_ready:
            self._dart_ready = True
        remaining = []
        while self._pending_writes and self.page and self._dart_ready:
            task_fn, args = self._pending_writes.pop(0)
            if task_fn == self.send_bytes and not self._channel_ready:
                remaining.append((task_fn, args))
                continue
            if args is not None:
                self.page.run_task(task_fn, *args)
            else:
                self.page.run_task(task_fn)
        if remaining:
            self._pending_writes.extend(remaining)

    def did_mount(self):
        super().did_mount()
        self._mark_dart_ready()

    def _handle_data_channel_open(self, e: DataChannelOpenEvent):
        if e.channel_name == "pty" or not self._channel:
            self._channel = self.get_data_channel(e.channel_id)
            if self._on_bytes_handler:
                self._channel.on_bytes(self._on_bytes_handler)
            self._channel_ready = True
        self._mark_dart_ready()

    def set_on_bytes(self, handler):
        """Registers a callback for raw bytes pushed from Dart to Python."""
        self._on_bytes_handler = handler
        if self._channel:
            self._channel.on_bytes(handler)

    def send_bytes(self, payload: bytes):
        """Sends raw bytes from Python to Dart (writing to terminal canvas)."""
        if self._channel is not None and self._channel_ready and self._dart_ready:
            self._channel.send(payload)
        else:
            self._pending_writes.append((self.send_bytes, (payload,)))

    def will_unmount(self):
        """Disposes resources and sockets when the terminal control is removed from tree."""
        super().will_unmount()
        self._dart_ready = False
        self._pending_writes.clear()
        if self._on_unmount_callback:
            try:
                self._on_unmount_callback()
            except Exception:
                pass

    async def write_async(self, data: str | bytes):
        """Writes text or escape sequences to the terminal via Flet method invocation."""
        try:
            if not self.page or not self._dart_ready:
                self._pending_writes.append((self.write_async, (data,)))
                return
        except RuntimeError:
            self._pending_writes.append((self.write_async, (data,)))
            return
        payload = (
            data if isinstance(data, str) else data.decode("utf-8", errors="ignore")
        )
        try:
            await self._invoke_method("write", {"data": payload})
        except RuntimeError:
            self._pending_writes.append((self.write_async, (data,)))

    def write(self, data: str | bytes):
        """Synchronous wrapper for write_async."""
        try:
            if not self.page or not self._dart_ready:
                self._pending_writes.append((self.write_async, (data,)))
                return
            self.page.run_task(self.write_async, data)
        except RuntimeError:
            self._pending_writes.append((self.write_async, (data,)))

    async def clear_async(self):
        """Clears the terminal scrollback and buffer."""
        try:
            if not self.page or not self._dart_ready:
                self._pending_writes.append((self.clear_async, None))
                return
        except RuntimeError:
            self._pending_writes.append((self.clear_async, None))
            return
        try:
            await self._invoke_method("clear")
        except RuntimeError:
            self._pending_writes.append((self.clear_async, None))

    def clear(self):
        """Synchronous wrapper for clear_async."""
        try:
            if not self.page or not self._dart_ready:
                self._pending_writes.append((self.clear_async, None))
                return
            self.page.run_task(self.clear_async)
        except RuntimeError:
            self._pending_writes.append((self.clear_async, None))

    async def focus_async(self):
        """Requests keyboard focus on the terminal."""
        try:
            if not self.page or not self._dart_ready:
                self._pending_writes.append((self.focus_async, None))
                return
        except RuntimeError:
            self._pending_writes.append((self.focus_async, None))
            return
        try:
            await self._invoke_method("focus")
        except RuntimeError:
            self._pending_writes.append((self.focus_async, None))

    def focus(self):
        """Synchronous wrapper for focus_async."""
        try:
            if not self.page or not self._dart_ready:
                self._pending_writes.append((self.focus_async, None))
                return
            self.page.run_task(self.focus_async)
        except RuntimeError:
            self._pending_writes.append((self.focus_async, None))

    async def search_async(self, query: str, start: int = 0):
        """Searches for text within the terminal scrollback ring buffer.

        `start` is the character offset to resume scanning from (used to step
        through successive matches). The Dart side selects the match and
        reports the total count via the `on_selection_change` event.
        """
        try:
            if not self.page or not self._dart_ready:
                self._pending_writes.append((self.search_async, (query, start)))
                return
        except RuntimeError:
            self._pending_writes.append((self.search_async, (query, start)))
            return
        try:
            await self._invoke_method("search", {"query": query, "start": start})
        except RuntimeError:
            self._pending_writes.append((self.search_async, (query, start)))

    def search(self, query: str, start: int = 0):
        """Synchronous wrapper for search_async."""
        try:
            if not self.page or not self._dart_ready:
                self._pending_writes.append((self.search_async, (query, start)))
                return
            self.page.run_task(self.search_async, query, start)
        except RuntimeError:
            self._pending_writes.append((self.search_async, (query, start)))

    async def clear_selection_async(self):
        """Clears any active text selection in the terminal."""
        try:
            if not self.page or not self._dart_ready:
                self._pending_writes.append((self.clear_selection_async, None))
                return
        except RuntimeError:
            self._pending_writes.append((self.clear_selection_async, None))
            return
        try:
            await self._invoke_method("clear_selection")
        except RuntimeError:
            self._pending_writes.append((self.clear_selection_async, None))

    def clear_selection(self):
        """Synchronous wrapper for clear_selection_async."""
        try:
            if not self.page or not self._dart_ready:
                self._pending_writes.append((self.clear_selection_async, None))
                return
            self.page.run_task(self.clear_selection_async)
        except RuntimeError:
            self._pending_writes.append((self.clear_selection_async, None))

    async def select_all_async(self):
        """Selects all text currently in the terminal buffer and scrollback."""
        try:
            if not self.page or not self._dart_ready:
                self._pending_writes.append((self.select_all_async, None))
                return
        except RuntimeError:
            self._pending_writes.append((self.select_all_async, None))
            return
        try:
            await self._invoke_method("select_all")
        except RuntimeError:
            self._pending_writes.append((self.select_all_async, None))

    def select_all(self):
        """Synchronous wrapper for select_all_async."""
        try:
            if not self.page or not self._dart_ready:
                self._pending_writes.append((self.select_all_async, None))
                return
            self.page.run_task(self.select_all_async)
        except RuntimeError:
            self._pending_writes.append((self.select_all_async, None))
