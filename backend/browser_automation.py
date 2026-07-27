import atexit
import json
import logging
import os
import re
import subprocess
import tempfile
import threading
import time
from typing import Optional

logger = logging.getLogger("soda.browser_automation")

CDP_PORT_START = 19222
CDP_PORT_END = 19322
SESSION_IDLE_TIMEOUT = 120.0  # ponytail: 120s default, configure via SESSION_IDLE_TIMEOUT env var if needed
CLEANUP_INTERVAL = 30.0
SNAPSHOT_MAX_CHARS = 15000  # truncate snapshots above this, save full to temp file

BOT_WARNINGS = re.compile(r'(captcha|access denied|cloudflare|blocked|automated.*query|unusual.*traffic)', re.IGNORECASE)
SECRET_PATTERNS = [
    (re.compile(r'(?i)(api[_-]?key|apikey|secret|password|passwd|token|auth_token|bearer)\s*[:=]\s*["\']?[A-Za-z0-9_\-\.]{8,}["\']?'), r'\1: ***REDACTED***'),
    (re.compile(r'(?i)(authorization|set-cookie|x-api-key)\s*[:=]\s*["\']?[A-Za-z0-9_\-\.]{8,}["\']?'), r'\1: ***REDACTED***'),
]
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

# ── Element Reference System ──

def assign_refs(snapshot_dict: dict, prefix: str = "e"):
    ref_map = {}
    counter = [0]

    def walk(node):
        if not isinstance(node, dict):
            return node
        ref = f"@{prefix}{counter[0]}"
        counter[0] += 1
        entry = {
            "ref": ref,
            "role": node.get("role", "unknown"),
            "name": node.get("name", ""),
            "value": node.get("value"),
            "disabled": node.get("disabled", False),
            "focused": node.get("focused", False),
            "level": node.get("level"),
        }
        ref_map[ref] = entry
        children = node.get("children")
        if isinstance(children, list):
            entry["children"] = [walk(c) for c in children if isinstance(c, dict)]
        else:
            entry["children"] = []
        return entry

    tree = walk(snapshot_dict) if isinstance(snapshot_dict, dict) else {"role": "error", "name": "empty"}
    return {"tree": tree, "refs": ref_map, "interactive_count": len(ref_map)}


def resolve_ref(ref_map: dict, ref: str) -> dict:
    entry = ref_map.get(ref)
    if not entry:
        raise ValueError(f"Element ref {ref} not found in snapshot. Call browser_snapshot() first to get current refs.")
    return entry


def format_snapshot_result(page, snapshot_data: dict, supervisor_snapshot: dict = None) -> dict:
    result = {
        "url": page.url,
        "title": page.title(),
        "snapshot": snapshot_data,
        "interactive_count": snapshot_data.get("interactive_count", 0),
    }
    if supervisor_snapshot:
        result["pending_dialogs"] = supervisor_snapshot.get("pending_dialogs", [])
        result["console_errors"] = [e for e in supervisor_snapshot.get("console_events", []) if e.get("type") in ("error", "exception")]
    return result


def _redact_secrets(text: str) -> str:
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _truncate_snapshot(snapshot: dict) -> dict:
    raw = json.dumps(snapshot, default=str)
    raw = _redact_secrets(raw)
    if len(raw) <= SNAPSHOT_MAX_CHARS:
        return snapshot
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, prefix="soda-snapshot-")
    tmp.write(raw)
    tmp_path = tmp.name
    tmp.close()
    logger.info(f"Snapshot truncated ({len(raw)} -> {SNAPSHOT_MAX_CHARS} chars), full saved to {tmp_path}")
    truncated = json.loads(raw[:SNAPSHOT_MAX_CHARS])
    truncated["_truncated"] = True
    truncated["_full_path"] = tmp_path
    truncated["_full_size"] = len(raw)
    return truncated


def _check_bot_warning(title: str) -> Optional[str]:
    m = BOT_WARNINGS.search(title)
    if m:
        return f"Bot detection warning: page title contains '{m.group(0)}'. Proceed with caution."
    return None


