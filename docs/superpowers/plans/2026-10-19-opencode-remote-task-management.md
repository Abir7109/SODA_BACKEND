# OpenCode Remote Task Management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let SODA launch OpenCode sessions on the local machine via the agent, monitor progress in background, stream updates via voice, and log results to a persistent notebook.

**Architecture:** New `agent_push` Socket.IO event lets the local agent push updates to SODA at any time (not just in response to tool calls). New `opencode_monitor.py` tracks OpenCode sessions. New `notebook.py` provides persistent task logging (Supabase + file backup). Five new tools give SODA the ability to start/stop/monitor OpenCode tasks and read notebook history. System prompt updated so SODA knows the workflow.

**Tech Stack:** Python 3.11, FastAPI + Socket.IO, asyncio, Supabase (PostgreSQL), existing local_agent.py + background_cmd.py patterns.

**Spec:** This plan file (no separate spec — design was agreed in conversation).

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/server.py` | Modify | Add `agent_push` event handler |
| `backend/local_agent.py` | Modify | Add `agent_push` emit capability + opencode stdout streaming |
| `backend/opencode_monitor.py` | Create | OpenCode session lifecycle, stdout parsing, progress callbacks |
| `backend/notebook.py` | Create | Notebook read/write/search (Supabase + file backup) |
| `backend/tools.py` | Modify | 5 new tool definitions |
| `backend/soda.py` | Modify | New tool dispatch cases + system prompt section |
| `backend/supabase_client.py` | Modify | Add `opencode_notebook` table creation |

---

## Phase 1: agent_push Event — Agent → SODA Communication

### Task 1.1: Add `agent_push` handler to server.py

**Files:**
- Modify: `backend/server.py`

**What it does:** When the local agent emits `agent_push`, the server routes the data to SODA's session via `audio_loop.inject_text()`.

- [ ] **Step 1: Read the current server.py agent event handlers**

Read `backend/server.py` lines 340-415 to understand existing `agent_register`, `agent_tool_result`, `agent_pong` patterns.

- [ ] **Step 2: Add `agent_push` event handler**

After the `agent_pong` handler, add:

```python
@sio.event
async def agent_push(sid, data):
    """Agent-initiated push — agent sends updates without being asked."""
    agent_info = _connected_agents.get(sid)
    if not agent_info:
        log.warning(f"[AGENT_PUSH] Unknown agent {sid}, ignoring")
        return
    push_type = data.get("type", "unknown")
    task_id = data.get("task_id", "")
    text = data.get("text", "")
    log.info(f"[AGENT_PUSH] type={push_type} task={task_id} from={agent_info.get('machine_id', sid)}")
    
    if not audio_loop:
        log.warning("[AGENT_PUSH] audio_loop not initialized")
        return
    
    # Inject into SODA's Gemini session
    formatted = f"[Agent update: {push_type}] {text}"
    await audio_loop.inject_text(formatted)
```

- [ ] **Step 3: Verify server.py compiles**

Run: `py -3.11 -c "import py_compile; py_compile.compile('backend/server.py', doraise=True)"`

- [ ] **Step 4: Commit**

```bash
git add backend/server.py
git commit -m "feat: add agent_push event handler for agent-initiated communication"
```

### Task 1.2: Add `agent_push` emit to local_agent.py

**Files:**
- Modify: `backend/local_agent.py`

**What it does:** Gives the local agent a helper method to push updates to the server at any time.

- [ ] **Step 1: Read the local_agent.py dispatch and emit patterns**

Read `backend/local_agent.py` lines 417-460 (tool result emission) and lines 2656-2668 (heartbeat).

- [ ] **Step 2: Add `push_update` helper method**

After the heartbeat method, add:

```python
def push_update(self, push_type: str, task_id: str, text: str):
    """Push an update to SODA without being asked."""
    if not self.sio.connected:
        return
    self.sio.emit("agent_push", {
        "type": push_type,
        "task_id": task_id,
        "text": text,
    })
