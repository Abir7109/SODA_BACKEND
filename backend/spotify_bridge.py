"""
Spotify bridge — Spicetify extension via WebSocket.
- Search: Pathfinder GraphQL via extension's native fetch
- Playback: Spicetify.Player API (play, pause, skip, volume, status)
"""

import asyncio, json, threading, time, uuid, os, sys, subprocess
from urllib.parse import urlencode
from logger import log

# ── Search via Spicetify extension (native fetch, not rate-limited) ──

def search(query, limit=10):
    return _send_command("search", {"query": query, "limit": limit})


# ── Playback control via Spicetify WebSocket ──

WS_PORT = 18920
_loop = None
_extension_ws = None
_extension_last_seen = 0.0
_extension_connected_at = 0.0
_server_started = False
_server_ready = False
_auto_launch_attempted = False
_server_lock = threading.Lock()
_response_events = {}
_results = {}

def _run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _loop)


def _spotify_is_running():
    """Check if Spotify.exe process exists. Returns True/False/None."""
    try:
        if sys.platform == "win32":
            r = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Spotify.exe", "/NH"],
                capture_output=True, text=True, timeout=5
            )
            found = "Spotify.exe" in r.stdout
            log.info("[Spotify] Process check: Spotify.exe %s", "RUNNING" if found else "NOT FOUND")
            return found
        else:
            r = subprocess.run(
                ["pgrep", "-x", "spotify"],
                capture_output=True, timeout=5
            )
            found = r.returncode == 0
            log.info("[Spotify] Process check: spotify %s", "RUNNING" if found else "NOT FOUND")
            return found
    except FileNotFoundError:
        log.warning("[Spotify] Cannot check process (tasklist/pgrep not available in this environment)")
        return None
    except Exception as e:
        log.warning("[Spotify] Process check failed: %s", e)
        return None


def _build_error_msg():
    """Return a detailed, scenario-specific error message."""
    now = time.time()
    since_last_seen = (now - _extension_last_seen) if _extension_last_seen > 0 else float("inf")

    if _server_started and not _server_ready:
        return (
            f"Spotify bridge WebSocket server failed to start on port {WS_PORT}. "
            "Check if another process is using that port, then restart the backend."
        )

    if since_last_seen < 60 and _extension_last_seen > 0:
        return (
            f"Spicetify extension disconnected {since_last_seen:.0f}s ago. "
            "It will auto-reconnect — try again in a moment."
        )

    spotify_running = _spotify_is_running()

    if spotify_running is True:
        return (
            "Spotify is running but the Spicetify extension isn't loaded. "
            "Run: spicetify refresh -e"
        )
    elif spotify_running is False:
        return (
            "Spotify is not running. "
            "Run: spicetify restart"
        )
    else:
        return (
            "Could not detect Spotify. "
            "Make sure Spotify is running with Spicetify loaded, then try again."
        )