# ── Chrome Utilities ──

def find_chrome() -> str:
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    which = os.environ.get("PATH", "")
    for dir in which.split(os.pathsep):
        for name in ("chrome.exe", "brave.exe", "msedge.exe"):
            candidate = os.path.join(dir, name)
            if os.path.exists(candidate):
                return candidate
    raise FileNotFoundError("No supported browser found (Chrome, Brave, or Edge)")


_chrome_processes: dict[str, subprocess.Popen] = {}
_cdp_ports: set[int] = set()
_cdp_port_lock = threading.Lock()


def _acquire_cdp_port() -> int:
    with _cdp_port_lock:
        for port in range(CDP_PORT_START, CDP_PORT_END):
            if port not in _cdp_ports:
                _cdp_ports.add(port)
                return port
    raise RuntimeError("No available CDP ports")


def _release_cdp_port(port: int):
    with _cdp_port_lock:
        _cdp_ports.discard(port)


def launch_chrome(session_id: str) -> tuple[int, str, subprocess.Popen]:
    chrome_path = find_chrome()
    port = _acquire_cdp_port()
    user_data = os.path.expandvars(f"%TEMP%\\soda-browser-{session_id}")
    proc = subprocess.Popen(
        [
            chrome_path,
            f"--remote-debugging-port={port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={user_data}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-sync",
            "--disable-extensions",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    cdp_url = _wait_for_cdp(port, timeout=15.0)
    _chrome_processes[session_id] = proc
    return port, cdp_url, proc


def _wait_for_cdp(port: int, timeout: float = 15.0) -> str:
    import requests
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=2)
            if resp.status_code == 200:
                return resp.json()["webSocketDebuggerUrl"]
        except (requests.ConnectionError, ValueError):
            pass
        time.sleep(0.5)
    raise TimeoutError(f"CDP endpoint not ready on port {port}")


def kill_chrome(session_id: str):
    proc = _chrome_processes.pop(session_id, None)
    if proc and proc.poll() is None:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass


# ── BrowserSession ──

class BrowserSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._cdp_port = None
        self._cdp_url = None
        self._chrome_proc = None
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._supervisor = None
        self._last_activity = time.time()
        self._ref_map = {}
        self._dialog_mode = "dismiss"  # dismiss | accept | prompt
        self._crashed = False

    def start(self):
        logger.info(f"[{self.session_id}] Starting browser session...")
        self._cdp_port, cdp_browser_url, self._chrome_proc = launch_chrome(self.session_id)
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{self._cdp_port}")
        self._context = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = self._context.new_page()
        self._page.set_viewport_size({"width": 1280, "height": 720})
        self._page.on("dialog", self._handle_dialog)
        self._page.on("console", self._handle_console)
        self._page.on("page", lambda p: None)
        from cdp_supervisor import CDPSupervisor
        try:
            supervisor_url = cdp_browser_url.replace("/devtools/browser/", f"/devtools/browser/")
            self._supervisor = CDPSupervisor(cdp_browser_url, self.session_id)
            self._supervisor.start()
        except Exception as e:
            logger.warning(f"[{self.session_id}] CDP supervisor start failed: {e}")
        self.touch()
        logger.info(f"[{self.session_id}] Browser session ready")

    def stop(self):
        logger.info(f"[{self.session_id}] Stopping browser session...")
        if self._supervisor:
            try:
                self._supervisor.stop()
            except Exception:
                pass
            self._supervisor = None
        if self._playwright:
            try:
                if self._page and not self._page.is_closed():
                    self._page.remove_listener("dialog", self._handle_dialog)
                    self._page.close()
                if self._context:
                    self._context.close()
                if self._browser:
                    self._browser.close()
                self._playwright.stop()
            except Exception as e:
                logger.warning(f"[{self.session_id}] Playwright cleanup: {e}")
            self._playwright = None
        kill_chrome(self.session_id)
        if self._cdp_port:
            _release_cdp_port(self._cdp_port)
            self._cdp_port = None
        logger.info(f"[{self.session_id}] Browser session stopped")

    def touch(self):
        self._last_activity = time.time()

    @property
    def idle_seconds(self) -> float:
        return time.time() - self._last_activity

    def _ensure_page(self):
        if self._crashed:
            logger.info(f"[{self.session_id}] Session was crashed, restarting...")
            self.stop()
            self.__init__(self.session_id)
            self.start()
            self._crashed = False
        if not self._page or self._page.is_closed():
            try:
                self._page = self._context.new_page() if self._context else None
            except Exception:
                logger.warning(f"[{self.session_id}] Context dead, restarting session...")
                self._crashed = True
                self._ensure_page()
                return
            if self._page:
                self._page.on("dialog", self._handle_dialog)
                self._page.on("console", self._handle_console)

    def _handle_dialog(self, dialog):
        from playwright.sync_api import Dialog
        logger.info(f"[{self.session_id}] Dialog: {dialog.type} - {dialog.message[:100]}")
        if self._dialog_mode == "accept":
            dialog.accept()
        elif self._dialog_mode == "dismiss":
            dialog.dismiss()
        else:
            dialog.dismiss()

    def _handle_console(self, msg):
        if msg.type in ("error", "warning"):
            logger.debug(f"[{self.session_id}] Console {msg.type}: {msg.text[:200]}")

    # ── Tool Handlers ──

    def navigate(self, url: str) -> dict:
        self._ensure_page()
        try:
            self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self.touch()
            result = self.snapshot(full=False)
            if result.get("success"):
                warning = _check_bot_warning(self._page.title())
                if warning:
                    result["bot_warning"] = warning
            return result
        except Exception as e:
            return {"success": False, "error": f"Navigation failed: {e}"}

    def snapshot(self, full: bool = False) -> dict:
        self._ensure_page()
        try:
            acc_tree = self._page.accessibility.snapshot()
            if acc_tree is None:
                return {"success": False, "error": "No accessibility tree available"}
            snap = assign_refs(acc_tree)
            self._ref_map = snap["refs"]
            supervisor_state = self._supervisor.snapshot() if self._supervisor else None
            result = format_snapshot_result(self._page, snap, supervisor_state)
            result["success"] = True
            result["snapshot"] = _truncate_snapshot(result["snapshot"])
            warning = _check_bot_warning(result.get("title", ""))
            if warning:
                result["bot_warning"] = warning
            self.touch()
            return result
        except Exception as e:
            return {"success": False, "error": f"Snapshot failed: {e}"}

    def click(self, ref: str) -> dict:
        self._ensure_page()
        try:
            entry = resolve_ref(self._ref_map, ref)
            locator = self._page.get_by_role(entry["role"], name=entry.get("name", ""))
            locator.click(timeout=10000)
            self.touch()
            return {"success": True, "clicked": ref, "role": entry["role"], "name": entry.get("name", "")}
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Click failed: {e}"}

    def type_text(self, ref: str, text: str) -> dict:
        self._ensure_page()
        try:
            entry = resolve_ref(self._ref_map, ref)
            locator = self._page.get_by_role(entry["role"], name=entry.get("name", ""))
            locator.fill(text, timeout=10000)
            self.touch()
            return {"success": True, "typed_into": ref}
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Type failed: {e}"}

    def scroll(self, direction: str = "down") -> dict:
        self._ensure_page()
        try:
            if direction == "top":
                js = "window.scrollTo(0, 0)"
            elif direction == "bottom":
                js = "window.scrollTo(0, document.body.scrollHeight)"
            elif direction == "up":
                js = "window.scrollBy(0, -window.innerHeight * 0.8)"
            else:
                js = "window.scrollBy(0, window.innerHeight * 0.8)"
            self._page.evaluate(js)
            self.touch()
            return {"success": True, "direction": direction}
        except Exception as e:
            return {"success": False, "error": f"Scroll failed: {e}"}

    def go_back(self) -> dict:
        self._ensure_page()
        try:
            self._page.go_back(wait_until="domcontentloaded")
            self.touch()
            return self.snapshot(full=False)
        except Exception as e:
            return {"success": False, "error": f"Back failed: {e}"}

    def press_key(self, key: str) -> dict:
        self._ensure_page()
        try:
            self._page.keyboard.press(key)
            self.touch()
            return {"success": True, "key": key}
        except Exception as e:
            return {"success": False, "error": f"Key press failed: {e}"}

    def vision_qa(self, question: str) -> dict:
        self._ensure_page()
        try:
            screenshot_bytes = self._page.screenshot(full_page=False)
            import base64, io
            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            import google.genai as genai
            import os as _os
            key = _os.getenv("GEMINI_API_KEY", "")
            if not key:
                return {"success": False, "error": "GEMINI_API_KEY not configured"}
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[question, genai.types.Part.from_bytes(data=screenshot_bytes, mime_type="image/png")],
            )
            self.touch()
            return {"success": True, "analysis": response.text}
        except Exception as e:
            return {"success": False, "error": f"Vision analysis failed: {e}"}

    def get_console(self) -> dict:
        if not self._supervisor:
            return {"success": True, "console_events": []}
        snap = self._supervisor.snapshot()
        self.touch()
        return {"success": True, "console_events": snap.get("console_events", [])}

    def get_images(self) -> dict:
        self._ensure_page()
        try:
            images = self._page.evaluate("""() => {
                return Array.from(document.images).map(img => ({
                    src: img.src || '',
                    alt: img.alt || '',
                    width: img.naturalWidth || 0,
                    height: img.naturalHeight || 0,
                })).filter(img => img.src);
            }""")
            self.touch()
            return {"success": True, "images": images, "count": len(images)}
        except Exception as e:
            return {"success": False, "error": f"Get images failed: {e}"}

    def handle_dialog(self, action: str, text: str = None) -> dict:
        if action in ("auto_accept", "auto_dismiss", "auto_prompt"):
            self._dialog_mode = action.replace("auto_", "")
            return {"success": True, "mode": self._dialog_mode}
        if not self._supervisor:
            return {"success": False, "error": "CDP supervisor not available"}
        snap = self._supervisor.snapshot()
        dialogs = snap.get("pending_dialogs", [])
        if not dialogs:
            return {"success": True, "result": "No pending dialogs"}
        dialog = dialogs[0]
        dialog_id = dialog.get("id", 0)
        result = self._supervisor.respond_dialog(dialog_id, action, text)
        self.touch()
        return {"success": result.get("success", False), "dialog": dialog, "result": result}

    def cdp_command(self, method: str, params: dict = None) -> dict:
        if not self._supervisor:
            return {"success": False, "error": "CDP supervisor not available"}
        try:
            import asyncio
            coro = self._supervisor.send_cdp(method, params or {})
            future = asyncio.run_coroutine_threadsafe(coro, self._supervisor._loop)
            result = future.result(timeout=30)
            self.touch()
            return {"success": True, "method": method, "result": result}
        except Exception as e:
            return {"success": False, "error": f"CDP command failed: {e}"}


