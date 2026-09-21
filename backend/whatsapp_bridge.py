"""
WhatsApp Desktop automation bridge.
Uses keyboard automation + AI Vision to control WhatsApp Desktop on Windows.

Provides: open, search contact, send message, read chat, check unread, call.
"""

import time
import os
import sys
import subprocess
import base64
import io

_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

_log_file = os.path.join(os.path.dirname(_backend_dir), "agent.log")


def _log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] [whatsapp] {msg}"
    try:
        print(line, flush=True)
    except:
        pass
    try:
        with open(_log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass


# ── Window helpers ──

def _find_whatsapp_window():
    """Find WhatsApp Desktop window. Returns hwnd or None."""
    try:
        import win32gui
        matches = []
        def cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                if "whatsapp" in title:
                    matches.append(hwnd)
            return True
        win32gui.EnumWindows(cb, None)
        return matches[0] if matches else None
    except ImportError:
        pass
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle("WhatsApp")
        return wins[0]._hWnd if wins else None
    except:
        pass
    return None


def _focus_whatsapp():
    """Bring WhatsApp Desktop to foreground. Returns True on success."""
    hwnd = _find_whatsapp_window()
    if not hwnd:
        return False
    try:
        import win32gui, win32con
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.3)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        return True
    except:
        pass
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle("WhatsApp")
        if wins:
            wins[0].activate()
            time.sleep(0.5)
            return True
    except:
        pass
    return False


def _open_whatsapp():
    """Open or focus WhatsApp Desktop. Returns True if WhatsApp is in focus."""
    if _focus_whatsapp():
        return True
    _log("WhatsApp not found, launching...")
    subprocess.Popen(["start", "whatsapp:"], shell=True)
    time.sleep(3.0)
    for _ in range(6):
        if _focus_whatsapp():
            return True
        time.sleep(1.0)
    return False


def _screenshot_whatsapp():
    """Take a screenshot of the WhatsApp window. Returns PNG bytes or None."""
    try:
        import win32gui
        hwnd = _find_whatsapp_window()
        if not hwnd:
            return None
        import win32gui, win32con
        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        w, h = right - left, bottom - top
        if w < 50 or h < 50:
            return None
        import mss
        with mss.mss() as sct:
            img = sct.grab({"left": left, "top": top, "width": w, "height": h})
            return mss.tools.to_png(img.rgb, img.size)
    except Exception as e:
        _log(f"screenshot failed: {e}")
        return None


def _screenshot_region():
    """Screenshot the full screen. Returns PNG bytes."""
    try:
        import mss
        with mss.mss() as sct:
            img = sct.grab(sct.monitors[1])
            return mss.tools.to_png(img.rgb, img.size)
    except:
        pass
    try:
        import pyautogui
        png = pyautogui.screenshot()
        buf = io.BytesIO()
        png.save(buf, format="PNG")
        return buf.getvalue()
    except:
        return None


def _analyze_screenshot(png_bytes, prompt):
    """Use Gemini vision to analyze a screenshot."""
    if not png_bytes:
        return {"success": False, "error": "No screenshot available"}
    try:
        from screen_vision import analyze_screen
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(analyze_screen(
                prompt=prompt,
                screenshot=png_bytes,
            ))
            return result
        finally:
            loop.close()
    except Exception as e:
        _log(f"vision analyze failed: {e}")
        return {"success": False, "error": str(e)}


def _type_text(text, interval=0.04):
    """Type text using pyautogui."""
    import pyautogui
    pyautogui.write(text, interval=interval)


def _press_key(key):
    """Press a single key."""
    import pyautogui
    pyautogui.press(key)


def _hotkey(*keys):
    """Press a key combination."""
    import pyautogui
    pyautogui.hotkey(*keys)


# ── Tool handlers ──

