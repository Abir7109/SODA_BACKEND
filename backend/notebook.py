"""OpenCode Notebook — persistent task logging.

Dual-writes to Supabase (opencode_notebook table) and file backup
(projects/long_term_memory/notebook.json).
"""
import json
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
