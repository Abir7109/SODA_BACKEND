"""
Spotify Desktop bridge for SODA.
Search & play music, global media key control (pause/next/prev).
Two-step flow: Enter opens top result, then click big play button at top of page.
"""

import os
import re
import json
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
from tool_abort import safe_sleep, check, AbortError

_SPOTIFY_BIG_PLAY_TEMPLATE = os.path.join(
    os.path.dirname(__file__), "vision_templates", "spotify_big_play.png"
)

_PLAY_BUTTON_CALIBRATION = os.path.join(
    os.path.dirname(__file__), "play_button_calibration.json"
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
    """Bring Spotify window to foreground by clicking its title bar.
    No Alt-key bypass — that triggers Spotify's menu bar and breaks Ctrl+K."""
    if win32gui.GetForegroundWindow() == hwnd:
        return True
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        safe_sleep(0.3)
    rect = win32gui.GetWindowRect(hwnd)
    if not rect:
        return False
    cx = (rect[0] + rect[2]) // 2
    cy = rect[1] + 10
    pyautogui.click(cx, cy)
    safe_sleep(0.5)
    return win32gui.GetForegroundWindow() == hwnd


def _within_spotify_bounds(x, y):
    """Check if (x,y) falls within the Spotify window (with a 50px margin).
    Returns True if we can safely click there. Prevents random desktop clicking."""
    rect = _get_spotify_rect()
    if not rect:
        return False
    left, top, right, bottom = rect
    margin = 50
    return (left + margin <= x <= right - margin and
            top + margin <= y <= bottom - margin)


def _click_play_area():
    """Click the big green play button on Spotify after navigating to a result page.
    The button is in the top-left content area: ~8-10% from left, ~18-22% from top.
    Only clicks if coordinates are within Spotify window bounds. Returns True if playback detected."""
    rect = _get_spotify_rect()
    if not rect:
        return False
    left, top, right, bottom = rect
    cx = left + int((right - left) * 0.10)
    cy = top + int((bottom - top) * 0.20)
    if not _within_spotify_bounds(cx, cy):
        log.warning(f"[Spotify] Play area click ({cx},{cy}) outside bounds — skipping")
        return False
    log.info(f"[Spotify] Clicking play area ({cx},{cy})")
    pyautogui.click(cx, cy)
    safe_sleep(1.0)
    if _wait_for_playback(timeout=5.0):
        log.info(f"[Spotify] Playback confirmed via area click ({cx},{cy})")
        return True
    return False


def _click_trained_play_button():
    """Click the play button using user-trained calibration from train_play_button.py.
    Method 0 (highest priority) — uses percentage offsets saved by the training script.
    Verifies playback started before returning True. Falls through if calibration
    file doesn't exist or playback isn't confirmed."""
    if not os.path.exists(_PLAY_BUTTON_CALIBRATION):
        return False
    try:
        with open(_PLAY_BUTTON_CALIBRATION) as f:
            cal = json.load(f)
    except Exception:
        return False
    x_pct = cal.get("x_pct")
    y_pct = cal.get("y_pct")
    if x_pct is None or y_pct is None:
        return False
    rect = _get_spotify_rect()
    if not rect:
        return False
    left, top, right, bottom = rect
    w, h = right - left, bottom - top
    cx = left + int(w * x_pct)
    cy = top + int(h * y_pct)
    if not _within_spotify_bounds(cx, cy):
        log.warning(f"[Spotify] Trained click ({cx},{cy}) outside bounds — skipping")
        return False
    log.info(f"[Spotify] Clicking trained play button ({cx},{cy}) at {x_pct*100:.1f}%,{y_pct*100:.1f}%")
    pyautogui.click(cx, cy)
    safe_sleep(2.0)
    check()
    if _wait_for_playback(timeout=8.0):
        log.info(f"[Spotify] Playback confirmed via trained click")
        return True
    log.warning(f"[Spotify] Trained click did not start playback")
    return False


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
    safe_sleep(6.0)
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
        log.info(f"[Spotify] AI Vision: screenshot={w}x{h}, calling analyze_screen...")
        result = await analyze_screen(prompt=prompt, screenshot=png_bytes)
        log.info(f"[Spotify] AI Vision analyze_screen result success={result.get('success')}")
        if not result.get("success"):
            log.warning(f"[Spotify] AI Vision API error: {result.get('error')}")
            return False
        text = result.get("analysis", "").strip()
        log.info(f"[Spotify] AI Vision raw response: {text[:120]}")
        # analyze_screen resizes to max 1024px — Gemini coords are in THAT space
        rw = result.get("width", w) or w
        rh = result.get("height", h) or h
        match = re.search(r'(\d{1,5})\s*,\s*(\d{1,5})', text)
        if match:
            img_x, img_y = int(match.group(1)), int(match.group(2))
            # Scale from resized-image coords → original window coords → absolute screen
            x = int(left + img_x * w / max(rw, 1))
            y = int(top + img_y * h / max(rh, 1))
            if not _within_spotify_bounds(x, y):
                log.warning(f"[Spotify] AI Vision click ({x},{y}) outside Spotify bounds — skipping")
                return False
            log.info(f"[Spotify] AI Vision big play -> click ({x}, {y}) (orig img {img_x},{img_y} scaled from {rw}x{rh} to {w}x{h})")
            pyautogui.click(x, y)
            safe_sleep(1.5)
            _save_big_play_template(x, y)
            log.info("[Spotify] Click made, waiting for playback...")
            if _wait_for_playback(timeout=6.0):
                log.info("[Spotify] Playback confirmed via window title")
                return True
            log.info("[Spotify] Click didn't start playback, retrying click...")
            if _within_spotify_bounds(x, y):
                pyautogui.click(x, y)
                safe_sleep(1.5)
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
        safe_sleep(0.5)
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
        safe_sleep(0.5)
        check()
        if _is_playing():
            return True
    return False


def _wait_for_navigation(timeout=8.0):
    """Wait for Spotify to navigate to a new page by monitoring window title changes.
    Returns True if title changed (page loaded), False on timeout."""
    prev_title = _get_window_title()
    for _ in range(int(timeout / 0.3)):
        safe_sleep(0.3)
        check()
        title = _get_window_title()
        if title and title != prev_title and title not in ("", "Spotify", "Advertisement"):
            return True
    return False


def _keyboard_play():
    """Navigate to big play via Tab→Enter. Falls back to Space and Ctrl+Shift+Down.
    Used as final fallback after simpler area-click and AI Vision methods."""
    log.info("[Spotify] Keyboard play attempt (Tab→Enter)")
    for i in range(6):
        pyautogui.press("tab")
        safe_sleep(0.15)
    pyautogui.press("enter")
    safe_sleep(0.8)
    if _wait_for_playback(timeout=5.0):
        log.info("[Spotify] Playback confirmed via Tab→Enter")
        return True
    # Space key (play/pause toggle on focused track)
    pyautogui.press("space")
    safe_sleep(0.8)
    if _wait_for_playback(timeout=5.0):
        log.info("[Spotify] Playback confirmed via Space")
        return True
    # Ctrl+Shift+Down (Spotify native play shortcut)
    pyautogui.hotkey("ctrl", "shift", "down")
    safe_sleep(1.0)
    if _wait_for_playback(timeout=5.0):
        log.info("[Spotify] Playback confirmed via Ctrl+Shift+Down")
        return True
    log.warning("[Spotify] All keyboard play methods failed")
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
                safe_sleep(0.2)
        except Exception:
            return False

        # Method 1: Alt-key UIPI bypass + SetForegroundWindow
        ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
        try:
            safe_sleep(0.1)
            win32gui.SetForegroundWindow(hwnd)
            safe_sleep(0.15)
        finally:
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
        safe_sleep(0.1)
        # Escape dismisses any menu triggered by the Alt keypress
        pyautogui.press("escape")
        safe_sleep(0.1)
        if win32gui.GetForegroundWindow() == hwnd:
            return True

        # Method 2: SwitchToThisWindow (bypasses UIPI on most Windows versions)
        try:
            ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
            safe_sleep(0.15)
            if win32gui.GetForegroundWindow() == hwnd:
                return True
        except Exception:
            pass

        # Method 3: BringWindowToTop + SetForegroundWindow
        try:
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
            safe_sleep(0.15)
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
    safe_sleep(1.0)
    pyautogui.write(search_text, interval=0.05)
    safe_sleep(2.5)
    pyautogui.press("down")
    safe_sleep(0.8)
    pyautogui.press("enter")
    safe_sleep(3.0)
    pyautogui.press("home")
    safe_sleep(0.5)


def _get_spotify_search_region():
    """Return region covering the search dropdown (below nav bar, ~top 8-55% of window)."""
    rect = _get_spotify_rect()
    if not rect:
        return None
    left, top, right, bottom = rect
    w = right - left
    h = bottom - top
    return {
        "left": left,
        "top": top + int(h * 0.08),
        "width": w,
        "height": int(h * 0.47),
    }


def search_music(query):
    """Search Spotify, extract visible results via AI Vision, return structured list.
    Does NOT auto-play — returns results for user selection.
    """
    if not _PYAUTOGUI or not _WIN32:
        return {"success": False, "error": "PyAutoGUI or win32 not available"}

    try:
        if not _focus_or_open_spotify():
            return {"success": False, "error": "Could not open Spotify"}

        # Escape clears any stray menu/focus before triggering search
        pyautogui.press("escape")
        safe_sleep(0.3)
        pyautogui.hotkey("ctrl", "k")
        safe_sleep(1.0)
        pyautogui.write(query, interval=0.05)
        safe_sleep(2.5)

        region = _get_spotify_search_region()
        if not region:
            return {"success": False, "error": "Could not get Spotify window region"}

        import mss
        from PIL import Image
        with mss.mss() as sct:
            shot = sct.grab(region)
            img = Image.frombytes("RGB", shot.size, shot.rgb)

        results = []
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

            skip_keywords = {"top result", "songs", "artists", "albums", "playlists", "podcasts", "genres", "profiles"}
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
        except ImportError:
            log.info("[Spotify] pytesseract not available — returning empty results")
        except Exception as e:
            log.warning(f"[Spotify] OCR failed: {e}")

        _maximize_soda()
        return {
            "success": True,
            "query": query,
            "results": results,
        }
    except Exception as e:
        log.error(f"[Spotify] search_music failed: {e}")
        return {"success": False, "error": str(e)}


def _ocr_click_search_result(index):
    """Use pytesseract OCR to find the Nth search result by Y position and click it.
    Skips header rows (Top result, Songs, Artists, etc.) to match search_music() indexing.
    Returns True if click was made."""
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

        skip_keywords = {"top result", "songs", "artists", "albums", "playlists", "podcasts", "genres", "profiles"}
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
            log.warning(f"[Spotify] OCR click: index {index} out of range (1-{len(sorted_rows)})")
            return False

        target_y = sorted_rows[index - 1][0]
        rect = _get_spotify_rect()
        if not rect:
            return False
        left, top, right, bottom = rect
        cx = left + int((right - left) * 0.25)
        cy = region["top"] + target_y + 8

        log.info(f"[Spotify] OCR click result {index}: '{sorted_rows[index-1][1]}' -> ({cx}, {cy})")
        pyautogui.click(cx, cy)
        if _wait_for_navigation(timeout=8.0):
            log.info(f"[Spotify] Navigation confirmed after OCR click")
        else:
            log.warning(f"[Spotify] Navigation timeout after OCR click — continuing anyway")
        return True
    except ImportError:
        log.info("[Spotify] pytesseract not available for OCR click navigation")
        return False
    except Exception as e:
        log.warning(f"[Spotify] OCR click navigation failed: {e}")
        return False


def play_music_result(query, index):
    """Play a specific search result from the already-visible Spotify dropdown.
    Does NOT re-search — the dropdown is still there from search_music().
    Only re-searches as fallback if OCR fails to find results.
    """
    if not _PYAUTOGUI or not _WIN32:
        return {"success": False, "error": "PyAutoGUI or win32 not available"}

    try:
        if not _focus_or_open_spotify():
            return {"success": False, "error": "Could not open Spotify"}

        # Escape clears any stray menu triggered by _maximize_soda() during search_music
        pyautogui.press("escape")
        safe_sleep(0.3)

        # Try to OCR-click from existing search dropdown (no re-search needed)
        clicked = _ocr_click_search_result(index)

        if not clicked:
            log.info("[Spotify] Existing dropdown not found — re-searching")
            pyautogui.hotkey("ctrl", "k")
            safe_sleep(1.0)
            pyautogui.write(query, interval=0.05)
            safe_sleep(2.5)
            if not _ocr_click_search_result(index):
                log.warning("[Spotify] OCR click navigation failed, falling back to keyboard navigation")
                for _ in range(index):
                    pyautogui.press("down")
                    safe_sleep(0.3)
                pyautogui.press("enter")
                safe_sleep(3.0)

        # Let the page fully render before attempting play
        safe_sleep(1.5)

        if _is_playing():
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            _maximize_soda()
            return {"success": True, "query": query, "now_playing": now_playing}

        # Method 0: User-trained play button calibration (highest priority)
        if _click_trained_play_button():
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            _maximize_soda()
            return {"success": True, "query": query, "now_playing": now_playing}

        # Method 1: Area click (10% left, 20% top — matches big green play button)
        if _click_play_area():
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            _maximize_soda()
            return {"success": True, "query": query, "now_playing": now_playing}

        # Method 2: OpenCV template matching (big green play button)
        if _click_big_play_template():
            safe_sleep(1.0)
            if _is_playing():
                now_playing = _get_now_playing()
                record_play(query, _get_window_title())
                _maximize_soda()
                return {"success": True, "query": query, "now_playing": now_playing}

        # Method 3: Keyboard Tab→Enter / Space / Ctrl+Shift+Down
        if _keyboard_play():
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            _maximize_soda()
            return {"success": True, "query": query, "now_playing": now_playing}

        # Method 4: AI Vision (last resort — slow, expensive)
        import asyncio
        try:
            clicked = asyncio.run(_click_big_play_ai_vision())
        except Exception:
            clicked = False
        if clicked:
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            _maximize_soda()
            return {"success": True, "query": query, "now_playing": now_playing}

        _maximize_soda()
        return {"success": False, "error": "Could not start playback"}
    except Exception as e:
        log.error(f"[Spotify] play_music_result failed: {e}")
        _maximize_soda()
        return {"success": False, "error": str(e)}


def _get_now_playing():
    """Parse 'Song - Artist' from Spotify window title. Returns dict or None."""
    title = _get_window_title()
    if not title or title in ("Spotify", "Advertisement") or title.lower().endswith(" - spotify"):
        return None
    if " - " in title and len(title) > 10:
        parts = title.split(" - ", 1)
        return {"track": parts[0].strip(), "artist": parts[1].strip()}
    return None


def play_music(query, emit_callback=None):
    """Search music, open top result, click big play button.
    Method priority: 1. area click (fast) 2. keyboard (reliable) 3. AI Vision (last resort).
    Returns {'success': True, 'query': query, 'now_playing': {...}} on success.
    """
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
            if emit_callback:
                emit_callback({"event": "status", "message": "Spotify opened. What would you like to listen to?"})
            return {"success": True, "query": query, "note": "Spotify opened. What would you like to listen to?"}

        if not _focus_or_open_spotify():
            return {"success": False, "error": "Could not open Spotify. Is it installed?"}

        _do_search(search_text)

        # Pre-playback check: many Spotify pages auto-play after search
        if _is_playing():
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            log.info(f"[Spotify] Already playing after search ({now_playing})")
            _maximize_soda()
            if emit_callback:
                emit_callback({"event": "now_playing", "data": now_playing or {"query": query}})
            return {"success": True, "query": query, "now_playing": now_playing}

        # Method 0: User-trained play button click (set via train_play_button.py)
        if _click_trained_play_button():
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            log.info(f"[Spotify] Playback via trained click")
            _maximize_soda()
            if emit_callback and now_playing:
                emit_callback({"event": "now_playing", "data": now_playing})
            return {"success": True, "query": query, "now_playing": now_playing}

        # Method 1: Simple area click (fast, no dependencies)
        if _click_play_area():
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            log.info(f"[Spotify] Playback via area click")
            _maximize_soda()
            if emit_callback and now_playing:
                emit_callback({"event": "now_playing", "data": now_playing})
            return {"success": True, "query": query, "now_playing": now_playing}

        # Method 2: Keyboard Tab→Enter / Space / Ctrl+Shift+Down
        if _keyboard_play():
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            log.info(f"[Spotify] Playback via keyboard")
            _maximize_soda()
            if emit_callback and now_playing:
                emit_callback({"event": "now_playing", "data": now_playing})
            return {"success": True, "query": query, "now_playing": now_playing}

        # Method 3: AI Vision (last resort — slow, expensive, can give wrong coords)
        import asyncio
        try:
            clicked = asyncio.run(_click_big_play_ai_vision())
        except Exception:
            clicked = False
        if clicked:
            now_playing = _get_now_playing()
            record_play(query, _get_window_title())
            log.info(f"[Spotify] Playback via AI Vision")
            _maximize_soda()
            if emit_callback and now_playing:
                emit_callback({"event": "now_playing", "data": now_playing})
            return {"success": True, "query": query, "now_playing": now_playing}

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
        safe_sleep(0.02)
        ctypes.windll.user32.SendInput(1, ctypes.byref(input_up), ctypes.sizeof(input_up))
    except Exception as e:
        log.warning(f"[Spotify] media key 0x{vk_code:02X} failed: {e}")


def play_pause():
    _send_media_key(0xB3)


def next_track():
    _send_media_key(0xB0)


def previous_track():
    _send_media_key(0xB1)