def _whatsapp_find_and_message(contact_name, message):
    """Search for a contact in WhatsApp Desktop and send them a message."""
    _log(f"find_and_message: contact='{contact_name}', msg='{message[:50]}...'")
    if not _open_whatsapp():
        return {"success": False, "error": "Could not open or focus WhatsApp Desktop"}

    time.sleep(0.8)

    # Ctrl+F opens search in WhatsApp Desktop
    _hotkey("ctrl", "f")
    time.sleep(0.6)

    # Type contact name to search
    _type_text(contact_name, interval=0.05)
    time.sleep(1.5)

    # Press Enter or Down+Enter to select first search result
    _press_key("enter")
    time.sleep(1.5)

    # Now the chat should be open. Type the message.
    # The message input field should be focused after selecting a contact.
    _type_text(message, interval=0.03)
    time.sleep(0.5)

    # Press Enter to send
    _press_key("enter")
    time.sleep(0.5)

    _log(f"Message sent to {contact_name}")
    return {
        "success": True,
        "detail": f"Opened WhatsApp, searched for '{contact_name}', and sent message.",
        "contact": contact_name,
        "message_preview": message[:80],
    }


def _whatsapp_find_and_call(contact_name):
    """Search for a contact in WhatsApp Desktop and initiate a voice call."""
    _log(f"find_and_call: contact='{contact_name}'")
    if not _open_whatsapp():
        return {"success": False, "error": "Could not open or focus WhatsApp Desktop"}

    time.sleep(0.8)

    # Open search
    _hotkey("ctrl", "f")
    time.sleep(0.6)

    # Type contact name
    _type_text(contact_name, interval=0.05)
    time.sleep(1.5)

    # Select first result
    _press_key("enter")
    time.sleep(1.5)

    # Take a screenshot to see the chat and find the call button
    png = _screenshot_whatsapp()
    if png:
        result = _analyze_screenshot(png, (
            "Look at this WhatsApp chat window. Find the voice call button "
            "(phone icon). Tell me its approximate position as x,y coordinates "
            "relative to this window. If you can see a phone/call icon, give "
            "the coordinates. If not found, say 'not_found'."
        ))
        analysis = result.get("analysis", "") if isinstance(result, dict) else str(result)
        _log(f"Call button analysis: {analysis[:200]}")

        # Try to extract coordinates from the analysis
        import re
        coords = re.findall(r'(\d+)\s*,\s*(\d+)', analysis)
        if coords:
            x, y = int(coords[0][0]), int(coords[0][1])
            import pyautogui
            # Get window position to convert relative to absolute
            try:
                import win32gui
                hwnd = _find_whatsapp_window()
                if hwnd:
                    rect = win32gui.GetWindowRect(hwnd)
                    abs_x = rect[0] + x
                    abs_y = rect[1] + y
                    pyautogui.click(abs_x, abs_y)
                    time.sleep(1.0)
                    return {
                        "success": True,
                        "detail": f"Opened chat with '{contact_name}' and clicked call button.",
                        "contact": contact_name,
                    }
            except:
                pass

    # Fallback: try keyboard shortcut for call (Ctrl+Shift+C or the call icon)
    # In WhatsApp Desktop, Alt+C or the phone button starts a call
    _hotkey("alt", "c")
    time.sleep(1.0)

    return {
        "success": True,
        "detail": f"Opened chat with '{contact_name}' and initiated call.",
        "contact": contact_name,
    }


def _check_whatsapp():
    """Check for unread WhatsApp messages by screenshotting the chat list."""
    _log("check_whatsapp: checking for unread messages")
    if not _open_whatsapp():
        return {"success": False, "error": "Could not open WhatsApp Desktop"}

    time.sleep(1.0)

    # Make sure we're on the chat list (press Escape to close any open chat)
    _press_key("escape")
    time.sleep(0.5)

    png = _screenshot_whatsapp()
    if not png:
        png = _screenshot_region()

    if not png:
        return {"success": False, "error": "Could not take screenshot"}

    result = _analyze_screenshot(png, (
        "You are looking at the WhatsApp Desktop chat list. "
        "Identify any unread messages — look for: "
        "(1) Green notification badges with numbers, "
        "(2) Bold contact names (unread chats appear bold), "
        "(3) Unread message previews. "
        "For each unread chat found, report: "
        "- Contact name "
        "- Last message preview "
        "- Number of unread messages if visible "
        "If no unread messages, say 'No unread messages found'. "
        "Be precise — only report what you can clearly see."
    ))

    analysis = result.get("analysis", "") if isinstance(result, dict) else str(result)

    return {
        "success": True,
        "analysis": analysis,
        "detail": "Screenshot analyzed for unread messages.",
    }


