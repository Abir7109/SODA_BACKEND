"""
Spotify Desktop bridge for SODA.
Search & play music, global media key control (pause/next/prev).
Two-step flow: Enter opens top result, then click big play button at top of page.
"""

import os
import re
import time
import subprocess
import ctypes

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import win32gui
    import win32con
    _WIN32 = True
except ImportError:
    _WIN32 = False

from logger import log
from template_matcher import find_on_screen, capture_template
from play_history import find_similar, record_play

_SPOTIFY_BIG_PLAY_TEMPLATE = os.path.join(
    os.path.dirname(__file__), "vision_templates", "spotify_big_play.png"
)


# ── Window Management ──

def _find_spotify_window():
    if not _WIN32:
        return None
    matches = []
    def enum_cb(hwnd, _matches):
        if win32gui.IsWindowVisible(hwnd):
            text = win32gui.GetWindowText(hwnd)
            if "spotify" in text.lower():
                _matches.append((hwnd, text))
        return True
    win32gui.EnumWindows(enum_cb, matches)
    return matches[0] if matches else None


def _launch_spotify():
    candidates = [
        os.path.join(os.environ.get("APPDATA", ""), "Spotify", "Spotify.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Spotify", "Spotify.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WindowsApps", "Spotify.exe"),
    ]
    for exe in candidates:
        if exe and os.path.isfile(exe):
            try:
                subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                log.info(f"[Spotify] Launched via {exe}")
                return True
            except Exception as e:
                log.warning(f"[Spotify] EXE launch failed: {exe} — {e}")
    # Fallback: try URI scheme (handles AppX installs)
    try:
        subprocess.Popen(["start", "spotify:"], shell=True)
        log.info("[Spotify] Launched via URI scheme 'spotify:'")
        return True
    except Exception as e:
        log.warning(f"[Spotify] URI scheme launch failed: {e}")
    return False


def _activate_window(hwnd):
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        if win32gui.IsZoomed(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)
    rect = win32gui.GetWindowRect(hwnd)
    cx = (rect[0] + rect[2]) // 2
    cy = rect[1] + 10
    pyautogui.click(cx, cy)
    time.sleep(0.3)


def _focus_or_open_spotify():
    found = _find_spotify_window()
    if found:
        hwnd, _ = found
        _activate_window(hwnd)
        return True
    if not _launch_spotify():
        try:
            from system_app import open_app
            open_app("spotify")
        except Exception:
            return False
    time.sleep(6.0)
    found = _find_spotify_window()
    if not found:
        log.warning("[Spotify] Window not found after launch")
        return False
    _activate_window(found[0])
    return True


# ── Spotify Window Bounds ──

def _get_spotify_rect():
    found = _find_spotify_window()
    if not found:
        return None
    hwnd, _ = found
    try:
        return win32gui.GetWindowRect(hwnd)
    except Exception:
        return None


def _get_spotify_top_region():
    """Return region covering the play button zone (below the nav bar, above the track list).
    Skips the top 8% (header/nav bar) and captures a 20%-high strip.
    """
    rect = _get_spotify_rect()
    if not rect:
        return None
    left, top, right, bottom = rect
    w = right - left
    h = bottom - top
    return (left, top + int(h * 0.08), w, int(h * 0.20))


# ── Big Play Button: AI Vision ──

