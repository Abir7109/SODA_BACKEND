# SODA Browser Automation — Implementation Plan

> Based on Hermes Agent (NousResearch) browser automation architecture
> Integration target: SODA v2 Tactical HUD

---

## Table of Contents

1. [Current State vs Target State](#1-current-state-vs-target-state)
2. [Architecture Overview](#2-architecture-overview)
3. [Component Specifications](#3-component-specifications)
4. [Element Reference System](#4-element-reference-system)
5. [CDP Supervisor](#5-cdp-supervisor)
6. [Snapshot Output Format](#6-snapshot-output-format)
7. [Tool Definitions](#7-tool-definitions)
8. [Implementation Phases](#8-implementation-phases)
9. [Files Summary](#9-files-summary)
10. [Open Questions](#10-open-questions)

---

## 1. Current State vs Target State

### What SODA Currently Does for Browser Automation

SODA's current browser automation is **vision-based**:

```
User asks to do something in browser
  → Launch Chrome via subprocess
  → Screenshot Chrome window
  → Send screenshot to Gemini Vision API (costs money, slow)
  → Gemini returns pixel coordinates
  → PyAutoGUI moves mouse and clicks/types at those coordinates
  → Repeat for every action
```

**Problems:**
- Fragile: font size, zoom level, window position all break coordinates
- Slow: each action needs an AI vision API call (1-3 seconds)
- Expensive: Gemini Vision API costs per screenshot
- No DOM access: can't read page structure, execute JS, get console errors
- No dialog handling: alerts/confirms/prompts crash the flow
- No multi-tab: single Chrome window, no tab awareness

### What We're Building (Hermes-Style Automation)

```
User asks to do something in browser
  → Playwright connects to Chrome via CDP (Chrome DevTools Protocol)
  → Get accessibility tree — structured, machine-readable page representation
  → Each element gets a ref ID like @e23
  → Click/type by ref ID — Playwright locators are deterministic
  → CDP Supervisor monitors dialogs, console errors, frames
  → Screenshot + AI Vision only when visual understanding is needed
```

**Key improvements:**
- Deterministic: DOM-based element selection never misses
- Free: no AI API cost for navigation, clicking, typing
- Fast: sub-millisecond DOM queries vs seconds per AI vision call
- Structured: accessibility tree gives roles, states, values — not raw pixels
- Extensible: CDP gives full DevTools access for future features

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                      SODA CLOUD BACKEND                              │
│                                                                      │
│  backend/tools.py                                                    │
│    12 new Hermes-style function declarations added to tools_list     │
│    + existing tools kept unchanged (backward compatible)             │
│                                                                      │
│  backend/soda.py:_dispatch_tool()                                    │
│    Routes hermest browser tools → LOCAL_AGENT_TOOLS                  │
│    Same pattern as existing browser_command/browser_automate         │
│    Timeout: 5-30s depending on tool                                  │
│                                                                      │
│  backend/server.py                                                   │
│    agent_execute → Socket.IO → local_agent.py (unchanged)            │
│    agent_tool_result ← Socket.IO ← local_agent.py (unchanged)        │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ Socket.IO
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│                      LOCAL AGENT (Windows PC)                        │
│                                                                      │
│  backend/local_agent.py:_dispatch()                                  │
│    tool.startswith("browser_") → routes to BrowserSessionManager     │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              backend/browser_automation.py                    │    │
│  │                                                               │    │
│  │  BrowserSessionManager (singleton)                            │    │
│  │    ├─ get_or_create(session_id) → BrowserSession             │    │
│  │    ├─ close(session_id)                                      │    │
│  │    ├─ close_all()                                            │    │
│  │    └─ Idle cleanup daemon (120s timeout)                     │    │
│  │                                                               │    │
│  │  BrowserSession (per task_id)                                 │    │
│  │    ├─ Owns: Playwright instance                               │    │
│  │    ├─ Owns: CDP-connected Chromium browser                    │    │
│  │    ├─ Owns: BrowserContext + Page                             │    │
│  │    ├─ Owns: CDPSupervisor thread                              │    │
│  │    └─ Methods: navigate, snapshot, click, type_text,          │    │
│  │                scroll, go_back, press_key, vision_qa,         │    │
│  │                get_console, get_images, handle_dialog,        │    │
│  │                cdp_command                                    │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              backend/cdp_supervisor.py                        │    │
│  │                                                               │    │
│  │  CDPSupervisor (daemon thread per session)                    │    │
│  │    ├─ Persistent WebSocket to Chrome DevTools                 │    │
│  │    ├─ Subscribes: Page, Runtime, Target CDP domains           │    │
│  │    ├─ Tracks: pending dialogs, console errors, frame tree     │    │
│  │    ├─ Reconnect: exponential backoff 0.5s → 10s              │    │
│  │    └─ Dialog bridge: intercepts alert/confirm/prompt          │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  Element Reference System (built into browser_automation.py) │    │
│  │                                                               │    │
│  │  Ref format:  "role::name"  (e.g. "button::Submit")          │    │
│  │  Display:     "@e0", "@e1"  (short ref IDs in snapshot)      │    │
│  │  Resolution:  page.get_by_role(role, name=name)              │    │
│  │  Key property: locators auto-retry and never go stale        │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  backend/install_browser_deps.ps1 (install script)                   │
│    ├─ pip install playwright                                          │
│    └─ python -m playwright install chromium                          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Specifications

### 3.1 `backend/browser_automation.py` (~800 lines)

**New file.** Core browser automation module implementing 12 Hermes-style tools.

#### Class: `BrowserSessionManager`

Singleton managing all active browser sessions.

```python
class BrowserSessionManager:
    """Thread-safe singleton managing per-task browser sessions."""
    
    _instances: dict[str, 'BrowserSession'] = {}
    _lock = threading.RLock()
    _cleanup_thread: threading.Thread = None
    _running = False
    
    @classmethod
    def get_or_create(cls, session_id: str) -> 'BrowserSession'
        """Get existing session or create new one (launches Chrome)."""
    
    @classmethod
    def get(cls, session_id: str) -> Optional['BrowserSession']
        """Get existing session or None."""
    
    @classmethod
    def close(cls, session_id: str)
        """Close session, stop CDP supervisor, kill Chrome."""
    
    @classmethod
    def close_all(cls)
        """Emergency cleanup — closes every session."""
    
    @classmethod
    def _start_cleanup_daemon(cls)
        """Background thread: evict idle sessions every 30s."""
```

#### Class: `BrowserSession`

One session per concurrent task. Owns all browser resources.

```python
class BrowserSession:
    """A single browser automation session tied to a task."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._playwright = None
        self._browser = None    # CDP-connected browser
        self._context = None    # BrowserContext
        self._page = None       # Page
        self._cdp_session = None
        self._supervisor = None
        self._last_activity = 0.0
        self._lock = threading.RLock()
    
    def start(self) -> dict
        """1. Find Chrome executable
           2. Launch Chrome with --remote-debugging-port=<port>
           3. Wait for CDP endpoint to be ready
           4. playwright.chromium.connect_over_cdp(endpoint)
           5. Create CDP session: context.new_cdp_session(page)
           6. Start CDPSupervisor daemon thread
           7. Set up dialog handler (page.on("dialog"))
        """
    
    def stop(self)
        """1. Stop CDP supervisor
           2. Close CDP session
           3. Close page
           4. Close context
           5. Close browser (if we launched it)
           6. Stop Playwright
           7. Kill Chrome process (if we launched it)
        """
    
    def touch(self)
        """Update last activity timestamp (prevent idle eviction)."""
    
    # ── Tool Handlers ──
    
    def navigate(self, url: str) -> dict
        """Navigate to URL, wait for domcontentloaded, auto-snapshot."""
    
    def snapshot(self, full: bool = False) -> dict
        """Get accessibility tree, assign refs, merge CDP state."""
    
    def click(self, ref: str) -> dict
        """Parse ref → role+name → locator.click()."""
    
    def type_text(self, ref: str, text: str) -> dict
        """Parse ref → role+name → locator.fill(text)."""
    
    def scroll(self, direction: str = "down") -> dict
        """page.evaluate(window.scrollBy/scrollTo)."""
    
    def go_back(self) -> dict
        """page.go_back()."""
    
    def press_key(self, key: str) -> dict
        """page.keyboard.press(key)."""
    
    def vision_qa(self, question: str) -> dict
        """Screenshot → send to Gemini Vision → return analysis.
           Only tool that uses AI vision (for visual understanding)."""
    
    def get_console(self) -> dict
        """Return recent console errors from CDP supervisor."""
    
    def get_images(self) -> dict
        """page.evaluate: list all img tags with src + alt."""
    
    def handle_dialog(self, action: str, text: str = None) -> dict
        """Resolve a pending dialog via CDP supervisor."""
    
    def cdp_command(self, method: str, params: dict = None) -> dict
        """cdp_session.send(method, params)."""
```

#### Chrome Launch Sequence (in `start()`)

```python
import subprocess, time, requests
from playwright.sync_api import sync_playwright

def _find_chrome() -> str:
    """Find Chrome in standard install locations."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return "chrome"  # hope it's in PATH

def _launch_chrome_with_cdp(port: int) -> subprocess.Popen:
    chrome_path = _find_chrome()
    user_data = os.path.expandvars(f"%TEMP%\\soda-browser-{port}")
    proc = subprocess.Popen([
        chrome_path,
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        f"--user-data-dir={user_data}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-sync",
    ])
    return proc

def _wait_for_cdp(port: int, timeout: float = 15.0) -> str:
    """Poll /json/version until ready, return WebSocket URL."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=2)
            if resp.status_code == 200:
                return resp.json()["webSocketDebuggerUrl"]
        except requests.ConnectionError:
            time.sleep(0.5)
    raise TimeoutError(f"CDP endpoint not ready on port {port}")
```

### 3.2 `backend/cdp_supervisor.py` (~400 lines)

**New file.** Persistent Chrome DevTools Protocol connection for dialog/console/frame monitoring.

```python
class CDPSupervisor:
    """
    Daemon thread with persistent WebSocket to Chrome DevTools.
    Tracks JS dialogs, console errors, and frame tree.
    Auto-reconnects on disconnect with exponential backoff.
    """
    
    def __init__(self, cdp_url: str, task_id: str):
        self.cdp_url = cdp_url
        self.task_id = task_id
        self._ws = None
        self._loop = None
        self._thread = None
        self._msg_id = 0
        self._pending_calls: dict[int, asyncio.Future] = {}
        self._pending_dialogs: list[dict] = []
        self._console_events: list[dict] = []
        self._frame_tree: dict = {}
        self._running = False
        self._lock = threading.RLock()
    
    def start(self):
        """Launch daemon thread with its own asyncio event loop."""
    
    def stop(self):
        """Signal stop, close WebSocket, join thread."""
    
    def snapshot(self) -> dict:
        """Thread-safe: return current dialogs, console, frames."""
    
    def respond_dialog(self, dialog_id: int, action: str, text: str = None) -> dict:
        """Thread-safe: schedule dialog response on asyncio loop."""
    
    # ── Internal ──
    
    def _run(self):
        """Thread entry: create event loop, run connect loop."""
    
    async def _connect_loop(self):
        """Connect → listen → reconnect on close with backoff."""
    
    async def _send(self, method: str, params: dict = None) -> dict:
        """Send CDP method, wait for response."""
    
    def _on_event(self, data: dict):
        """Dispatch CDP events to handlers."""
```

#### CDP Events Subscribed To

| Domain | Event | Purpose |
|--------|-------|---------|
| `Page.enable` | `Page.javascriptDialogOpening` | Detect alert/confirm/prompt dialogs |
| `Page.enable` | `Page.javascriptDialogClosed` | Track dialog resolution |
| `Runtime.enable` | `Runtime.consoleAPICalled` | Capture console.log/warn/error |
| `Runtime.enable` | `Runtime.exceptionThrown` | Track JS exceptions |
| `Target.setAutoAttach` | `Target.attachedToTarget` | Detect new iframes/popups |
| `Page.enable` | `Page.frameStartedLoading` | Frame load tracking |
| `Page.enable` | `Page.frameStoppedLoading` | Frame load complete |

#### Dialog Bridge (Injected JavaScript)

```javascript
// Overrides window.alert, window.confirm, window.prompt
// Uses synchronous XHR intercepted by CDP Fetch domain
// The page's JS thread blocks until the supervisor responds

window.alert = function(message) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', 'http://soda-dialog-bridge/alert?message=' + encodeURIComponent(message), false);
    xhr.send();
};

window.confirm = function(message) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', 'http://soda-dialog-bridge/confirm?message=' + encodeURIComponent(message), false);
    xhr.send();
    return xhr.responseText === 'true';
};

window.prompt = function(message, defaultText) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', 'http://soda-dialog-bridge/prompt?message=' + encodeURIComponent(message)
        + '&default=' + encodeURIComponent(defaultText || ''), false);
    xhr.send();
    return xhr.responseText || defaultText;
};
```

---

## 4. Element Reference System

### 4.1 How Refs Work

Each interactive element in the accessibility tree gets a short ref ID like `@e0`, `@e1`. The Gemini model uses these refs to click or type without needing to know coordinates or CSS selectors.

### 4.2 Ref Assignment

```python
def assign_refs(snapshot_dict: dict, prefix: str = "e") -> dict:
    """
    Walk accessibility tree, assign ref IDs, return tree + flat ref map.
    
    Returns:
    {
        "tree": [{ref, role, name, value, disabled, children}, ...],
        "refs": {"@e0": {ref, role, name, ...}, "@e1": {...}},
        "interactive_count": int
    }
    """
```

### 4.3 Ref Resolution (for click/type)

```python
def resolve_ref(ref_map: dict, ref: str) -> dict:
    """Look up ref in map. Returns {role, name, ...} or raises ValueError."""
```

### 4.4 Re-Executing an Action (Playwright locator)

```python
# From {role, name} → Playwright locator
locator = page.get_by_role(entry["role"], name=entry.get("name"))
locator.click()  # Auto-waits for element, auto-retries on stale
```

**Why this is reliable:**
- `get_by_role` queries the live DOM, not a stale reference
- Playwright locators auto-wait for the element to be actionable
- If the page re-renders, the locator finds the new element by its semantic role + name
- This is the same pattern Playwright tests use (proven stable across millions of test runs)

---

## 5. CDP Supervisor

### 5.1 Architecture

```
┌──────────────────────────────────────────────────┐
│                  Main Thread                      │
│  BrowserSession                                  │
│    ├─ Playwright API (synchronous)               │
│    └─ CDPSupervisor.snapshot() (thread-safe)     │
└────────────────────┬─────────────────────────────┘
                     │ Thread boundary
                     │ (daemon thread, own asyncio loop)
┌────────────────────▼─────────────────────────────┐
│           CDP Supervisor Thread                   │
│                                                   │
│  asyncio.new_event_loop()                         │
│    ├─ websockets.connect(cdp_url)                │
│    ├─ async for message in ws:                    │
│    │    ├─ Response → resolve Future              │
│    │    └─ Event → update dialog/console state    │
│    ├─ Reconnect on close (0.5s → 10s backoff)    │
│    └─ respond_dialog() via safe_schedule          │
└──────────────────────────────────────────────────┘
```

### 5.2 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Threading** | Daemon thread with own asyncio loop | CDP WebSocket is async; Playwright is sync. Separate threads avoid conflict. |
| **Reconnect** | Exponential backoff 0.5s → 10s | Chrome can restart; CDP URL changes; supervisor should adapt. |
| **Dialog policy** | `auto_dismiss` initially, `must_respond` later | Simpler to start; minimal loss (auto-dismiss is less harmful than auto-accept). |
| **Console ring** | Max 50 events | Bounded memory; most recent errors are most relevant. |
| **Frame tree** | Max 30 entries, depth 2 | Bounded; iframes beyond depth 2 are rare. |
| **Thread safety** | `threading.RLock()` for all shared state | Snapshot reads are lock-protected; dialog responses write under lock. |

---

## 6. Snapshot Output Format

`browser_snapshot()` returns this JSON structure to the Gemini model:

```json
{
    "url": "https://example.com/login",
    "title": "Sign In - Example",
    "snapshot": {
        "tree": [
            {
                "ref": "@e0",
                "role": "heading",
                "name": "Sign In",
                "level": 1
            },
            {
                "ref": "@e1",
                "role": "textbox",
                "name": "Username",
                "value": "",
                "required": true,
                "focused": true
            },
            {
                "ref": "@e2",
                "role": "textbox",
                "name": "Password",
                "value": "",
                "required": true,
                "focused": false
            },
            {
                "ref": "@e3",
                "role": "button",
                "name": "Submit",
                "disabled": false
            },
            {
                "ref": "@e4",
                "role": "link",
                "name": "Forgot password?"
            }
        ]
    },
    "interactive_count": 4,
    "pending_dialogs": [],
    "console_errors": [],
    "session_id": "task_abc123"
}
```

The Gemini model can then call:
- `browser_snapshot()` → get this tree
- `browser_type(ref="@e1", text="myusername")` → type into Username field
- `browser_type(ref="@e2", text="mypassword")` → type into Password field
- `browser_click(ref="@e3")` → click Submit button

---

## 7. Tool Definitions

### 7.1 The 12 New Tools

All 12 tools are **additive** — they do not replace any existing SODA tools. The existing `browser_automate`, `browser_command`, `click_element`, `type_into`, etc. remain unchanged.

| # | Tool Name | Description | Parameters |
|---|-----------|-------------|------------|
| 1 | `browser_navigate` | Open a URL, init browser session | `url: STRING` (required) |
| 2 | `browser_snapshot` | Get accessibility tree with element refs | `full: BOOLEAN` (optional, default False) |
| 3 | `browser_click` | Click element by ref ID | `ref: STRING` (required, e.g. "@e3") |
| 4 | `browser_type` | Type text into element by ref ID | `ref: STRING` (required), `text: STRING` (required) |
| 5 | `browser_scroll` | Scroll the page | `direction: STRING` (enum: up/down/top/bottom) |
| 6 | `browser_back` | Navigate back in history | none |
| 7 | `browser_press` | Press a keyboard key | `key: STRING` (required, e.g. "Enter") |
| 8 | `browser_vision` | Screenshot + AI visual analysis | `question: STRING` (required) |
| 9 | `browser_console` | Get JS console errors | none |
| 10 | `browser_get_images` | List page images with URLs | none |
| 11 | `browser_dialog` | Respond to JS dialog | `action: STRING` (enum: accept/dismiss), `text: STRING` (optional) |
| 12 | `browser_cdp` | Raw CDP command | `method: STRING` (required), `params: STRING` (optional JSON) |

### 7.2 Typical Tool Use Sequence

```
1. browser_navigate(url="https://github.com/login")
   → Returns {url, title, snapshot with refs}

2. browser_snapshot()
   → Returns structured tree with @e0, @e1, @e2...

3. browser_type(ref="@e1", text="myusername")
   → Returns {success: true}

4. browser_type(ref="@e2", text="mypassword")

5. browser_click(ref="@e3")
   → Returns {success: true, new_url: "https://github.com"}

6. browser_vision(question="What's on the page?")
   → Screenshot + Gemini Vision analysis (only paid AI call in the flow)
```

---

## 8. Implementation Phases

### Phase 1: Foundation — Core Backend Modules

**Goal**: Create the two new Python modules (`browser_automation.py`, `cdp_supervisor.py`) and install Playwright dependencies.

#### Tasks

| # | Task | File | Est. Lines |
|---|------|------|------------|
| 1.1 | Add `playwright` to requirements.txt | `requirements.txt` | +1 |
| 1.2 | Create install script for Playwright + Chromium | `backend/install_browser_deps.ps1` | ~30 |
| 1.3 | Implement `BrowserSessionManager` singleton | `backend/browser_automation.py` | ~100 |
| 1.4 | Implement Chrome launcher (find Chrome, launch with CDP port) | `backend/browser_automation.py` | ~80 |
| 1.5 | Implement `BrowserSession` (Playwright connect, page, CDP session) | `backend/browser_automation.py` | ~120 |
| 1.6 | Implement element ref system (`assign_refs`, `resolve_ref`) | `backend/browser_automation.py` | ~80 |
| 1.7 | Implement snapshot formatting (acc tree → ref tree) | `backend/browser_automation.py` | ~60 |
| 1.8 | Implement tool handlers (navigate, click, type, scroll, back, press) | `backend/browser_automation.py` | ~200 |
| 1.9 | Implement vision_qa (screenshot + Gemini Vision) | `backend/browser_automation.py` | ~60 |
| 1.10 | Implement get_images, get_console, handle_dialog, cdp_command | `backend/browser_automation.py` | ~100 |
| 1.11 | Implement `CDPSupervisor` (daemon thread, WebSocket connect, event dispatch) | `backend/cdp_supervisor.py` | ~250 |
| 1.12 | Implement dialog bridge (JS injection, Fetch domain) | `backend/cdp_supervisor.py` | ~80 |
| 1.13 | Implement idle cleanup daemon | `backend/browser_automation.py` | ~50 |
| 1.14 | Emergency cleanup (`atexit` registration) | `backend/browser_automation.py` | ~20 |

**Estimated total**: ~1,230 lines across 2 new files + 1 modified file

**Verification**: Run `python backend/install_browser_deps.ps1` and test that Chromium launches and connects via CDP.

---

### Phase 2: SODA Integration — Wire Tools Into Pipeline

**Goal**: Register the 12 new tools with Gemini, route them to the local agent, and handle them in `_dispatch()`.

#### Tasks

| # | Task | File | Lines |
|---|------|------|-------|
| 2.1 | Write 12 tool schema dicts (Hermes-style) | `backend/tools.py` | ~200 |
| 2.2 | Import schemas and add to `tools_list` | `backend/tools.py` | +20 |
| 2.3 | Add 12 tool names to `LOCAL_AGENT_TOOLS` set | `backend/soda.py` | +2 |
| 2.4 | Add timeout entries for each tool | `backend/soda.py` | +12 |
| 2.5 | Add 12 `elif` branches in `_dispatch()` | `backend/local_agent.py` | ~150 |
| 2.6 | Add `"browser_navigate"` etc. to `LOCAL_TOOLS` list | `backend/local_agent.py` | +2 |

**Estimated total**: ~386 lines across 3 modified files

**Verification**: Run `npm run dev` (backend only), send a test `agent_execute` with a browser tool, verify session creates and Chrome opens.

---

### Phase 3: Frontend Panel — Visual Browser Session

**Goal**: Add a React panel that shows the browser session state (URL, title, screenshot, console, dialogs).

#### Tasks

| # | Task | File | Lines |
|---|------|------|-------|
| 3.1 | Create BrowserPanel component | `src/components/panels/BrowserPanel.jsx` | ~250 |
| 3.2 | Add panel state handling in App.jsx | `src/App.jsx` | +15 |
| 3.3 | Export from panels/index.js | `src/components/panels/index.js` | +2 |

**Estimated total**: ~267 lines across 3 files (1 new, 2 modified)

**Verification**: Open SODA HUD, start browser automation task, see panel slide in showing browser state.

---

### Phase 4: Polish & Hardening

**Goal**: Add error recovery, security, snapshot size management, backward compatibility.

#### Tasks

| # | Task | Details |
|---|------|---------|
| 4.1 | Snapshot size management | Truncate >15K chars, save full to temp file for model to read |
| 4.2 | Secrets redaction | Strip API keys, passwords from snapshot text before returning |
| 4.3 | Bot detection warning | Detect "captcha", "access denied", "cloudflare" in page titles, warn model |
| 4.4 | Dialog policy implementation | Add `must_respond` (LLM-routed), `auto_dismiss`, `auto_accept` modes |
| 4.5 | Chrome crash recovery | Detect browser exit, auto-restart session on next tool call |
| 4.6 | Idle timeout tuning | Default 120s, configurable via settings |
| 4.7 | Backward compatibility test | Ensure existing `browser_automate` vision tools still work |
| 4.8 | Error handling audit | Every tool handler returns `{"success": bool, "error": str}` on failure |

**Estimated total**: Logic changes only, ~150 lines scattered across existing files

**Verification**: Full integration test: navigate → login → fill form → submit → verify result. Test crash recovery by killing Chrome mid-session.

---

## 9. Files Summary

### New Files (3)

| File | Est. Lines | Purpose |
|------|------------|---------|
| `backend/browser_automation.py` | ~800 | Session manager, 12 tool handlers, element ref system, Chrome launcher |
| `backend/cdp_supervisor.py` | ~400 | CDP WebSocket daemon, dialog/console/frame tracking |
| `src/components/panels/BrowserPanel.jsx` | ~250 | Frontend browser session visualization panel |

### Modified Files (6)

| File | Lines Added | Changes |
|------|-------------|---------|
| `requirements.txt` | +1 | Add `playwright` |
| `backend/tools.py` | +220 | 12 new schema dicts + imports |
| `backend/soda.py` | +14 | Add to LOCAL_AGENT_TOOLS + timeouts |
| `backend/local_agent.py` | +152 | 12 tool handlers in dispatch chain |
| `src/App.jsx` | +15 | Wire BrowserPanel |
| `src/components/panels/index.js` | +2 | Export BrowserPanel |

### Install Script (1)

| File | Purpose |
|------|---------|
| `backend/install_browser_deps.ps1` | `pip install playwright; python -m playwright install chromium` |

### Total

- **New code**: ~1,830 lines
- **New files**: 3
- **Modified files**: 6
- **Install scripts**: 1

---

## 10. Open Questions

| Question | Options | Recommendation |
|----------|---------|----------------|
| **Headed vs headless?** | Headed (user sees what bot does) vs headless (faster, no display needed) | Headed on Windows (local agent has display); config option for headless |
| **Playwright `connect_over_cdp` vs `chromium.launch()`?** | `connect_over_cdp` gives CDP port + cloud compat; `launch()` simpler | `connect_over_cdp` from v1 |
| **Persistent browser across tasks or fresh per task?** | Hermes uses per-task with timeout cleanup | Per-task (same), 120s idle timeout |
| **Keep existing `browser_automate` tool?** | Yes (backward compat) vs no (replace) | Yes — additive, not replasive |
| **Dialog initial policy?** | `auto_dismiss`, `auto_accept`, `must_respond` | `auto_dismiss` in v1, `must_respond` in Phase 4 |
| **Target browser?** | Chrome vs Edge vs Playwright bundled Chromium | Found Chrome first → fall back to bundled Chromium |
| **CDP connection: Playwright CDP session vs manual WebSocket?** | Playwright's `new_cdp_session()` is simpler; manual WebSocket gives more control | Manual WebSocket for supervisor (full event subscription); Playwright CDP session for `browser_cdp` tool |

---

*End of planning document. Next: Phase 1 implementation.*