```

- [ ] **Step 3: Verify local_agent.py compiles**

Run: `py -3.11 -c "import py_compile; py_compile.compile('backend/local_agent.py', doraise=True)"`

- [ ] **Step 4: Commit**

```bash
git add backend/local_agent.py
git commit -m "feat: add push_update helper to local agent for agent_push events"
```

### Task 1.3: Test agent_push round-trip

- [ ] **Step 1: Verify both files compile together**

Run: `py -3.11 -c "import py_compile; py_compile.compile('backend/server.py', doraise=True); py_compile.compile('backend/local_agent.py', doraise=True); print('Phase 1 OK')"`

- [ ] **Step 2: Re-read the plan file for Phase 2 context**

Read `docs/superpowers/plans/2026-10-19-opencode-remote-task-management.md` from the top.

---

## Phase 2: Notebook System

### Task 2.1: Create notebook.py

**Files:**
- Create: `backend/notebook.py`

**What it does:** Provides `save_task`, `read_task`, `search_tasks`, `list_recent` functions. Dual-writes to Supabase and file backup.

- [ ] **Step 1: Create backend/notebook.py**

```python
"""OpenCode Notebook — persistent task logging.

Dual-writes to Supabase (opencode_notebook table) and file backup
(projects/long_term_memory/notebook.json).
"""
import json, os, time
from pathlib import Path
from datetime import datetime, timezone

NOTEBOOK_FILE = Path(__file__).parent.parent / "projects" / "long_term_memory" / "notebook.json"

_supabase = None

def _get_supabase():
    global _supabase
    if _supabase is None:
        try:
            from supabase_client import get_client
            _supabase = get_client()
        except Exception:
            _supabase = False
    return _supabase if _supabase else None

def _load_file():
    if NOTEBOOK_FILE.exists():
        try:
            return json.loads(NOTEBOOK_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"tasks": []}

def _save_file(data):
    NOTEBOOK_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

async def save_task(task_id: str, folder: str, prompt: str, status: str,
                    output_summary: str = "", error: str = "",
                    started_at: str = "", completed_at: str = ""):
    """Save a task record to notebook."""
    entry = {
        "task_id": task_id,
        "folder": folder,
        "prompt": prompt,
        "status": status,
        "output_summary": output_summary,
        "error": error,
        "started_at": started_at or datetime.now(timezone.utc).isoformat(),
        "completed_at": completed_at or datetime.now(timezone.utc).isoformat(),
    }
    # File backup
    data = _load_file()
    data["tasks"].append(entry)
    _save_file(data)
    # Supabase
    client = _get_supabase()
    if client:
        try:
            client.table("opencode_notebook").insert(entry).execute()
        except Exception as e:
            print(f"[NOTEBOOK] Supabase write failed: {e}")
    return entry

async def read_task(task_id: str):
    """Read a single task by ID."""
    client = _get_supabase()
    if client:
        try:
            result = client.table("opencode_notebook").select("*").eq("task_id", task_id).execute()
            if result.data:
                return result.data[0]
        except Exception:
            pass
    # Fallback to file
    data = _load_file()
    for t in data["tasks"]:
        if t["task_id"] == task_id:
            return t
    return None

async def search_tasks(keyword: str, limit: int = 10):
    """Search tasks by keyword in prompt or output."""
    client = _get_supabase()
    if client:
        try:
            result = client.table("opencode_notebook").select("*").or_(
                f"prompt.ilike.%{keyword}%,output_summary.ilike.%{keyword}%"
            ).order("started_at", desc=True).limit(limit).execute()
            return result.data
        except Exception:
            pass
    # Fallback to file
    data = _load_file()
    results = []
    kw = keyword.lower()
    for t in reversed(data["tasks"]):
        if kw in t.get("prompt", "").lower() or kw in t.get("output_summary", "").lower():
            results.append(t)
            if len(results) >= limit:
                break
    return results

async def list_recent(limit: int = 10):
    """List most recent tasks."""
    client = _get_supabase()
    if client:
        try:
            result = client.table("opencode_notebook").select("*").order(
                "started_at", desc=True
            ).limit(limit).execute()
            return result.data
        except Exception:
            pass
    data = _load_file()
    return list(reversed(data["tasks"][-limit:]))
