"""PTY Service — cross-platform process and PTY management for Linux, Windows, and Android."""

from __future__ import annotations

import contextlib
import os
import struct
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Optional


def _default_shell() -> str:
    """Pick a working interactive shell for this host.

    Order: $SHELL (desktop logins set it) → Android's /system/bin/sh ->
    /bin/bash → /bin/sh. Android has no $SHELL and no /bin/bash, which is why
    the demo used to die with "no PTY" there.
    """
    env_shell = os.environ.get("SHELL", "")
    if env_shell and Path(env_shell).exists():
        return env_shell
    for candidate in ("/system/bin/sh", "/bin/bash", "/bin/sh"):
        if Path(candidate).exists():
            return candidate
    return "/bin/sh"


# Try importing POSIX pty
HAS_POSIX_PTY = False
try:
    if sys.platform not in ("emscripten", "wasi", "win32"):
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


class PTYService:
    """Manages OS terminal sessions (POSIX pty or Windows ConPTY)."""

    def __init__(
        self, on_output: Callable[[bytes], None], on_error: Callable[[str], None]
    ):
        self._on_output = on_output
        self._on_error = on_error
        self.pty_master_fd: Optional[int] = None
        self.pty_process = None
        self.active_engine: str = self.get_default_engine()

    @classmethod
    def get_default_engine(cls) -> str:
        if HAS_POSIX_PTY or HAS_WIN_PTY:
            return "Local OS PTY"
        return "Local OS PTY"

    @classmethod
    def available_engines(cls) -> list[str]:
        engines = []
        if HAS_POSIX_PTY or HAS_WIN_PTY:
            engines.append("Local OS PTY")
        if not engines:
            engines.append("Local OS PTY")
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
                self._on_error("PTY engine unavailable on this OS.")

    def stop_session(self):
        if self.pty_master_fd is not None:
            # Closes the master — the slave side (and the child) see EOF.
            with contextlib.suppress(OSError):
                os.close(self.pty_master_fd)
            self.pty_master_fd = None
        if self.pty_process is not None:
            proc, self.pty_process = self.pty_process, None
            with contextlib.suppress(Exception):
                if not getattr(proc, "isalive", lambda: False)():
                    return
            # Preferred: ask the shell to exit (works for both engines).
            with contextlib.suppress(Exception):
                proc.write(b"exit\r\n")
            # Give it a moment, then force whatever API is available.
            deadline = 0.0
            while deadline < 1.0:
                if not getattr(proc, "isalive", lambda: False)():
                    break
                time.sleep(0.05)
                deadline += 0.05
            with contextlib.suppress(Exception):
                if getattr(proc, "isalive", lambda: False)():
                    if hasattr(proc, "terminate"):
                        proc.terminate()
                    elif hasattr(proc, "close"):
                        proc.close()

    def write(self, payload: bytes):
        if self.active_engine == "Local OS PTY":
            if HAS_POSIX_PTY and self.pty_master_fd is not None:
                with contextlib.suppress(OSError):
                    os.write(self.pty_master_fd, payload)
            elif HAS_WIN_PTY and self.pty_process is not None:
                with contextlib.suppress(Exception):
                    self.pty_process.write(payload.decode("utf-8", errors="ignore"))

    def resize(self, cols: int, rows: int):
        if self.active_engine == "Local OS PTY":
            if self.pty_master_fd is not None and HAS_POSIX_PTY:
                with contextlib.suppress(Exception):
                    winsize = struct.pack("HHHH", rows, cols, 0, 0)
                    fcntl.ioctl(self.pty_master_fd, termios.TIOCSWINSZ, winsize)
            elif HAS_WIN_PTY and self.pty_process is not None and cols > 0 and rows > 0:
                with contextlib.suppress(Exception):
                    self.pty_process.set_size(cols, rows)

    def _start_posix(self):
        import subprocess

        try:
            master_fd, slave_fd = pty.openpty()
            shell = _default_shell()
            # A login shell gives the interactive prompt profile (PS1 etc.);
            # Android's /system/bin/sh (mksh) has no -l login convention.
            argv = [shell]
            if not shell.startswith("/system/bin/sh"):
                argv.append("-l")
            env = dict(os.environ)
            env.setdefault("TERM", "xterm-256color")
            env.setdefault("HOME", os.path.expanduser("~"))
            self.pty_process = subprocess.Popen(
                argv,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                start_new_session=True,
                env=env,
            )
            os.close(slave_fd)
            self.pty_master_fd = master_fd

            def read_loop():
                while True:
                    proc = self.pty_process
                    if proc is None:
                        break
                    try:
                        data = os.read(master_fd, 4096)
                    except (OSError, ValueError):
                        break  # master closed (stop_session) or fd gone
                    if data:
                        self._on_output(data)
                    elif proc.poll() is not None:
                        break

            threading.Thread(target=read_loop, daemon=True).start()
        except Exception as ex:
            self._on_error(f"POSIX PTY start failed: {ex}")

    def _start_winpty(self):
        try:
            proc = winpty.PTY(80, 24)
            proc.spawn(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
            self.pty_process = proc

            def read_loop():
                # pywinpty's read() defaults to NON-blocking and returns only
                # what is currently buffered — the old loop treated that first
                # empty read as EOF and exited instantly. blocking=True waits
                # for the next chunk; empty+lifeless means the child is gone.
                while True:
                    live = self.pty_process
                    if live is None or live is not proc:
                        break
                    try:
                        data = proc.read(blocking=True)
                    except Exception:
                        break
                    if data:
                        self._on_output(data.encode("utf-8"))
                    elif not proc.isalive():
                        break

            threading.Thread(target=read_loop, daemon=True).start()
        except Exception as ex:
            self._on_error(f"Windows PTY failed: {ex}")
