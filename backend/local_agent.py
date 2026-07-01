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
from tool_abort import abort, clear, AbortError
from pathlib import Path

# Ensure backend/ directory is on the path
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

# ── File Logging (pythonw.exe has no console, so log() is invisible) ──
# PID suffix prevents zombie/duplicate agent log interleaving
_agent_pid = os.getpid()
_agent_log_file = os.path.join(os.path.dirname(_script_dir), f"agent_{_agent_pid}.log")

def log(msg):
    """Write to both stdout AND agent.log (pythonw.exe-safe)."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    # Print still works when running with python.exe (for testing)
    try:
        log(line, flush=True)
    except:
        pass
    # Always write to file (works with pythonw.exe too)
    try:
        with open(_agent_log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass

BACKEND_URL = os.getenv("BACKEND_URL", "https://soda-backend-sar2.onrender.com")
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
    "terminal_execute", "execute_command", "open_app", "list_installed_apps", "refresh_app_registry", "close_window", "close_app",
    "control_system", "screenshot", "screenshot_region",
    "clipboard_read", "clipboard_write",
    "mouse_click", "mouse_move", "mouse_scroll", "mouse_drag",
    "mouse_get_pos", "mouse_hover", "mouse_right_click",
    "keyboard_type", "keyboard_press", "keyboard_hotkey",
    "window_focus", "window_list", "window_move",
    "window_manage", "window_get_info",
    "send_whatsapp", "whatsapp_find_and_call", "whatsapp_find_and_message",
    "check_whatsapp", "reply_whatsapp", "read_whatsapp_chat",
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
    "app_search", "app_scroll",
    "browser_automate",
    "credential_save", "credential_get", "credential_list", "credential_delete",
]

HAS_PYAUTOGUI = False
HAS_MSS = False
HAS_PYPERCLIP = False
HAS_PYWIN32 = False
HAS_PYGETWINDOW = False
HAS_PSUTIL = False
HAS_CV2 = False

# ── App Registry ──
# Cached map of app names -> launch info for instant open_app lookups.
_script_root = os.path.dirname(os.path.abspath(__file__))
_app_registry_cache = os.path.join(_script_root, "..", "app_registry.json")
APP_REGISTRY: dict[str, dict] = {}  # name_lower -> {paths: [{path, method}], aliases: [str], name: str}


def _build_app_registry():
    """Scan Start Menu, registry, AppX, and known paths to build APP_REGISTRY.
    Returns the registry dict and saves cache to app_registry.json."""
    from collections import defaultdict
    entries = defaultdict(list)  # name_lower -> list of {path, method, display}

    def _add(name, path, method, display=None):
        if not path or not os.path.isfile(path):
            return
        name_lower = name.lower().strip()
        for existing in entries[name_lower]:
            if existing["path"].lower() == path.lower():
                return
        entries[name_lower].append({
            "path": path,
            "method": method,
            "display": display or os.path.splitext(os.path.basename(path))[0],
        })

    log("[AppRegistry] Scanning installed apps...")

    # ── 1. Start Menu shortcuts ──
    for sm_env in ("APPDATA", "PROGRAMDATA"):
        sm_base = os.path.expandvars(f"%{sm_env}%\\Microsoft\\Windows\\Start Menu\\Programs")
        if not os.path.isdir(sm_base):
            continue
        try:
            for root, dirs, files in os.walk(sm_base):
                for f in files:
                    if f.lower().endswith(".lnk"):
                        name_no_ext = os.path.splitext(f)[0]
                        shortcut_path = os.path.join(root, f)
                        _add(name_no_ext, shortcut_path, "start_menu", name_no_ext)
                        # Also add by folder category (e.g., "Accessories\Notepad")
                        rel = os.path.relpath(root, sm_base)
                        if rel and rel != ".":
                            cat_name = f"{name_no_ext} ({os.path.basename(rel)})"
                            _add(cat_name, shortcut_path, "start_menu", name_no_ext)
        except Exception as e:
            log(f"[AppRegistry] Start Menu scan error: {e}")

    # ── 2. App Paths registry ──
    try:
        import winreg
        for root_key in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                key = winreg.OpenKey(root_key, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
                count = winreg.QueryInfoKey(key)[0]
                for i in range(count):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)
                        exe_path = winreg.QueryValue(subkey, "")
                        winreg.CloseKey(subkey)
                        if exe_path and os.path.isfile(exe_path):
                            name = subkey_name.lower().replace(".exe", "").replace(".cmd", "").replace(".bat", "")
                            display = os.path.splitext(subkey_name)[0]
                            _add(name, exe_path, "registry", display)
                            _add(display, exe_path, "registry", display)
                    except:
                        pass
                winreg.CloseKey(key)
            except:
                pass
    except Exception as e:
        log(f"[AppRegistry] Registry scan error: {e}")

    # ── 3. AppX / Microsoft Store packages ──
    try:
        ps_cmd = (
            "Get-AppxPackage | Where-Object { $_.InstallLocation } | ForEach-Object { "
            "  $manifest = [xml](Get-Content (Join-Path $_.InstallLocation 'AppxManifest.xml') -ErrorAction SilentlyContinue); "
            "  if ($manifest.Package.Applications.Application) { "
            "    $appId = $manifest.Package.Applications.Application.Id; "
            "    $aumid = \"$($_.PackageFamilyName)!$appId\"; "
            "    $name = $_.Name; "
            "    $display = if ($manifest.Package.Applications.Application.VisualElements.DisplayName -and $manifest.Package.Applications.Application.VisualElements.DisplayName -notmatch '^ms-resource') { $manifest.Package.Applications.Application.VisualElements.DisplayName } else { $_.Name }; "
            "    Write-Output \"$name||$display||$aumid\" "
            "  } "
            "}"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                parts = line.strip().split("||")
                if len(parts) >= 3:
                    pkg_name, display_name, aumid = parts[0], parts[1], parts[2]
                    appx_path = f"shell:AppsFolder\\{aumid}"
                    _add(pkg_name, appx_path, "appx", display_name)
                    _add(display_name, appx_path, "appx", display_name)
        log(f"[AppRegistry] Scanned AppX packages")
    except Exception as e:
        log(f"[AppRegistry] AppX scan error: {e}")

    # ── 4. Known system utilities (guaranteed to exist) ──
    system_utils = {
        "notepad": r"C:\Windows\System32\notepad.exe",
        "calculator": r"C:\Windows\System32\calc.exe",
        "paint": r"C:\Windows\System32\mspaint.exe",
        "cmd": r"C:\Windows\System32\cmd.exe",
        "command prompt": r"C:\Windows\System32\cmd.exe",
        "powershell": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "explorer": r"C:\Windows\explorer.exe",
        "file explorer": r"C:\Windows\explorer.exe",
        "wordpad": r"C:\Program Files\Windows NT\Accessories\wordpad.exe",
        "snipping tool": r"C:\Windows\System32\SnippingTool.exe",
        "character map": r"C:\Windows\System32\charmap.exe",
        "task manager": r"C:\Windows\System32\Taskmgr.exe",
        "regedit": r"C:\Windows\regedit.exe",
        "control panel": r"C:\Windows\System32\control.exe",
        "settings": r"C:\Windows\System32\SystemSettings.exe",
    }
    for name, path in system_utils.items():
        _add(name, path, "system", name)

    # ── 5. Common third-party app locations ──
    common_paths = [
        (r"C:\Program Files", 2),
        (r"C:\Program Files (x86)", 2),
        (os.path.expandvars(r"%LOCALAPPDATA%\Programs"), 2),
        (os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps"), 1),
    ]
    for base, max_depth in common_paths:
        if not os.path.isdir(base):
            continue
        try:
            for root, dirs, files in os.walk(base):
                depth = root.replace(base, "").count(os.sep)
                if depth > max_depth:
                    dirs.clear()
                    continue
                for f in files:
                    if f.lower().endswith(".exe") and f.lower() not in ("uninstall.exe", "setup.exe"):
                        name = os.path.splitext(f)[0]
                        full_path = os.path.join(root, f)
                        _add(name, full_path, "common", name)
                        _add(os.path.basename(root), full_path, "common", name)
        except:
            pass

    # ── Build final registry ──
    global APP_REGISTRY
    APP_REGISTRY = {}
    for name_lower, path_list in entries.items():
        sorted_paths = sorted(path_list, key=lambda x: (
            0 if x["method"] in ("system", "registry") else
            1 if x["method"] == "start_menu" else
            2 if x["method"] == "common" else 3
        ))
        APP_REGISTRY[name_lower] = {
            "paths": sorted_paths,
            "name": sorted_paths[0]["display"] if sorted_paths else name_lower,
            "aliases": [],
        }

    # ── Generate aliases for multi-word names ──
    for name_lower, entry in list(APP_REGISTRY.items()):
        words = name_lower.replace("-", " ").replace("_", " ").split()
        if len(words) > 1:
            for w in words:
                if len(w) > 3 and w not in APP_REGISTRY:
                    entry["aliases"].append(w)

    # ── Save cache ──
    try:
        cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app_registry.json")
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(APP_REGISTRY, f, indent=2, ensure_ascii=False)
        log(f"[AppRegistry] Cached {len(APP_REGISTRY)} apps to {cache_path}")
    except Exception as e:
        log(f"[AppRegistry] Cache save error: {e}")

    log(f"[AppRegistry] ✅ Registry built: {len(APP_REGISTRY)} entries")
    return APP_REGISTRY


def _find_app(name):
    """Look up an app name in APP_REGISTRY by name or alias. Returns (entry, matched_key) or None."""
    key = name.lower().strip()
    if key in APP_REGISTRY:
        return APP_REGISTRY[key], key
    for reg_key, entry in APP_REGISTRY.items():
        if key in entry.get("aliases", []):
            return entry, reg_key
        if key in reg_key or reg_key in key:
            return entry, reg_key
    return None


def _load_app_registry():
    """Load cached registry, or build it if missing."""
    global APP_REGISTRY
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app_registry.json")
    if os.path.isfile(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                APP_REGISTRY = json.load(f)
            log(f"[AppRegistry] Loaded {len(APP_REGISTRY)} apps from cache")
            return True
        except Exception as e:
            log(f"[AppRegistry] Cache load error: {e}")
    return False


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


_reconnect_count = 0
_last_connected = None


@sio.event
def connect():
    global _reconnect_count, _last_connected
    _reconnect_count = 0
    _last_connected = time.strftime("%Y-%m-%d %H:%M:%S")
    log(f"[LocalAgent] ✅ Connected to {BACKEND_URL}")
    # Register with app registry stats
    registry_info = {"count": len(APP_REGISTRY)} if APP_REGISTRY else {}
    sio.emit("agent_register", {
        "token": AGENT_TOKEN,
        "machine_id": MACHINE_ID,
        "platform": sys.platform,
        "tools": LOCAL_TOOLS,
        "app_registry": registry_info,
    })
    log(f"[LocalAgent] Registered as {MACHINE_ID} ({len(LOCAL_TOOLS)} tools, {len(APP_REGISTRY)} apps)")


@sio.event
def connect_error(data):
    _reconnect_count += 1
    log(f"[LocalAgent] ❌ Connection error ({_reconnect_count}): {data}")
    log(f"[LocalAgent]    Check: (1) Backend at {BACKEND_URL} is running, (2) Internet is up, (3) No firewall blocking")


@sio.event
def disconnect():
    log(f"[LocalAgent] ⚠️  Disconnected from {BACKEND_URL}")
    log(f"[LocalAgent]    Last connected: {_last_connected or 'never'}")
    abort()


@sio.on("agent_execute")
def on_agent_execute(data):
    tool = data.get("tool", "")
    args = data.get("args", {})
    callback_id = data.get("callback_id", "")

    clear()
    log(f"[LocalAgent] Executing: {tool}({json.dumps(args)[:200]})")

    def _run():
        try:
            result = _dispatch(tool, args)
            sio.emit("agent_tool_result", {
                "callback_id": callback_id,
                "tool": tool,
                "result": result,
                "success": True,
            })
        except AbortError:
            log(f"[LocalAgent] Tool {tool} aborted (frontend disconnected)")
            try:
                sio.emit("agent_tool_result", {
                    "callback_id": callback_id,
                    "tool": tool,
                    "result": {"success": False, "error": "Tool aborted — frontend disconnected"},
                    "success": False,
                })
            except Exception:
                pass
        except Exception as e:
            tb = traceback.format_exc()
            log(f"[LocalAgent] Error executing {tool}: {e}")
            log(tb)
            sio.emit("agent_tool_result", {
                "callback_id": callback_id,
                "tool": tool,
                "result": {"error": str(e)},
                "success": False,
            })

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


@sio.on("agent_status")
def on_agent_status(data):
    log(f"[LocalAgent] Status: {data}")


# ── Generic app window helpers (for app_search / app_scroll) ──
def _find_app_window(app_name):
    """Find a visible window whose title contains app_name. Returns hwnd or None."""
    if not HAS_PYWIN32:
        return None
    import win32gui, win32con
    matches = []
    def enum_cb(hwnd, _matches):
        if win32gui.IsWindowVisible(hwnd):
            text = win32gui.GetWindowText(hwnd)
            if app_name.lower() in text.lower():
                _matches.append(hwnd)
        return True
    win32gui.EnumWindows(enum_cb, matches)
    return matches[0] if matches else None


def _get_any_window_rect(app_name):
    """Get the screen rect of the first visible window matching app_name.
    Returns (left, top, right, bottom) or None."""
    hwnd = _find_app_window(app_name)
    if not hwnd:
        return None
    try:
        import win32gui
        return win32gui.GetWindowRect(hwnd)
    except:
        return None


def _focus_any_app(app_name):
    """Bring a window matching app_name to the foreground. Returns True on success."""
    hwnd = _find_app_window(app_name)
    if not hwnd:
        return False
    try:
        import win32gui, win32con
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.2)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        return True
    except:
        return False


def _focus_or_open_app(app_name):
    """Try to focus an app window, or open it via open_app. Returns True if focused."""
    if _focus_any_app(app_name):
        return True
    try:
        result = _dispatch("open_app", {"name": app_name})
        time.sleep(2.0)
        return _focus_any_app(app_name)
    except Exception as e:
        log.warning(f"[app_helper] Could not open '{app_name}': {e}")
        return False


def _screenshot_window_region(app_name):
    """Take a screenshot of the app window. Returns PNG bytes or None."""
    if not HAS_MSS:
        return None
    rect = _get_any_window_rect(app_name)
    if not rect:
        return None
    left, top, right, bottom = rect
    w = right - left
    h = bottom - top
    if w < 50 or h < 50:
        return None
    try:
        import mss
        with mss.mss() as sct:
            img = sct.grab({"left": left, "top": top, "width": w, "height": h})
            return mss.tools.to_png(img.rgb, img.size)
    except:
        return None


# ── Chrome profile detection ──────────────────────────────────────
CHROME_USER_DATA = os.path.expandvars(
    r"%LOCALAPPDATA%\Google\Chrome\User Data"
)
_CREDENTIALS_KEY = None
_CREDENTIALS_FILE = Path("credentials.json.enc")
_CREDENTIALS_KEY_FILE = Path("credentials.key")


def _detect_chrome_profile(profile_name=None):
    """Find Chrome profile directory by display name.
    Reads Chrome's Local State file to map profile names to directories.
    Returns profile directory name (e.g. 'Profile 1') or 'Default'."""
    local_state = Path(CHROME_USER_DATA) / "Local State"
    if not local_state.exists():
        log.warning(f"[Chrome] Local State not found at {local_state}")
        return "Default"
    try:
        import json
        data = json.loads(local_state.read_text(encoding="utf-8"))
        info_cache = data.get("profile", {}).get("info_cache", {})
        if profile_name:
            for prof_dir, info in info_cache.items():
                if profile_name.lower() in info.get("name", "").lower():
                    log.info(f"[Chrome] Found profile '{profile_name}' → {prof_dir}")
                    return prof_dir
        # Fallback: return first non-Default profile, or Default
        for prof_dir, info in info_cache.items():
            if prof_dir != "Default":
                return prof_dir
        return "Default"
    except Exception as e:
        log.warning(f"[Chrome] Profile detection failed: {e}")
        return "Default"


def _launch_chrome_url(url):
    """Open URL in Chrome using the user's profile. Returns True on success."""
    import shutil
    profile_dir = _detect_chrome_profile("rahikulmakhtum")
    chrome_exe = (
        shutil.which("chrome")
        or shutil.which("google-chrome")
        or shutil.which("googlechrome")
        or rf"C:\Program Files\Google\Chrome\Application\chrome.exe"
        or os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    )
    if not chrome_exe or not os.path.isfile(chrome_exe):
        log.warning("[Chrome] chrome.exe not found")
        return False
    try:
        subprocess.Popen([
            chrome_exe, f"--profile-directory={profile_dir}",
            "--new-window", url
        ], shell=False)
        time.sleep(2.0)
        return True
    except Exception as e:
        log.warning(f"[Chrome] Launch failed: {e}")
        return False


