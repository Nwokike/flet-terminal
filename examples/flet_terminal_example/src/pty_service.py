"""PTY Service — cross-platform process and PTY management for Linux, Windows, and Android."""

from __future__ import annotations
import os
import signal
import struct
import sys
import threading
from typing import Callable, Optional

# Try importing POSIX pty
HAS_POSIX_PTY = False
try:
    if sys.platform not in ("emscripten", "wasi", "win32", "android"):
        import fcntl
        import pty
        import termios

        try:
            _m, _s = pty.openpty()
            os.close(_m)
            os.close(_s)
            HAS_POSIX_PTY = True
        except OSError:
            HAS_POSIX_PTY = False
except ImportError:
    HAS_POSIX_PTY = False

# Try importing Windows ConPTY
HAS_WIN_PTY = False
try:
    if sys.platform not in ("emscripten", "wasi"):
        import winpty

        HAS_WIN_PTY = True
except ImportError:
    HAS_WIN_PTY = False

HAS_ANDROID_SUBPROCESS = sys.platform == "android"


class PTYService:
    """Manages OS terminal sessions (POSIX pty, Windows ConPTY, or Android subprocess)."""

    def __init__(
        self, on_output: Callable[[bytes], None], on_error: Callable[[str], None]
    ):
        self._on_output = on_output
        self._on_error = on_error
        self.pty_master_fd: Optional[int] = None
        self.pty_process = None
        self.android_proc = None
        self.active_engine: str = self.get_default_engine()

    @classmethod
    def get_default_engine(cls) -> str:
        if HAS_ANDROID_SUBPROCESS:
            return "Android Local Shell"
        if HAS_POSIX_PTY or HAS_WIN_PTY:
            return "Local OS PTY"
        return "ANSI Demo Engine"

    @classmethod
    def available_engines(cls) -> list[str]:
        engines = ["ANSI Demo Engine"]
        if HAS_POSIX_PTY or HAS_WIN_PTY:
            engines.insert(0, "Local OS PTY")
        if HAS_ANDROID_SUBPROCESS:
            engines.insert(0, "Android Local Shell")
        return engines

    def start_session(self, engine: str):
        self.stop_session()
        self.active_engine = engine
        if engine == "Local OS PTY":
            if HAS_POSIX_PTY:
                self._start_posix()
            elif HAS_WIN_PTY:
                self._start_winpty()
            else:
                self._on_error(
                    "PTY engine unavailable on this OS. Falling back to Demo Engine."
                )
                self.active_engine = "ANSI Demo Engine"
        elif engine == "Android Local Shell":
            self._start_android()

    def stop_session(self):
        if self.pty_master_fd is not None:
            try:
                os.close(self.pty_master_fd)
            except OSError:
                pass
            self.pty_master_fd = None
        if self.pty_process is not None:
            try:
                if hasattr(self.pty_process, "terminate"):
                    self.pty_process.terminate()
                else:
                    self.pty_process.close()
            except Exception:
                pass
            self.pty_process = None
        if self.android_proc is not None:
            try:
                self.android_proc.terminate()
            except Exception:
                pass
            self.android_proc = None

    def write(self, payload: bytes):
        if self.active_engine == "Local OS PTY":
            if HAS_POSIX_PTY and self.pty_master_fd is not None:
                try:
                    os.write(self.pty_master_fd, payload)
                except OSError:
                    pass
            elif HAS_WIN_PTY and self.pty_process is not None:
                try:
                    self.pty_process.write(payload.decode("utf-8", errors="ignore"))
                except Exception:
                    pass
        elif self.active_engine == "Android Local Shell":
            if self.android_proc is not None and self.android_proc.poll() is None:
                try:
                    if payload == b"\x03":
                        self.android_proc.send_signal(signal.SIGINT)
                    elif payload != b"\x1b":
                        self.android_proc.stdin.write(payload)
                        self.android_proc.stdin.flush()
                except Exception:
                    pass

    def resize(self, cols: int, rows: int):
        if self.active_engine == "Local OS PTY":
            if self.pty_master_fd is not None and HAS_POSIX_PTY:
                try:
                    winsize = struct.pack("HHHH", rows, cols, 0, 0)
                    fcntl.ioctl(self.pty_master_fd, termios.TIOCSWINSZ, winsize)
                except Exception:
                    pass
            elif HAS_WIN_PTY and self.pty_process is not None and cols > 0 and rows > 0:
                try:
                    self.pty_process.set_size(cols, rows)
                except Exception:
                    pass

    def _start_posix(self):
        import subprocess

        try:
            master_fd, slave_fd = pty.openpty()
            shell = os.environ.get("SHELL", "/bin/bash")
            self.pty_process = subprocess.Popen(
                [shell, "-l"],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                start_new_session=True,
            )
            os.close(slave_fd)
            self.pty_master_fd = master_fd

            def read_loop():
                while (
                    self.pty_master_fd == master_fd and self.pty_master_fd is not None
                ):
                    try:
                        data = os.read(master_fd, 4096)
                        if not data:
                            break
                        self._on_output(data)
                    except (OSError, Exception):
                        break

            threading.Thread(target=read_loop, daemon=True).start()
        except Exception as ex:
            self._on_error(f"POSIX PTY start failed: {ex}. Reverting to Demo Engine.")
            self.active_engine = "ANSI Demo Engine"

    def _start_winpty(self):
        try:
            self.pty_process = winpty.PTY(80, 24)
            self.pty_process.spawn(
                r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
            )

            def read_loop():
                while self.pty_process is not None:
                    try:
                        data = self.pty_process.read()
                        if not data:
                            break
                        self._on_output(data.encode("utf-8"))
                    except Exception:
                        break

            threading.Thread(target=read_loop, daemon=True).start()
        except Exception as ex:
            self._on_error(f"Windows PTY failed: {ex}. Reverting to Demo Engine.")
            self.active_engine = "ANSI Demo Engine"

    def _start_android(self):
        import subprocess

        try:
            shell_cmd = (
                ["/system/bin/sh", "-i"]
                if os.path.exists("/system/bin/sh")
                else ["sh", "-i"]
            )
            self.android_proc = subprocess.Popen(
                shell_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
            )

            def read_loop():
                while (
                    self.android_proc is not None and self.android_proc.poll() is None
                ):
                    try:
                        data = self.android_proc.stdout.read(4096)
                        if not data:
                            break
                        self._on_output(data)
                    except Exception:
                        break

            threading.Thread(target=read_loop, daemon=True).start()
        except Exception as ex:
            self._on_error(f"Android shell failed: {ex}. Reverting to Demo Engine.")
            self.active_engine = "ANSI Demo Engine"