# ── BrowserSessionManager ──

class BrowserSessionManager:
    _instances: dict[str, BrowserSession] = {}
    _lock = threading.RLock()
    _cleanup_thread: Optional[threading.Thread] = None
    _running = False

    @classmethod
    def get_or_create(cls, session_id: str) -> BrowserSession:
        with cls._lock:
            if session_id not in cls._instances:
                session = BrowserSession(session_id)
                session.start()
                cls._instances[session_id] = session
                cls._ensure_cleanup_daemon()
            else:
                cls._instances[session_id].touch()
            return cls._instances[session_id]

    @classmethod
    def get(cls, session_id: str) -> Optional[BrowserSession]:
        with cls._lock:
            return cls._instances.get(session_id)

    @classmethod
    def close(cls, session_id: str):
        with cls._lock:
            session = cls._instances.pop(session_id, None)
            if session:
                try:
                    session.stop()
                except Exception as e:
                    logger.error(f"Error stopping session {session_id}: {e}")

    @classmethod
    def close_all(cls):
        with cls._lock:
            for sid in list(cls._instances.keys()):
                try:
                    cls._instances[sid].stop()
                except Exception as e:
                    logger.error(f"Error stopping session {sid}: {e}")
            cls._instances.clear()

    @classmethod
    def _ensure_cleanup_daemon(cls):
        if cls._running:
            return
        cls._running = True
        cls._cleanup_thread = threading.Thread(target=cls._cleanup_loop, daemon=True, name="browser-cleanup")
        cls._cleanup_thread.start()

    @classmethod
    def _cleanup_loop(cls):
        while cls._running:
            time.sleep(CLEANUP_INTERVAL)
            with cls._lock:
                now = time.time()
                for sid in list(cls._instances.keys()):
                    session = cls._instances[sid]
                    if session.idle_seconds > SESSION_IDLE_TIMEOUT:
                        logger.info(f"Closing idle session: {sid} ({session.idle_seconds:.0f}s idle)")
                        try:
                            session.stop()
                        except Exception as e:
                            logger.error(f"Cleanup error for {sid}: {e}")
                        del cls._instances[sid]

    @classmethod
    def cleanup_for_sid(cls, sid: str):
        cls.close(sid)