def _focus_chrome():
    """Focus any visible Chrome window. Returns True on success."""
    for name in ("chrome", "google chrome", "google_chrome", "chromium"):
        if _focus_any_app(name):
            return True
    return False


# ── Credential Manager ─────────────────────────────────────────────
def _get_fernet():
    """Get or create a Fernet key for credential encryption."""
    global _CREDENTIALS_KEY
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None
    if _CREDENTIALS_KEY:
        return Fernet(_CREDENTIALS_KEY)
    if _CREDENTIALS_KEY_FILE.exists():
        _CREDENTIALS_KEY = _CREDENTIALS_KEY_FILE.read_bytes()
    else:
        _CREDENTIALS_KEY = Fernet.generate_key()
        _CREDENTIALS_KEY_FILE.write_bytes(_CREDENTIALS_KEY)
    return Fernet(_CREDENTIALS_KEY)


def _load_credentials():
    """Decrypt and load all credentials. Returns list of dicts."""
    f = _get_fernet()
    if not f or not _CREDENTIALS_FILE.exists():
        return []
    try:
        encrypted = _CREDENTIALS_FILE.read_bytes()
        decrypted = f.decrypt(encrypted)
        import json
        return json.loads(decrypted.decode())
    except Exception as e:
        log.warning(f"[Credential] Load failed: {e}")
        return []


