"""ANSI Demo Engine — simulated terminal session for web/demo environments."""

from __future__ import annotations
import threading
import time
from typing import Callable

__all__ = ["DemoEngine"]


class DemoEngine:
    """Provides a realistic interactive terminal experience without a real OS shell."""

    def __init__(self, write_fn: Callable[[bytes], None], clear_fn: Callable[[], None]):
        self._write = write_fn
        self._clear = clear_fn
        self._input_buf = ""
        self._prompt = b"\r\n\x1b[32m[Demo Shell]>\x1b[0m "
        self._running_test = False

    def start(self):
        self._write(b"\x1b[2J\x1b[H")
        self._write(
            b"\x1b[1;36m=================================================================\x1b[0m\r\n"
        )
        self._write(
            b"\x1b[1;36m * FletTerminal Cross-Platform Demo Shell (ANSI Engine)\x1b[0m\r\n"
        )
        self._write(
            b"\x1b[1;36m * Type 'help' for commands, 'matrix' or 'colors' to test.\x1b[0m\r\n"
        )
        self._write(
            b"\x1b[1;36m=================================================================\x1b[0m\r\n"
        )
        self._write(self._prompt[2:])

    def handle_input(self, payload: bytes):
        if self._running_test:
            if payload == b"\x03":  # Ctrl+C interrupts test
                self._running_test = False
                self._write(b"^C" + self._prompt)
            return

        text = payload.decode("utf-8", errors="ignore")
        if text == "\r":
            cmd = self._input_buf.strip().lower()
            self._input_buf = ""
            self._execute_command(cmd)
        elif text == "\x03":  # Ctrl+C
            self._input_buf = ""
            self._write(b"^C" + self._prompt)
        elif text == "\x0c":  # Ctrl+L
            self._input_buf = ""
            self._clear()
            self._write(self._prompt[2:])
        elif text == "\x7f" or text == "\x08":  # Backspace
            if self._input_buf:
                self._input_buf = self._input_buf[:-1]
                self._write(b"\x08 \x08")
        elif text == "\t":  # TAB completion
            self._handle_tab()
        elif text.startswith("\x1b"):
            pass  # Ignore raw escape sequences in prompt
        else:
            self._input_buf += text
            self._write(payload)

    def _handle_tab(self):
        commands = ["help", "clear", "colors", "matrix", "stress", "about"]
        matches = [c for c in commands if c.startswith(self._input_buf.lower())]
        if len(matches) == 1:
            remainder = matches[0][len(self._input_buf) :]
            self._input_buf = matches[0]
            self._write(remainder.encode("utf-8"))
        elif len(matches) > 1:
            self._write(b"\r\n" + "  ".join(matches).encode("utf-8") + b"\r\n")
            self._write(self._prompt[2:] + self._input_buf.encode("utf-8"))
        else:
            self._write(b"\a")  # Bell if no match

    def _execute_command(self, cmd: str):
        if not cmd:
            self._write(self._prompt)
            return
        if cmd == "help":
            self._write(b"\r\n\x1b[1;33mAvailable Commands:\x1b[0m\r\n")
            self._write(b"  \x1b[36mhelp\x1b[0m    - Show this list\r\n")
            self._write(b"  \x1b[36mclear\x1b[0m   - Clear terminal buffer\r\n")
            self._write(b"  \x1b[36mcolors\x1b[0m  - Display 16-color ANSI grid\r\n")
            self._write(b"  \x1b[36mmatrix\x1b[0m  - Run simulated digital rain\r\n")
            self._write(
                b"  \x1b[36mstress\x1b[0m  - High throughput line generator\r\n"
            )
            self._write(self._prompt)
        elif cmd == "clear":
            self._clear()
            self._write(self._prompt[2:])
        elif cmd == "colors":
            self._run_colors_test()
        elif cmd == "matrix":
            self._run_matrix_test()
        elif cmd == "stress":
            self._run_stress_test()
        else:
            self._write(
                f"\r\nCommand not found: {cmd}. Type 'help' for commands.".encode(
                    "utf-8"
                )
                + self._prompt
            )

    def _run_colors_test(self):
        self._write(b"\r\n\x1b[1mStandard & Bright ANSI Colors:\x1b[0m\r\n")
        for i in range(8):
            self._write(f"\x1b[4{i}m   \x1b[0m ".encode("utf-8"))
        self._write(b"\r\n")
        for i in range(8):
            self._write(f"\x1b[10{i}m   \x1b[0m ".encode("utf-8"))
        self._write(self._prompt)

    def _run_matrix_test(self):
        self._running_test = True
        self._write(b"\r\n\x1b[32mStarting Matrix (Press Ctrl+C to stop)...\x1b[0m\r\n")

        def loop():
            for i in range(60):
                if not self._running_test:
                    break
                self._write(
                    f"\x1b[32m{' '.join(['10'[((i + j) * 7) % 2] for j in range(40)])}\x1b[0m\r\n".encode(
                        "utf-8"
                    )
                )
                time.sleep(0.05)
            self._running_test = False
            self._write(self._prompt)

        try:
            threading.Thread(target=loop, daemon=True).start()
        except RuntimeError:
            import asyncio

            async def async_loop():
                for i in range(60):
                    if not self._running_test:
                        break
                    self._write(
                        f"\x1b[32m{' '.join(['10'[((i + j) * 7) % 2] for j in range(40)])}\x1b[0m\r\n".encode(
                            "utf-8"
                        )
                    )
                    await asyncio.sleep(0.05)
                self._running_test = False
                self._write(self._prompt)

            try:
                loop_obj = asyncio.get_running_loop()
                loop_obj.create_task(async_loop())
            except Exception:
                pass

    def _run_stress_test(self):
        self._running_test = True
        self._write(
            b"\r\n\x1b[33mGenerating 1000 lines (Press Ctrl+C to stop)...\x1b[0m\r\n"
        )

        def loop():
            for i in range(1, 1001):
                if not self._running_test:
                    break
                self._write(
                    f"\x1b[36m[LINE {i:04d}]\x1b[0m High-speed throughput test payload string...\r\n".encode(
                        "utf-8"
                    )
                )
                time.sleep(0.002)
            self._running_test = False
            self._write(self._prompt)

        try:
            threading.Thread(target=loop, daemon=True).start()
        except RuntimeError:
            import asyncio

            async def async_loop():
                for i in range(1, 1001):
                    if not self._running_test:
                        break
                    self._write(
                        f"\x1b[36m[LINE {i:04d}]\x1b[0m High-speed throughput test payload string...\r\n".encode(
                            "utf-8"
                        )
                    )
                    await asyncio.sleep(0.002)
                self._running_test = False
                self._write(self._prompt)

            try:
                loop_obj = asyncio.get_running_loop()
                loop_obj.create_task(async_loop())
            except Exception:
                pass