```

- [ ] **Step 2: Verify notebook.py compiles**

Run: `py -3.11 -c "import py_compile; py_compile.compile('backend/notebook.py', doraise=True); print('notebook.py OK')"`

### Task 2.2: Add Supabase table creation

**Files:**
- Modify: `backend/supabase_client.py`

**What it does:** Ensures the `opencode_notebook` table exists on startup.

- [ ] **Step 1: Read supabase_client.py**

Read `backend/supabase_client.py` to find where tables are created/initialized.

- [ ] **Step 2: Add table creation SQL comment**

Find the table creation section and add a comment documenting the required table:

```python
# opencode_notebook table (created manually or via migration):
# CREATE TABLE IF NOT EXISTS opencode_notebook (
#     id BIGSERIAL PRIMARY KEY,
#     task_id TEXT UNIQUE NOT NULL,
#     folder TEXT NOT NULL,
#     prompt TEXT NOT NULL,
#     status TEXT NOT NULL DEFAULT 'running',
#     output_summary TEXT DEFAULT '',
#     error TEXT DEFAULT '',
#     started_at TIMESTAMPTZ DEFAULT NOW(),
#     completed_at TIMESTAMPTZ
# );
```

- [ ] **Step 3: Verify compilation**

Run: `py -3.11 -c "import py_compile; py_compile.compile('backend/supabase_client.py', doraise=True); print('supabase_client.py OK')"`

### Task 2.3: Verify notebook system

- [ ] **Step 1: Compile check all modified files**

Run: `py -3.11 -c "import py_compile; py_compile.compile('backend/notebook.py', doraise=True); py_compile.compile('backend/supabase_client.py', doraise=True); print('Phase 2 OK')"`

- [ ] **Step 2: Re-read the plan file for Phase 3 context**

Read `docs/superpowers/plans/2026-10-19-opencode-remote-task-management.md` from the top.

---

## Phase 3: OpenCode Monitor

### Task 3.1: Create opencode_monitor.py

**Files:**
- Create: `backend/opencode_monitor.py`

**What it does:** Manages OpenCode session lifecycle. The local agent runs OpenCode and streams stdout via `agent_push`. This module parses output for progress signals and manages task state.

- [ ] **Step 1: Create backend/opencode_monitor.py**

```python
"""OpenCode Session Monitor — tracks running OpenCode tasks.

Used by the local agent to stream stdout/stderr and by SODA to
check task status. The actual execution happens on the local agent
via terminal_execute; this module tracks state.
"""
import asyncio, time, uuid
from datetime import datetime, timezone

# In-memory task registry (server-side)
_tasks = {}  # task_id -> OpencodeTask

class OpencodeTask:
    __slots__ = ("task_id", "folder", "prompt", "status", "output_lines",
                 "started_at", "completed_at", "error", "exit_code",
                 "progress_callbacks")
    
    def __init__(self, task_id, folder, prompt):
        self.task_id = task_id
        self.folder = folder
        self.prompt = prompt
        self.status = "running"
        self.output_lines = []
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.completed_at = ""
        self.error = ""
        self.exit_code = None
        self.progress_callbacks = []
    
    def add_output(self, line: str):
        self.output_lines.append(line)
        if len(self.output_lines) > 500:
            self.output_lines = self.output_lines[-500:]
    
    def to_dict(self):
        return {
            "task_id": self.task_id,
            "folder": self.folder,
            "prompt": self.prompt,
            "status": self.status,
            "output_lines": self.output_lines[-50:],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "exit_code": self.exit_code,
        }
    
    def summary(self) -> str:
        """Generate a human-readable summary of the task."""
        lines = self.output_lines[-20:]
        output = "\n".join(lines) if lines else "(no output)"
        status_msg = f"Task {self.status}"
        if self.status == "completed":
            status_msg += f" (exit code {self.exit_code})"
        elif self.status == "failed":
            status_msg += f": {self.error}"
        return f"{status_msg}\nFolder: {self.folder}\nPrompt: {self.prompt}\nLast output:\n{output}"


def create_task(folder: str, prompt: str) -> OpencodeTask:
    """Create and register a new OpenCode task."""
    task_id = str(uuid.uuid4())[:8]
    task = OpencodeTask(task_id, folder, prompt)
    _tasks[task_id] = task
    return task

def get_task(task_id: str) -> OpencodeTask:
    return _tasks.get(task_id)

