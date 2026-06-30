"""
WhatsApp Desktop bridge for SODA.
Three-tier button detection:
  1. uiautomation (finds buttons by UIA name — most reliable)
  2. AI Vision on cropped window (Gemini sees only the WhatsApp area)
  3. Coordinate fallback (window-relative)

Contact search clicks the search bar, types name, clicks first result.
"""

import re
import time
import asyncio

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

try:
    import uiautomation as auto
    _UIA = True
except ImportError:
    _UIA = False

from logger import log

TYPE_INTERVAL = 0.06


def _require_pyautogui():
    if not _PYAUTOGUI:
        raise RuntimeError("pyautogui not available. Install with: pip install pyautogui")


def _require_win32():
    if not _WIN32:
        raise RuntimeError("win32api not available. Install with: pip install pywin32")


_BROWSER_KEYWORDS = {"chrome", "firefox", "edge", "opera", "brave", "mozilla", "internet explorer"}


def _find_whatsapp_window():
    """Find the WhatsApp Desktop window, skipping browser windows with web.whatsapp.com."""
    _require_win32()
    matches = []
    def enum_cb(hwnd, _matches):
        if win32gui.IsWindowVisible(hwnd):
            text = win32gui.GetWindowText(hwnd)
            if "whatsapp" in text.lower():
                for bk in _BROWSER_KEYWORDS:
                    if bk in text.lower():
                        return True
                _matches.append((hwnd, text))
        return True
    win32gui.EnumWindows(enum_cb, matches)
    return matches[0] if matches else None


def _get_window_rect():
    found = _find_whatsapp_window()
    if not found:
        return None
    hwnd, _ = found
    try:
        return win32gui.GetWindowRect(hwnd)
    except Exception:
        return None


def _focus_whatsapp():
    """Bring WhatsApp window to foreground. Returns True if window was found."""
    found = _find_whatsapp_window()
    if not found:
        log.warning("[WA] WhatsApp window not found")
        return False
    hwnd, title = found
    log.info(f"[WA] Focusing window: '{title}'")
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.2)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.8)
    return True


def _focus_or_open_whatsapp():
    """Focus existing WhatsApp window or launch it. Returns True on success."""
    if _focus_whatsapp():
        return True
    try:
        from system_app import open_app
        result = open_app("whatsapp")
        time.sleep(4.0)
        if _focus_whatsapp():
            return True
        log.warning(f"[WA] open_app result: {result}")
        return False
    except Exception as e:
        log.error(f"[WA] Failed to launch WhatsApp: {e}")
        return False


def _click_search_bar():
    """Click the search bar at the top of WhatsApp's left panel using window-relative coords."""
    rect = _get_window_rect()
    if not rect:
        log.warning("[WA] Cannot get window rect for search bar click")
        return False
    left, top, right, bottom = rect
    win_w = right - left
    search_x = left + int(win_w * 0.16)
    search_y = top + 30
    log.info(f"[WA] Clicking search bar at ({search_x}, {search_y})")
    pyautogui.click(search_x, search_y)
    time.sleep(0.8)
    return True


def _click_new_chat_button():
    """Click the new chat (pencil) button at the top-left of WhatsApp."""
    rect = _get_window_rect()
    if not rect:
        return False
    left, top, right, bottom = rect
    x = left + 40
    y = top + 30
    log.info(f"[WA] Clicking new chat button at ({x}, {y})")
    pyautogui.click(x, y)
    time.sleep(0.8)
    return True


def _click_first_search_result():
    """Click the first contact in the search results list."""
    rect = _get_window_rect()
    if not rect:
        return False
    left, top, right, bottom = rect
    win_w = right - left
    result_x = left + int(win_w * 0.16)
    result_y = top + 100
    log.info(f"[WA] Clicking first search result at ({result_x}, {result_y})")
    pyautogui.click(result_x, result_y)
    time.sleep(1.0)
    return True


