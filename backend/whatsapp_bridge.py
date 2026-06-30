"""
WhatsApp Desktop bridge for SODA.
Contact search uses Ctrl+N (New Chat dialog), types name, presses Enter to select,
then types message and sends.
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


def _require_pyautogui():
    if not _PYAUTOGUI:
        raise RuntimeError("pyautogui not available. Install with: pip install pyautogui")


def _require_win32():
    if not _WIN32:
        raise RuntimeError("win32api not available. Install with: pip install pywin32")


_BROWSER_KEYWORDS = {"chrome", "firefox", "edge", "opera", "brave", "mozilla", "internet explorer"}


def _find_whatsapp_window():
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
    found = _find_whatsapp_window()
    if not found:
        log.warning("[WA] WhatsApp window not found")
        return False
    hwnd, title = found
    log.info(f"[WA] Focusing: '{title}'")
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.2)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    return True


def _focus_or_open_whatsapp():
    if _focus_whatsapp():
        return True
    try:
        from system_app import open_app
        result = open_app("whatsapp")
        time.sleep(3.0)
        if _focus_whatsapp():
            return True
        log.warning(f"[WA] open_app result: {result}")
        return False
    except Exception as e:
        log.error(f"[WA] Failed to launch WhatsApp: {e}")
        return False


def _send_whatsapp_message(contact_name, message):
    """
    Synchronous flow: Ctrl+N → type contact → Enter → type message → Enter.
    Returns {"success": bool, ...}.
    """
    _require_pyautogui()

    log.info(f"[WA] Opening WhatsApp for '{contact_name}'")
    if not _focus_or_open_whatsapp():
        return {"success": False, "error": "Could not open WhatsApp Desktop"}

    # Step 1: Ctrl+N opens new chat dialog
    log.info("[WA] Step 1: Ctrl+N new chat")
    pyautogui.hotkey("ctrl", "n")
    time.sleep(1.0)

    # Step 2: Type contact name
    log.info(f"[WA] Step 2: Typing '{contact_name}'")
    pyautogui.write(contact_name, interval=0.06)
    time.sleep(1.5)

    # Step 3: Press Enter to select first result
    log.info("[WA] Step 3: Selecting contact")
    pyautogui.press("enter")
    time.sleep(1.5)

    # Step 4: Type message
    log.info(f"[WA] Step 4: Typing message ({len(message)} chars)")
    pyautogui.write(message, interval=0.06)
    time.sleep(0.3)

    # Step 5: Send
    log.info("[WA] Step 5: Sending")
    pyautogui.press("enter")
    time.sleep(0.5)

    log.info(f"[WA] ✅ Sent to '{contact_name}': {message[:60]}")
    return {"success": True, "action": "message", "contact": contact_name}


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
            return {"success": False, "error": "Could not open WhatsApp Desktop"}
        _focus_whatsapp()
        pyautogui.hotkey("ctrl", "n")
        time.sleep(0.8)
        pyautogui.write(contact_name, interval=0.06)
        time.sleep(1.5)
        pyautogui.press("enter")
        time.sleep(1.5)
        if await _click_call_button():
            return {"success": True, "action": "call", "contact": contact_name}
        return {"success": False, "error": "Could not locate call button in WhatsApp"}
    except Exception as e:
        log.error(f"[WA] call_contact failed: {e}")
        return {"success": False, "error": str(e)}


# ── Synchronous message send (no async needed) ──
def message_contact_sync(contact_name, message):
    """Fully synchronous version — runs directly in the _dispatch thread without asyncio.run()."""
    if not _PYAUTOGUI:
        return {"success": False, "error": "PyAutoGUI not installed"}
    if not _WIN32:
        return {"success": False, "error": "win32api not available"}
    try:
        return _send_whatsapp_message(contact_name, message)
    except Exception as e:
        log.error(f"[WA] message_contact_sync failed: {e}")
        return {"success": False, "error": str(e)}


# ── Check WhatsApp for unread messages ──
async def check_whatsapp():
    """Take a screenshot of WhatsApp and use AI Vision to find unread messages."""
    if not _PYAUTOGUI:
        return {"success": False, "error": "PyAutoGUI not installed"}
    if not _WIN32:
        return {"success": False, "error": "win32api not available"}
    if not _focus_or_open_whatsapp():
        return {"success": False, "error": "Could not open WhatsApp"}
    time.sleep(1.5)
    rect = _get_window_rect()
    if not rect:
        return {"success": False, "error": "Could not get WhatsApp window position"}
    left, top, right, bottom = rect
    win_w = right - left
    win_h = bottom - top
    if win_w < 200 or win_h < 200:
        return {"success": False, "error": "WhatsApp window too small"}
    try:
        import mss
        from screen_vision import analyze_screen
        with mss.mss() as sct:
            screenshot = sct.grab({"left": left, "top": top, "width": win_w, "height": win_h})
            png_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)
        prompt = (
            "This is a screenshot of WhatsApp Desktop. "
            "Look at the CHAT LIST on the LEFT panel. "
            "For each chat that has UNREAD messages (green dot, green number badge, or bold contact name):\n"
            "1. List the contact name exactly as shown\n"
            "2. Show the last message preview text\n"
            "3. Number of unread messages if visible\n\n"
            "If NO chats have unread messages, say 'No unread messages'.\n"
            "Format each unread chat as: 'CONTACT: [name] | PREVIEW: [last message] | UNREAD: [count]'"
        )
        result = await analyze_screen(prompt=prompt, screenshot=png_bytes)
        return result
    except Exception as e:
        log.error(f"[WA] check_whatsapp failed: {e}")
        return {"success": False, "error": str(e)}


def check_whatsapp_sync():
    """Synchronous wrapper for check_whatsapp."""
    return asyncio.run(check_whatsapp())


# ── Reply to an existing WhatsApp chat ──
def reply_whatsapp_sync(contact_name, message):
    """Open an existing WhatsApp chat by name, type reply, and send.
    Uses the chat list search bar (not Ctrl+N) to find existing conversations."""
    _require_pyautogui()
    if not _focus_or_open_whatsapp():
        return {"success": False, "error": "Could not open WhatsApp"}
    log.info(f"[WA] Replying to '{contact_name}'")
    rect = _get_window_rect()
    if not rect:
        return {"success": False, "error": "Could not get window position"}
    left, top, right, bottom = rect
    win_w = right - left

    # Click the chat list search bar (top of left panel)
    search_x = left + int(win_w * 0.16)
    search_y = top + 26
    pyautogui.click(search_x, search_y)
    time.sleep(0.5)

    # Clear any existing search text and type contact name
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.2)
    pyautogui.press("backspace")
    time.sleep(0.3)
    pyautogui.write(contact_name, interval=0.05)
    time.sleep(1.5)

    # Click the first search result (the existing chat)
    result_y = top + 80
    pyautogui.click(search_x, result_y)
    time.sleep(1.5)

    # Type and send the reply
    pyautogui.write(message, interval=0.06)
    time.sleep(0.3)
    pyautogui.press("enter")
    time.sleep(0.5)
    log.info(f"[WA] Reply sent to '{contact_name}': {message[:60]}")
    return {"success": True, "action": "reply", "contact": contact_name}


# ── Sync entry point for local_agent._dispatch thread ──
def whatsapp_handler(tool, args):
    """Synchronous handler called by local_agent._dispatch() in a worker thread.
    All WhatsApp message operations are fully synchronous (keyboard/mouse automation).
    Only voice calls and check need async (for AI Vision).
    """
    contact = args.get("contact", "") or args.get("contact_name", "") or args.get("name", "")
    message = args.get("message", "") or args.get("text", "") or args.get("msg", "")
    log.info(f"[WA] whatsapp_handler: tool={tool}, contact='{contact}', msg_len={len(message)}")

    if tool == "whatsapp_find_and_call":
        return asyncio.run(call_contact(contact))

    if tool in ("whatsapp_find_and_message", "send_whatsapp"):
        if not message:
            return {"success": False, "error": "No message provided"}
        return message_contact_sync(contact, message)

    if tool == "check_whatsapp":
        return check_whatsapp_sync()

    if tool == "reply_whatsapp":
        if not message:
            return {"success": False, "error": "No reply message provided"}
        return reply_whatsapp_sync(contact, message)

    return {"success": False, "error": f"Unknown WhatsApp tool: {tool}"}
