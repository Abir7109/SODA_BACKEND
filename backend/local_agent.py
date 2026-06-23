"""
SODA Local Agent — runs on your Windows machine.
Connects to the cloud backend and executes local file/system operations.

Usage:
    pip install -r requirements-local.txt
    py -3.11 backend/local_agent.py

For packaging as an installable exe:
    pip install pyinstaller
    pyinstaller --onefile backend/local_agent.py --name "SODA Agent"
"""

import os
import sys
import json
import time
import uuid
import socketio
import traceback
import subprocess
import asyncio
import threading
import urllib.parse
from pathlib import Path

# Ensure backend/ directory is on the path
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

BACKEND_URL = os.getenv("BACKEND_URL", "https://soda-backend-rdvz.onrender.com")
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "soda-local-agent-default")
MACHINE_ID = os.getenv(
    "MACHINE_ID",
    os.environ.get("COMPUTERNAME")
    or os.environ.get("HOSTNAME")
    or f"pc-{uuid.uuid4().hex[:8]}",
)

sio = socketio.Client(logger=False, engineio_logger=False)

LOCAL_TOOLS = [
    "list_files", "open_file", "write_file", "read_file", "create_folder",
    "delete_items", "rename_item", "copy_item", "move_item", "list_drives",
    "scroll_file_list", "view_file",
    "terminal_execute", "execute_command", "open_app", "close_window", "close_app",
    "control_system", "screenshot", "screenshot_region",
    "clipboard_read", "clipboard_write",
    "mouse_click", "mouse_move", "mouse_scroll", "mouse_drag",
    "mouse_get_pos", "mouse_hover", "mouse_right_click",
    "keyboard_type", "keyboard_press", "keyboard_hotkey",
    "window_focus", "window_list", "window_move",
    "window_manage", "window_get_info",
    "play_music", "control_music",
    "send_whatsapp", "whatsapp_find_and_call", "whatsapp_find_and_message",
    "send_telegram_message", "send_telegram_file",
    "get_active_window", "list_processes", "process_kill",
    "get_system_status",
    "analyze_screen", "read_screen_text", "recognize_face",
    "go_to_sleep", "wake_up", "go_background", "come_back",
    "ui_find_image", "ui_click_image", "ui_click_text",
    "ui_wait_for_image", "ui_drag_drop",
    "system_volume", "system_brightness",
    "send_keys_window", "app_launch", "app_wait",
    "run_script", "power_control", "service_control",
    "env_get", "file_compress", "file_download",
    "browser_command",
]

HAS_PYAUTOGUI = False
HAS_MSS = False
HAS_PYPERCLIP = False
HAS_PYWIN32 = False
HAS_PYGETWINDOW = False
HAS_PSUTIL = False
HAS_CV2 = False


def _check_deps():
    global HAS_PYAUTOGUI, HAS_MSS, HAS_PYPERCLIP, HAS_PYWIN32, HAS_PYGETWINDOW, HAS_PSUTIL, HAS_CV2
    try:
        import pyautogui
        HAS_PYAUTOGUI = True
    except ImportError:
        pass
    try:
        import mss
        HAS_MSS = True
    except ImportError:
        pass
    try:
        import pyperclip
        HAS_PYPERCLIP = True
    except ImportError:
        pass
    try:
        import win32api
        HAS_PYWIN32 = True
    except ImportError:
        pass
    try:
        import pygetwindow as gw
        HAS_PYGETWINDOW = True
    except ImportError:
        pass
    try:
        import psutil
        HAS_PSUTIL = True
    except ImportError:
        pass
    try:
        import cv2
        HAS_CV2 = True
    except ImportError:
        pass


@sio.event
def connect():
    print(f"[LocalAgent] Connected to {BACKEND_URL}")
    sio.emit("agent_register", {
        "token": AGENT_TOKEN,
        "machine_id": MACHINE_ID,
        "platform": sys.platform,
        "tools": LOCAL_TOOLS,
    })
    print(f"[LocalAgent] Registered as {MACHINE_ID}")


@sio.event
def connect_error(data):
    print(f"[LocalAgent] Connection error: {data}")


@sio.event
def disconnect():
    print(f"[LocalAgent] Disconnected")


@sio.on("agent_execute")
def on_agent_execute(data):
    tool = data.get("tool", "")
    args = data.get("args", {})
    callback_id = data.get("callback_id", "")

    print(f"[LocalAgent] Executing: {tool}({json.dumps(args)[:200]})")

    try:
        result = _dispatch(tool, args)
        sio.emit("agent_tool_result", {
            "callback_id": callback_id,
            "tool": tool,
            "result": result,
            "success": True,
        })
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[LocalAgent] Error executing {tool}: {e}")
        print(tb)
        sio.emit("agent_tool_result", {
            "callback_id": callback_id,
            "tool": tool,
            "result": {"error": str(e)},
            "success": False,
        })


@sio.on("agent_status")
def on_agent_status(data):
    print(f"[LocalAgent] Status: {data}")