def _launch_spotify():
    """Try to launch Spotify via spicetify restart."""
    spicetify_exe = os.path.join(
        os.environ.get("LOCALAPPDATA", ""), "spicetify", "spicetify.exe"
    )
    if not os.path.isfile(spicetify_exe):
        log.warning("[Spotify] spicetify.exe not found at %s", spicetify_exe)
        # Try to find it via PATH
        try:
            r = subprocess.run(["where", "spicetify"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                spicetify_exe = r.stdout.strip().split("\n")[0].strip()
                log.info("[Spotify] Found spicetify via PATH: %s", spicetify_exe)
            else:
                log.error("[Spotify] spicetify not found in PATH either")
                return False
        except Exception as e:
            log.error("[Spotify] Failed to locate spicetify: %s", e)
            return False
    try:
        log.info("[Spotify] Launching: %s restart", spicetify_exe)
        subprocess.Popen(
            [spicetify_exe, "restart"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        log.info("[Spotify] spicetify restart launched")
        return True
    except Exception as e:
        log.error("[Spotify] spicetify launch failed: %s", e)
        return False


def _try_auto_launch_if_needed():
    """Called once after the WS server starts. Launches Spotify if not running."""
    global _auto_launch_attempted
    if _auto_launch_attempted:
        return
    _auto_launch_attempted = True

    if _extension_ws is not None:
        log.info("[Spotify] Auto-launch skipped — extension already connected")
        return

    running = _spotify_is_running()
    if running is True:
        log.info("[Spotify] Auto-launch skipped — Spotify is already running")
        return
    elif running is False:
        log.info("[Spotify] Auto-launch: Spotify not running — launching via spicetify restart")
        _launch_spotify()
    else:
        log.info("[Spotify] Auto-launch: cannot detect Spotify state — trying spicetify restart anyway")
        _launch_spotify()


def _ensure_server():
    global _server_started, _loop, _server_ready

    # Fast path: server is running and ready
    if _server_started and _server_ready:
        return

    # Server was started but never became ready (crashed silently) — reset
    if _server_started and not _server_ready:
        log.warning("[Spotify] Server was started but never became ready — resetting for retry")
        _server_started = False
        _loop = None

    with _server_lock:
        if _server_started and _server_ready:
            return
        if _server_started and not _server_ready:
            _server_started = False
            _loop = None
        _server_started = True
        _server_ready = False

    def start_loop():
        global _loop, _server_ready
        try:
            _loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_loop)
            _loop.run_until_complete(_ws_main())
        except Exception as e:
            log.error("[Spotify] WS server thread crashed: %s", e)
            _server_ready = False

    threading.Thread(target=start_loop, daemon=True).start()

    # Wait up to 10s for server to become ready
    for i in range(100):
        if _server_ready:
            _try_auto_launch_if_needed()
            return
        time.sleep(0.1)

    # Timed out
    _server_started = False
    log.error("[Spotify] WebSocket server failed to start within 10s timeout — is port %d in use?", WS_PORT)
    raise ConnectionError(
        f"Spotify bridge failed to start on port {WS_PORT}. "
        "Check if another process is using that port."
    )


async def _ws_main():
    global _extension_ws, _server_ready, _extension_last_seen, _extension_connected_at
    import websockets
    import asyncio
    import logging
    import traceback

    logging.getLogger("websockets.server").setLevel(logging.CRITICAL)

    async def handler(ws):
        global _extension_ws, _extension_last_seen, _extension_connected_at
        remote = ws.remote_address
        _extension_ws = ws
        _extension_connected_at = time.time()
        _extension_last_seen = time.time()
        log.info("[Spotify] Extension connected (remote=%s:%s)", remote[0], remote[1])
        try:
            async for raw in ws:
                _extension_last_seen = time.time()
                msg = json.loads(raw)
                resp_id = msg.get("id")
                if resp_id and resp_id in _response_events:
                    _results[resp_id] = msg
                    _response_events[resp_id].set()
        except Exception as e:
            log.warning("[Spotify] WS error: %s", e)
        finally:
            _extension_ws = None
            _extension_last_seen = time.time()
            duration = time.time() - _extension_connected_at
            log.info("[Spotify] Extension disconnected (was connected %.1fs)", duration)

    try:
        async with websockets.serve(handler, "0.0.0.0", WS_PORT):
            _server_ready = True
            log.info("[Spotify] WebSocket server listening on 0.0.0.0:%d", WS_PORT)
            await asyncio.Future()
    except OSError as e:
        _server_ready = False
        log.error("[Spotify] FAILED to start WebSocket server on port %d: %s", WS_PORT, e)
    except Exception as e:
        _server_ready = False
        log.error("[Spotify] WebSocket server crashed: %s", e)
        traceback.print_exc()


def _send_command(cmd, params=None, timeout=10):
    _ensure_server()

    if not _server_ready:
        raise ConnectionError(
            f"Spotify bridge server is down (port {WS_PORT}). "
            "Restart the backend to fix this."
        )

    now = time.time()
    since_last_seen = (now - _extension_last_seen) if _extension_last_seen > 0 else float("inf")

    if _extension_ws is None:
        if since_last_seen < 20 and _extension_last_seen > 0:
            # Extension was recently connected — wait for reconnect
            wait_limit = min(15, timeout)
            log.info(
                "[Spotify] Extension reconnecting (gone %.0fs, last_seen=%.3f), waiting up to %.0fs",
                since_last_seen, _extension_last_seen, wait_limit
            )
            for _ in range(int(wait_limit * 2)):
                if _extension_ws is not None:
                    log.info("[Spotify] Extension reconnected after %.1fs", time.time() - now)
                    break
                time.sleep(0.5)
        else:
            # Never connected or gone too long — fast fail
            wait_time = min(timeout, 5)
            log.info(
                "[Spotify] Extension not connected (last_seen=%.3f, since=%.0fs), waiting %.0fs",
                _extension_last_seen, since_last_seen, wait_time
            )
            for _ in range(int(wait_time * 2)):
                if _extension_ws is not None:
                    break
                time.sleep(0.5)

    if _extension_ws is None:
        msg = _build_error_msg()
        log.warning("[Spotify] Command '%s' failed: %s", cmd, msg)
        raise ConnectionError(msg)

    cmd_id = str(uuid.uuid4())
    evt = threading.Event()
    _response_events[cmd_id] = evt
    msg = json.dumps({"id": cmd_id, "cmd": cmd, "params": params or {}})
    future = _run_async(_extension_ws.send(msg))
    try:
        future.result(timeout=5)
    except Exception as e:
        _response_events.pop(cmd_id, None)
        raise RuntimeError(f"Send failed: {e}")

    if not evt.wait(timeout=timeout):
        _response_events.pop(cmd_id, None)
        log.warning("[Spotify] Command '%s' timed out after %ds (no response from extension)", cmd, timeout)
        raise TimeoutError(f"No response for '{cmd}' after {timeout}s")

    resp = _results.pop(cmd_id, {})
    if resp.get("ok"):
        log.info("[Spotify] Command '%s' succeeded in %.1fs", cmd, time.time() - now)
        return resp.get("result", True)
    raise RuntimeError(resp.get("error", "Unknown error"))


# ── Playback Public API ──

def play_track(track_id):
    return _send_command("play_uri", {"uri": f"spotify:track:{track_id}"})

def play_uri(uri):
    return _send_command("play_uri", {"uri": uri})

def play_music(query, emit_callback=None):
    data = search(query, limit=1)
    if not data:
        return {"success": False, "error": "Search failed"}
    tracks = (data.get("tracks") or {}).get("items") or []
    if not tracks:
        return {"success": False, "error": "No tracks found"}
    track = tracks[0]
    try:
        play_track(track["id"])
    except Exception as e:
        return {"success": False, "error": str(e)}
    now_playing = {
        "title": track["name"],
        "artist": track["artists"][0]["name"] if track.get("artists") else "Unknown",
        "album": (track.get("album") or {}).get("name", ""),
        "id": track["id"],
        "uri": track.get("uri", f"spotify:track:{track['id']}"),
        "image": (track.get("album") or {}).get("images", [{}])[0].get("url", ""),
    }
    if emit_callback:
        try:
            emit_callback({"data": now_playing})
        except Exception:
            pass
    return {"success": True, "now_playing": now_playing}

def play_pause():
    return {"success": _send_command("toggle_play")}

def resume():
    return {"success": _send_command("play")}

def next_track():
    return {"success": _send_command("next")}

def previous_track():
    return {"success": _send_command("previous")}

def set_volume(level):
    return {"success": _send_command("set_volume", {"level": level / 100.0})}

def get_status():
    result = _send_command("get_status", timeout=5)
    return result.get("status", result) if isinstance(result, dict) else {}
