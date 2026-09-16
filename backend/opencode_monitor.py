"""OpenCode Session Monitor — tracks running OpenCode tasks.

Used by the local agent to stream stdout/stderr and by SODA to
check task status. The actual execution happens on the local agent
via terminal_execute; this module tracks state.
"""
import uuid
from datetime import datetime, timezone

# In-memory task registry (server-side)
_tasks = {}  # task_id -> OpencodeTask


class OpencodeTask:
    __slots__ = ("task_id", "folder", "prompt", "status", "output_lines",
                 "started_at", "completed_at", "error", "exit_code")

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
