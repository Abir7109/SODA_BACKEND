"""
Spotify workflow — sequential music playback with AI Vision.
Step-by-step: open → search (OCR for text) → AI Vision finds+clicks result → AI Vision finds+clicks play.
No coordinate math, no hardcoded Y positions, no destructive retry cascade.
"""

import os
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
from tool_abort import safe_sleep

from spotify_bridge import (
    _find_spotify_window,
    _launch_spotify,
    _is_playing,
    _get_window_title,
    _get_now_playing,
    _wait_for_playback,
    _wait_for_navigation,
    _click_big_play_ai_vision,
    _vision_find_and_click,
    _get_spotify_search_region,
)


# ── Step 1: Open / activate Spotify ──

def _step_open_spotify():
    """Bring Spotify to foreground. Uses SwitchToThisWindow + title-bar click."""
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
    point_hwnd = win32gui.WindowFromPoint((cx, cy))
    if point_hwnd != hwnd and not win32gui.IsChild(hwnd, point_hwnd):
        ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
        safe_sleep(0.3)
    pyautogui.click(cx, cy)
    safe_sleep(0.5)
    return win32gui.GetForegroundWindow() == hwnd


def _focus_spotify_quiet():
    """Bring Spotify to foreground WITHOUT clicking title bar.
    Preserves existing UI state (search dropdown, focus)."""
    found = _find_spotify_window()
    if not found:
        return _step_open_spotify()
    hwnd, _ = found
    if win32gui.GetForegroundWindow() == hwnd:
        return True
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        safe_sleep(0.3)
    try:
        ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
        safe_sleep(0.3)
    except Exception:
        pass
    return win32gui.GetForegroundWindow() == hwnd


# ── Step 2: Clear stale menu state ──

def _step_clear_menu():
    """Escape dismisses any stale menu/focus."""
    pyautogui.press("escape")
    safe_sleep(0.3)


# ── Step 3: Search ──

def _step_do_search(query):
    """Ctrl+K to open search bar, then type the query."""
    pyautogui.hotkey("ctrl", "k")
    safe_sleep(0.5)
    pyautogui.write(query, interval=0.05)
    safe_sleep(1.5)


# ── Step 4: OCR once, extract text for display ──

def _ocr_screenshot():
    """Take a screenshot of the search dropdown region and return PIL Image."""
    region = _get_spotify_search_region()
    if not region:
        return None, None
    import mss
    from PIL import Image
    with mss.mss() as sct:
        shot = sct.grab(region)
        img = Image.frombytes("RGB", shot.size, shot.rgb)
    return region, img


def _ocr_extract_rows(img):
    """Run pytesseract on image, return sorted list of (avg_y, line) tuples.
    Skips category headers (Top result, Songs, Artists, etc.)."""
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    binned = {}
    for i in range(len(data["text"])):
        txt = data["text"][i].strip()
        if not txt or int(data["conf"][i]) < 30:
            continue
        y = data["top"][i]
        row_key = round(y / 20) * 20
        binned.setdefault(row_key, []).append({
            "text": txt,
            "x": data["left"][i],
            "y": y,
        })

    skip_keywords = {"top result", "songs", "artists", "albums", "playlists",
                     "podcasts", "genres", "profiles"}
    sorted_rows = []
    for row_key in sorted(binned):
        words = binned[row_key]
        words.sort(key=lambda w: w["x"])
        line = " ".join(w["text"] for w in words).strip()
        if not line or len(line) < 2:
            continue
        if line.lower() in skip_keywords:
            continue
        avg_y = sum(w["y"] for w in words) // len(words)
        sorted_rows.append((avg_y, line))
    return sorted_rows


def _ocr_with_timeout(img):
    """Run _ocr_extract_rows with an 8s timeout guard."""
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_ocr_extract_rows, img)
        try:
            return future.result(timeout=8.0)
        except concurrent.futures.TimeoutError:
            log.warning("[Workflow] OCR timed out after 8s")
            return []