async def _click_big_play_ai_vision():
    """Use Gemini Vision on the full Spotify window to find the big green play button.
    Single-shot: click once, wait for playback, no destructive retry.
    """
    rect = _get_spotify_rect()
    if not rect:
        return False
    left, top, right, bottom = rect
    w, h = right - left, bottom - top
    if w < 200 or h < 100:
        return False
    try:
        import mss
        from screen_vision import analyze_screen
        capture = {"left": left, "top": top, "width": w, "height": h}
        with mss.mss() as sct:
            shot = sct.grab(capture)
            png_bytes = mss.tools.to_png(shot.rgb, shot.size)
        prompt = (
            "This is a screenshot of the Spotify Desktop window. "
            "At the top of the PAGE CONTENT area (below the header/navigation bar), "
            "there is a BIG green circular play button (white play triangle ▶ inside). "
            "There is also a SMALL play/pause button in the dark "
            "'now playing' bar at the very BOTTOM of the window — IGNORE IT COMPLETELY. "
            "Return ONLY the X,Y pixel coordinates of the BIG play button's center "
            "within this screenshot image. Format: 'X,Y'. No other text."
        )
        result = await analyze_screen(prompt=prompt, screenshot=png_bytes)
        if not result.get("success"):
            return False
        text = result.get("analysis", "").strip()
        # analyze_screen resizes to max 1024px — Gemini coords are in THAT space
        rw = result.get("width", w) or w
        rh = result.get("height", h) or h
        match = re.search(r'(\d{1,5})\s*,\s*(\d{1,5})', text)
        if match:
            img_x, img_y = int(match.group(1)), int(match.group(2))
            # Scale from resized-image coords → original window coords → absolute screen
            x = int(left + img_x * w / max(rw, 1))
            y = int(top + img_y * h / max(rh, 1))
            log.info(f"[Spotify] AI Vision big play -> click ({x}, {y}) (orig img {img_x},{img_y} scaled from {rw}x{rh} to {w}x{h})")
            pyautogui.click(x, y)
            time.sleep(1.5)
            _save_big_play_template(x, y)
            log.info("[Spotify] Click made, waiting for playback...")
            if _wait_for_playback(timeout=6.0):
                log.info("[Spotify] Playback confirmed via window title")
                return True
            log.info("[Spotify] Click didn't start playback, retrying click...")
            pyautogui.click(x, y)
            time.sleep(1.5)
            if _wait_for_playback(timeout=5.0):
                log.info("[Spotify] Playback confirmed on retry")
                return True
            log.info("[Spotify] Retry click failed, trying template match...")
            if _click_big_play_template():
                if _wait_for_playback(timeout=6.0):
                    log.info("[Spotify] Playback confirmed via template match")
                    return True
            log.info("[Spotify] All click methods failed, trying keyboard fallback...")
            return _keyboard_play()
        log.warning(f"[Spotify] AI Vision unparseable: {text[:80]}")
        return False
    except Exception as e:
        log.warning(f"[Spotify] AI Vision failed: {e}")
        return False


# ── Big Play Button: OpenCV Template Matching ──

def _save_big_play_template(x, y, size=24):
    """Save a tight region around click coords as an OpenCV template for the big play button."""
    try:
        region = (x - size // 2, y - size // 2, size, size)
        os.makedirs(os.path.dirname(_SPOTIFY_BIG_PLAY_TEMPLATE), exist_ok=True)
        capture_template(_SPOTIFY_BIG_PLAY_TEMPLATE, region)
        log.info(f"[Spotify] Auto-saved big play template at ({x},{y})")
    except Exception as e:
        log.warning(f"[Spotify] Failed to save big play template: {e}")


def _click_big_play_template():
    """Try OpenCV template matching to find the big green play button at the top of a page."""
    region = _get_spotify_top_region()
    if not region:
        return False
    point = find_on_screen(
        _SPOTIFY_BIG_PLAY_TEMPLATE,
        confidence=0.7,
        region=region
    )
    if point:
        log.info(f"[Spotify] Big play template match -> click ({point[0]}, {point[1]})")
        pyautogui.click(point[0], point[1])
        time.sleep(0.5)
        return True
    return False


# ── Playback Verification ──

def _is_playing():
    """Check if Spotify is currently playing by reading window title.
    A playing track shows 'Song - Artist' while a playlist page shows 'Playlist - Spotify'.
    We exclude playlist pages by checking the suffix.
    """
    found = _find_spotify_window()
    if not found:
        return False
    _, title = found
    title = title.strip()
    if title in ("Spotify", "Advertisement"):
        return False
    if title.lower().endswith(" - spotify"):
        return False
    if " - " in title \
       and not title.startswith(" - ") \
       and not title.endswith(" - ") \
       and len(title) > 10:
        return True
    return False


def _get_window_title():
    """Get current Spotify window title (used for recording play history)."""
    found = _find_spotify_window()
    if not found:
        return ""
    return found[1].strip()


# ── Single-Shot Play Methods ──

def _wait_for_playback(timeout=8.0):
    """Poll _is_playing() until playback starts or timeout. Returns True if confirmed."""
    for _ in range(int(timeout / 0.5)):
        time.sleep(0.5)
        if _is_playing():
            return True
    return False


def _keyboard_play():
    """Single-shot: press Home, Enter, Space to start playback."""
    log.info("[Spotify] Keyboard play attempt")
    pyautogui.press("home")
    time.sleep(0.3)
    pyautogui.press("enter")
    time.sleep(0.5)
    pyautogui.press("space")
    time.sleep(0.5)
    if _wait_for_playback(timeout=6.0):
        log.info("[Spotify] Playback confirmed via keyboard")
        return True
    log.warning("[Spotify] Keyboard play did not start playback")
    return False


def _maximize_soda():
    """Force SODA main window to foreground using Alt-key UIPI bypass.
    Tries multiple title patterns and fallback techniques.
    """
    if not _WIN32:
        return False

    def _bring_to_foreground(hwnd):
        """Try all foreground methods on one window handle."""
        try:
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if w < 200 or h < 100:
                return False
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.2)
        except Exception:
            return False

        # Method 1: Alt-key UIPI bypass + SetForegroundWindow
        try:
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
            time.sleep(0.1)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.15)
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
            time.sleep(0.1)
            if win32gui.GetForegroundWindow() == hwnd:
                return True
        except Exception:
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)

        # Method 2: SwitchToThisWindow (bypasses UIPI on most Windows versions)
        try:
            ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
            time.sleep(0.15)
            if win32gui.GetForegroundWindow() == hwnd:
                return True
        except Exception:
            pass

        # Method 3: BringWindowToTop + SetForegroundWindow
        try:
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.15)
            if win32gui.GetForegroundWindow() == hwnd:
                return True
        except Exception:
            pass

        return False

    patterns = ["soda core intelligence", "core intelligence", "soda"]
    for pattern in patterns:
        candidates = []
        def enum_cb(hwnd, _c):
            if win32gui.IsWindowVisible(hwnd):
                text = win32gui.GetWindowText(hwnd)
                if pattern in text.lower() and "file explorer" not in text.lower() and "explorer" not in text.lower():
                    _c.append(hwnd)
            return True
        win32gui.EnumWindows(enum_cb, candidates)
        for hwnd in candidates[:5]:
            if _bring_to_foreground(hwnd):
                log.info(f"[Spotify] SODA window brought to foreground (pattern='{pattern}')")
                return True

    log.warning("[Spotify] SODA main window not found")
    return False