def update_task(task_id: str, **kwargs) -> OpencodeTask:
    """Update task fields from agent_push data."""
    task = _tasks.get(task_id)
    if not task:
        return None
    if "status" in kwargs:
        task.status = kwargs["status"]
    if "output_line" in kwargs:
        task.add_output(kwargs["output_line"])
    if "error" in kwargs:
        task.error = kwargs["error"]
    if "exit_code" in kwargs:
        task.exit_code = kwargs["exit_code"]
    if task.status in ("completed", "failed", "killed"):
        task.completed_at = datetime.now(timezone.utc).isoformat()
    return task

def list_tasks(limit: int = 10):
    """List recent tasks, newest first."""
    tasks = sorted(_tasks.values(), key=lambda t: t.started_at, reverse=True)
    return [t.to_dict() for t in tasks[:limit]]

def is_progress_line(line: str) -> bool:
    """Check if an output line is a significant milestone."""
    keywords = [
        "building", "deploy", "success", "error", "failed", "complete",
        "published", "ready", "compiled", "bundled", "uploaded",
        "install", "download", "link:", "https://", "netlify", "vercel",
    ]
    low = line.lower()
    return any(kw in low for kw in keywords)
```

- [ ] **Step 2: Verify opencode_monitor.py compiles**

Run: `py -3.11 -c "import py_compile; py_compile.compile('backend/opencode_monitor.py', doraise=True); print('opencode_monitor.py OK')"`

### Task 3.2: Verify monitor module

- [ ] **Step 1: Compile check**

Run: `py -3.11 -c "import py_compile; py_compile.compile('backend/opencode_monitor.py', doraise=True); print('Phase 3 OK')"`

- [ ] **Step 2: Re-read the plan file for Phase 4 context**

Read `docs/superpowers/plans/2026-10-19-opencode-remote-task-management.md` from the top.

---

## Phase 4: New Tools + Dispatch

### Task 4.1: Add tool definitions to tools.py

**Files:**
- Modify: `backend/tools.py`

**What it does:** Adds 5 new tool definitions that Gemini can call.

- [ ] **Step 1: Read tools.py end section**

Read `backend/tools.py` lines 2050-2110 to see existing `bg_spawn`/`bg_status` tool definitions and find the tool list.

- [ ] **Step 2: Add 5 new tool definitions**

Before the closing `ALL_TOOLS` list, add:

```python
opencode_start_tool = {
    "name": "opencode_start",
    "description": "Launch an OpenCode session in a specific folder on the local machine. The agent will cd into the folder, confirm it exists, and start OpenCode with the given prompt. Use when the user wants to run OpenCode tasks in a project folder.",
    "parameters": {
        "folder": {"type": "STRING", "description": "Full path to the project folder (e.g. D:\\projects\\my-site)"},
        "prompt": {"type": "STRING", "description": "The task prompt for OpenCode (e.g. 'deploy this site to netlify')"},
    },
    "required": ["folder", "prompt"]
}

opencode_status_tool = {
    "name": "opencode_status",
    "description": "Check the status of a running OpenCode task. Returns output lines, progress, and status.",
    "parameters": {
        "task_id": {"type": "STRING", "description": "The task ID returned by opencode_start"},
    },
    "required": ["task_id"]
}

opencode_stop_tool = {
    "name": "opencode_stop",
    "description": "Kill a running OpenCode task.",
    "parameters": {
        "task_id": {"type": "STRING", "description": "The task ID to stop"},
    },
    "required": ["task_id"]
}

notebook_read_tool = {
    "name": "notebook_read",
    "description": "Read a past OpenCode task result from the notebook. Returns the full task record including output summary.",
    "parameters": {
        "task_id": {"type": "STRING", "description": "The task ID to read"},
    },
    "required": ["task_id"]
}

notebook_search_tool = {
    "name": "notebook_search",
    "description": "Search the OpenCode notebook by keyword. Returns matching task records.",
    "parameters": {
        "keyword": {"type": "STRING", "description": "Search keyword (matches prompt and output)"},
    },
    "required": ["keyword"]
}
```

- [ ] **Step 3: Add tools to the ALL_TOOLS list**

Find the `ALL_TOOLS` list and add the 5 new tools:

```python
    opencode_start_tool,
    opencode_status_tool,
    opencode_stop_tool,
    notebook_read_tool,
    notebook_search_tool,
