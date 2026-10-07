"""MCP stdio transport.

Adapted from open-jarvis/OpenJarvis (Apache License 2.0).
Only the stdio transport is ported — SSE/HTTP deferred until needed.
"""

from __future__ import annotations

import json
import logging
import queue
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from mcp.protocol import MCPRequest, MCPResponse

logger = logging.getLogger(__name__)


class MCPTransport(ABC):
    """Abstract transport layer for MCP communication."""

    @abstractmethod
    def send(self, request: MCPRequest) -> MCPResponse:
        """Send a request and return the response."""

    def send_notification(self, request: MCPRequest) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        self.send(request)

    @abstractmethod
    def close(self) -> None:
        """Release transport resources."""


class StdioTransport(MCPTransport):
    """JSON-RPC over stdin/stdout subprocess transport.

    Launches a subprocess and communicates via JSON lines on stdin/stdout.
    """

    _STDOUT_QUEUE_SIZE = 1024
    _STDOUT_EOF = object()

    def __init__(
        self,
        command: List[str],
        *,
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
        response_timeout: float = 600.0,
    ) -> None:
        if response_timeout <= 0:
            raise ValueError("response_timeout must be positive")
        self._command = command
        self._env = env
        self._cwd = cwd
        self._response_timeout = response_timeout
        self._process: Optional[subprocess.Popen] = None
        self._stdout_queue: queue.Queue = queue.Queue(
            maxsize=self._STDOUT_QUEUE_SIZE
        )
        self._reader_stop = threading.Event()
        self._reader_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        # A single stdout stream cannot safely serve multiple independent
        # readers: one request could consume and discard another request's
        # response. Serialize complete write/read exchanges so response
        # correlation remains lossless.
        self._request_lock = threading.Lock()
        self._start()

    def _start(self) -> None:
        """Start the subprocess."""
        import os
        import shutil

        cmd = list(self._command)
        # Windows: resolve .cmd/.bat wrappers (npx, uvx, …) through cmd.exe —
        # CreateProcess cannot execute them directly.
        if os.name == "nt" and cmd:
            resolved = shutil.which(cmd[0])
            if resolved and resolved.lower().endswith((".cmd", ".bat")):
                cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/c", resolved, *cmd[1:]]

        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self._env,
            cwd=self._cwd,
        )
        self._reader_thread = threading.Thread(
            target=self._read_stdout,
            name="soda-mcp-stdout",
            daemon=True,
        )
        self._reader_thread.start()
        # Nothing else reads stderr. Once the child writes more than the OS
        # pipe buffer to it, the child blocks on that write and never gets
        # to answer on stdout. Drain it continuously on a background thread.
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr,
            args=(self._process,),
            name="soda-mcp-stderr",
            daemon=True,
        )
        self._stderr_thread.start()

    def _read_stdout(self) -> None:
        """Read the subprocess pipe without tying up the request thread.

        A dedicated reader is portable to Windows, where ``select`` cannot
        wait on an anonymous subprocess pipe. The bounded queue also applies
        backpressure if a server writes stdout while no request is reading.
        """
        proc = self._process
        stdout = proc.stdout if proc is not None else None
        if stdout is None:
            return

        try:
            while not self._reader_stop.is_set():
                line = stdout.readline()
                if not line:
                    break
                while not self._reader_stop.is_set():
                    try:
                        self._stdout_queue.put(line, timeout=0.1)
                        break
                    except queue.Full:
                        continue
        finally:
            while not self._reader_stop.is_set():
                try:
                    self._stdout_queue.put(self._STDOUT_EOF, timeout=0.1)
                    break
                except queue.Full:
                    continue

    def _next_stdout_line(self, deadline: float, request_id: Any) -> str:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError(f"Timed out waiting for MCP response id {request_id!r}")
        try:
            item = self._stdout_queue.get(timeout=remaining)
        except queue.Empty as exc:
            raise RuntimeError(
                f"Timed out waiting for MCP response id {request_id!r}"
            ) from exc
        if item is self._STDOUT_EOF:
            raise RuntimeError("No response from subprocess")
        return item

    def _drain_stderr(self, proc: subprocess.Popen) -> None:
        """Continuously read the child's stderr so its pipe never fills."""
        if proc.stderr is None:
            return
        for line in proc.stderr:
            line = line.rstrip("\n")
            if line:
                logger.debug("[%s stderr] %s", self._command[0], line)

    def send(self, request: MCPRequest) -> MCPResponse:
        """Write request as JSON line, read lines until the matching response.

        MCP servers may emit unsolicited notifications or stray/stale
        replies on stdout before the real response. Skip anything that
        isn't a well-formed JSON-RPC response carrying this request's id,
        rather than treating the first line as gospel.
        """
        with self._request_lock:
            proc = self._process
            if proc is None or proc.stdin is None or proc.stdout is None:
                raise RuntimeError("Transport process is not running")

            line = request.to_json() + "\n"
            proc.stdin.write(line)
            proc.stdin.flush()

            deadline = time.monotonic() + self._response_timeout
            while True:
                # Check the wall-clock deadline even when a server continuously
                # floods stdout, so queued blank/noise/notification lines cannot
                # keep extending the request forever.
                response_line = self._next_stdout_line(deadline, request.id)
                response_line = response_line.strip()
                if not response_line:
                    continue

                try:
                    parsed = json.loads(response_line)
                except (json.JSONDecodeError, ValueError):
                    parsed = None

                is_response = (
                    isinstance(parsed, dict)
                    and "id" in parsed
                    and ("result" in parsed or "error" in parsed)
                    and parsed["id"] == request.id
                )
                if is_response:
                    return MCPResponse.from_json(response_line)

    def send_notification(self, request: MCPRequest) -> None:
        """Send a JSON-RPC notification — write only, never read."""
        with self._request_lock:
            proc = self._process
            if proc is None or proc.stdin is None:
                raise RuntimeError("Transport process is not running")
            line = request.to_json() + "\n"
            proc.stdin.write(line)
            proc.stdin.flush()

    def close(self) -> None:
        """Terminate the subprocess."""
        if self._process is not None:
            self._reader_stop.set()
            # Wake a request waiting on the queue before stopping the process.
            try:
                self._stdout_queue.put_nowait(self._STDOUT_EOF)
            except queue.Full:
                try:
                    self._stdout_queue.get_nowait()
                    self._stdout_queue.put_nowait(self._STDOUT_EOF)
                except (queue.Empty, queue.Full):
                    pass
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)
            if self._reader_thread is not None:
                self._reader_thread.join(timeout=1)
                self._reader_thread = None
            self._process = None
        if self._stderr_thread is not None:
            self._stderr_thread.join(timeout=5)
            self._stderr_thread = None


__all__ = ["MCPTransport", "StdioTransport"]