def _focus_message_input():
    """Click the message input area at the bottom of the chat."""
    rect = _get_window_rect()
    if not rect:
        return False
    left, top, right, bottom = rect
    win_w = right - left
    win_h = bottom - top
    msg_x = left + int(win_w * 0.6)
    msg_y = bottom - 50
    log.info(f"[WA] Clicking message input at ({msg_x}, {msg_y})")
    pyautogui.click(msg_x, msg_y)
    time.sleep(0.5)
    return True


def _send_whatsapp_message(contact_name, message):
    """
    Full flow: focus WhatsApp, search contact, type message, send.
    Uses click-based navigation with shortcut fallbacks.
    """
    _require_pyautogui()

    # ── Step 1: Focus / open WhatsApp ──
    log.info("[WA] Step 1: Focusing WhatsApp")
    if not _focus_or_open_whatsapp():
        return {"success": False, "error": "Could not open WhatsApp Desktop"}

    # ── Step 2: Click search bar and type contact name ──
    log.info(f"[WA] Step 2: Searching for '{contact_name}'")
    _click_search_bar()
    pyautogui.write(contact_name, interval=TYPE_INTERVAL)
    time.sleep(1.5)

    # ── Step 3: Click first result ──
    log.info("[WA] Step 3: Selecting first contact result")
    _click_first_search_result()
    time.sleep(1.0)

    # ── Step 4: Click message input and type ──
    log.info("[WA] Step 4: Typing message")
    _focus_message_input()
    pyautogui.write(message, interval=TYPE_INTERVAL)
    time.sleep(0.3)

    # ── Step 5: Send ──
    log.info("[WA] Step 5: Sending")
    pyautogui.press("enter")
    time.sleep(0.5)

    log.info(f"[WA] Message sent to '{contact_name}': {message[:60]}")
    return {"success": True, "action": "message", "contact": contact_name}


# ── Old shortcut-based contact search (kept as fallback) ──
def _search_contact_pyautogui(contact_name):
    _require_pyautogui()
    log.info(f"[WA] Fallback: Ctrl+N search for '{contact_name}'")
    pyautogui.hotkey("ctrl", "n")
    time.sleep(0.8)
    pyautogui.write(contact_name, interval=TYPE_INTERVAL)
    time.sleep(1.5)
    pyautogui.press("enter")
    time.sleep(1.5)
    return True


def _search_contact_uia(contact_name):
    if not _UIA:
        return False
    try:
        wa = auto.WindowControl(searchDepth=1, Name="WhatsApp")
        if not wa.Exists(0, 0):
            return False
        wa.SetActive()
        time.sleep(0.3)
        log.info(f"[WA] uiautomation focused WhatsApp window")
        return True
    except Exception as e:
        log.warning(f"[WA] uia focus failed: {e}")
        return False


def _click_call_uia():
    if not _UIA:
        return False
    try:
        wa = auto.WindowControl(searchDepth=1, Name="WhatsApp")
        if not wa.Exists(0, 0):
            return False
        for btn_name in ("Voice call", "Call", "Voice Call", "Audio call"):
            btn = wa.ButtonControl(Name=btn_name)
            if btn.Exists(0, 0):
                btn.Click()
                time.sleep(0.3)
                log.info(f"[WA] uiautomation clicked '{btn_name}'")
                return True
        return False
    except Exception as e:
        log.warning(f"[WA] uiautomation call button failed: {e}")
        return False