# ── Search & Play ──

def _do_search(search_text):
    """Ctrl+K, type text, Down enters results list (selects first), Enter opens it."""
    pyautogui.hotkey("ctrl", "k")
    time.sleep(1.0)
    pyautogui.write(search_text, interval=0.05)
    time.sleep(2.5)
    pyautogui.press("down")
    time.sleep(0.8)
    pyautogui.press("enter")
    time.sleep(3.0)
    pyautogui.press("home")
    time.sleep(0.5)


def play_music(query):
    """Search music, open top result, click big play button (single-shot, no retry loops)."""
    if not _PYAUTOGUI:
        return {"success": False, "error": "PyAutoGUI not installed"}
    if not _WIN32:
        return {"success": False, "error": "win32api not available"}

    try:
        history_match = find_similar(query)
        search_text = history_match["title"] if history_match else query

        if not search_text or search_text.strip() == '':
            _focus_or_open_spotify()
            _maximize_soda()
            return {"success": True, "query": query, "note": "Spotify opened. What would you like to listen to?"}

        if not _focus_or_open_spotify():
            return {"success": False, "error": "Could not open Spotify. Is it installed?"}

        _do_search(search_text)

        import asyncio
        try:
            clicked = asyncio.run(_click_big_play_ai_vision())
        except Exception:
            clicked = False

        if clicked:
            record_play(query, _get_window_title())
            _maximize_soda()
            return {"success": True, "query": query}

        if _keyboard_play():
            record_play(query, _get_window_title())
            _maximize_soda()
            return {"success": True, "query": query}

        return {"success": False, "error": "Could not start playback after all methods"}
    except Exception as e:
        log.error(f"[Spotify] play_music failed: {e}")
        return {"success": False, "error": str(e)}


# ── Global Media Keys ──

def _send_media_key(vk_code):
    try:
        from ctypes import wintypes
        INPUT_KEYBOARD = 1
        KEYEVENTF_KEYUP = 0x0002

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [("wVk", wintypes.WORD),
                        ("wScan", wintypes.WORD),
                        ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD),
                        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

        class INPUT_UNION(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]

        class INPUT(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD),
                        ("union", INPUT_UNION)]

        input_down = INPUT()
        input_down.type = INPUT_KEYBOARD
        input_down.union.ki.wVk = vk_code
        input_down.union.ki.dwFlags = 0

        input_up = INPUT()
        input_up.type = INPUT_KEYBOARD
        input_up.union.ki.wVk = vk_code
        input_up.union.ki.dwFlags = KEYEVENTF_KEYUP

        ctypes.windll.user32.SendInput(1, ctypes.byref(input_down), ctypes.sizeof(input_down))
        time.sleep(0.02)
        ctypes.windll.user32.SendInput(1, ctypes.byref(input_up), ctypes.sizeof(input_up))
    except Exception as e:
        log.warning(f"[Spotify] media key 0x{vk_code:02X} failed: {e}")


def play_pause():
    _send_media_key(0xB3)


def next_track():
    _send_media_key(0xB0)


def previous_track():
    _send_media_key(0xB1)
