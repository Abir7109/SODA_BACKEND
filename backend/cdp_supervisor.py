import asyncio
import json
import logging
import threading
import time
from typing import Optional

logger = logging.getLogger("soda.cdp_supervisor")

DIALOG_BRIDGE_SCRIPT = """
(function() {
    if (window.__sodaDialogBridge) return;
    window.__sodaDialogBridge = true;
    var origAlert = window.alert;
    var origConfirm = window.confirm;
    var origPrompt = window.prompt;
    window.alert = function(msg) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/__soda_dialog_bridge__/alert?message=' + encodeURIComponent(String(msg)), false);
        xhr.send();
    };
    window.confirm = function(msg) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/__soda_dialog_bridge__/confirm?message=' + encodeURIComponent(String(msg)), false);
        xhr.send();
        return xhr.status === 200 && xhr.responseText === 'true';
    };
    window.prompt = function(msg, def) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/__soda_dialog_bridge__/prompt?message=' + encodeURIComponent(String(msg)) + '&default=' + encodeURIComponent(String(def || '')), false);
        xhr.send();
        return xhr.status === 200 ? xhr.responseText : def;
    };
})();
"""


class CDPSupervisor:
    def __init__(self, cdp_url: str, task_id: str):
        self.cdp_url = cdp_url
        self.task_id = task_id
        self._ws = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._msg_id = 0
        self._pending_calls: dict[int, asyncio.Future] = {}
        self._pending_dialogs: list[dict] = []
        self._console_events: list[dict] = []
        self._frame_tree: dict = {}
        self._running = False
        self._lock = threading.RLock()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name=f"cdp-supervisor-{self.task_id}")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._ws and self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._close_ws(), self._loop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    async def _close_ws(self):
        if self._ws:
            await self._ws.close()
            self._ws = None

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "pending_dialogs": list(self._pending_dialogs),
                "console_events": list(self._console_events[-50:]),
                "frame_tree": dict(self._frame_tree) if self._frame_tree else {},
                "connected": self._ws is not None and self._running,
            }

    def respond_dialog(self, dialog_id: int, action: str, text: Optional[str] = None) -> dict:
        if not self._loop or self._loop.is_closed():
            return {"success": False, "error": "CDP supervisor not running"}
        future = asyncio.run_coroutine_threadsafe(
            self._do_respond_dialog(dialog_id, action, text), self._loop
        )
        try:
            return future.result(timeout=10)
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def send_cdp(self, method: str, params: dict = None) -> dict:
        if not self._ws:
            return {"error": "CDP not connected"}
        self._msg_id += 1
        msg_id = self._msg_id
        future = asyncio.get_event_loop().create_future()
        self._pending_calls[msg_id] = future
        try:
            await self._ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
            result = await asyncio.wait_for(future, timeout=30)
            return result.get("result", {})
        except asyncio.TimeoutError:
            return {"error": f"CDP method {method} timed out"}
        finally:
            self._pending_calls.pop(msg_id, None)

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_loop())
        self._loop.close()

    async def _connect_loop(self):
        import websockets
        backoff = 0.5
        while self._running:
            try:
                async with websockets.connect(self._cdp_browser_url(), max_size=0) as ws:
                    self._ws = ws
                    backoff = 0.5
                    await self._send("Target.setAutoAttach", {"autoAttach": True, "flatten": True, "waitForDebuggerOnStart": False})
                    await self._send("Target.getTargets")
                    await self._listen(ws)
            except Exception as e:
                logger.warning(f"[{self.task_id}] CDP supervisor disconnected: {e}")
                if not self._running:
                    break
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10.0)

    def _cdp_browser_url(self) -> str:
        if "/devtools/browser/" in self.cdp_url:
            return self.cdp_url
        return self.cdp_url.replace("/devtools/page/", "/devtools/browser/")

    async def _send(self, method: str, params: dict = None):
        if not self._ws:
            return
        self._msg_id += 1
        await self._ws.send(json.dumps({"id": self._msg_id, "method": method, "params": params or {}}))

    async def _listen(self, ws):
        async for raw in ws:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if "id" in data:
                future = self._pending_calls.pop(data["id"], None)
                if future and not future.done():
                    future.set_result(data)
            else:
                self._on_event(data)

    def _on_event(self, data: dict):
        method = data.get("method", "")
        params = data.get("params", {})
        if method == "Page.javascriptDialogOpening":
            with self._lock:
                entry = {
                    "id": len(self._pending_dialogs),
                    "type": params.get("type"),
                    "message": params.get("message"),
                    "default_prompt": params.get("defaultPrompt"),
                    "has_browser_handler": params.get("hasBrowserHandler", False),
                    "ts": time.time(),
                }
                self._pending_dialogs.append(entry)
        elif method == "Page.javascriptDialogClosed":
            with self._lock:
                self._pending_dialogs = [d for d in self._pending_dialogs if d.get("id") != params.get("dialogId")]
        elif method == "Runtime.consoleAPICalled":
            with self._lock:
                args = []
                for a in params.get("args", []):
                    if isinstance(a, dict):
                        args.append(a.get("value", a.get("description", str(a))))
                    else:
                        args.append(str(a))
                self._console_events.append({
                    "type": params.get("type", "log"),
                    "args": args,
                    "ts": time.time(),
                })
                if len(self._console_events) > 50:
                    self._console_events.pop(0)
        elif method == "Runtime.exceptionThrown":
            exc = params.get("exceptionDetails", {})
            with self._lock:
                self._console_events.append({
                    "type": "exception",
                    "text": exc.get("text", ""),
                    "url": exc.get("url", ""),
                    "line": exc.get("lineNumber", 0),
                    "ts": time.time(),
                })
                if len(self._console_events) > 50:
                    self._console_events.pop(0)
        elif method == "Target.targetCreated":
            target = params.get("targetInfo", {})
            with self._lock:
                self._frame_tree[target.get("targetId", "")] = {
                    "url": target.get("url", ""),
                    "type": target.get("type", ""),
                    "title": target.get("title", ""),
                }
        elif method == "Target.targetDestroyed":
            tid = params.get("targetId", "")
            with self._lock:
                self._frame_tree.pop(tid, None)
