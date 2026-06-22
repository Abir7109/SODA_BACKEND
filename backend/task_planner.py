"""
Task planner — tracks multi-step task execution with TODO items.
Each plan has a list of tasks. Tasks can be pending/running/done/failed.
"""
import json, uuid, time
from datetime import datetime
from pathlib import Path

TODO_FILE = Path(__file__).parent / "todos.json"

class TaskPlanner:
    def __init__(self):
        self.active_plan = None
        self.history = []
        self._load()

    def _save(self):
        if not self.active_plan:
            TODO_FILE.write_text("null", encoding="utf-8")
            return
        data = {
            "id": self.active_plan["id"],
            "title": self.active_plan["title"],
            "created_at": self.active_plan["created_at"],
            "status": self.active_plan["status"],
            "tasks": []
        }
        for t in self.active_plan["tasks"]:
            data["tasks"].append({
                "id": t["id"],
                "index": t["index"],
                "title": t["title"],
                "description": t["description"],
                "status": t["status"],
                "result": t["result"],
            })
        TODO_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load(self):
        try:
            if TODO_FILE.exists():
                raw = TODO_FILE.read_text(encoding="utf-8").strip()
                if raw and raw != "null":
                    data = json.loads(raw)
                    self.active_plan = {
                        "id": data["id"],
                        "title": data["title"],
                        "created_at": data.get("created_at", datetime.now().isoformat()),
                        "status": data.get("status", "running"),
                        "tasks": data.get("tasks", []),
                    }
        except Exception:
            self.active_plan = None

    def create_plan(self, title, tasks):
        plan = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "created_at": datetime.now().isoformat(),
            "tasks": [],
            "status": "running",
        }
        for i, t in enumerate(tasks):
            if isinstance(t, str):
                t = {"title": t}
            plan["tasks"].append({
                "id": str(uuid.uuid4())[:8],
                "index": i,
                "title": t.get("title", f"Step {i+1}"),
                "description": t.get("description", ""),
                "status": "pending",
                "result": None,
            })
        self.active_plan = plan
        self.history.append(plan)
        self._save()
        return self._dump()

    def update_task(self, task_id, status, result=None):
        if not self.active_plan:
            return {"error": "No active plan"}
        for task in self.active_plan["tasks"]:
            if task["id"] == task_id:
                task["status"] = status
                if result:
                    task["result"] = result
                # Check if all tasks done/failed
                all_terminal = all(
                    t["status"] in ("done", "failed") for t in self.active_plan["tasks"]
                )
                if all_terminal:
                    self.active_plan["status"] = "completed"
                self._save()
                return self._dump()
        return {"error": f"Task {task_id} not found"}

    def cancel_plan(self):
        if not self.active_plan:
            return {"error": "No active plan"}
        self.active_plan = None
        self._save()
        return {"status": "cancelled"}

    def get_plan_summary(self):
        if not self.active_plan:
            return None
        tasks = self.active_plan["tasks"]
        done = sum(1 for t in tasks if t["status"] == "done")
        total = len(tasks)
        remaining = [t["title"] for t in tasks if t["status"] not in ("done", "failed")]
        summary = f"{done}/{total} tasks done"
        if remaining:
            summary += f". Remaining: {', '.join(remaining)}"
        return summary

    def get_plan(self):
        if not self.active_plan:
            return {"error": "No active plan"}
        return self._dump()

    def _dump(self):
        return {
            "id": self.active_plan["id"],
            "title": self.active_plan["title"],
            "status": self.active_plan["status"],
            "tasks": [
                {
                    "id": t["id"],
                    "index": t["index"],
                    "title": t["title"],
                    "description": t["description"],
                    "status": t["status"],
                    "result": t["result"],
                }
                for t in self.active_plan["tasks"]
            ],
        }

_planner = TaskPlanner()

def plan_tasks(title, tasks):
    return _planner.create_plan(title, tasks)

def update_task(task_id, status, result=None):
    return _planner.update_task(task_id, status, result)

def get_active_plan():
    return _planner.get_plan()

def cancel_plan():
    return _planner.cancel_plan()