```

- [ ] **Step 4: Verify tools.py compiles**

Run: `py -3.11 -c "import py_compile; py_compile.compile('backend/tools.py', doraise=True); print('tools.py OK')"`

### Task 4.2: Add tool dispatch cases to soda.py

**Files:**
- Modify: `backend/soda.py`

**What it does:** Adds dispatch logic for the 5 new tools in `_dispatch_tool`.

- [ ] **Step 1: Read soda.py dispatch section**

Read `backend/soda.py` around the `bg_spawn` dispatch (lines 3354-3388) to see the pattern.

- [ ] **Step 2: Add dispatch cases**

After the `bg_list` dispatch, add:

```python
        elif name == "opencode_start":
            folder = args.get("folder", "")
            prompt = args.get("prompt", "")
            if not folder or not prompt:
                return types.FunctionResponse(id=fc.id, name=name, response={"result": "Error: folder and prompt are required"})
            from opencode_monitor import create_task
            task = create_task(folder, prompt)
            task_id = task.task_id
            # Tell the local agent to cd + start opencode
            if _connected_agents:
                agent_sid = max(_connected_agents, key=lambda s: len(_connected_agents[s].get('tools', [])))
                self.sio.emit("agent_execute", {
                    "tool": "terminal_execute",
                    "args": {"command": f'cd "{folder}" && dir /b'},
                    "callback_id": f"opencode_check_{task_id}",
                    "_opencode_check": True,
                    "_task_id": task_id,
                }, room=agent_sid)
            return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Task {task_id} created. Checking folder '{folder}'..."})

        elif name == "opencode_status":
            task_id = args.get("task_id", "")
            from opencode_monitor import get_task
            task = get_task(task_id)
            if not task:
                return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Task {task_id} not found"})
            return types.FunctionResponse(id=fc.id, name=name, response={"result": task.to_dict()})

        elif name == "opencode_stop":
            task_id = args.get("task_id", "")
            from opencode_monitor import get_task, update_task
            task = update_task(task_id, status="killed")
            if not task:
                return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Task {task_id} not found"})
            # Tell agent to kill the process
            if _connected_agents:
                agent_sid = max(_connected_agents, key=lambda s: len(_connected_agents[s].get('tools', [])))
                self.sio.emit("agent_execute", {
                    "tool": "terminal_execute",
                    "args": {"command": "taskkill /F /IM opencode.exe 2>nul || echo no process"},
                    "callback_id": f"opencode_kill_{task_id}",
                }, room=agent_sid)
            return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Task {task_id} killed"})

        elif name == "notebook_read":
            from notebook import read_task
            task_id = args.get("task_id", "")
            result = await read_task(task_id)
            if not result:
                return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Task {task_id} not found in notebook"})
            return types.FunctionResponse(id=fc.id, name=name, response={"result": result})

        elif name == "notebook_search":
            from notebook import search_tasks
            keyword = args.get("keyword", "")
            results = await search_tasks(keyword)
            return types.FunctionResponse(id=fc.id, name=name, response={"result": results})
