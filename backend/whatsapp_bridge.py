"""
WhatsApp Desktop bridge for SODA.
Three-tier button detection:
  1. uiautomation (finds buttons by UIA name — most reliable)
  2. AI Vision on cropped window (Gemini sees only the WhatsApp area)
  3. Coordinate fallback (window-relative)

Contact search uses Ctrl+N (New Chat dialog), NOT Ctrl+F (find in chat).
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

SEARCH_COOLDOWN = 0.5
TYPE_INTERVAL = 0.05
WAIT_AFTER_SEARCH = 1.0
WAIT_AFTER_OPEN = 1.0


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


def _get_window_rect(title="WhatsApp"):
    found = _find_whatsapp_window()
    if not found:
        return None
    hwnd, _ = found
    try:
        return win32gui.GetWindowRect(hwnd)
    except Exception:
        return None


def _focus_or_open_whatsapp():
    """Focus existing WhatsApp window or launch it. Returns True on success."""
    found = _find_whatsapp_window()
    if found:
        hwnd, _ = found
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.15)
            if win32gui.IsZoomed(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        return True
    try:
        from system_app import open_app
        result = open_app("whatsapp")
        time.sleep(2.5)
        return "Opened" in result
    except Exception as e:
        log.error(f"[WA] Failed to launch WhatsApp Desktop: {e}")
        return False


def _search_contact_pyautogui(contact_name):
    """Search for a contact using Ctrl+N (New Chat dialog)."""
    _require_pyautogui()
    pyautogui.hotkey("ctrl", "n")
    time.sleep(0.5)
    pyautogui.write(contact_name, interval=TYPE_INTERVAL)
    time.sleep(WAIT_AFTER_SEARCH)
    pyautogui.press("enter")
    time.sleep(WAIT_AFTER_OPEN)
    return True


def _search_contact_uia(contact_name):
    """Focus WhatsApp via uiautomation, then use PyAutoGUI for search."""
    if not _UIA:
        return False
    try:
        wa = auto.WindowControl(searchDepth=1, Name="WhatsApp")
        if not wa.Exists(0, 0):
            return False
        wa.SetActive()
        time.sleep(0.3)
        log.info(f"[WA] uiautomation focused WhatsApp window")
        return True  # window is focused, PyAutoGUI will now work reliably
    except Exception as e:
        log.warning(f"[WA] uia focus failed: {e}")
        return False


def _search_contact(contact_name):
    """Focus WhatsApp window, then search contact via PyAutoGUI."""
    _search_contact_uia(contact_name)  # focus the window (may or may not have uia)
    _search_contact_pyautogui(contact_name)
    return True


def _click_call_uia():
    """Try finding the call button via uiautomation by name. Returns True if clicked."""
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
    """Use Gemini Vision on a cropped WhatsApp window screenshot.
    Returns True if coordinates were successfully used to click.
    """
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
    """Coordinate fallback: below title bar, right side of chat header."""
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
    """Three-tier call button detection. Returns True if clicked."""
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
        _search_contact(contact_name)
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
        if not _focus_or_open_whatsapp():
            log.info("[WA] Desktop unavailable, trying web.whatsapp.com fallback")
            try:
                from system_app import open_url
                encoded = message.replace(" ", "%20").replace("\n", "%0A")
                url = f"https://web.whatsapp.com/send?text={encoded}"
                open_url(url)
                return {"success": True, "action": "message", "contact": contact_name, "fallback": "web"}
            except Exception as web_e:
                log.warning(f"[WA] Web fallback failed: {web_e}")
                return {"success": False, "error": "Could not open WhatsApp Desktop or web version. Is WhatsApp installed?"}
        _search_contact(contact_name)
        pyautogui.write(message, interval=TYPE_INTERVAL)
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.3)
        return {"success": True, "action": "message", "contact": contact_name}
    except Exception as e:
        log.error(f"[WA] message_contact failed: {e}")
        return {"success": False, "error": str(e)}


def _open_new_chat(contact_name):
    """Open Ctrl+N new chat dialog, type contact, select it. Returns True if chat opened."""
    _require_pyautogui()
    log.info(f"[WA] Opening new chat for '{contact_name}'")
    pyautogui.hotkey("ctrl", "n")
    time.sleep(0.8)
    pyautogui.write(contact_name, interval=0.05)
    time.sleep(1.5)
    pyautogui.press("enter")
    time.sleep(1.5)
    # Check if message input exists by trying to type a period and delete it
    try:
        pyautogui.write(".", interval=0.02)
        time.sleep(0.2)
        pyautogui.press("backspace")
        time.sleep(0.1)
    except:
        pass
    return True


async def message_contact(contact_name, message):
    """Search a contact in WhatsApp Desktop and send a message."""
    if not _PYAUTOGUI:
        return {"success": False, "error": "PyAutoGUI not installed"}
    if not _WIN32:
        return {"success": False, "error": "win32api not available"}
    try:
        if not _focus_or_open_whatsapp():
            log.info("[WA] Desktop unavailable, trying web.whatsapp.com fallback")
            try:
                from system_app import open_url
                encoded = message.replace(" ", "%20").replace("\n", "%0A")
                url = f"https://web.whatsapp.com/send?text={encoded}"
                open_url(url)
                return {"success": True, "action": "message", "contact": contact_name, "fallback": "web"}
            except Exception as web_e:
                log.warning(f"[WA] Web fallback failed: {web_e}")
                return {"success": False, "error": "Could not open WhatsApp Desktop or web version. Is WhatsApp installed?"}
        _open_new_chat(contact_name)
        pyautogui.write(message, interval=0.05)
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.5)
        log.info(f"[WA] Message sent to '{contact_name}': {message[:50]}")
        return {"success": True, "action": "message", "contact": contact_name}
    except Exception as e:
        log.error(f"[WA] message_contact failed: {e}")
        return {"success": False, "error": str(e)}


# ── Sync entry point for local_agent._dispatch thread ──
def whatsapp_handler(tool, args):
    """Synchronous handler called by local_agent._dispatch() in a worker thread.

    Routes tool calls to the appropriate async function using asyncio.run().
    """
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