def _dispatch(tool, args):
    """Dispatch tool execution using backend modules or fallback implementations."""

    # ── File operations (use builtins + backend modules) ──────────
    if tool == "list_files":
        try:
            from system_local import list_files
            return list_files(args.get("path", "."), args.get("search", ""))
        except ImportError:
            return _fallback_list_files(args.get("path", "."))

    elif tool == "open_file":
        try:
            from system_local import open_file
            return open_file(args.get("path", ""))
        except ImportError:
            return _fallback_open_file(args.get("path", ""))

    elif tool == "read_file":
        p = args.get("path", "")
        import codecs
        for enc in ["utf-8", "utf-16", "latin-1", "cp1252"]:
            try:
                with codecs.open(p, "r", encoding=enc) as f:
                    content = f.read()
                return {"success": True, "content": content, "path": p, "encoding": enc}
            except UnicodeError:
                continue
            except Exception:
                break
        return {"success": False, "error": f"Cannot read {p}"}

    elif tool == "write_file":
        p = args.get("path", "")
        c = args.get("content", "")
        Path(p).parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(c)
        return {"success": True, "path": p, "size": len(c)}

    elif tool == "create_folder":
        try:
            from system_local import create_folder
            return create_folder(args.get("path", ""))
        except ImportError:
            Path(args.get("path", "")).mkdir(parents=True, exist_ok=True)
            return {"success": True}

    elif tool == "delete_items":
        import shutil
        paths = args.get("paths", [])
        deleted = []
        errors = []
        for p in paths:
            try:
                if os.path.isfile(p) or os.path.islink(p):
                    os.remove(p)
                elif os.path.isdir(p):
                    shutil.rmtree(p)
                deleted.append(p)
            except Exception as e:
                errors.append(str(e))
        return {"success": len(errors) == 0, "deleted": deleted, "errors": errors}

    elif tool == "rename_item":
        import shutil
        try:
            os.rename(args.get("old_path", ""), args.get("new_path", ""))
            return {"success": True}
        except:
            shutil.move(args.get("old_path", ""), args.get("new_path", ""))
            return {"success": True}

    elif tool == "copy_item":
        import shutil
        src, dst = args.get("source", ""), args.get("dest", "")
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        return {"success": True}

    elif tool == "move_item":
        import shutil
        shutil.move(args.get("source", ""), args.get("dest", ""))
        return {"success": True}

    elif tool == "list_drives":
        if sys.platform == "win32":
            import ctypes
            drives = []
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if bitmask & 1:
                    drives.append(f"{letter}:\\")
                bitmask >>= 1
            return {"success": True, "drives": drives}
        return {"success": True, "drives": ["/"]}

    elif tool == "view_file":
        p = args.get("path", "")
        import mimetypes, base64
        mime, _ = mimetypes.guess_type(p)
        mime = mime or "text/plain"
        try:
            if mime.startswith("text/"):
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                return {"success": True, "type": "text", "content": content[:50000], "mime": mime}
            elif mime.startswith("image/"):
                with open(p, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                return {"success": True, "type": "image", "content": f"data:{mime};base64,{b64}", "mime": mime}
            else:
                return {"success": True, "type": "text", "content": f"[Binary: {mime}]", "mime": mime}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Terminal ──────────────────────────────────────────────────
    elif tool in ("terminal_execute", "execute_command"):
        command = args.get("command", "")
        if not command:
            return {"success": False, "output": "", "error": "No command"}
        try:
            r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=args.get("timeout", 30))
            output = r.stdout + r.stderr
            return {"success": r.returncode == 0, "output": output, "returncode": r.returncode}
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": "Timed out"}

    # ── App / System Control ──────────────────────────────────────
    elif tool == "open_app":
        app = args.get("name", "") or args.get("app_name", "") or args.get("app", "")
        if not app:
            return {"success": False, "error": "No app name provided"}
        app_lower = app.lower().strip()

        # Hardcoded lookup for common apps
        KNOWN_APPS = {
            "chrome": ["chrome.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                       r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"],
            "firefox": ["firefox.exe", r"C:\Program Files\Mozilla Firefox\firefox.exe"],
            "edge": ["msedge.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"],
            "notepad": ["notepad.exe"],
            "cmd": ["cmd.exe"],
            "command prompt": ["cmd.exe"],
            "terminal": ["wt.exe", "cmd.exe"],
            "powershell": ["powershell.exe"],
            "explorer": ["explorer.exe"],
            "file explorer": ["explorer.exe"],
            "this pc": ["explorer.exe"],
            "calculator": ["calc.exe"],
            "paint": ["mspaint.exe"],
            "word": ["winword.exe", r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"],
            "excel": ["excel.exe", r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"],
            "outlook": ["outlook.exe"],
            "vscode": ["code.exe"],
            "visual studio code": ["code.exe"],
            "spotify": ["Spotify.exe"],
            "discord": ["Discord.exe"],
            "slack": ["slack.exe"],
            "zoom": ["Zoom.exe"],
            "vlc": ["vlc.exe"],
            "soda": ["chrome.exe", "--app=https://soda-hud.netlify.app"],
        }

        if app_lower in KNOWN_APPS:
            candidates = KNOWN_APPS[app_lower]
            # First try exe name via start command
            exe_name = candidates[0]
            # Try full path first
            for path in candidates:
                if os.path.isfile(path):
                    try:
                        subprocess.Popen([path], shell=False)
                        return {"success": True, "app": app, "path": path}
                    except:
                        pass
            # Try just the executable name
            try:
                subprocess.Popen(["start", "", exe_name], shell=True)
                return {"success": True, "app": app, "method": "start"}
            except:
                pass

        # Try os.startfile (works for registered apps)
        try:
            os.startfile(app)
            return {"success": True, "app": app, "method": "startfile"}
        except:
            pass

        # Try `start` command
        try:
            subprocess.Popen(["start", "", app], shell=True)
            return {"success": True, "app": app, "method": "start"}
        except:
            pass

        # Search PATH for the executable
        try:
            result = subprocess.run(["where", app], shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                exe_path = result.stdout.strip().split("\n")[0].strip()
                subprocess.Popen([exe_path], shell=False)
                return {"success": True, "app": app, "path": exe_path}
        except:
            pass

        # Try with .exe extension
        try:
            result = subprocess.run(["where", f"{app}.exe"], shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                exe_path = result.stdout.strip().split("\n")[0].strip()
                subprocess.Popen([exe_path], shell=False)
                return {"success": True, "app": app, "path": exe_path}
        except:
            pass

        return {"success": False, "error": f"Could not find or open '{app}'. Try a different name."}

    elif tool == "close_window":
        name = args.get("name", "") or args.get("window_name", "") or args.get("title", "")
        return _close_app_by_name(name)

    elif tool == "close_app":
        name = args.get("name", "") or args.get("app", "") or args.get("app_name", "")
        return _close_app_by_name(name)

    elif tool == "control_system":
        try:
            from system_control import computer_settings_action
            r = _await_it(computer_settings_action(args.get("action", ""), args.get("value")))
            return r
        except ImportError:
            return {"success": False, "error": "control_system not available"}

    elif tool in ("go_to_sleep", "wake_up", "go_background", "come_back"):
        return {"success": True, "note": f"Action '{tool}' acknowledged, but full support requires the system_control module."}

    # ── Screen / Vision ──────────────────────────────────────────
    elif tool == "screenshot":
        if HAS_MSS:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                img = sct.grab(monitor)
                import base64, io
                from PIL import Image
                pil_img = Image.frombytes("RGB", img.size, img.rgb)
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode()
                return {"success": True, "image_base64": b64, "size": img.size}
        elif HAS_PYAUTOGUI:
            import pyautogui, base64, io
            from PIL import Image
            pil_img = pyautogui.screenshot()
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            return {"success": True, "image_base64": b64}
        return {"success": False, "error": "Install mss or pyautogui for screenshots"}

    elif tool == "analyze_screen":
        cap = _dispatch("screenshot", {})
        if not cap.get("success"):
            return {"success": False, "error": cap.get("error", "Screenshot failed")}
        try:
            from screen_vision import analyze_screenshot
            r = _await_it(analyze_screenshot(cap.get("image_base64", ""), args.get("prompt", "Describe what you see")))
            return r
        except ImportError:
            return {"success": True, "analysis": "Screenshot captured. To analyze, ensure screen_vision module is available."}

    elif tool == "read_screen_text":
        cap = _dispatch("screenshot", {})
        if not cap.get("success"):
            return {"success": False, "error": cap.get("error", "Screenshot failed")}
        try:
            from screen_vision import ocr_screenshot
            r = _await_it(ocr_screenshot(cap.get("image_base64", "")))
            return r
        except ImportError:
            return {"success": False, "error": "OCR not available"}

    elif tool == "recognize_face":
        return {"success": False, "note": "Face recognition requires camera access. Use the web frontend for this."}

    # ── Mouse / Keyboard ─────────────────────────────────────────
    elif tool == "mouse_click":
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required"}
        import pyautogui
        pyautogui.click(args.get("x", None), args.get("y", None), button=args.get("button", "left"), clicks=args.get("clicks", 1))
        return {"success": True}

    elif tool == "mouse_move":
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required"}
        import pyautogui
        pyautogui.moveTo(args.get("x", 0), args.get("y", 0), duration=args.get("duration", 0.3))
        return {"success": True}

    elif tool == "mouse_scroll":
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required"}
        import pyautogui
        pyautogui.scroll(args.get("amount", 0))
        return {"success": True}

    elif tool == "mouse_drag":
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required"}
        import pyautogui
        pyautogui.drag(args.get("start_x", 0), args.get("start_y", 0), args.get("end_x", 0), args.get("end_y", 0), duration=args.get("duration", 0.5))
        return {"success": True}

    elif tool == "keyboard_type":
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required"}
        import pyautogui
        pyautogui.write(args.get("text", ""), interval=args.get("interval", 0.05))
        return {"success": True}

    elif tool == "keyboard_press":
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required"}
        import pyautogui
        pyautogui.hotkey(*args.get("keys", "").split("+"))
        return {"success": True}

    # ── Windows ───────────────────────────────────────────────────
    elif tool == "window_focus":
        if not HAS_PYGETWINDOW:
            return {"success": False, "error": "pygetwindow required"}
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle(args.get("title", ""))
        if wins:
            wins[0].activate()
            return {"success": True, "title": wins[0].title}
        return {"success": False, "error": "Window not found"}

    elif tool == "window_list":
        if not HAS_PYGETWINDOW:
            return {"success": False, "error": "pygetwindow required"}
        import pygetwindow as gw
        wins = [{"title": w.title, "visible": w.visible} for w in gw.getAllWindows() if w.title.strip()]
        return {"success": True, "windows": wins}

    elif tool == "window_move":
        if not HAS_PYGETWINDOW:
            return {"success": False, "error": "pygetwindow required"}
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle(args.get("title", ""))
        if wins:
            w = wins[0]
            w.moveTo(args.get("x", 0), args.get("y", 0))
            if args.get("width") and args.get("height"):
                w.resizeTo(args.get("width"), args.get("height"))
            return {"success": True}
        return {"success": False, "error": "Window not found"}

    # ── Clipboard ─────────────────────────────────────────────────
    elif tool == "clipboard_read":
        if HAS_PYPERCLIP:
            import pyperclip
            text = pyperclip.paste()
            return {"success": True, "text": text, "length": len(text)}
        return {"success": False, "error": "pyperclip required"}

    elif tool == "clipboard_write":
        if HAS_PYPERCLIP:
            import pyperclip
            pyperclip.copy(args.get("text", ""))
            return {"success": True}
        return {"success": False, "error": "pyperclip required"}

    # ── Processes / System ────────────────────────────────────────
    elif tool == "list_processes":
        if HAS_PSUTIL:
            import psutil
            limit = args.get("limit", 20)
            sort_by = args.get("sort_by", "memory")
            procs = []
            for p in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
                try:
                    procs.append(p.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            if sort_by == "memory":
                procs.sort(key=lambda x: x.get("memory_percent", 0) or 0, reverse=True)
            else:
                procs.sort(key=lambda x: x.get("cpu_percent", 0) or 0, reverse=True)
            return {"success": True, "processes": procs[:limit], "count": len(procs)}
        return {"success": False, "error": "psutil required"}

    elif tool == "get_system_status":
        try:
            from external_apis import get_system_status
            return _await_it(get_system_status())
        except ImportError:
            info = {"platform": sys.platform, "hostname": MACHINE_ID}
            if HAS_PSUTIL:
                import psutil
                info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
                info["memory"] = psutil.virtual_memory()._asdict()
                info["disk"] = psutil.disk_usage("/")._asdict()
            return {"success": True, **info}

    elif tool == "get_active_window":
        if HAS_PYGETWINDOW:
            import pygetwindow as gw
            try:
                w = gw.getActiveWindow()
                if w:
                    return {"success": True, "title": w.title}
            except Exception:
                pass
        if HAS_PYWIN32:
            import win32gui
            try:
                hwnd = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(hwnd)
                return {"success": True, "title": title}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "pygetwindow or pywin32 required"}

    # ── Music ──────────────────────────────────────────────────────
    elif tool in ("play_music", "control_music"):
        try:
            from spotify_bridge import play_music_handler, control_music_handler
            if tool == "play_music":
                return play_music_handler(args.get("query", ""))
            return control_music_handler(args.get("action", ""))
        except ImportError:
            return {"success": False, "error": "spotify_bridge not available locally"}

    # ── Messaging ──────────────────────────────────────────────────
    elif tool in ("send_whatsapp", "whatsapp_find_and_call", "whatsapp_find_and_message"):
        try:
            from whatsapp_bridge import whatsapp_handler
            return whatsapp_handler(tool, args)
        except ImportError:
            return {"success": False, "error": "whatsapp_bridge not available locally"}

    elif tool in ("send_telegram_message", "send_telegram_file"):
        return {"success": False, "error": f"{tool} requires cloud backend. Use from the SODA web interface."}

    # ── UI Automation ──────────────────────────────────────────────
    elif tool == "ui_find_image":
        img_path = args.get("image", "") or args.get("path", "")
        confidence = args.get("confidence", 0.8)
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required for image search"}
        import pyautogui
        try:
            pos = pyautogui.locateOnScreen(img_path, confidence=confidence)
            if pos:
                cx, cy = pyautogui.center(pos)
                return {"success": True, "x": int(cx), "y": int(cy), "width": pos.width, "height": pos.height}
            return {"success": False, "error": "Image not found on screen"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif tool == "ui_click_image":
        img_path = args.get("image", "") or args.get("path", "")
        confidence = args.get("confidence", 0.8)
        button = args.get("button", "left")
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required"}
        import pyautogui
        try:
            pos = pyautogui.locateOnScreen(img_path, confidence=confidence)
            if pos:
                cx, cy = pyautogui.center(pos)
                pyautogui.click(cx, cy, button=button)
                return {"success": True, "x": int(cx), "y": int(cy)}
            return {"success": False, "error": "Image not found on screen"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif tool == "ui_click_text":
        text = args.get("text", "")
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required for OCR click"}
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            return {"success": False, "error": "pytesseract required. Install: pip install pytesseract"}
        try:
            import pyautogui
            img = pyautogui.screenshot()
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            for i in range(len(data["text"])):
                if text.lower() in data["text"][i].lower():
                    x = data["left"][i] + data["width"][i] // 2
                    y = data["top"][i] + data["height"][i] // 2
                    pyautogui.click(x, y)
                    return {"success": True, "x": x, "y": y, "matched": data["text"][i]}
            return {"success": False, "error": f"Text '{text}' not found on screen"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif tool == "ui_wait_for_image":
        img_path = args.get("image", "") or args.get("path", "")
        timeout = args.get("timeout", 10)
        confidence = args.get("confidence", 0.8)
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required"}
        import pyautogui
        try:
            pos = pyautogui.locateOnScreen(img_path, confidence=confidence)
            start = time.time()
            while not pos and (time.time() - start) < timeout:
                time.sleep(0.5)
                pos = pyautogui.locateOnScreen(img_path, confidence=confidence)
            if pos:
                cx, cy = pyautogui.center(pos)
                elapsed = time.time() - start
                return {"success": True, "x": int(cx), "y": int(cy), "elapsed_s": round(elapsed, 1)}
            return {"success": False, "error": f"Image not found within {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif tool == "ui_drag_drop":
        sx, sy = args.get("start_x", 0), args.get("start_y", 0)
        ex, ey = args.get("end_x", 0), args.get("end_y", 0)
        duration = args.get("duration", 0.5)
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required"}
        import pyautogui
        pyautogui.moveTo(sx, sy)
        pyautogui.drag(ex - sx, ey - sy, duration=duration)
        return {"success": True}

    # ── Enhanced App Control ───────────────────────────────────────
    elif tool == "app_launch":
        app = args.get("app", "") or args.get("name", "") or args.get("app_name", "")
        params = args.get("params", "") or args.get("arguments", "") or args.get("args", "")
        try:
            if params:
                subprocess.Popen(f'start "" "{app}" {params}', shell=True)
            elif sys.platform == "win32":
                os.startfile(app)
            else:
                subprocess.Popen([app])
            return {"success": True, "app": app}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif tool == "app_wait":
        title = args.get("title", "") or args.get("window", "")
        timeout = args.get("timeout", 15)
        if not HAS_PYGETWINDOW:
            return {"success": False, "error": "pygetwindow required"}
        import pygetwindow as gw
        start = time.time()
        while (time.time() - start) < timeout:
            try:
                wins = gw.getWindowsWithTitle(title)
                if wins:
                    return {"success": True, "title": wins[0].title, "elapsed_s": round(time.time() - start, 1)}
            except:
                pass
            time.sleep(0.5)
        return {"success": False, "error": f"Window '{title}' did not appear within {timeout}s"}

    elif tool == "process_kill":
        name = args.get("name", "") or args.get("process", "")
        force = args.get("force", True)
        if not HAS_PSUTIL:
            return {"success": False, "error": "psutil required"}
        import psutil
        killed = []
        for p in psutil.process_iter(["pid", "name"]):
            try:
                if name.lower() in p.info["name"].lower():
                    if force:
                        p.kill()
                    else:
                        p.terminate()
                    killed.append({"pid": p.info["pid"], "name": p.info["name"]})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return {"success": len(killed) > 0, "killed": killed, "count": len(killed)}

    elif tool == "window_manage":
        title = args.get("title", "")
        action = args.get("action", "minimize")
        if not HAS_PYGETWINDOW:
            return {"success": False, "error": "pygetwindow required"}
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle(title)
        if not wins:
            return {"success": False, "error": f"Window '{title}' not found"}
        w = wins[0]
        try:
            if action == "minimize":
                w.minimize()
            elif action == "maximize":
                w.maximize()
            elif action == "restore":
                w.restore()
            elif action == "close":
                w.close()
            elif action == "activate":
                w.activate()
            return {"success": True, "action": action, "title": w.title}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif tool == "window_get_info":
        if not HAS_PYGETWINDOW:
            return {"success": False, "error": "pygetwindow required"}
        import pygetwindow as gw
        title = args.get("title", "")
        if title:
            wins = gw.getWindowsWithTitle(title)
        else:
            wins = gw.getAllWindows()
        results = []
        for w in wins[:20]:
            try:
                results.append({"title": w.title, "visible": w.visible, "activated": False})
            except:
                pass
        # Get active window
        try:
            active = gw.getActiveWindow()
            active_title = active.title if active else ""
        except:
            active_title = ""
        return {"success": True, "windows": results, "active": active_title}

    elif tool == "send_keys_window":
        title = args.get("title", "") or args.get("window", "")
        keys = args.get("keys", "") or args.get("text", "")
        if not HAS_PYWIN32:
            # Fallback: type directly
            import pyautogui
            if title:
                try:
                    import pygetwindow as gw
                    wins = gw.getWindowsWithTitle(title)
                    if wins:
                        wins[0].activate()
                        time.sleep(0.3)
                except:
                    pass
            pyautogui.write(keys, interval=args.get("interval", 0.02))
            return {"success": True, "sent": keys[:100], "method": "pyautogui"}
        import win32gui, win32con
        import pyautogui
        def enum_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd) and title.lower() in win32gui.GetWindowText(hwnd).lower():
                results.append(hwnd)
        hwnds = []
        win32gui.EnumWindows(enum_callback, hwnds)
        if hwnds:
            win32gui.SetForegroundWindow(hwnds[0])
            time.sleep(0.3)
            pyautogui.write(keys, interval=args.get("interval", 0.02))
            return {"success": True, "sent": keys[:100], "window": win32gui.GetWindowText(hwnds[0])}
        return {"success": False, "error": f"Window '{title}' not found"}

    # ── System Control ─────────────────────────────────────────────
    elif tool == "system_volume":
        action = args.get("action", "get")
        value = args.get("value")
        if HAS_PYWIN32:
            try:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                if action == "get":
                    current = volume.GetMasterVolumeLevelScalar()
                    return {"success": True, "volume": round(current * 100), "muted": volume.GetMute()}
                elif action == "set" and value is not None:
                    volume.SetMasterVolumeLevelScalar(max(0.0, min(1.0, value / 100)), None)
                    return {"success": True, "volume": value}
                elif action == "up":
                    current = volume.GetMasterVolumeLevelScalar()
                    step = (value or 10) / 100
                    volume.SetMasterVolumeLevelScalar(min(1.0, current + step), None)
                    return {"success": True, "volume": round(min(1.0, current + step) * 100)}
                elif action == "down":
                    current = volume.GetMasterVolumeLevelScalar()
                    step = (value or 10) / 100
                    volume.SetMasterVolumeLevelScalar(max(0.0, current - step), None)
                    return {"success": True, "volume": round(max(0.0, current - step) * 100)}
                elif action == "mute":
                    volume.SetMute(1, None)
                    return {"success": True, "muted": True}
                elif action == "unmute":
                    volume.SetMute(0, None)
                    return {"success": True, "muted": False}
                elif action == "toggle_mute":
                    current = volume.GetMute()
                    volume.SetMute(not current, None)
                    return {"success": True, "muted": not current}
            except ImportError:
                pass
        # Fallback using pyautogui keyboard
        if action == "get":
            return {"success": True, "note": "Volume query requires pycaw. Try: pip install pycaw comtypes"}
        if action == "mute":
            import pyautogui
            pyautogui.press("volumemute")
            return {"success": True, "method": "keyboard"}
        if action == "up":
            import pyautogui
            for _ in range(value or 10):
                pyautogui.press("volumeup")
            return {"success": True, "method": "keyboard"}
        if action == "down":
            import pyautogui
            for _ in range(value or 10):
                pyautogui.press("volumedown")
            return {"success": True, "method": "keyboard"}
        return {"success": False, "error": "Volume control not available"}

    elif tool == "system_brightness":
        action = args.get("action", "get")
        value = args.get("value")
        try:
            import screen_brightness_control as sbc
            if action == "get":
                current = sbc.get_brightness()
                return {"success": True, "brightness": current[0] if current else 0}
            elif action == "set" and value is not None:
                sbc.set_brightness(max(0, min(100, value)))
                return {"success": True, "brightness": value}
            return {"success": False, "error": f"Unknown brightness action: {action}"}
        except ImportError:
            return {"success": False, "error": "screen_brightness_control required. Install: pip install screen-brightness-control"}

    elif tool == "power_control":
        action = args.get("action", "")
        if action == "shutdown":
            os.system("shutdown /s /t 5")
            return {"success": True, "action": "shutdown"}
        elif action == "restart":
            os.system("shutdown /r /t 5")
            return {"success": True, "action": "restart"}
        elif action == "sleep":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return {"success": True, "action": "sleep"}
        elif action == "hibernate":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 1,0,0")
            return {"success": True, "action": "hibernate"}
        elif action == "lock":
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return {"success": True, "action": "lock"}
        elif action == "logoff":
            os.system("shutdown /l")
            return {"success": True, "action": "logoff"}
        return {"success": False, "error": f"Unknown power action: {action}"}

    elif tool == "service_control":
        action = args.get("action", "status")
        name = args.get("name", "")
        if not name:
            return {"success": False, "error": "Service name required"}
        try:
            if action == "status":
                r = subprocess.run(f'sc query "{name}"', shell=True, capture_output=True, text=True)
                return {"success": True, "output": r.stdout, "name": name}
            elif action == "start":
                subprocess.run(f'net start "{name}"', shell=True, capture_output=True, text=True)
                return {"success": True, "action": "start", "name": name}
            elif action == "stop":
                subprocess.run(f'net stop "{name}"', shell=True, capture_output=True, text=True)
                return {"success": True, "action": "stop", "name": name}
            elif action == "restart":
                subprocess.run(f'net stop "{name}"', shell=True, capture_output=True, text=True)
                time.sleep(1)
                subprocess.run(f'net start "{name}"', shell=True, capture_output=True, text=True)
                return {"success": True, "action": "restart", "name": name}
            return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Environment / Scripts ──────────────────────────────────────
    elif tool == "env_get":
        var = args.get("variable", "") or args.get("var", "")
        if var:
            return {"success": True, "variable": var, "value": os.environ.get(var, "")}
        return {"success": True, "variables": dict(sorted(os.environ.items()))}

    elif tool == "run_script":
        script = args.get("script", "") or args.get("content", "")
        lang = args.get("language", "") or args.get("lang", "")
        path = args.get("path", "")
        try:
            if path:
                ext = os.path.splitext(path)[1].lower()
                if ext in (".ps1",):
                    r = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", path],
                                       capture_output=True, text=True, timeout=args.get("timeout", 60))
                elif ext in (".bat", ".cmd"):
                    r = subprocess.run([path], shell=True, capture_output=True, text=True, timeout=args.get("timeout", 60))
                elif ext in (".py",):
                    r = subprocess.run(["python", path], capture_output=True, text=True, timeout=args.get("timeout", 60))
                else:
                    r = subprocess.run([path], shell=True, capture_output=True, text=True, timeout=args.get("timeout", 60))
                return {"success": r.returncode == 0, "output": r.stdout + r.stderr, "returncode": r.returncode}
            if script:
                if lang in ("powershell", "ps1"):
                    r = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", script],
                                       capture_output=True, text=True, timeout=args.get("timeout", 60))
                elif lang in ("python", "py"):
                    r = subprocess.run(["python", "-c", script],
                                       capture_output=True, text=True, timeout=args.get("timeout", 60))
                elif lang in ("batch", "bat", "cmd"):
                    r = subprocess.run(script, shell=True, capture_output=True, text=True, timeout=args.get("timeout", 60))
                else:
                    r = subprocess.run(script, shell=True, capture_output=True, text=True, timeout=args.get("timeout", 60))
                return {"success": r.returncode == 0, "output": r.stdout + r.stderr, "returncode": r.returncode}
            return {"success": False, "error": "No script content or path provided"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Script timed out"}

    # ── File Utils ─────────────────────────────────────────────────
    elif tool == "file_compress":
        source = args.get("source", "") or args.get("path", "")
        dest = args.get("dest", "") or args.get("output", "")
        mode = args.get("mode", "zip")
        import shutil
        try:
            if mode == "zip":
                if os.path.isdir(source):
                    shutil.make_archive(dest or source, "zip", source)
                else:
                    import zipfile
                    with zipfile.ZipFile(dest or (source + ".zip"), "w") as zf:
                        zf.write(source, os.path.basename(source))
            elif mode == "unzip":
                import zipfile
                with zipfile.ZipFile(source, "r") as zf:
                    zf.extractall(dest or os.path.dirname(source))
            return {"success": True, "source": source, "dest": dest or (source + ".zip")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif tool == "file_download":
        url = args.get("url", "")
        dest = args.get("dest", "") or args.get("path", "")
        if not url:
            return {"success": False, "error": "URL required"}
        try:
            import urllib.request
            dest = dest or os.path.basename(url.split("?")[0]) or "downloaded_file"
            urllib.request.urlretrieve(url, dest)
            size = os.path.getsize(dest)
            return {"success": True, "path": dest, "size": size}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif tool == "screenshot_region":
        x, y, w, h = args.get("x", 0), args.get("y", 0), args.get("width", 0), args.get("height", 0)
        if not HAS_MSS and not HAS_PYAUTOGUI:
            return {"success": False, "error": "mss or pyautogui required"}
        import base64, io
        from PIL import Image
        if HAS_MSS and w > 0 and h > 0:
            import mss
            with mss.mss() as sct:
                monitor = {"top": y, "left": x, "width": w, "height": h}
                img = sct.grab(monitor)
                pil_img = Image.frombytes("RGB", img.size, img.rgb)
        elif HAS_PYAUTOGUI:
            import pyautogui
            if w > 0 and h > 0:
                pil_img = pyautogui.screenshot(region=(x, y, w, h))
            else:
                pil_img = pyautogui.screenshot()
        else:
            return {"success": False, "error": "Screenshot not available"}
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {"success": True, "image_base64": b64, "width": pil_img.width, "height": pil_img.height}

    # ── Mouse extras ───────────────────────────────────────────────
    elif tool == "mouse_get_pos":
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required"}
        import pyautogui
        x, y = pyautogui.position()
        return {"success": True, "x": x, "y": y}

    elif tool == "mouse_hover":
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required"}
        import pyautogui
        pyautogui.moveTo(args.get("x", 0), args.get("y", 0), duration=args.get("duration", 0.2))
        return {"success": True}

    elif tool == "mouse_right_click":
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required"}
        import pyautogui
        pyautogui.click(args.get("x", None), args.get("y", None), button="right")
        return {"success": True}

    elif tool == "keyboard_hotkey":
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui required"}
        import pyautogui
        keys = args.get("keys", "")
        if isinstance(keys, str):
            keys = keys.split("+")
        pyautogui.hotkey(*keys)
        return {"success": True, "keys": keys}

    # ── Browser ────────────────────────────────────────────────────
    elif tool == "browser_command":
        action = args.get("action", "")
        url = args.get("url", "")
        if action == "open":
            import webbrowser
            webbrowser.open(url or "https://www.google.com")
            return {"success": True, "action": "open", "url": url}
        elif action == "search":
            import webbrowser
            query = args.get("query", "")
            webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
            return {"success": True}
        return {"success": False, "error": f"Unknown browser action: {action}"}

    # ── Fallback ──────────────────────────────────────────────────
    return {"error": f"Tool '{tool}' not implemented in local agent"}


def _fallback_list_files(path="."):
    """Built-in file listing without system_local module."""
    import stat
    try:
        p = Path(path).resolve()
        if not p.exists():
            return {"success": False, "error": f"Path not found: {path}"}
        items = []
        for entry in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                s = entry.stat()
                items.append({
                    "name": entry.name,
                    "path": str(entry),
                    "is_dir": entry.is_dir(),
                    "size": s.st_size if not entry.is_dir() else 0,
                    "modified": s.st_mtime,
                    "created": getattr(s, "st_ctime", 0),
                })
            except (PermissionError, OSError):
                items.append({"name": entry.name, "path": str(entry), "is_dir": entry.is_dir(), "size": 0, "modified": 0, "created": 0})
        return {"success": True, "path": str(p), "items": items, "parent": str(p.parent)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _close_app_by_name(name):
    """Close an app by name — searches windows first, then kills process."""
    if not name:
        return {"success": False, "error": "No app/window name provided. Say 'close Chrome' or 'close Notepad'."}

    # Method 1: Close via window title (pygetwindow)
    if HAS_PYGETWINDOW:
        import pygetwindow as gw
        try:
            all_wins = gw.getAllWindows()
            matching = [w for w in all_wins if w.title and name.lower() in w.title.lower()]
            if matching:
                closed = []
                for w in matching:
                    try:
                        w.close()
                        closed.append(w.title)
                    except:
                        pass
                if closed:
                    return {"success": True, "closed": closed, "method": "window_title", "count": len(closed)}
        except:
            pass

    # Method 2: Kill process by name
    for proc_name in [name if name.endswith(".exe") else f"{name}.exe",
                      name, f"{name}.EXE"]:
        try:
            r = subprocess.run(["taskkill", "/f", "/im", proc_name],
                               shell=True, capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return {"success": True, "method": "taskkill", "process": proc_name}
        except:
            pass

    # Method 3: psutil-based process kill
    if HAS_PSUTIL:
        import psutil
        killed = []
        for p in psutil.process_iter(["pid", "name"]):
            try:
                if name.lower() in p.info["name"].lower():
                    p.kill()
                    killed.append(p.info["name"])
            except:
                pass
        if killed:
            return {"success": True, "killed": killed, "method": "psutil"}

    return {"success": False, "error": f"Could not find or close '{name}'. No matching window or process found."}


def _fallback_open_file(path=""):
    """Open a file with the default OS handler."""
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=True)
        else:
            subprocess.run(["xdg-open", path], check=True)
        return {"success": True, "path": path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _await_it(coro):
    """Run an async function synchronously."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        import threading
        result = []
        def run():
            r = asyncio.run(coro)
            result.append(r)
        t = threading.Thread(target=run)
        t.start()
        t.join()
        return result[0]
    return loop.run_until_complete(coro)


def _heartbeat_loop():
    """Print a heartbeat every 60 seconds so user knows agent is alive."""
    while True:
        time.sleep(60)
        if sio.connected:
            print(f"[LocalAgent] Alive — connected to {BACKEND_URL}, tools: {len(LOCAL_TOOLS)}")
        else:
            print(f"[LocalAgent] Disconnected. Waiting...")
            break


if __name__ == "__main__":
    _check_deps()

    print("=" * 50)
    print("  SODA Local Agent")
    print("=" * 50)
    print(f"  Machine:  {MACHINE_ID}")
    print(f"  Backend:  {BACKEND_URL}")
    print(f"  Platform: {sys.platform}")
    print(f"  Tools:    {len(LOCAL_TOOLS)}")
    print(f"  Deps:     pyautogui={'OK' if HAS_PYAUTOGUI else 'MISS'}, "
          f"mss={'OK' if HAS_MSS else 'MISS'}, "
          f"pyperclip={'OK' if HAS_PYPERCLIP else 'MISS'}, "
          f"psutil={'OK' if HAS_PSUTIL else 'MISS'}")
    print("=" * 50)

    try:
        sio.connect(BACKEND_URL, transports=["websocket", "polling"], wait_timeout=10)
        # Start heartbeat in background
        threading.Thread(target=_heartbeat_loop, daemon=True).start()
        print(f"[LocalAgent] Waiting for commands from backend...")
        sio.wait()
    except KeyboardInterrupt:
        print("\n[LocalAgent] Shutting down")
        sio.disconnect()
    except Exception as e:
        print(f"[LocalAgent] Failed: {e}")
        traceback.print_exc()
        sys.exit(1)
