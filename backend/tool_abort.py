"""Shared abort mechanism for local agent tools.
Allows external cancellation of long-running tool operations (Spotify clicks, etc.).
Thread-safe: uses threading.Event so a monitor thread can abort from outside.
"""

import time
import threading

_abort_flag = threading.Event()


def abort():
    """Signal all running tools to abort immediately."""
    _abort_flag.set()


def clear():
    """Reset abort flag before starting a new tool."""
    _abort_flag.clear()


def is_aborted():
    """Check if abort has been signalled."""
    return _abort_flag.is_set()


class AbortError(BaseException):
    """Raised when a tool operation is aborted (frontend disconnected, etc.).
    Inherits from BaseException (not Exception) so normal `except Exception`
    handlers in tool code don't accidentally swallow it."""
    pass


def check():
    """Call periodically from long-running tool code. Raises AbortError if aborted."""
    if _abort_flag.is_set():
        raise AbortError("Tool execution aborted")


def safe_sleep(seconds, interval=0.5):
    """Sleep in small intervals, checking abort flag each tick.
    Raises AbortError if abort is signalled during sleep.
    """
    elapsed = 0.0
    while elapsed < seconds:
        check()
        step = min(interval, seconds - elapsed)
        time.sleep(step)
        elapsed += step
    check()