def _save_credentials(entries):
    """Encrypt and save all credentials."""
    f = _get_fernet()
    if not f:
        return False
    try:
        import json
        plain = json.dumps(entries, indent=2).encode()
        encrypted = f.encrypt(plain)
        _CREDENTIALS_FILE.write_bytes(encrypted)
        return True
    except Exception as e:
        log.warning(f"[Credential] Save failed: {e}")
        return False


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

        # ── WhatsApp intercept: open_app("whatsapp") → check_whatsapp ──
        if app_lower in ("whatsapp", "whatapp", "watsapp", "whats app", "what's app", "whats"):
            log.info(f"[WA] open_app('{app_lower}') intercepted → redirecting to check_whatsapp")
            try:
                from whatsapp_bridge import check_whatsapp_sync
                result = check_whatsapp_sync()
                result["_intercepted_from"] = "open_app"
                return result
            except ImportError:
                log.warning("[WA] whatsapp_bridge not available for intercept")
            except Exception as e:
                log.warning(f"[WA] intercept failed: {e}")

        def _verify_started(path_or_name=None, timeout=3.0):
            """Check that the app actually launched. Returns (ok: bool, detail: str)."""
            # Method 1: Check if process started (psutil) — most reliable
            if HAS_PSUTIL and path_or_name and os.path.isfile(path_or_name):
                import psutil as _psutil
                exe_name = os.path.basename(path_or_name).lower()
                before = set()
                try:
                    before = set(p.info['pid'] for p in _psutil.process_iter(['pid', 'name']))
                except:
                    pass
                time.sleep(timeout)
                after = set()
                try:
                    after = set(p.info['pid'] for p in _psutil.process_iter(['pid', 'name']))
                except:
                    pass
                new_pids = after - before
                for pid in new_pids:
                    try:
                        p = _psutil.Process(pid)
                        if exe_name in p.name().lower() or exe_name.replace('.exe','') in p.name().lower():
                            return (True, f"Process {p.name()} (PID {pid}) started")
                    except:
                        pass
                # Give it one more chance — some apps start via a launcher
                time.sleep(2.0)
                try:
                    after2 = set(p.info['pid'] for p in _psutil.process_iter(['pid', 'name']))
                    new_pids2 = after2 - before
                    for pid in new_pids2:
                        try:
                            p = _psutil.Process(pid)
                            return (True, f"Process {p.name()} (PID {pid}) started (delayed)")
                        except:
                            pass
                except:
                    pass
                # psutil matched nothing — return false instead of falling through
                return (False, f"No new process matching '{os.path.basename(path_or_name)}' detected")

            # Method 2: Check for new window (pygetwindow) — only used when psutil not available
            if HAS_PYGETWINDOW:
                import pygetwindow as gw
                try:
                    before = set(w.title.strip() for w in gw.getAllWindows() if w.title.strip() and len(w.title.strip()) > 2)
                except:
                    before = set()
                time.sleep(timeout)
                try:
                    after = set(w.title.strip() for w in gw.getAllWindows() if w.title.strip() and len(w.title.strip()) > 2)
                except:
                    after = set()
                new_windows = after - before
                if new_windows:
                    new_title = new_windows.pop()
                    # Only confirm if window title relates to app name
                    if not path_or_name or app_lower in new_title.lower() or any(w in new_title.lower() for w in path_or_name.lower().replace('.exe','').replace('.lnk','').split('\\')):
                        return (True, f"Window opened: '{new_title}'")
                    # Window appeared but doesn't match — might be a false positive
                    return (False, f"Unrelated window '{new_title}' appeared, target app not confirmed")
                # Try once more after delay
                time.sleep(2.0)
                try:
                    after2 = set(w.title.strip() for w in gw.getAllWindows() if w.title.strip() and len(w.title.strip()) > 2)
                except:
                    after2 = set()
                new_windows2 = after2 - before
                if new_windows2:
                    new_title = new_windows2.pop()
                    if not path_or_name or app_lower in new_title.lower() or any(w in new_title.lower() for w in path_or_name.lower().replace('.exe','').replace('.lnk','').split('\\')):
                        return (True, f"Window opened (delayed): '{new_title}'")
                    return (False, f"Unrelated window '{new_title}' appeared, target app not confirmed")

            # No verification available — return false instead of guessing success
            return (False, "Could not verify if app launched (no process or window detection available)")

        def _launch(path_or_name):
            """Try to launch, returns (ok, detail)."""
            try:
                subprocess.Popen([path_or_name], shell=False)
                return _verify_started(path_or_name)
            except:
                try:
                    subprocess.Popen(["start", "", path_or_name], shell=True)
                    return _verify_started()
                except Exception as e:
                    return (False, str(e))

        # ── 0. URI scheme (fastest) ───────────────────────────────
        _URI_APPS = {
            "whatsapp": "whatsapp://", "telegram": "tg://", "discord": "discord://",
            "zoom": "zoommtg://", "teams": "msteams://", "skype": "skype://",
            "signal": "signal://",
        }
        # ── Web apps: open in default browser via https ────────────
        _WEB_APPS = {
            "youtube": "https://youtube.com", "yt": "https://youtube.com",
            "spotify": "https://open.spotify.com", "twitter": "https://twitter.com",
            "x": "https://x.com", "facebook": "https://facebook.com",
            "instagram": "https://instagram.com", "linkedin": "https://linkedin.com",
            "reddit": "https://reddit.com", "github": "https://github.com",
            "gmail": "https://mail.google.com", "maps": "https://maps.google.com",
            "drive": "https://drive.google.com", "docs": "https://docs.google.com",
            "sheets": "https://sheets.google.com", "netflix": "https://netflix.com",
            "twitch": "https://twitch.com", "chatgpt": "https://chat.openai.com",
            "gpt": "https://chat.openai.com", "claude": "https://claude.ai",
            "gemini": "https://gemini.google.com",
        }
        if app_lower in _URI_APPS:
            try:
                subprocess.Popen(["start", "", _URI_APPS[app_lower]], shell=True)
                _ok, _detail = _verify_started()
                if _ok:
                    return {"success": True, "app": app, "method": "uri", "detail": _detail}
            except:
                pass

        # ── 0b. Web apps (open in browser) ─────────────────────────
        if app_lower in _WEB_APPS:
            url = _WEB_APPS[app_lower]
            log.info(f"[LocalAgent] Opening web app '{app}' → {url}")
            if _launch_chrome_url(url):
                _ok, _detail = _verify_started()
                if _ok:
                    return {"success": True, "app": app, "url": url, "method": "web_app_chrome", "detail": _detail}
                return {"success": True, "app": app, "url": url, "method": "web_app_chrome", "detail": f"Opened {url} in Chrome"}
            try:
                subprocess.Popen(["start", "", url], shell=True)
                _ok, _detail = _verify_started()
                if _ok:
                    return {"success": True, "app": app, "url": url, "method": "web_app", "detail": _detail}
                # Even if verify fails, web pages load in tab — trust it
                return {"success": True, "app": app, "url": url, "method": "web_app", "detail": f"Opened {url} in default browser"}
            except Exception as e:
                log.warning(f"[LocalAgent] web_app '{app}' failed: {e}")
                # fall through to other methods

        # ── 1. APP_REGISTRY lookup (instant, no search delay) ────
        reg_match = _find_app(app)
        if reg_match:
            entry, matched_key = reg_match
            for pinfo in entry.get("paths", []):
                p = pinfo["path"]
                method = pinfo.get("method", "registry")
                try:
                    if method == "appx":
                        subprocess.Popen(["explorer", p], shell=False)
                    else:
                        subprocess.Popen([p], shell=False)
                    _ok, _detail = _verify_started(p)
                    if _ok:
                        return {
                            "success": True, "app": app,
                            "path": p, "method": f"registry_{method}",
                            "matched": matched_key, "detail": _detail,
                        }
                except:
                    try:
                        subprocess.Popen(["start", "", p], shell=True)
                        _ok, _detail = _verify_started(p)
                        if _ok:
                            return {
                                "success": True, "app": app,
                                "path": p, "method": f"registry_{method}_start",
                                "matched": matched_key, "detail": _detail,
                            }
                    except:
                        continue

        # ── 2. Search Windows App Paths registry ──────────────────
        try:
            import winreg
            for root_key in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    key = winreg.OpenKey(root_key, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
                    count = winreg.QueryInfoKey(key)[0]
                    for i in range(count):
                        subkey_name = winreg.EnumKey(key, i)
                        if app_lower in subkey_name.lower().replace(".exe", "").replace(".cmd", "").replace(".bat", ""):
                            subkey = winreg.OpenKey(key, subkey_name)
                            try:
                                exe_path = winreg.QueryValue(subkey, "")
                                winreg.CloseKey(subkey)
                                if exe_path and os.path.isfile(exe_path):
                                    _ok, _detail = _launch(exe_path)
                                    if _ok:
                                        return {"success": True, "app": app, "path": exe_path, "method": "registry", "detail": _detail}
                            except:
                                winreg.CloseKey(subkey)
                    winreg.CloseKey(key)
                except:
                    pass
        except:
            pass

        # ── 3. where command (PATH) ───────────────────────────────
        for ext in ("", ".exe", ".cmd", ".bat"):
            try:
                r = subprocess.run(["where", f"{app}{ext}"], shell=True, capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    exe_path = r.stdout.strip().split("\n")[0].strip()
                    _ok, _detail = _launch(exe_path)
                    if _ok:
                        return {"success": True, "app": app, "path": exe_path, "method": "where", "detail": _detail}
            except:
                pass

        # ── 4. Start Menu walk (live scan, slower) ────────────────
        for sm_env in ("APPDATA", "PROGRAMDATA"):
            sm_base = os.path.expandvars(f"%{sm_env}%\\Microsoft\\Windows\\Start Menu\\Programs")
            if not os.path.isdir(sm_base):
                continue
            try:
                for root, dirs, files in os.walk(sm_base):
                    for f in files:
                        if not f.lower().endswith(".lnk"):
                            continue
                        name_no_ext = f.lower().replace(".lnk", "")
                        if app_lower in name_no_ext or name_no_ext in app_lower:
                            shortcut_path = os.path.join(root, f)
                            _ok, _detail = _launch(shortcut_path)
                            if _ok:
                                return {"success": True, "app": app, "path": shortcut_path, "method": "start_menu", "detail": _detail}
            except:
                pass

        # ── 5. AppX / Store packages ──────────────────────────────
        try:
            ps_cmd = (
                "$pkg = Get-AppxPackage -Name '*" + app_lower.replace("'", "''") +
                "*' | Select-Object -First 1; "
                "if ($pkg) { "
                "  $manifest = [xml](Get-Content (Join-Path $pkg.InstallLocation 'AppxManifest.xml')); "
                "  $appId = $manifest.Package.Applications.Application.Id; "
                "  Write-Output \"$($pkg.PackageFamilyName)!$appId\" "
                "}"
            )
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=8)
            if r.returncode == 0 and r.stdout.strip():
                for aumid in r.stdout.strip().split("\n"):
                    aumid = aumid.strip()
                    if not aumid:
                        continue
                    try:
                        subprocess.Popen(["explorer", f"shell:AppsFolder\\{aumid}"], shell=False)
                        _ok, _detail = _verify_started(timeout=3.0)
                        if _ok:
                            return {"success": True, "app": app, "method": "appx", "aumid": aumid, "detail": _detail}
                    except:
                        pass
        except:
            pass

        # ── 6. os.startfile + `start` shell ───────────────────────
        try:
            os.startfile(app)
            _ok, _detail = _verify_started()
            if _ok:
                return {"success": True, "app": app, "method": "startfile", "detail": _detail}
        except:
            pass
        try:
            subprocess.Popen(["start", "", app], shell=True)
            _ok, _detail = _verify_started()
            if _ok:
                return {"success": True, "app": app, "method": "start_cmd", "detail": _detail}
        except:
            pass

        # ── 7. PowerShell SendKeys (Start Menu search) ────────────
        for attempt in range(3):
            try:
                search_ps = (
                    "$null = Add-Type -AssemblyName System.Windows.Forms; "
                    "[System.Windows.Forms.SendKeys]::SendWait('^{ESC}'); "
                    "Start-Sleep -Milliseconds 1000; "
                    "[System.Windows.Forms.SendKeys]::SendWait('" + app.replace("'", "''") + "'); "
                    "Start-Sleep -Milliseconds 2000; "
                    "[System.Windows.Forms.SendKeys]::SendWait('{ENTER}'); "
                    "Start-Sleep -Milliseconds 2000"
                )
                subprocess.run(["powershell", "-NoProfile", "-Command", search_ps], capture_output=True, timeout=8)
                _ok, _detail = _verify_started(timeout=2.0)
                if _ok:
                    return {"success": True, "app": app, "method": "powershell_search", "detail": _detail}
            except:
                time.sleep(1)

        # ── 8. PyAutoGUI fallback ─────────────────────────────────
        if HAS_PYAUTOGUI:
            import pyautogui
            for attempt in range(2):
                try:
                    time.sleep(0.5)
                    pyautogui.hotkey("win", "s")
                    time.sleep(1.0)
                    pyautogui.write(app, interval=0.05)
                    time.sleep(1.5)
                    pyautogui.press("enter")
                    time.sleep(2)
                    _ok, _detail = _verify_started(timeout=1.5)
                    if _ok:
                        return {"success": True, "app": app, "method": "pyautogui_start", "detail": _detail}
                except:
                    time.sleep(1)

        # ── 9. Final fallback: try as website https://{app}.com ────
        if "." not in app_lower and " " not in app_lower:
            web_url = f"https://{app_lower}.com"
            log.info(f"[LocalAgent] Final fallback: trying {web_url} in browser")
            try:
                subprocess.Popen(["start", "", web_url], shell=True)
                return {"success": True, "app": app, "url": web_url, "method": "website_fallback", "detail": f"Could not find '{app}' as an installed app. Opened {web_url} in browser instead."}
            except Exception as e:
                return {"success": False, "error": f"Could not find '{app}' installed on this system. Also failed to open website: {e}", "not_found": True}

        # ── All methods exhausted ─────────────────────────────────
        return {"success": False, "error": f"Could not find '{app}' installed on this system. Try searching the web for it.", "not_found": True}

    elif tool == "list_installed_apps":
        search = (args.get("search", "") or "").lower().strip()
        if not APP_REGISTRY:
            return {"success": False, "error": "App registry not built yet"}
        if search:
            results = {k: v for k, v in APP_REGISTRY.items() if search in k or any(search in a for a in v.get("aliases", []))}
        else:
            results = APP_REGISTRY
        sorted_names = sorted(results.keys())
        return {
            "success": True,
            "total": len(APP_REGISTRY),
            "matching": len(sorted_names),
            "apps": [{"name": results[n]["name"], "key": n, "paths": len(results[n]["paths"])} for n in sorted_names[:200]],
            "hint": "Say the app name to open it, e.g. 'open notepad' or 'launch chrome'",
        }

    elif tool == "refresh_app_registry":
        _build_app_registry()
        return {"success": True, "total": len(APP_REGISTRY), "message": f"Registry rebuilt: {len(APP_REGISTRY)} apps"}

    elif tool == "reconnect":
        log("[LocalAgent] Manual reconnect requested")
        try:
            sio.disconnect()
        except:
            pass
        _connect_with_retry()
        return {"success": True, "message": "Reconnected"}

    elif tool == "close_window":
        name = args.get("name", "") or args.get("window_name", "") or args.get("title", "")
        return _close_app_by_name(name)

    elif tool == "close_app":
        name = args.get("name", "") or args.get("app", "") or args.get("app_name", "")
        return _close_app_by_name(name)

    elif tool == "control_system":
        action = (args.get("action", "") or "").lower()
        value = args.get("value", "") or args.get("val", "")

        # Close app by name
        if action in ("close_app", "close", "exit", "quit"):
            return _close_app_by_name(value or args.get("name", "") or args.get("app", ""))

        # Minimize window
        elif action == "minimize":
            return _dispatch("window_manage", {"title": value, "action": "minimize"})

        # Maximize window
        elif action == "maximize":
            return _dispatch("window_manage", {"title": value, "action": "maximize"})

        # Focus window
        elif action in ("focus", "switch_window"):
            return _dispatch("window_focus", {"title": value})

        # Show desktop
        elif action == "show_desktop":
            if HAS_PYAUTOGUI:
                import pyautogui
                pyautogui.hotkey("win", "d")
                return {"success": True, "action": "show_desktop"}
            return {"success": False, "error": "pyautogui required"}

        # Open app
        elif action == "open_app":
            return _dispatch("open_app", {"name": value})

        # Volume control
        elif action in ("volume_up", "volume_down", "volume_set", "mute", "unmute", "toggle_mute"):
            vol_action = action.replace("volume_", "").replace("volume", "")
            return _dispatch("system_volume", {"action": vol_action or action, "value": value})

        # Brightness
        elif action in ("brightness_up", "brightness_down", "brightness_set"):
            b_action = action.replace("brightness_", "")
            return _dispatch("system_brightness", {"action": b_action, "value": value})

        # Screenshot
        elif action == "screenshot":
            return _dispatch("screenshot", {})

        # Lock screen
        elif action == "lock_screen":
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return {"success": True}

        # Power
        elif action in ("restart", "shutdown", "sleep", "hibernate", "logoff"):
            return _dispatch("power_control", {"action": action})

        # File explorer
        elif action == "file_explorer":
            subprocess.Popen(["explorer.exe"])
            return {"success": True}

        # Type text
        elif action == "type_text":
            if HAS_PYAUTOGUI:
                import pyautogui
                pyautogui.write(value, interval=0.02)
                return {"success": True}
            return {"success": False, "error": "pyautogui required"}

        # Press key
        elif action == "press_key":
            if HAS_PYAUTOGUI:
                import pyautogui
                pyautogui.press(value)
                return {"success": True}
            return {"success": False, "error": "pyautogui required"}

        # Scroll
        elif action in ("scroll_up", "scroll_down"):
            if HAS_PYAUTOGUI:
                import pyautogui
                amount = int(value) if value and value.isdigit() else 3
                pyautogui.scroll(amount if action == "scroll_up" else -amount)
                return {"success": True}
            return {"success": False, "error": "pyautogui required"}

        # Open settings
        elif action == "open_settings":
            subprocess.Popen(["start", "ms-settings:"], shell=True)
            return {"success": True}

        # Task manager
        elif action == "task_manager":
            subprocess.Popen(["taskmgr.exe"])
            return {"success": True}

        # Fallback — catch all errors gracefully
        try:
            from system_control import computer_settings_action
            r = computer_settings_action(action, value)
            if hasattr(r, '__await__'):
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    r = loop.run_until_complete(r)
                except:
                    r = asyncio.run(r)
            return {"success": True, "result": str(r) if r else "done"}
        except:
            return {"success": False, "error": f"control_system action '{action}' not available locally. Try: say 'open (app)', 'close (app)', or 'minimize (window)'"}

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
            from screen_vision import analyze_screen
            b64 = cap.get("image_base64", "")
            import base64, io
            png_bytes = base64.b64decode(b64)
            r = _await_it(analyze_screen(prompt=args.get("prompt", "Describe what you see"), screenshot=png_bytes))
            return r
        except ImportError:
            return {"success": True, "analysis": "Screenshot captured. To analyze, ensure screen_vision module is available."}

    elif tool == "read_screen_text":
        cap = _dispatch("screenshot", {})
        if not cap.get("success"):
            return {"success": False, "error": cap.get("error", "Screenshot failed")}
        try:
            from screen_vision import analyze_screen
            b64 = cap.get("image_base64", "")
            import base64, io
            png_bytes = base64.b64decode(b64)
            r = _await_it(analyze_screen(prompt="Read all text visible in this screenshot. Output exactly what you see.", screenshot=png_bytes))
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

    # ── Messaging ──────────────────────────────────────────────────
    elif tool in ("send_whatsapp", "whatsapp_find_and_call", "whatsapp_find_and_message",
                  "check_whatsapp", "reply_whatsapp", "read_whatsapp_chat"):
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
            target = url or "https://www.google.com"
            if _launch_chrome_url(target):
                return {"success": True, "action": "open", "url": target, "detail": f"Opened {target} in Chrome"}
            subprocess.Popen(["start", "", target], shell=True)
            return {"success": True, "action": "open", "url": target, "detail": f"Opened {target} in system browser"}
        elif action == "search":
            query = args.get("query", "")
            encoded = urllib.parse.quote(query)
            search_url = f"https://www.google.com/search?q={encoded}"
            if _launch_chrome_url(search_url):
                return {"success": True, "action": "search", "query": query, "detail": f"Searched '{query}' in Chrome"}
            subprocess.Popen(["start", "", search_url], shell=True)
            return {"success": True, "action": "search", "query": query, "detail": f"Searched '{query}' in system browser"}
        return {"success": False, "error": f"Unknown browser action: {action}"}

    # ── App search (YouTube, Spotify, etc.) ──────────────────────────
    elif tool == "app_search":
        app_name = args.get("app_name", "")
        query = args.get("query", "")
        search_key = args.get("search_key", "/")
        if not app_name or not query:
            return {"success": False, "error": "app_name and query are required"}
        log(f"[app_search] Searching '{query}' in '{app_name}' (search_key={search_key})")

        if not _focus_or_open_app(app_name):
            return {"success": False, "error": f"Could not open or focus '{app_name}'"}
        time.sleep(1.0)

        if HAS_PYAUTOGUI:
            import pyautogui
            if "+" in search_key:
                keys = [k.strip() for k in search_key.split("+")]
                pyautogui.hotkey(*keys)
            else:
                pyautogui.write(search_key, interval=0.05)
            time.sleep(0.5)
            pyautogui.write(query, interval=0.04)
            time.sleep(0.3)
            pyautogui.press("enter")
            time.sleep(2.0)

            try:
                from screen_vision import analyze_screen
                png_bytes = _screenshot_window_region(app_name)
                if png_bytes:
                    result = _await_it(analyze_screen(
                        prompt=(
                            f"You are looking at search results in the '{app_name}' app.\n"
                            f"User searched for: '{query}'.\n"
                            "STRICT RULES:\n"
                            "TASK: Look at the visible search results.\n"
                            "Only report the items/results you can clearly see.\n"
                            "Do NOT guess or add items not visible.\n"
                            "OUTPUT: List each visible result with its number, title, and key detail."
                        ),
                        screenshot=png_bytes
                    ))
                    result["_app"] = app_name
                    result["_query"] = query
                    return result
            except Exception as e:
                log.warning(f"[app_search] Screenshot failed: {e}")

        return {"success": True, "app": app_name, "query": query, "detail": f"Searched '{query}' in {app_name}"}

    # ── App scroll (up/down in desktop apps) ─────────────────────────
    elif tool == "app_scroll":
        app_name = args.get("app_name", "")
        direction = args.get("direction", "down")
        amount = args.get("amount", 5)
        if not app_name or direction not in ("up", "down"):
            return {"success": False, "error": "app_name and direction required"}
        log(f"[app_scroll] Scrolling {direction} in '{app_name}'")

        if not _focus_or_open_app(app_name):
            return {"success": False, "error": f"Could not focus '{app_name}'"}
        time.sleep(0.5)

        if HAS_PYAUTOGUI:
            import pyautogui
            clicks = -amount if direction == "down" else amount
            pyautogui.scroll(clicks)
            time.sleep(0.5)

            try:
                from screen_vision import analyze_screen
                png_bytes = _screenshot_window_region(app_name)
                if png_bytes:
                    result = _await_it(analyze_screen(
                        prompt=(
                            f"You are looking at the '{app_name}' app after scrolling {direction}.\n"
                            "TASK: List the visible items/results.\n"
                            "Only report what you can CLEARLY SEE.\n"
                            "OUTPUT: List each visible item."
                        ),
                        screenshot=png_bytes
                    ))
                    result["_app"] = app_name
                    result["_direction"] = direction
                    return result
            except Exception as e:
                log.warning(f"[app_scroll] Screenshot failed: {e}")

        return {"success": True, "app": app_name, "direction": direction, "detail": f"Scrolled {direction} in {app_name}"}

    # ── Credential Manager ──────────────────────────────────────────
    elif tool == "credential_save":
        service = args.get("service", "")
        username = args.get("username", "")
        password = args.get("password", "")
        if not all([service, username, password]):
            return {"success": False, "error": "service, username, and password are required"}
        entries = _load_credentials()
        existing = [e for e in entries if e["service"] != service]
        existing.append({"service": service, "username": username, "password": password})
        if _save_credentials(existing):
            return {"success": True, "service": service, "username": username, "detail": f"Saved credentials for {service}"}
        return {"success": False, "error": "Failed to save credentials"}

    elif tool == "credential_get":
        service = args.get("service", "")
        if not service:
            return {"success": False, "error": "service is required"}
        entries = _load_credentials()
        for e in entries:
            if e["service"] == service:
                return {"success": True, "service": service, "username": e["username"], "password": e["password"]}
        return {"success": False, "error": f"No credentials found for {service}"}

    elif tool == "credential_list":
        entries = _load_credentials()
        services = [{"service": e["service"], "username": e["username"]} for e in entries]
        return {"success": True, "services": services, "count": len(services)}

    elif tool == "credential_delete":
        service = args.get("service", "")
        if not service:
            return {"success": False, "error": "service is required"}
        entries = _load_credentials()
        filtered = [e for e in entries if e["service"] != service]
        if len(filtered) == len(entries):
            return {"success": False, "error": f"No credentials found for {service}"}
        if _save_credentials(filtered):
            return {"success": True, "service": service, "detail": f"Deleted credentials for {service}"}
        return {"success": False, "error": "Failed to save"}

    # ── Browser Automation ──────────────────────────────────────────
    elif tool == "browser_automate":
        url = args.get("url", "")
        steps = args.get("steps", [])
        profile = args.get("profile", "rahikulmakhtum")
        if not url:
            return {"success": False, "error": "url is required"}
        if not steps or not isinstance(steps, list):
            return {"success": False, "error": "steps[] is required with at least one step"}

        # Launch Chrome to the URL
        if not _launch_chrome_url(url):
            return {"success": False, "error": "Failed to launch Chrome"}
        if not _focus_chrome():
            time.sleep(2.0)
            _focus_chrome()
        time.sleep(3.0)

        from screen_vision import analyze_screen
        results = []
        overall_success = True

        for i, step in enumerate(steps):
            action = step.get("action", "")
            params = step.get("params", {})
            max_retries = 3 if action in ("click", "type") else 1
            step_ok = False
            last_error = ""

            for attempt in range(max_retries):
                try:
                    if action == "navigate":
                        target_url = params.get("url", url)
                        _launch_chrome_url(target_url)
                        time.sleep(3.0)
                        results.append({"step": i, "action": "navigate", "success": True, "url": target_url})
                        step_ok = True
                        break

                    elif action == "wait":
                        time.sleep(params.get("seconds", 2))
                        results.append({"step": i, "action": "wait", "success": True})
                        step_ok = True
                        break

                    elif action in ("click", "type", "read"):
                        # Take screenshot of Chrome window
                        png_bytes = _screenshot_window_region("chrome")
                        if not png_bytes:
                            last_error = "Could not screenshot Chrome window"
                            time.sleep(1)
                            continue

                        if action == "click":
                            # Vision element location: get coordinates relative to cropped screenshot
                            desc = params.get("description", "the element")
                            import json
                            coords_str = _await_it(analyze_screen(
                                prompt=(
                                    f"You are looking at a screenshot of a Chrome browser.\n"
                                    f"TASK: Find the coordinates (x, y) of: {desc}\n"
                                    f"RULES:\n"
                                    f"- Return ONLY a JSON object with 'x' and 'y' as integers.\n"
                                    f"- Coordinates must be RELATIVE to the screenshot (NOT the full screen).\n"
                                    f"- If you cannot find it, return {{'x': -1, 'y': -1}}.\n"
                                    f"Do NOT include any other text."
                                ),
                                screenshot=png_bytes
                            ))
                        else:
                            vision_prompt = params.get("prompt", "Describe what you see on this page")

                        if action == "click":
                            try:
                                coords = json.loads(coords_str) if isinstance(coords_str, str) else coords_str
                            except:
                                try:
                                    import re
                                    m = re.search(r'\{\s*"x"\s*:\s*(-?\d+)\s*,\s*"y"\s*:\s*(-?\d+)\s*\}', coords_str if isinstance(coords_str, str) else str(coords_str))
                                    if m:
                                        coords = {"x": int(m.group(1)), "y": int(m.group(2))}
                                    else:
                                        raise ValueError("No coordinates found")
                                except:
                                    last_error = f"Could not parse coordinates from Vision: {coords_str}"
                                    time.sleep(1)
                                    continue
                            if coords.get("x", -1) < 0 or coords.get("y", -1) < 0:
                                last_error = f"Vision could not find '{desc}'"
                                time.sleep(1)
                                continue

                            # Validate coordinates against window bounds
                            rect = _get_any_window_rect("chrome")
                            if rect:
                                screen_x = rect[0] + coords["x"]
                                screen_y = rect[1] + coords["y"]
                                if screen_x < rect[0] or screen_x > rect[2] or screen_y < rect[1] or screen_y > rect[3]:
                                    last_error = f"Coordinates ({screen_x},{screen_y}) out of window bounds {rect}"
                                    time.sleep(1)
                                    continue
                            else:
                                screen_x, screen_y = coords["x"], coords["y"]

                            if not HAS_PYAUTOGUI:
                                last_error = "pyautogui required for click"
                                continue
                            import pyautogui
                            pyautogui.moveTo(screen_x, screen_y, duration=0.3)
                            time.sleep(0.2)
                            pyautogui.click()
                            time.sleep(1.0)
                            results.append({"step": i, "action": "click", "success": True, "element": desc, "coordinates": {"x": screen_x, "y": screen_y}})
                            step_ok = True
                            break

                        elif action == "type":
                            text = params.get("text", "")
                            if not text:
                                last_error = "No text provided for typing"
                                continue
                            # Click target first
                            desc = params.get("target", "the input field")
                            import json as _json
                            _inner_png = _screenshot_window_region("chrome")
                            if not _inner_png:
                                last_error = "Could not screenshot"
                                continue
                            _target_coords = _await_it(analyze_screen(
                                prompt=(
                                    f"You are looking at a Chrome screenshot.\n"
                                    f"TASK: Find the coordinates (x, y) of: {desc}\n"
                                    f"Return ONLY a JSON object with 'x' and 'y' integers relative to the screenshot.\n"
                                    f"If not found, return {{'x': -1, 'y': -1}}."
                                ),
                                screenshot=_inner_png
                            ))
                            try:
                                _tc = _json.loads(_target_coords) if isinstance(_target_coords, str) else _target_coords
                            except:
                                last_error = f"Could not parse target coordinates: {_target_coords}"
                                continue
                            _tc_x = _tc.get("x", -1)
                            _tc_y = _tc.get("y", -1)
                            if _tc_x < 0 or _tc_y < 0:
                                last_error = f"Vision could not find '{desc}'"
                                continue
                            _inner_rect = _get_any_window_rect("chrome")
                            _sx = (_inner_rect[0] if _inner_rect else 0) + _tc_x
                            _sy = (_inner_rect[1] if _inner_rect else 0) + _tc_y
                            import pyautogui as _pg
                            _pg.moveTo(_sx, _sy, duration=0.3)
                            time.sleep(0.2)
                            _pg.click()
                            time.sleep(0.5)
                            _pg.write(text, interval=0.05)
                            if params.get("press_enter"):
                                _pg.press("enter")
                            time.sleep(1.0)
                            results.append({"step": i, "action": "type", "success": True, "target": desc, "text_length": len(text)})
                            step_ok = True
                            break

                        elif action == "read":
                            text_result = _await_it(analyze_screen(
                                prompt=vision_prompt,
                                screenshot=png_bytes
                            ))
                            results.append({"step": i, "action": "read", "success": True, "content": text_result})
                            step_ok = True
                            break

                except Exception as e:
                    last_error = str(e)
                    time.sleep(1)
                    continue

            if not step_ok:
                overall_success = False
                results.append({"step": i, "action": action, "success": False, "error": last_error or "Failed after retries"})

        return {
            "success": overall_success,
            "url": url,
            "profile": profile,
            "steps_executed": len(results),
            "results": results
        }

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


def _start_abort_monitor():
    """Daemon thread that monitors socket connection and signals abort on disconnect.
    Runs continuously (never breaks) so reconnects are also monitored.
    Runs independently of the socketio callback thread so it can detect disconnection
    even while a tool is executing synchronously."""
    def monitor():
        while True:
            if not sio.connected:
                abort()
            time.sleep(0.2)
    t = threading.Thread(target=monitor, daemon=True)
    t.start()


def _heartbeat_loop():
    """Print a heartbeat every 30 seconds so user knows agent is alive.
    Also sends agent_pong so the server can detect stale agents."""
    while True:
        time.sleep(30)
        if sio.connected:
            try:
                sio.emit('agent_pong', {'ts': time.time()})
            except Exception:
                pass
            log(f"[LocalAgent] Alive — connected to {BACKEND_URL} | {len(LOCAL_TOOLS)} tools loaded")
        else:
            log(f"[LocalAgent] Disconnected — will auto-reconnect...")


def _connect_with_retry():
    """Connect to backend with exponential backoff retry. Never exits on failure."""
    retry_delay = 1
    max_delay = 60
    global _reconnect_count
    local_attempt = 0
    while True:
        try:
            local_attempt += 1
            _reconnect_count = local_attempt
            log(f"[LocalAgent] Connecting to {BACKEND_URL} (attempt {local_attempt})...")
            sio.connect(BACKEND_URL, transports=["websocket", "polling"], wait_timeout=10)
            log(f"[LocalAgent] ✅ Connected (attempt {local_attempt})")
            retry_delay = 1
            _reconnect_count = 0
            return
        except socketio.exceptions.ConnectionError as e:
            log(f"[LocalAgent] ❌ Socket.IO connection rejected: {e}")
        except Exception as e:
            log(f"[LocalAgent] ❌ Connection failed: {type(e).__name__}: {e}")
            import traceback as _tb
            log(f"[LocalAgent]    Detail: {_tb.format_exc()[:200]}")
        log(f"[LocalAgent]    Retry #{local_attempt} in {retry_delay}s...")
        time.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, max_delay)