```

- [ ] **Step 3: Verify soda.py compiles**

Run: `py -3.11 -c "import py_compile; py_compile.compile('backend/soda.py', doraise=True); print('soda.py OK')"`

### Task 4.3: Handle agent_push for opencode updates in server.py

**Files:**
- Modify: `backend/server.py`

**What it does:** When agent_push comes with type `opencode_output`, update the task in opencode_monitor.

- [ ] **Step 1: Update agent_push handler**

Read the current `agent_push` handler in server.py and enhance it:

```python
@sio.event
async def agent_push(sid, data):
    """Agent-initiated push — agent sends updates without being asked."""
    agent_info = _connected_agents.get(sid)
    if not agent_info:
        log.warning(f"[AGENT_PUSH] Unknown agent {sid}, ignoring")
        return
    push_type = data.get("type", "unknown")
    task_id = data.get("task_id", "")
    text = data.get("text", "")
    log.info(f"[AGENT_PUSH] type={push_type} task={task_id} from={agent_info.get('machine_id', sid)}")
    
    if not audio_loop:
        log.warning("[AGENT_PUSH] audio_loop not initialized")
        return
    
    # Handle OpenCode-specific updates
    if push_type in ("opencode_output", "opencode_complete", "opencode_error"):
        from opencode_monitor import update_task, get_task
        if push_type == "opencode_output":
            update_task(task_id, output_line=text)
        elif push_type == "opencode_complete":
            update_task(task_id, status="completed", exit_code=0)
            task = get_task(task_id)
            if task:
                from notebook import save_task
                await save_task(task_id, task.folder, task.prompt, "completed",
                              output_summary=task.summary())
        elif push_type == "opencode_error":
            update_task(task_id, status="failed", error=text)
            task = get_task(task_id)
            if task:
                from notebook import save_task
                await save_task(task_id, task.folder, task.prompt, "failed",
                              error=text, output_summary=task.summary())
    
    # Inject into SODA's Gemini session for voice response
    formatted = f"[Agent update: {push_type}] {text}"
    await audio_loop.inject_text(formatted)
```

- [ ] **Step 2: Verify server.py compiles**

Run: `py -3.11 -c "import py_compile; py_compile.compile('backend/server.py', doraise=True); print('server.py OK')"`

### Task 4.4: Add opencode launch capability to local_agent.py

**Files:**
- Modify: `backend/local_agent.py`

**What it does:** When the agent receives an `agent_execute` for `opencode_start`, it should cd into the folder, confirm it, then launch OpenCode and stream output back via `agent_push`.

- [ ] **Step 1: Read local_agent.py dispatch**

Read `backend/local_agent.py` lines 872-888 (terminal_execute handling) to see the pattern.

- [ ] **Step 2: Add opencode handler in _dispatch**

After the existing terminal_execute handler, add an opencode-specific branch. Actually, the existing `terminal_execute` handler in local_agent already handles `cd` commands. The agent_push streaming needs to be added to the general execution flow.

The simpler approach: when the agent runs a terminal command that starts opencode, it monitors the subprocess and streams output via `agent_push`. Let me modify the `run_hidden_command` to support streaming.

- [ ] **Step 3: Add run_hidden_command_streaming to background_cmd.py**

Read `backend/background_cmd.py` and add a streaming variant:

```python
def run_hidden_command_streaming(command, timeout=90, task_id=None, agent=None):
    """Run a command and stream output lines via agent_push."""
    import subprocess, threading
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    
    proc = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        startupinfo=startupinfo, text=True, bufsize=1
    )
    
    def reader():
        try:
            for line in proc.stdout:
                line = line.rstrip("\n\r")
                if line and agent:
                    agent.push_update("opencode_output", task_id, line)
            proc.wait(timeout=timeout)
            if agent:
                if proc.returncode == 0:
                    agent.push_update("opencode_complete", task_id, f"Process exited with code 0")
                else:
                    agent.push_update("opencode_error", task_id, f"Process exited with code {proc.returncode}")
        except Exception as e:
            if agent:
                agent.push_update("opencode_error", task_id, str(e))
    
    t = threading.Thread(target=reader, daemon=True)
    t.start()
    return {"success": True, "pid": proc.pid, "task_id": task_id}
