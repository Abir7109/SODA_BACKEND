"""
Spotify workflow — sequential 6-step music playback.
Step-by-step: open → clear menu → search → show results → click result → play.
NO Alt-key bypass anywhere (triggers Spotify menu bar).
Clean separation from spotify_bridge.py (which remains as fallback).
"""

import os
import re
import json
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
from play_history import record_play
from tool_abort import safe_sleep, check

# Reuse play-method helpers and constants from spotify_bridge
from spotify_bridge import (
    _find_spotify_window,
    _launch_spotify,
    _is_playing,
    _get_window_title,
    _get_now_playing,
    _wait_for_playback,
    _wait_for_navigation,
    _click_trained_play_button,
    _click_play_area,
    _click_big_play_template,
    _click_big_play_ai_vision,
    _keyboard_play,
    _get_spotify_search_region,
    _within_spotify_bounds,
)


# ── Step 1: Open / activate Spotify ──

def _step_open_spotify():
    """Bring Spotify to foreground. Uses SwitchToThisWindow + title-bar click.
    No Alt-key — that triggers Spotify's menu bar and breaks subsequent Ctrl+K."""
    found = _find_spotify_window()
    if found:
        hwnd, _ = found
        return _activate_spotify_window(hwnd)

    if not _launch_spotify():
        try:
            from system_app import open_app
            open_app("spotify")
        except Exception:
            log.error("[Workflow] Could not launch Spotify")
            return False

    safe_sleep(6.0)
    found = _find_spotify_window()
    if not found:
        log.error("[Workflow] Spotify window not found after launch")
        return False
    return _activate_spotify_window(found[0])


def _activate_spotify_window(hwnd):
    """Elevate Spotify to top of Z-order, then click title bar to activate."""
    if win32gui.GetForegroundWindow() == hwnd:
        return True

    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        safe_sleep(0.3)

    # Bring to top of Z-order so title-bar click lands on Spotify
    try:
        ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
        safe_sleep(0.3)
    except Exception:
        pass

    rect = win32gui.GetWindowRect(hwnd)
    if not rect:
        return False
    cx = (rect[0] + rect[2]) // 2
    cy = rect[1] + 10

    # Verify click target before clicking
    point_hwnd = win32gui.WindowFromPoint((cx, cy))
    if point_hwnd != hwnd and not win32gui.IsChild(hwnd, point_hwnd):
        ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
        safe_sleep(0.3)

    pyautogui.click(cx, cy)
    safe_sleep(0.5)
    return win32gui.GetForegroundWindow() == hwnd


# ── Step 2: Clear stale menu state ──

def _step_clear_menu():
    """Escape dismisses any stale menu/focus (e.g., from _maximize_soda Alt-key)."""
    pyautogui.press("escape")
    safe_sleep(0.3)


# ── Step 3: Search ──

def _step_do_search(query):
    """Ctrl+K to open search bar, then type the query."""
    pyautogui.hotkey("ctrl", "k")
    safe_sleep(0.5)
    pyautogui.write(query, interval=0.05)
    safe_sleep(1.5)


# ── Step 4: Extract search results via OCR ──

def _ocr_group(img):
    """Run tesseract OCR on image and group results into structured rows.
    Raises on failure; caller handles timeout."""
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    rows = {}
    for i in range(len(data["text"])):
        txt = data["text"][i].strip()
        if not txt or int(data["conf"][i]) < 30:
            continue
        y = data["top"][i]
        row_key = round(y / 20) * 20
        rows.setdefault(row_key, []).append({
            "text": txt,
            "x": data["left"][i],
            "y": y,
        })

    skip_keywords = {"top result", "songs", "artists", "albums", "playlists",
                     "podcasts", "genres", "profiles"}
    results = []
    for row_key in sorted(rows):
        words = rows[row_key]
        words.sort(key=lambda w: w["x"])
        line = " ".join(w["text"] for w in words).strip()
        if not line or len(line) < 2:
            continue
        if line.lower() in skip_keywords:
            continue

        title = line
        result_type = "result"
        lower = line.lower()
        if any(k in lower for k in ("song", "single")):
            result_type = "song"
        elif any(k in lower for k in ("artist", "artists")):
            result_type = "artist"
        elif any(k in lower for k in ("album", "ep")):
            result_type = "album"
        elif any(k in lower for k in ("playlist", "radio")):
            result_type = "playlist"
        elif any(k in lower for k in ("podcast", "episode", "show")):
            result_type = "podcast"

        results.append({"index": len(results) + 1, "title": title, "type": result_type})
    return results


def _step_extract_results():
    """Screenshot the search dropdown region, run pytesseract OCR,
    group by Y-position, skip headers, return structured result list.
    OCR runs with a timeout guard so slow tesseract doesn't hang the agent."""
    region = _get_spotify_search_region()
    if not region:
        return []

    import mss
    from PIL import Image
    with mss.mss() as sct:
        shot = sct.grab(region)
        img = Image.frombytes("RGB", shot.size, shot.rgb)

    try:
        import pytesseract
    except ImportError:
        log.info("[Workflow] pytesseract not available")
        return []

    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_ocr_group, img)
            return future.result(timeout=8.0)
    except concurrent.futures.TimeoutError:
        log.warning("[Workflow] OCR timed out after 8s")
        return []
    except Exception as e:
        log.warning(f"[Workflow] OCR failed: {e}")
        return []


# ── Step 5: Click a specific search result by index ──