def _format_results(sorted_rows):
    """Convert OCR rows to the result list format for frontend display."""
    results = []
    for avg_y, line in sorted_rows:
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
        results.append({"index": len(results) + 1, "title": line, "type": result_type})
    return results


# ── Step 5: AI Vision — find and click Nth search result ──

def _step_vision_click_result(index, query):
    """Use AI Vision to find and click the Nth search result in the Spotify search dropdown."""
    import asyncio
    loop = _get_or_create_eventloop()
    try:
        return loop.run_until_complete(_vision_find_and_click(index, query))
    except Exception as e:
        log.error(f"[Workflow] Vision click result failed: {e}")
        return False


# ── Step 6: AI Vision — find and click play button ──

def _step_vision_play():
    """Use AI Vision to find the big green play button."""
    if _is_playing():
        return True
    import asyncio
    loop = _get_or_create_eventloop()
    try:
        return loop.run_until_complete(_click_big_play_ai_vision())
    except Exception as e:
        log.error(f"[Workflow] Vision play failed: {e}")
        return False


def _get_or_create_eventloop():
    """Get current event loop or create a new one for async Vision calls."""
    import asyncio
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


# ── Clean SODA foreground ──

def _step_return_to_soda():
    """Bring SODA window to foreground WITHOUT using Alt-key."""
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
                    return
            except Exception:
                continue


# ── Main workflow: search_music ──

def search_music(query):
    """Open Spotify → search → OCR → return results as text.
    No Y-coordinate caching — AI Vision handles clicking in play_music_result."""
    if not _PYAUTOGUI or not _WIN32:
        return {"success": False, "error": "PyAutoGUI or win32 not available"}

    try:
        if not _step_open_spotify():
            return {"success": False, "error": "Could not open Spotify"}

        _step_clear_menu()
        _step_do_search(query)

        region, img = _ocr_screenshot()
        if not region:
            return {"success": True, "query": query, "results": []}

        sorted_rows = _ocr_with_timeout(img)
        results = _format_results(sorted_rows)
        return {"success": True, "query": query, "results": results}
    except Exception as e:
        log.error(f"[Workflow] search_music failed: {e}")
        return {"success": False, "error": str(e)}


# ── Main workflow: play_music_result ──

def play_music_result(query, index):
    """Use AI Vision to find and click Nth search result → navigate → find and click play button.
    No cached coordinates, no OCR-based clicking, no destructive retry cascade."""
    if not _PYAUTOGUI or not _WIN32:
        return {"success": False, "error": "PyAutoGUI or win32 not available"}

    try:
        # Quiet focus — no title-bar click (preserves search dropdown state)
        if not _focus_spotify_quiet():
            return {"success": False, "error": "Could not focus Spotify"}

        result = {"success": True, "query": query, "clicked": True}

        # Step 1: AI Vision finds and clicks the Nth search result
        if not _step_vision_click_result(index, query):
            log.warning("[Workflow] AI Vision could not find result — trying full search fallback")
            # Fallback: re-search and try again
            if not _focus_spotify_quiet():
                return {"success": False, "error": "Could not focus Spotify"}
            _step_do_search(query)
            safe_sleep(1.0)
            if not _step_vision_click_result(index, query):
                result["playback"] = "pending"
                result["success"] = False
                result["error"] = "AI Vision could not find the search result"
                _step_return_to_soda()
                return result

        # Step 2: Wait for navigation
        safe_sleep(1.5)

        # Step 3: Check if playback started automatically
        if _is_playing():
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            result["now_playing"] = now_playing
            _step_return_to_soda()
            return result

        # Step 4: AI Vision finds and clicks the big green play button
        if _step_vision_play():
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            result["now_playing"] = now_playing
            _step_return_to_soda()
            return result

        result["playback"] = "pending"
        _step_return_to_soda()
        return result

    except Exception as e:
        log.error(f"[Workflow] play_music_result failed: {e}")
        return {"success": False, "error": str(e)}