atexit.register(BrowserSessionManager.close_all)


# ── Standalone Tool Handlers (called by local_agent.py) ──

def _get_session(kwargs: dict) -> BrowserSession:
    session_id = kwargs.pop("task_id", "default")
    return BrowserSessionManager.get_or_create(session_id)


def tool_navigate(url: str, **kw) -> dict:
    session = _get_session(kw)
    return session.navigate(url)


def tool_snapshot(full: bool = False, **kw) -> dict:
    session = _get_session(kw)
    return session.snapshot(full=full)


def tool_click(ref: str, **kw) -> dict:
    session = _get_session(kw)
    return session.click(ref)


def tool_type(ref: str, text: str, **kw) -> dict:
    session = _get_session(kw)
    return session.type_text(ref, text)


def tool_scroll(direction: str = "down", **kw) -> dict:
    session = _get_session(kw)
    return session.scroll(direction)


def tool_back(**kw) -> dict:
    session = _get_session(kw)
    return session.go_back()


def tool_press(key: str, **kw) -> dict:
    session = _get_session(kw)
    return session.press_key(key)


def tool_vision(question: str, **kw) -> dict:
    session = _get_session(kw)
    return session.vision_qa(question)


def tool_console(**kw) -> dict:
    session = _get_session(kw)
    return session.get_console()


