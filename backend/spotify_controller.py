"""
Spotify Free Controller for SODA
===================================
Search, play from results, play/pause — no API keys, no Premium.
Uses Spotify URI protocol + keyboard automation + media keys.
"""

import os
import subprocess
import sys
import time
import json
from pathlib import Path


_SPOTIFY_EXE_PATHS = [
    r"C:\Users\{username}\AppData\Roaming\Spotify\Spotify.exe",
    r"C:\Program Files\Spotify\Spotify.exe",
    r"C:\Program Files (x86)\Spotify\Spotify.exe",
]


def _find_spotify_exe() -> str | None:
    import getpass, shutil
    username = getpass.getuser()
    for p in _SPOTIFY_EXE_PATHS:
        path = p.replace("{username}", username)
        if os.path.isfile(path):
            return path
    return shutil.which("spotify")


def _ensure_running(spotify_exe: str):
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Spotify.exe"],
            capture_output=True, text=True, timeout=5
        )
        if "Spotify.exe" not in result.stdout:
            subprocess.Popen([spotify_exe], shell=False)
            time.sleep(4.0)
    except Exception:
        pass


def _open_uri(uri: str) -> dict:
    spotify_exe = _find_spotify_exe()
    if not spotify_exe:
        return {"success": False, "error": "Spotify not installed. Download from spotify.com"}

    _ensure_running(spotify_exe)
    time.sleep(1.0)

    try:
        subprocess.Popen([spotify_exe, uri], shell=False)
        time.sleep(2.5)
        return {"success": True, "uri": uri}
    except Exception as e:
        return {"success": False, "error": f"Failed to open Spotify: {e}"}


def _focus_spotify() -> bool:
    """Bring Spotify window to foreground."""
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle("Spotify")
        if windows:
            w = windows[0]
            if w.isMinimized:
                w.restore()
            w.activate()
            time.sleep(0.5)
            return True
    except Exception:
        pass

    # Fallback: use pyautogui to Alt+Tab or find window
    try:
        import pyautogui
        # Try to find Spotify via taskbar
        pyautogui.hotkey("alt", "tab")
        time.sleep(0.3)
    except Exception:
        pass
    return False


def _key_press(keys: list[str], interval: float = 0.1):
    """Press a sequence of keys."""
    try:
        import pyautogui
        for key in keys:
            pyautogui.press(key)
            time.sleep(interval)
    except Exception:
        pass


def _key_hotkey(*keys: str):
    """Press a hotkey combination."""
    try:
        import pyautogui
        pyautogui.hotkey(*keys)
        time.sleep(0.3)
    except Exception:
        pass


def _media_key(key: str) -> bool:
    try:
        import pyautogui
        pyautogui.press(key)
        return True
    except Exception:
        return False


# ── Search ─────────────────────────────────────────────────────────

def search(query: str, search_type: str = "track", limit: int = 10) -> dict:
    """Open Spotify search. Returns URI for playback."""
    uri = f"spotify:search:{query}"
    r = _open_uri(uri)

    if r.get("success"):
        return {
            "success": True,
            "query": query,
            "uri": uri,
            "message": f"Opened Spotify search for '{query}'",
            "actions": [
                {"action": "play", "description": "Play first result"},
                {"action": "play", "query": "<song name>", "description": "Play specific song"},
            ],
        }
    return r


# ── Play ───────────────────────────────────────────────────────────

def play(uri: str = "", query: str = "", play_first: bool = True) -> dict:
    """
    Play music on Spotify Free.
    - uri: Direct Spotify URI (spotify:track:xxx, spotify:playlist:xxx)
    - query: Search term — opens search then auto-plays first result
    - play_first: If True, auto-selects first result from search
    """
    spotify_exe = _find_spotify_exe()
    if not spotify_exe:
        return {"success": False, "error": "Spotify not installed"}

    _ensure_running(spotify_exe)
    time.sleep(1.0)

    target = ""
    if uri:
        target = uri
    elif query:
        target = f"spotify:search:{query}"
    else:
        # Toggle play/pause
        _media_key("playpause")
        return {"success": True, "action": "playpause", "message": "Toggled playback"}

    # Open the URI
    try:
        subprocess.Popen([spotify_exe, target], shell=False)
        time.sleep(3.0)

        # If it's a direct track URI, just play it
        if target.startswith("spotify:track:"):
            _media_key("playpause")
            time.sleep(0.5)
            return {"success": True, "action": "play", "uri": target, "message": "Playing track"}

        # If it's a playlist/album/artist URI, just play it
        if target.startswith("spotify:playlist:") or target.startswith("spotify:album:") or target.startswith("spotify:artist:"):
            _media_key("playpause")
            time.sleep(0.5)
            return {"success": True, "action": "play", "uri": target, "message": "Playing collection"}

        # Search result — auto-play first item
        if play_first and query:
            time.sleep(1.5)  # Wait for search results to load
            _focus_spotify()
            time.sleep(0.5)

            # Navigate to first result and play
            # In Spotify search: results are listed, first one is usually focused
            # Press Enter to play the first result
            _key_press(["enter"], interval=0.2)
            time.sleep(1.0)

            return {
                "success": True,
                "action": "play",
                "query": query,
                "message": f"Playing first result for '{query}'",
            }

        return {"success": True, "action": "open", "uri": target, "message": "Opened in Spotify"}

    except Exception as e:
        return {"success": False, "error": f"Failed: {e}"}


# ── Control ────────────────────────────────────────────────────────

def control(action: str) -> dict:
    actions = {
        "play": "playpause",
        "pause": "playpause",
        "toggle": "playpause",
        "skip": "nexttrack",
        "next": "nexttrack",
        "previous": "previoustrack",
        "prev": "previoustrack",
        "volume_up": "volumeup",
        "volume_down": "volumedown",
        "volume_mute": "volumemute",
    }

    key = actions.get(action)
    if not key:
        return {"success": False, "error": f"Unknown: {action}. Valid: {', '.join(actions.keys())}"}

    success = _media_key(key)
    if success:
        return {"success": True, "action": action, "message": f"Spotify {action}"}
    return {"success": False, "error": "Media key failed"}


# ── Now Playing ────────────────────────────────────────────────────

def now_playing() -> dict:
    return {
        "success": True,
        "status": "running",
        "message": "Spotify is running",
        "tip": "Say 'skip', 'pause', 'volume up', etc.",
    }


if __name__ == "__main__":
    print("=== Spotify Free Controller ===")
    exe = _find_spotify_exe()
    print(f"Spotify: {exe}")
    if exe:
        r = play(query="lofi hip hop")
        print(json.dumps(r, indent=2))
