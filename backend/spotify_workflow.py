"""
Spotify workflow — sequential music playback.
Step-by-step: open → search (OCR once) → cache rows → click cached row → play.
NO re-OCR, NO re-search in play_music_result. Uses cached Y positions from search_music.
NO title-bar click in play_music_result (preserves search dropdown).
NO Alt-key anywhere (triggers Spotify menu bar).
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

from spotify_bridge import (
    _find_spotify_window,
    _launch_spotify,
    _is_playing,
    _get_window_title,
    _get_now_playing,
    _wait_for_playback,
    _wait_for_navigation,
    _click_play_area,
    _keyboard_play,
    _get_spotify_search_region,
    _get_spotify_rect,
    _within_spotify_bounds,
)

# ── Module-level cache: OCR rows from the last search_music() call ──
# Each entry: {"y": int, "line": str, "region_top": int}
_cached_rows = []
_cached_query = ""


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
    Preserves any existing UI state (search dropdown, focus).
    Only called from play_music_result where activation is not needed."""
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


# ── Step 4: OCR once, cache rows ──

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


# ── Step 5: Click a cached search result by index (NO RE-OCR) ──

def _click_cached_row(index, region_top):
    """Click the Nth search result using cached OCR row data.
    Uses the stored Y position directly — no screenshot, no OCR.
    """
    global _cached_rows
    if index < 1 or index > len(_cached_rows):
        log.warning(f"[Workflow] Cached click: index {index} out of range (1-{len(_cached_rows)})")
        return False

    target_y = _cached_rows[index - 1][0]
    rect = _get_spotify_rect()
    if not rect:
        return False
    left, top, right, bottom = rect
    cx = left + int((right - left) * 0.50)
    cy = region_top + target_y + 8

    log.info(f"[Workflow] Cached click result {index}: '{_cached_rows[index-1][1]}' -> ({cx}, {cy})")
    pyautogui.click(cx, cy)
    if _wait_for_navigation(timeout=8.0):
        log.info("[Workflow] Navigation confirmed after cached click")
    else:
        log.warning("[Workflow] Navigation timeout — continuing anyway")
    return True


def _keyboard_select_result(index):
    """Keyboard fallback: press Down N times + Enter to select Nth result.
    Adds +2 offset for Top result + first category header."""
    kb_offset = index + 2
    for _ in range(kb_offset):
        pyautogui.press("down")
        safe_sleep(0.3)
    pyautogui.press("enter")
    safe_sleep(3.0)


# ── Step 6: Play ──

def _step_play():
    """Try to start playback. Area click first (with 2 Y-position tries),
    then keyboard shortcuts. Max 2 methods, no random cascading."""
    if _is_playing():
        return True

    log.info("[Workflow] Play: area click at 10%/20%")
    if _click_play_area():
        log.info("[Workflow] Playback confirmed via area click")
        return True

    log.info("[Workflow] Play: keyboard shortcuts")
    if _keyboard_play():
        log.info("[Workflow] Playback confirmed via keyboard")
        return True

    log.warning("[Workflow] Play methods exhausted — returning")
    return False


# ── Clean SODA foreground (no Alt-key) ──

def _step_return_to_soda():
    """Bring SODA window to foreground WITHOUT using Alt-key.
    Uses SwitchToThisWindow — avoids triggering Spotify's menu bar."""
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
    """Open Spotify → search → OCR once → cache rows → return results.
    Does NOT auto-play. Caches OCR row data for play_music_result to use directly."""
    global _cached_rows, _cached_query

    if not _PYAUTOGUI or not _WIN32:
        return {"success": False, "error": "PyAutoGUI or win32 not available"}

    try:
        if not _step_open_spotify():
            return {"success": False, "error": "Could not open Spotify"}

        _step_clear_menu()
        _step_do_search(query)

        region, img = _ocr_screenshot()
        if not region:
            _cached_rows = []
            return {"success": True, "query": query, "results": []}

        sorted_rows = _ocr_with_timeout(img)

        # Cache the full OCR data (Y positions + region) for play_music_result
        _cached_rows = sorted_rows
        _cached_query = query
        _cached_region_top = region["top"]

        results = _format_results(sorted_rows)
        return {"success": True, "query": query, "results": results}
    except Exception as e:
        log.error(f"[Workflow] search_music failed: {e}")
        return {"success": False, "error": str(e)}


# Module-level cache for region top (set by search_music, read by play_music_result)
_cached_region_top = 0


# ── Main workflow: play_music_result ──

def play_music_result(query, index):
    """Click Nth search result from cache → navigate → play.
    Uses cached OCR rows from the search_music() call.
    No re-OCR, no re-search, no title-bar click on Spotify activation.
    """
    global _cached_rows, _cached_query, _cached_region_top

    if not _PYAUTOGUI or not _WIN32:
        return {"success": False, "error": "PyAutoGUI or win32 not available"}

    try:
        # Quiet focus — no title-bar click (preserves search dropdown)
        if not _focus_spotify_quiet():
            return {"success": False, "error": "Could not focus Spotify"}

        result = {"success": True, "query": query, "clicked": True}

        # Use cached rows from search_music() to click directly
        if _cached_rows and _cached_query == query:
            if _click_cached_row(index, _cached_region_top):
                safe_sleep(1.5)
                # Playback may start automatically after navigation
                if _is_playing():
                    now_playing = _get_now_playing()
                    record_play(query, _get_window_title())
                    result["now_playing"] = now_playing
                    _step_return_to_soda()
                    return result
                if _step_play():
                    now_playing = _get_now_playing()
                    record_play(query, _get_window_title())
                    result["now_playing"] = now_playing
                    _step_return_to_soda()
                    return result
                result["playback"] = "pending"
                _step_return_to_soda()
                return result
            else:
                log.warning("[Workflow] Cached click failed — index mismatch")
        else:
            log.info(f"[Workflow] No cache for query '{query}' — doing full search+click")

        # Fallback: full search + OCR click (cache miss or mismatch)
        if not _focus_spotify_quiet():
            return {"success": False, "error": "Could not focus Spotify"}

        _step_do_search(query)
        region, img = _ocr_screenshot()
        if region:
            sorted_rows = _ocr_with_timeout(img)
            # Temporarily overwrite cache for this attempt
            _cached_rows = sorted_rows
            _cached_query = query
            _cached_region_top = region["top"]
            if _click_cached_row(index, _cached_region_top):
                safe_sleep(1.5)
                if _is_playing():
                    now_playing = _get_now_playing()
                    record_play(query, _get_window_title())
                    result["now_playing"] = now_playing
                    _step_return_to_soda()
                    return result
                if _step_play():
                    now_playing = _get_now_playing()
                    record_play(query, _get_window_title())
                    result["now_playing"] = now_playing
                    _step_return_to_soda()
                    return result
                result["playback"] = "pending"
                _step_return_to_soda()
                return result

        # Last-resort: keyboard select
        log.warning("[Workflow] All click methods failed — keyboard fallback")
        _keyboard_select_result(index)
        safe_sleep(1.5)
        if _is_playing():
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            result["now_playing"] = now_playing
        elif _step_play():
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            result["now_playing"] = now_playing
        else:
            result["playback"] = "pending"
        _step_return_to_soda()
        return result

    except Exception as e:
        log.error(f"[Workflow] play_music_result failed: {e}")
        return {"success": False, "error": str(e)}