if __name__ == "__main__":
    _check_deps()

    log("=" * 50)
    log("  SODA Local Agent")
    log("=" * 50)
    log(f"  Machine:  {MACHINE_ID}")
    log(f"  Backend:  {BACKEND_URL}")
    log(f"  Platform: {sys.platform}")
    log(f"  Tools:    {len(LOCAL_TOOLS)}")
    log(f"  Log:      {_agent_log_file}")
    log(f"  Deps:     pyautogui={'OK' if HAS_PYAUTOGUI else 'MISS'}, "
          f"mss={'OK' if HAS_MSS else 'MISS'}, "
          f"pyperclip={'OK' if HAS_PYPERCLIP else 'MISS'}, "
          f"psutil={'OK' if HAS_PSUTIL else 'MISS'}, "
          f"pygetwindow={'OK' if HAS_PYGETWINDOW else 'MISS'}")
    log("=" * 50)

    # ── Build app registry (scan installed apps) ──
    if not _load_app_registry():
        log("[AppRegistry] No cached registry found — scanning installed apps...")
        try:
            _build_app_registry()
        except Exception as e:
            log(f"[AppRegistry] Build error: {e}")
    else:
        log(f"[AppRegistry] Using cached registry ({len(APP_REGISTRY)} apps)")
    log(f"[AppRegistry] {len(APP_REGISTRY)} apps available for instant launch")

    while True:
        try:
            _connect_with_retry()
            # Start background threads
            _start_abort_monitor()
            threading.Thread(target=_heartbeat_loop, daemon=True).start()
            log(f"[LocalAgent] ✅ ALIVE — waiting for commands from backend...")
            log(f"[LocalAgent] 💡 Say something to SODA in the browser, like 'open Notepad' or 'list my desktop files'")
            sio.wait()
        except KeyboardInterrupt:
            log("\n[LocalAgent] Shutting down")
            sio.disconnect()
            break
        except Exception as e:
            log(f"[LocalAgent] ⚠️  Connection lost: {type(e).__name__}: {e}")
            import traceback as _tb
            log(f"[LocalAgent]    {_tb.format_exc()[:300]}")
            log(f"[LocalAgent] Reconnecting in 3s...")
            time.sleep(3)
            continue
