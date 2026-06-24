"""
Spotify bridge — Spicetify extension via WebSocket.
- Search: Pathfinder GraphQL via extension's native fetch
- Playback: Spicetify.Player API (play, pause, skip, volume, status)
"""

import asyncio, json, threading, time, uuid, os, requests
from urllib.parse import urlencode
from logger import log



# ── Search via Spicetify extension (native fetch, not rate-limited) ──

def search(query, limit=10):
    return _send_command("search", {"query": query, "limit": limit})


# ── Playback control via Spicetify WebSocket ──

WS_PORT = 18920
_loop = None
_extension_ws = None
_server_started = False
_server_lock = threading.Lock()
_response_events = {}
_results = {}

def _run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _loop)

def _ensure_server():
    global _server_started, _loop
    if _server_started:
        return
    with _server_lock:
        if _server_started:
            return
        _server_started = True

    def start_loop():
        global _loop
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        _loop.run_until_complete(_ws_main())

    threading.Thread(target=start_loop, daemon=True).start()
    for _ in range(100):
        if _loop is not None:
            return
        time.sleep(0.1)
    raise TimeoutError("Failed to start WebSocket server")

async def _ws_main():
    global _extension_ws
    import websockets
    import asyncio
    import logging

    # Suppress noisy non-WebSocket connection errors (HEAD probes, etc.)
    logging.getLogger("websockets.server").setLevel(logging.CRITICAL)

    async def handler(ws):
        global _extension_ws
        _extension_ws = ws
        log.info("[Spotify] Extension connected")
        try:
            async for raw in ws:
                msg = json.loads(raw)
                resp_id = msg.get("id")
                if resp_id and resp_id in _response_events:
                    _results[resp_id] = msg
                    _response_events[resp_id].set()
        except Exception as e:
            log.warning("[Spotify] WS error: %s", e)
        finally:
            _extension_ws = None
            log.info("[Spotify] Extension disconnected")

    async with websockets.serve(handler, "0.0.0.0", WS_PORT):
        log.info("[Spotify] Bridge ready on port %d", WS_PORT)
        await asyncio.Future()

SPICETIFY_EXE = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "spicetify", "spicetify.exe"
)

def _launch_spotify():
    """Try to launch Spotify via spicetify restart."""
    if not os.path.isfile(SPICETIFY_EXE):
        log.warning("[Spotify] spicetify.exe not found at %s", SPICETIFY_EXE)
        return False
    try:
        import subprocess
        subprocess.Popen([SPICETIFY_EXE, "restart"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log.info("[Spotify] Launched via spicetify restart")
        return True
    except Exception as e:
        log.warning("[Spotify] spicetify launch failed: %s", e)
        return False

def _send_command(cmd, params=None, timeout=10):
    _ensure_server()
    # First wait: check if extension is already connected
    for _ in range(timeout * 2):
        if _extension_ws is not None:
            break
        time.sleep(0.5)
    if _extension_ws is None:
        # Extension not connected — try launching Spotify
        log.info("[Spotify] Extension not connected, launching Spotify...")
        _launch_spotify()
        # Second wait: give Spotify time to start and extension to connect
        for _ in range(40):
            if _extension_ws is not None:
                break
            time.sleep(0.5)
    if _extension_ws is None:
        raise ConnectionError("Spicetify extension not connected — is Spotify running via 'spicetify auto'?")

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
        raise TimeoutError(f"No response for '{cmd}' after {timeout}s")

    resp = _results.pop(cmd_id, {})
    if resp.get("ok"):
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
