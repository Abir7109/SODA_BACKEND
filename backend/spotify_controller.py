"""
Spotify Free Controller for SODA
==================================
Launches Spotify Desktop directly, searches inside the app,
plays from results, controls playback — no API keys, no Premium.
"""

import os
import subprocess
import sys
import time
import json
import getpass
import shutil
from pathlib import Path


_SPOTIFY_EXE_PATHS = [
    r"C:\Users\{username}\AppData\Roaming\Spotify\Spotify.exe",
    r"C:\Program Files\Spotify\Spotify.exe",
    r"C:\Program Files (x86)\Spotify\Spotify.exe",
]


def _find_spotify_exe() -> str | None:
    username = getpass.getuser()
    for p in _SPOTIFY_EXE_PATHS:
        path = p.replace("{username}", username)
        if os.path.isfile(path):
            return path
    return shutil.which("spotify")


def _is_running() -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Spotify.exe"],
            capture_output=True, text=True, timeout=5
        )
        return "Spotify.exe" in result.stdout
    except Exception:
        return False


def _launch_spotify(spotify_exe: str):
    """Launch Spotify Desktop if not already running."""
    if _is_running():
        return
    try:
        subprocess.Popen([spotify_exe], shell=False)
        time.sleep(5.0)  # Wait for full startup
    except Exception:
        pass


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
    return False


def _type_text(text: str, interval: float = 0.03):
    """Type text character by character."""
    try:
        import pyautogui
        pyautogui.typewrite(text, interval=interval)
    except Exception:
        # fallback: use clipboard
        try:
            import pyperclip
            pyperclip.copy(text)
            import pyautogui
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            pass


def _key_press(key: str, interval: float = 0.1):
    try:
        import pyautogui
        pyautogui.press(key)
        time.sleep(interval)
    except Exception:
        pass


def _hotkey(*keys: str):
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


# ── Play ───────────────────────────────────────────────────────────

def play(uri: str = "", query: str = "", play_first: bool = True) -> dict:
    """
    Play music on Spotify Free.
    - uri: Direct Spotify URI (spotify:track:xxx, spotify:playlist:xxx)
    - query: Search term — searches inside Spotify Desktop, plays first result
    - play_first: If True, auto-selects first result from search
    """
    spotify_exe = _find_spotify_exe()
    if not spotify_exe:
        return {"success": False, "error": "Spotify not installed. Download from spotify.com"}

    # Launch Spotify Desktop
    _launch_spotify(spotify_exe)
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

    # Direct URI: open via executable (not browser)
    if uri:
        try:
            subprocess.Popen([spotify_exe, uri], shell=False)
            time.sleep(2.0)
            _media_key("playpause")
            time.sleep(0.5)
            return {"success": True, "action": "play", "uri": uri, "message": "Playing from URI"}
        except Exception as e:
            return {"success": False, "error": f"Failed: {e}"}

    # Search: open search in Spotify Desktop via keyboard
    _focus_spotify()
    time.sleep(0.5)

    # Ctrl+L = focus search bar in Spotify Desktop
    _hotkey("ctrl", "l")
    time.sleep(0.3)

    # Clear existing search
    _hotkey("ctrl", "a")
    time.sleep(0.1)

    # Type the search query
    _type_text(query)
    time.sleep(2.0)  # Wait for search results to load

    if play_first:
        # Navigate down to first result and play
        _key_press("down")
        time.sleep(0.2)
        _key_press("enter")
        time.sleep(1.0)

        return {
            "success": True,
            "action": "play",
            "query": query,
            "message": f"Playing '{query}' in Spotify",
        }

    return {"success": True, "action": "search", "query": query, "message": f"Searched for '{query}'"}


# ── Search ─────────────────────────────────────────────────────────

def search(query: str, search_type: str = "track", limit: int = 10) -> dict:
    """Open Spotify and search. Returns results for user selection."""
    spotify_exe = _find_spotify_exe()
    if not spotify_exe:
        return {"success": False, "error": "Spotify not installed"}

    _launch_spotify(spotify_exe)
    time.sleep(1.0)
    _focus_spotify()
    time.sleep(0.5)

    # Ctrl+L = focus search bar
    _hotkey("ctrl", "l")
    time.sleep(0.3)
    _hotkey("ctrl", "a")
    time.sleep(0.1)
    _type_text(query)
    time.sleep(2.0)

    return {
        "success": True,
        "query": query,
        "message": f"Searched for '{query}' in Spotify Desktop",
        "actions": [
            {"action": "play", "query": query, "description": "Play first result"},
        ],
    }


# ── Play Playlist ──────────────────────────────────────────────────

def play_playlist(playlist_name: str) -> dict:
    """Search for a playlist and play it."""
    spotify_exe = _find_spotify_exe()
    if not spotify_exe:
        return {"success": False, "error": "Spotify not installed"}

    _launch_spotify(spotify_exe)
    time.sleep(1.0)
    _focus_spotify()
    time.sleep(0.5)

    # Search for the playlist
    _hotkey("ctrl", "l")
    time.sleep(0.3)
    _hotkey("ctrl", "a")
    time.sleep(0.1)
    _type_text(playlist_name)
    time.sleep(2.0)

    # Navigate to Playlists tab
    _key_press("tab")
    time.sleep(0.2)
    _key_press("tab")
    time.sleep(0.2)
    _key_press("tab")
    time.sleep(0.2)
    _key_press("enter")
    time.sleep(1.0)

    # Play the first playlist
    _key_press("down")
    time.sleep(0.2)
    _key_press("enter")
    time.sleep(1.0)

    return {
        "success": True,
        "action": "play_playlist",
        "query": playlist_name,
        "message": f"Playing playlist '{playlist_name}'",
    }


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
