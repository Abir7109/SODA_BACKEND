"""
Play Button Trainer for SODA Spotify Desktop bridge.
Run once to teach SODA where the big green play button is.

Usage:
  py -3.11 backend\train_play_button.py

Instructions:
  1. Script will focus Spotify (opens if needed)
  2. Navigate to any playlist/album page in Spotify manually
  3. Hold Ctrl on your keyboard and click the big green play button
  4. Script records the position and exits

The calibration is saved to backend/play_button_calibration.json
as percentage offsets relative to the Spotify window, so it works
even if the window is moved or resized later.
"""

import os
import sys
import json
import time
import ctypes
import subprocess

_CALIBRATION_FILE = os.path.join(os.path.dirname(__file__), "play_button_calibration.json")
VK_CONTROL = 0x11
VK_LBUTTON = 0x01

try:
    import win32gui
    import win32con
except ImportError:
    print("ERROR: pywin32 is required. Run: pip install pywin32")
    sys.exit(1)


def _find_spotify_window():
    matches = []
    def enum_cb(hwnd, _matches):
        if win32gui.IsWindowVisible(hwnd):
            text = win32gui.GetWindowText(hwnd)
            if "spotify" in text.lower():
                _matches.append((hwnd, text))
        return True
    win32gui.EnumWindows(enum_cb, matches)
    return matches[0] if matches else None


def _get_spotify_rect():
    found = _find_spotify_window()
    if not found:
        return None
    try:
        return win32gui.GetWindowRect(found[0])
    except Exception:
        return None


def _activate_window(hwnd):
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    rect = win32gui.GetWindowRect(hwnd)
    cx = (rect[0] + rect[2]) // 2
    cy = rect[1] + 10
    ctypes.windll.user32.SetCursorPos(cx, cy)
    ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.15)
    ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
    time.sleep(0.3)


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
                return True
            except Exception:
                continue
    try:
        subprocess.Popen(["start", "spotify:"], shell=True)
        return True
    except Exception:
        return False


def _is_ctrl_held():
    return bool(ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)


def _is_mouse_down():
    """Check if left mouse button is currently pressed."""
    return bool(ctypes.windll.user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)


def _get_cursor_pos():
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def main():
    print("=" * 54)
    print("  SODA Spotify Play Button Trainer")
    print("=" * 54)

    found = _find_spotify_window()
    if not found:
        print("\n[Opening Spotify...]")
        if not _launch_spotify():
            print("ERROR: Could not launch Spotify.")
            sys.exit(1)
        time.sleep(6)
        found = _find_spotify_window()
        if not found:
            print("ERROR: Spotify window not found after launch.")
            sys.exit(1)

    _activate_window(found[0])
    print("\nSpotify is now focused.")
    print()
    print("INSTRUCTIONS:")
    print("  1. Navigate to a playlist/album page in Spotify (using Spotify's own UI).")
    print("  2. Hold the LEFT Ctrl key on your keyboard.")
    print("  3. While holding Ctrl, click the BIG GREEN PLAY BUTTON at the top of the page.")
    print("  4. The trainer will beep \a and save the calibration.")
    print()
    print("Press Ctrl+C at any time to cancel.\n")

    input("Press Enter when you're ready on the playlist page... ")

    rect_before = _get_spotify_rect()
    if not rect_before:
        print("ERROR: Could not read Spotify window position.")
        sys.exit(1)

    print("\nListening for Ctrl+Click... Hold Ctrl and click the play button.\n")

    prev_mouse = False
    saved = False

    while not saved:
        rect = _get_spotify_rect()
        if not rect:
            print("\nSpotify window lost. Exiting.")
            sys.exit(1)

        ctrl_down = _is_ctrl_held()
        mouse_down = _is_mouse_down()

        # Detect rising edge of mouse click: was up, now down
        clicked = ctrl_down and mouse_down and not prev_mouse
        prev_mouse = mouse_down

        if not clicked:
            time.sleep(0.02)
            continue

        x, y = _get_cursor_pos()
        left, top, right, bottom = rect
        w = right - left
        h = bottom - top

        if w <= 0 or h <= 0:
            time.sleep(0.05)
            continue

        x_pct = (x - left) / w
        y_pct = (y - top) / h

        margin = 0.02
        if x_pct < -margin or x_pct > 1 + margin or y_pct < -margin or y_pct > 1 + margin:
            print(f"  Click at ({x}, {y}) is outside Spotify window — ignoring.")
            time.sleep(0.3)
            continue

        x_pct = max(0.0, min(1.0, x_pct))
        y_pct = max(0.0, min(1.0, y_pct))

        calibration = {
            "x_pct": round(x_pct, 4),
            "y_pct": round(y_pct, 4),
        }
        with open(_CALIBRATION_FILE, "w") as f:
            json.dump(calibration, f)

        saved = True
        print(f"\n  Calibration saved!")
        print(f"    Spotify window: {w}x{h} at ({left},{top})")
        print(f"    Click: absolute ({x}, {y})")
        print(f"    Percentage: x={x_pct*100:.1f}%, y={y_pct*100:.1f}%")
        print(f"    File: {_CALIBRATION_FILE}")
        print("\n  \aDone! SODA will now use this position to click the play button.")

    sys.exit(0)


if __name__ == "__main__":
    main()