```

- [ ] **Step 4: Verify background_cmd.py compiles**

Run: `py -3.11 -c "import py_compile; py_compile.compile('backend/background_cmd.py', doraise=True); print('background_cmd.py OK')"`

### Task 4.5: Full compile check

- [ ] **Step 1: Compile all modified files**

Run: `py -3.11 -c "import py_compile; [py_compile.compile(f, doraise=True) for f in ['backend/server.py', 'backend/soda.py', 'backend/tools.py', 'backend/local_agent.py', 'backend/background_cmd.py', 'backend/opencode_monitor.py', 'backend/notebook.py', 'backend/supabase_client.py']]; print('Phase 4 OK')"`

- [ ] **Step 2: Re-read the plan file for Phase 5 context**

Read `docs/superpowers/plans/2026-10-19-opencode-remote-task-management.md` from the top.

---

## Phase 5: System Prompt Updates

### Task 5.1: Add OpenCode workflow to system prompt

**Files:**
- Modify: `backend/soda.py` (in `_build_system_prompt`)

**What it does:** Tells SODA how to use the new OpenCode tools and notebook.

- [ ] **Step 1: Read the system prompt construction**

Read `backend/soda.py` lines 580-610 to see existing task planning and search workflow sections.

- [ ] **Step 2: Add OpenCode workflow section**

After the search workflow section, add:

```python
    base += "\n\nOPENCODE REMOTE TASKS:\n"
    base += "- When the user wants to run OpenCode in a project folder, use opencode_start(folder, prompt).\n"
    base += "- First confirm the folder exists: use terminal_execute with `cd \"<folder>\" && dir /b` to verify.\n"
    base += "- Show the folder listing to the user and ask for confirmation before launching.\n"
    base += "- After confirmation, call opencode_start with the folder path and the user's task prompt.\n"
    base += "- The task runs in background. Use opencode_status(task_id) to check progress.\n"
    base += "- The local agent streams output via agent_push — you will receive updates automatically.\n"
    base += "- When the task completes, results are auto-saved to the notebook. Read them aloud.\n"
    base += "- Use opencode_stop(task_id) to kill a running task if the user asks.\n"
    base += "\nNOTEBOOK:\n"
    base += "- All OpenCode task results are saved to the notebook (Supabase + file backup).\n"
    base += "- Use notebook_read(task_id) to read a past task result.\n"
    base += "- Use notebook_search(keyword) to search task history.\n"
    base += "- When recalling past work, check the notebook first before asking the user.\n"
```

- [ ] **Step 3: Verify soda.py compiles**

Run: `py -3.11 -c "import py_compile; py_compile.compile('backend/soda.py', doraise=True); print('soda.py OK')"`

### Task 5.2: Verify system prompt

- [ ] **Step 1: Compile check**

Run: `py -3.11 -c "import py_compile; py_compile.compile('backend/soda.py', doraise=True); print('Phase 5 OK')"`

- [ ] **Step 2: Re-read the plan file for Phase 6 context**

Read `docs/superpowers/plans/2026-10-19-opencode-remote-task-management.md` from the top.

---

## Phase 6: End-to-End Verification

### Task 6.1: Full compile check of all files

- [ ] **Step 1: Compile every modified/created file**

Run: `py -3.11 -c "import py_compile; files=['backend/server.py','backend/soda.py','backend/tools.py','backend/local_agent.py','backend/background_cmd.py','backend/opencode_monitor.py','backend/notebook.py','backend/supabase_client.py']; [py_compile.compile(f, doraise=True) for f in files]; print('ALL FILES COMPILE OK')"`

### Task 6.2: Verify imports work

- [ ] **Step 1: Test import chain**

Run: `cd backend; py -3.11 -c "import opencode_monitor; import notebook; print('Imports OK')"`

### Task 6.3: Verify tool definitions are valid

- [ ] **Step 1: Check tools.py loads**

Run: `cd backend; py -3.11 -c "from tools import ALL_TOOLS; names=[t['name'] for t in ALL_TOOLS]; assert 'opencode_start' in names; assert 'opencode_status' in names; assert 'opencode_stop' in names; assert 'notebook_read' in names; assert 'notebook_search' in names; print(f'All 5 tools found in ALL_TOOLS ({len(names)} total)')"`

### Task 6.4: Final commit

- [ ] **Step 1: Stage all changes**

Run: `git add -A`

- [ ] **Step 2: Review what changed**

Run: `git diff --cached --stat`

- [ ] **Step 3: Commit**

Run: `git commit -m "feat: OpenCode remote task management — agent_push, notebook, monitor, 5 new tools, system prompt"`

---

## Summary of Changes

| Phase | Files | What |
|-------|-------|------|
| 1 | server.py, local_agent.py | `agent_push` event for agent→SODA communication |
| 2 | notebook.py, supabase_client.py | Persistent task logging (Supabase + file) |
| 3 | opencode_monitor.py | OpenCode session lifecycle tracking |
| 4 | tools.py, soda.py, server.py, local_agent.py, background_cmd.py | 5 new tools + dispatch + streaming |
| 5 | soda.py | System prompt OpenCode workflow docs |
| 6 | — | End-to-end verification |