def _step_click_result(index):
    """OCR the search dropdown and click the Nth non-header result.
    If dropdown isn't visible, opens search first."""
    region = _get_spotify_search_region()
    if not region:
        return False

    import mss
    from PIL import Image
    with mss.mss() as sct:
        shot = sct.grab(region)
        img = Image.frombytes("RGB", shot.size, shot.rgb)

    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        rows = {}
        for i in range(len(data["text"])):
            txt = data["text"][i].strip()
            if not txt or int(data["conf"][i]) < 30:
                continue
            y = data["top"][i]
            row_key = round(y / 20) * 20
            rows.setdefault(row_key, []).append({
                "text": txt,
                "x": data["left"][i],
                "y": y,
            })

        skip_keywords = {"top result", "songs", "artists", "albums", "playlists",
                         "podcasts", "genres", "profiles"}
        sorted_rows = []
        for row_key in sorted(rows):
            words = rows[row_key]
            words.sort(key=lambda w: w["x"])
            line = " ".join(w["text"] for w in words).strip()
            if not line or len(line) < 2:
                continue
            if line.lower() in skip_keywords:
                continue
            avg_y = sum(w["y"] for w in words) // len(words)
            sorted_rows.append((avg_y, line))

        if index < 1 or index > len(sorted_rows):
            log.warning(f"[Workflow] OCR click: index {index} out of range (1-{len(sorted_rows)})")
            return False

        target_y = sorted_rows[index - 1][0]
        rect = _get_spotify_window_rect()
        if not rect:
            return False
        left, top, right, bottom = rect
        cx = left + int((right - left) * 0.25)
        cy = region["top"] + target_y + 8

        log.info(f"[Workflow] OCR click result {index}: '{sorted_rows[index-1][1]}' -> ({cx}, {cy})")
        pyautogui.click(cx, cy)
        if _wait_for_navigation(timeout=8.0):
            log.info("[Workflow] Navigation confirmed after OCR click")
        else:
            log.warning("[Workflow] Navigation timeout — continuing anyway")
        return True
    except ImportError:
        log.info("[Workflow] pytesseract not available")
        return False
    except Exception as e:
        log.warning(f"[Workflow] OCR click failed: {e}")
        return False


def _get_spotify_window_rect():
    """Get Spotify window bounding rectangle."""
    found = _find_spotify_window()
    if not found:
        return None
    try:
        return win32gui.GetWindowRect(found[0])
    except Exception:
        return None


# ── Step 6: Play ──

def _step_play():
    """Attempt to start playback using methods in priority order.
    Returns True if playback confirmed."""
    if _is_playing():
        return True

    # Method 0: User-trained calibration
    if _click_trained_play_button():
        return True

    # Method 1: Area click at big green play button position
    if _click_play_area():
        return True

    # Method 2: OpenCV template matching
    if _click_big_play_template():
        safe_sleep(1.0)
        if _is_playing():
            return True

    # Method 3: Keyboard Tab→Enter / Space / Ctrl+Shift+Down
    if _keyboard_play():
        return True

    # Method 4: AI Vision (last resort)
    import asyncio
    try:
        if asyncio.run(_click_big_play_ai_vision()):
            return True
    except Exception:
        pass

    return False


# ── Clean SODA foreground (no Alt-key) ──

def _step_return_to_soda():
    """Bring SODA window to foreground WITHOUT using Alt-key.
    Uses SwitchToThisWindow instead — avoids triggering Spotify's menu bar."""
    if not _WIN32:
        return

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
            try:
                ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
                safe_sleep(0.2)
                if win32gui.GetForegroundWindow() == hwnd:
                    log.info(f"[Workflow] SODA foreground via SwitchToThisWindow (pattern='{pattern}')")
                    return
            except Exception:
                continue


# ── Main workflow: search_music ──

def search_music(query):
    """Step 1-4: open Spotify → clear menu → search → extract results.
    Returns {success, query, results}. Does NOT auto-play."""
    if not _PYAUTOGUI or not _WIN32:
        return {"success": False, "error": "PyAutoGUI or win32 not available"}

    try:
        if not _step_open_spotify():
            return {"success": False, "error": "Could not open Spotify"}

        _step_clear_menu()
        _step_do_search(query)

        results = _step_extract_results()

        _step_return_to_soda()
        return {"success": True, "query": query, "results": results}
    except Exception as e:
        log.error(f"[Workflow] search_music failed: {e}")
        return {"success": False, "error": str(e)}


# ── Main workflow: play_music_result ──

def play_music_result(query, index):
    """Step 1-2-5-6: open Spotify → clear menu → click Nth result → play.
    Only re-searches if existing dropdown is gone (fallback).
    Calls _step_return_to_soda() once at the very end."""
    if not _PYAUTOGUI or not _WIN32:
        return {"success": False, "error": "PyAutoGUI or win32 not available"}

    try:
        if not _step_open_spotify():
            return {"success": False, "error": "Could not open Spotify"}

        _step_clear_menu()

        # Try to click from existing search dropdown (no re-search)
        if not _step_click_result(index):
            log.info("[Workflow] Existing dropdown not found — re-searching")
            _step_do_search(query)
            if not _step_click_result(index):
                log.warning("[Workflow] OCR click failed, trying keyboard fallback")
                for _ in range(index):
                    pyautogui.press("down")
                    safe_sleep(0.3)
                pyautogui.press("enter")
                safe_sleep(3.0)

        # Let the page fully render
        safe_sleep(1.5)

        if _is_playing():
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            _step_return_to_soda()
            return {"success": True, "query": query, "now_playing": now_playing}

        if _step_play():
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            _step_return_to_soda()
            return {"success": True, "query": query, "now_playing": now_playing}

        _step_return_to_soda()
        return {"success": False, "error": "Could not start playback"}
    except Exception as e:
        log.error(f"[Workflow] play_music_result failed: {e}")
        return {"success": False, "error": str(e)}