def _reply_whatsapp(contact_name, message):
    """Reply to an existing WhatsApp chat by contact name."""
    _log(f"reply_whatsapp: contact='{contact_name}', msg='{message[:50]}...'")
    if not _open_whatsapp():
        return {"success": False, "error": "Could not open or focus WhatsApp Desktop"}

    time.sleep(0.8)

    # Search for the contact
    _hotkey("ctrl", "f")
    time.sleep(0.6)
    _type_text(contact_name, interval=0.05)
    time.sleep(1.5)
    _press_key("enter")
    time.sleep(1.5)

    # Type and send the reply
    _type_text(message, interval=0.03)
    time.sleep(0.5)
    _press_key("enter")
    time.sleep(0.5)

    _log(f"Reply sent to {contact_name}")
    return {
        "success": True,
        "detail": f"Replied to '{contact_name}': {message[:60]}...",
        "contact": contact_name,
        "message_preview": message[:80],
    }


def _read_whatsapp_chat(contact_name, message=None):
    """Open a specific WhatsApp chat and read recent messages."""
    _log(f"read_whatsapp_chat: contact='{contact_name}'")
    if not _open_whatsapp():
        return {"success": False, "error": "Could not open WhatsApp Desktop"}

    time.sleep(0.8)

    # Search for the contact
    _hotkey("ctrl", "f")
    time.sleep(0.6)
    _type_text(contact_name, interval=0.05)
    time.sleep(1.5)
    _press_key("enter")
    time.sleep(2.0)

    # Take a screenshot of the chat
    png = _screenshot_whatsapp()
    if not png:
        png = _screenshot_region()

    if not png:
        return {"success": False, "error": "Could not take screenshot of chat"}

    result = _analyze_screenshot(png, (
        f"You are looking at a WhatsApp Desktop chat with '{contact_name}'. "
        "Read and describe the recent messages visible in this conversation. "
        "For each message, report: "
        "- Who sent it (you/me) "
        "- The message content "
        "- Approximate time if visible "
        "Be accurate — only report messages you can clearly read."
    ))

    analysis = result.get("analysis", "") if isinstance(result, dict) else str(result)

    # If a message was also provided, send it after reading
    if message:
        time.sleep(0.5)
        _type_text(message, interval=0.03)
        time.sleep(0.5)
        _press_key("enter")
        time.sleep(0.5)
        analysis += f"\n\n[Also sent: {message[:80]}]"

    return {
        "success": True,
        "analysis": analysis,
        "contact": contact_name,
        "detail": f"Read chat with '{contact_name}'." + (f" Sent: {message[:40]}..." if message else ""),
    }


# ── Main dispatcher ──

def whatsapp_handler(tool, args):
    """
    Main entry point called by local_agent.py's _dispatch().
    Routes WhatsApp tool calls to the appropriate handler.
    """
    try:
        import pyautogui
    except ImportError:
        return {"success": False, "error": "pyautogui required. Install: pip install pyautogui"}

    contact = args.get("contact_name", "") or args.get("contact", "")
    message = args.get("message", "") or args.get("text", "")
    query = args.get("query", "")

    if tool == "whatsapp_find_and_message":
        if not contact:
            return {"success": False, "error": "contact_name is required"}
        if not message:
            return {"success": False, "error": "message is required"}
        return _whatsapp_find_and_message(contact, message)

    elif tool == "whatsapp_find_and_call":
        if not contact:
            return {"success": False, "error": "contact_name is required"}
        return _whatsapp_find_and_call(contact)

    elif tool == "check_whatsapp":
        return _check_whatsapp()

    elif tool == "reply_whatsapp":
        if not contact:
            return {"success": False, "error": "contact_name is required"}
        if not message:
            return {"success": False, "error": "message is required"}
        return _reply_whatsapp(contact, message)

    elif tool == "read_whatsapp_chat":
        if not contact:
            return {"success": False, "error": "contact_name is required"}
        return _read_whatsapp_chat(contact, message=message if message else None)

    elif tool == "send_whatsapp":
        if not contact and not message:
            return {"success": False, "error": "contact_name and message required"}
        return _whatsapp_find_and_message(contact, message)

    else:
        return {"success": False, "error": f"Unknown WhatsApp tool: {tool}"}
