"""
Hermes Agent bridge for SODA.
Sends desktop-control tasks to the Hermes Agent gateway (localhost:8642).
Falls back to legacy local_agent automation when Hermes is slow or unavailable.

Fallback strategy:
  - Hermes gets HERMES_FAST_TIMEOUT seconds (default 10s) to respond
  - If it doesn't respond in time, caller falls back to legacy automation
  - This keeps SODA snappy even when Hermes/OpenRouter is slow
"""

import os
import sys
import time
import json
import logging
import threading
import subprocess
import urllib.request
import urllib.error

_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

HERMES_HOST = os.getenv("HERMES_HOST", "127.0.0.1")
HERMES_PORT = int(os.getenv("HERMES_PORT", "8642"))
HERMES_API_KEY = os.getenv("HERMES_API_KEY", "soda-hermes-local")
HERMES_BASE = f"http://{HERMES_HOST}:{HERMES_PORT}"
# Fast timeout: if Hermes doesn't respond within this window, fall back
HERMES_FAST_TIMEOUT = float(os.getenv("HERMES_FAST_TIMEOUT", "10"))
# Full timeout: maximum time to wait for Hermes (for hermes_execute tool)
HERMES_FULL_TIMEOUT = float(os.getenv("HERMES_FULL_TIMEOUT", "180"))

_hermes_process: subprocess.Popen | None = None
_hermes_lock = threading.Lock()

log = logging.getLogger("hermes_bridge")


# ── Health check ──────────────────────────────────────────────────────

def is_alive() -> bool:
    """Return True if Hermes gateway is reachable."""
    try:
        req = urllib.request.Request(
            f"{HERMES_BASE}/health",
            headers={"Authorization": f"Bearer {HERMES_API_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def wait_for_hermes(timeout: float = 30.0) -> bool:
    """Block until Hermes responds or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_alive():
            return True
        time.sleep(1.0)
    return False


# ── Gateway lifecycle ─────────────────────────────────────────────────

def start_gateway(timeout: float = 30.0) -> bool:
    """Start hermes gateway as a background process. Returns True if running."""
    global _hermes_process
    with _hermes_lock:
        if _hermes_process and _hermes_process.poll() is None:
            return True
        try:
            _hermes_process = subprocess.Popen(
                ["hermes", "gateway"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except FileNotFoundError:
            log.warning("hermes binary not found on PATH")
            return False
        except Exception as exc:
            log.warning(f"Failed to start hermes gateway: {exc}")
            return False
    return wait_for_hermes(timeout)


def stop_gateway():
    """Gracefully stop the gateway we started."""
    global _hermes_process
    with _hermes_lock:
        if _hermes_process and _hermes_process.poll() is None:
            _hermes_process.terminate()
            try:
                _hermes_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _hermes_process.kill()
        _hermes_process = None


# ── Low-level HTTP helper ─────────────────────────────────────────────

def _post_json(path: str, body: dict, timeout: float = 30.0) -> dict:
    """POST JSON to the Hermes API and return parsed response."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{HERMES_BASE}{path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {HERMES_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# ── Task execution ────────────────────────────────────────────────────

def execute_task(prompt: str, *, timeout: float = None) -> dict:
    """Send a task to Hermes with fast-fallback.

    Returns:
      {"success": True, "result": "..."} on completion
      {"success": False, "error": "hermes_timeout"} if Hermes was too slow
      {"success": False, "error": "hermes_not_running"} if gateway is down
    """
    if timeout is None:
        timeout = HERMES_FULL_TIMEOUT
    if not is_alive():
        return {"success": False, "error": "hermes_not_running"}

    body = {
        "model": "hermes-agent",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    try:
        raw = _post_json("/v1/chat/completions", body, timeout=timeout)
        choices = raw.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content", "")
            return {"success": True, "result": content, "raw": raw}
        return {"success": False, "error": "empty_response", "raw": raw}
    except urllib.error.URLError:
        return {"success": False, "error": "hermes_timeout"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def try_task(prompt: str, fast_timeout: float = None) -> dict | None:
    """Try a Hermes task with a fast timeout. Returns None if too slow.

    Use this for tool calls where we have a legacy fallback:
        result = try_task("open WhatsApp")
        if result is None:
            result = legacy_open_whatsapp()
    """
    if fast_timeout is None:
        fast_timeout = HERMES_FAST_TIMEOUT
    if not is_alive():
        return None
    result = execute_task(prompt, timeout=fast_timeout)
    if result.get("success"):
        return result
    if "timeout" in result.get("error", ""):
        log.info(f"Hermes timed out in {fast_timeout}s, fallback available")
        return None
    # Other error (model error, etc) — still return it so caller can decide
    return result


# ── Convenience wrappers (with fast-fallback) ─────────────────────────

def open_app(app_name: str) -> dict:
    r = try_task(
        f"Open the application '{app_name}' on this computer. "
        f"Use the Start Menu or search to find and launch it. "
        f"Return success/failure.",
    )
    if r is not None:
        return r
    return {"success": False, "error": "hermes_fallback"}


def send_whatsapp(contact: str, message: str) -> dict:
    r = try_task(
        f"Open WhatsApp Desktop, search for the contact '{contact}', "
        f"open the chat, and send them this message: {message}. "
        f"Confirm the message was sent successfully.",
    )
    if r is not None:
        return r
    return {"success": False, "error": "hermes_fallback"}


def read_whatsapp(contact: str) -> dict:
    r = try_task(
        f"Open WhatsApp Desktop, search for the contact '{contact}', "
        f"open the chat, and read the last 5 messages visible on screen.",
    )
    if r is not None:
        return r
    return {"success": False, "error": "hermes_fallback"}


def check_whatsapp() -> dict:
    r = try_task(
        "Open WhatsApp Desktop and check if there are any unread messages.",
    )
    if r is not None:
        return r
    return {"success": False, "error": "hermes_fallback"}


def reply_whatsapp(contact: str, message: str) -> dict:
    r = try_task(
        f"Open WhatsApp Desktop, search for '{contact}', open the chat, "
        f"and reply with this message: {message}.",
    )
    if r is not None:
        return r
    return {"success": False, "error": "hermes_fallback"}


def screenshot_and_analyze(prompt: str = "Describe what you see on screen") -> dict:
    r = try_task(
        f"Take a screenshot of the current screen and analyze it. Task: {prompt}",
    )
    if r is not None:
        return r
    return {"success": False, "error": "hermes_fallback"}


def desktop_task(prompt: str) -> dict:
    """Generic desktop task — full timeout, no fast-fallback."""
    return execute_task(prompt, timeout=HERMES_FULL_TIMEOUT)