def tool_get_images(**kw) -> dict:
    session = _get_session(kw)
    return session.get_images()


def tool_dialog(action: str, text: str = None, **kw) -> dict:
    session = _get_session(kw)
    return session.handle_dialog(action, text)


def tool_cdp(method: str, params: str = "{}", **kw) -> dict:
    session = _get_session(kw)
    try:
        params_dict = json.loads(params) if isinstance(params, str) else params
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON in params"}
    return session.cdp_command(method, params_dict)


TOOL_ROUTER = {
    "browser_navigate": tool_navigate,
    "browser_snapshot": tool_snapshot,
    "browser_click": tool_click,
    "browser_type": tool_type,
    "browser_scroll": tool_scroll,
    "browser_back": tool_back,
    "browser_press": tool_press,
    "browser_vision": tool_vision,
    "browser_console": tool_console,
    "browser_get_images": tool_get_images,
    "browser_dialog": tool_dialog,
    "browser_cdp": tool_cdp,
}


def dispatch(tool: str, args: dict) -> dict:
    handler = TOOL_ROUTER.get(tool)
    if not handler:
        return {"success": False, "error": f"Unknown browser tool: {tool}"}
    try:
        return handler(**args)
    except Exception as e:
        logger.exception(f"Error dispatching {tool}")
        return {"success": False, "error": str(e)}