async def _click_call_ai_vision():
    rect = _get_window_rect()
    if not rect:
        return False
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    if width < 100 or height < 100:
        return False
    try:
        import mss
        from screen_vision import analyze_screen
        with mss.mss() as sct:
            monitor = {"left": left, "top": top, "width": width, "height": height}
            screenshot = sct.grab(monitor)
            png_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)
        prompt = (
            "This is a screenshot of WhatsApp Desktop with a chat open. "
            "In the chat header at the top of the right panel, there is a "
            "voice call button (phone handset icon). "
            "Return ONLY the x,y pixel coordinates of its center "
            "on the FULL SCREEN (not relative to this crop). "
            "Format: 'X,Y' — example: '971,58'. No other text."
        )
        result = await analyze_screen(prompt=prompt, screenshot=png_bytes)
        if not result.get("success"):
            return False
        text = result.get("analysis", "").strip()
        match = re.search(r'(\d{1,5})\s*,\s*(\d{1,5})', text)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            log.info(f"[WA] AI Vision cropped -> click ({x}, {y})")
            pyautogui.click(x, y)
            time.sleep(0.3)
            return True
        log.warning(f"[WA] AI Vision unparseable: {text[:80]}")
        return False
    except Exception as e:
        log.warning(f"[WA] AI Vision failed: {e}")
        return False


def _click_call_fallback():
    rect = _get_window_rect()
    if not rect:
        return False
    left, top, right, bottom = rect
    x = right - 55
    y = top + 38
    pyautogui.click(x, y)
    time.sleep(0.3)
    log.info(f"[WA] Coordinate fallback click at ({x}, {y})")
    return True


async def _click_call_button():
    if _click_call_uia():
        return True
    log.info("[WA] uiautomation failed, trying AI Vision...")
    try:
        if await _click_call_ai_vision():
            return True
    except Exception as e:
        log.warning(f"[WA] AI Vision failed: {e}")
    log.info("[WA] AI Vision failed, trying coordinate fallback...")
    return _click_call_fallback()


async def call_contact(contact_name):
    """Search a contact in WhatsApp Desktop and initiate a voice call."""
    if not _PYAUTOGUI:
        return {"success": False, "error": "PyAutoGUI not installed"}
    if not _WIN32:
        return {"success": False, "error": "win32api not available"}
    try:
        if not _focus_or_open_whatsapp():
            return {"success": False, "error": "Could not open WhatsApp Desktop. Is it installed?"}
        _focus_whatsapp()
        _search_contact_pyautogui(contact_name)
        if await _click_call_button():
            return {"success": True, "action": "call", "contact": contact_name}
        return {"success": False, "error": "Could not locate call button in WhatsApp"}
    except Exception as e:
        log.error(f"[WA] call_contact failed: {e}")
        return {"success": False, "error": str(e)}


async def message_contact(contact_name, message):
    """Search a contact in WhatsApp Desktop and send a message."""
    if not _PYAUTOGUI:
        return {"success": False, "error": "PyAutoGUI not installed"}
    if not _WIN32:
        return {"success": False, "error": "win32api not available"}
    try:
        result = _send_whatsapp_message(contact_name, message)
        if result.get("success"):
            return result

        # Fallback: try Ctrl+N approach
        log.info("[WA] Click-based send failed, trying Ctrl+N fallback")
        _focus_whatsapp()
        _search_contact_pyautogui(contact_name)
        _focus_message_input()
        pyautogui.write(message, interval=TYPE_INTERVAL)
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.5)
        log.info(f"[WA] Fallback message sent to '{contact_name}'")
        return {"success": True, "action": "message", "contact": contact_name, "fallback": "shortcut"}

    except Exception as e:
        log.error(f"[WA] message_contact failed: {e}")
        return {"success": False, "error": str(e)}


# ── Sync entry point for local_agent._dispatch thread ──
def whatsapp_handler(tool, args):
    """Synchronous handler called by local_agent._dispatch() in a worker thread."""
    contact = args.get("contact", "") or args.get("contact_name", "") or args.get("name", "")
    message = args.get("message", "") or args.get("text", "") or args.get("msg", "")
    log.info(f"[WA] whatsapp_handler: tool={tool}, contact='{contact}', msg_len={len(message)}")

    if tool == "whatsapp_find_and_call":
        return asyncio.run(call_contact(contact))

    if tool in ("whatsapp_find_and_message", "send_whatsapp"):
        if not message:
            return {"success": False, "error": "No message provided"}
        return asyncio.run(message_contact(contact, message))

    return {"success": False, "error": f"Unknown WhatsApp tool: {tool}"}
