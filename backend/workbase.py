import os
import json
import time

WORKBASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workbase")
PROJECTS_DIR = os.path.join(WORKBASE_DIR, "projects")
INDEX_PATH = os.path.join(WORKBASE_DIR, "index.json")


workbase_tool = {
    "name": "workbase",
    "description": "Workbase project tracking system. Use action to select:\n"
        "  list — List all registered projects\n"
        "  get — Get detailed context, tech stack, status, progress log, and suggestions for a project\n"
        "  save_progress — Append a progress or status update to a project's log\n"
        "  import — Import an existing project folder into Workbase\n"
        "  save_context — Save a summary of current conversation about a project\n"
        "  compare — Compare project's current state against last saved context",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Workbase operation",
                "enum": ["list", "get", "save_progress", "import", "save_context", "compare"]
            },
            "project_name": {
                "type": "STRING",
                "description": "Internal project name (e.g. 'ai-autoresponder'). Required for get/save_progress/save_context/compare."
            },
            "entry": {
                "type": "STRING",
                "description": "Progress or status update text. Required for save_progress."
            },
            "folder_path": {
                "type": "STRING",
                "description": "Filesystem path to project folder. Required for import."
            },
            "context": {
                "type": "STRING",
                "description": "Summary of conversation/discussion. Required for save_context."
            }
        },
        "required": ["action"]
    }
}


class Workbase:
    def __init__(self):
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        self._load_index()
        self._scan_projects_dir()

    def _scan_projects_dir(self):
        indexed_names = {p["name"] for p in self.index["projects"]}
        for entry in os.listdir(PROJECTS_DIR):
            entry_path = os.path.join(PROJECTS_DIR, entry)
            if not os.path.isdir(entry_path) or entry in indexed_names:
                continue
            context_path = os.path.join(entry_path, "context.md")
            if not os.path.exists(context_path):
                continue
            display_name = entry.replace("-", " ").title()
            description = ""
            tech_stack = []
            content = ""
            try:
                with open(context_path, "r", encoding="utf-8") as f:
                    content = f.read()
                lines = content.split("\n")
                in_tech_stack = False
                in_description = False
                for i, line in enumerate(lines):
                    ll = line.strip().lower()
                    if ll.startswith("## tech stack"):
                        in_tech_stack = True
                        continue
                    if ll.startswith("## ") and not ll.startswith("## tech stack"):
                        in_tech_stack = False
                    if in_tech_stack and (ll.startswith("- ") or ll.startswith("* ")):
                        tech_stack.append(line.strip("- *").strip())
                    if ll.startswith("# ") and not description:
                        display_name = line.strip("# ").strip()
                    if ll.startswith("## description"):
                        in_description = True
                        continue
                    if ll.startswith("## ") and not ll.startswith("## description"):
                        in_description = False
                    if in_description and ll and not ll.startswith("#"):
                        description = line.strip()
                        in_description = False
            except Exception:
                pass
            self.index["projects"].append({
                "name": entry,
                "display_name": display_name,
                "description": description,
                "tech_stack": tech_stack,
                "status": "Tracked",
                "folder_path": "",
                "last_context": "",
                "last_context_time": "",
                "progress_log": [],
            })
        if os.listdir(PROJECTS_DIR):
            self._save_index()

    def _load_index(self):
        if os.path.exists(INDEX_PATH):
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                self.index = json.load(f)
        else:
            self.index = {"projects": []}
            self._save_index()

    def _save_index(self):
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

    def _find_project(self, name):
        for p in self.index["projects"]:
            if p["name"] == name:
                return p
        return None

    def list_projects(self):
        return [
            {
                "name": p["name"],
                "display_name": p.get("display_name", p["name"]),
                "status": p.get("status", "Unknown"),
                "description": p.get("description", ""),
                "tech_stack": p.get("tech_stack", []),
                "progress_count": len(p.get("progress_log", [])),
            }
            for p in self.index["projects"]
        ]

    def get_project_status(self, name):
        p = self._find_project(name)
        if not p:
            return None
        context_path = os.path.join(PROJECTS_DIR, name, "context.md")
        context = ""
        if os.path.exists(context_path):
            with open(context_path, "r", encoding="utf-8") as f:
                context = f.read()
        return {
            "name": p["name"],
            "display_name": p.get("display_name", p["name"]),
            "description": p.get("description", ""),
            "tech_stack": p.get("tech_stack", []),
            "status": p.get("status", "Unknown"),
            "folder_path": p.get("folder_path", ""),
            "context": context,
            "progress_log": p.get("progress_log", []),
            "progress_count": len(p.get("progress_log", [])),
            "last_context": p.get("last_context", ""),
            "last_context_time": p.get("last_context_time", "Never"),
            "suggestions": self._generate_suggestions(p),
        }

    def save_progress(self, name, entry):
        p = self._find_project(name)
        if not p:
            return False, f"Project '{name}' not found."
        if "progress_log" not in p:
            p["progress_log"] = []
        p["progress_log"].append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "entry": entry,
        })
        self._save_index()
        return True, f"Progress saved for '{p.get('display_name', name)}'."

    def save_context(self, name, context):
        p = self._find_project(name)
        if not p:
            return False, f"Project '{name}' not found."
        p["last_context"] = context
        p["last_context_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save_index()
        return True, f"Context saved for '{p.get('display_name', name)}'."

    def compare_progress(self, name):
        p = self._find_project(name)
        if not p:
            return {"error": f"Project '{name}' not found."}

        log = p.get("progress_log", [])
        old_context = p.get("last_context", "")
        folder_path = p.get("folder_path", "")

        folder_snapshot = ""
        if folder_path and os.path.isdir(folder_path):
            folder_snapshot = self._read_folder_snapshot(folder_path)

        context_path = os.path.join(PROJECTS_DIR, name, "context.md")
        context_content = ""
        if os.path.exists(context_path):
            try:
                with open(context_path, "r", encoding="utf-8") as f:
                    context_content = f.read()
            except Exception:
                pass

        return {
            "project": p["name"],
            "display_name": p.get("display_name", p["name"]),
            "status": p.get("status", "Unknown"),
            "description": p.get("description", ""),
            "tech_stack": p.get("tech_stack", []),
            "last_context": old_context,
            "last_context_time": p.get("last_context_time", "Never"),
            "context_md": context_content,
            "folder_path": folder_path or "Not set",
            "folder_snapshot": folder_snapshot,
            "progress_log": log,
            "progress_count": len(log),
            "recent_progress": log[-3:] if log else [],
            "suggestions": self._generate_suggestions(p),
        }

    def _read_folder_snapshot(self, folder_path):
        snapshot_parts = []
        try:
            entries = sorted(os.listdir(folder_path))
            snapshot_parts.append(f"Top-level contents ({len(entries)} items):")
            for e in entries[:20]:
                ep = os.path.join(folder_path, e)
                suffix = "/" if os.path.isdir(ep) else ""
                snapshot_parts.append(f"  {e}{suffix}")

            priority_files = ["README.md", "context.md", "package.json", "build.gradle", "pom.xml", "Cargo.toml", "pyproject.toml", "requirements.txt"]
            read_count = 0
            for pf in priority_files:
                if read_count >= 3:
                    break
                fp = os.path.join(folder_path, pf)
                if os.path.isfile(fp) and os.path.getsize(fp) < 5000:
                    try:
                        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read()
                        snapshot_parts.append(f"\n--- {pf} ---")
                        snapshot_parts.append(text[:2000])
                        read_count += 1
                    except Exception:
                        pass
        except Exception as e:
            snapshot_parts.append(f"(error reading folder: {e})")

        return "\n".join(snapshot_parts)

    def _generate_suggestions(self, p):
        suggestions = []
        log = p.get("progress_log", [])
        status = p.get("status", "")

        if not log:
            suggestions.append("No progress logged yet — start tracking updates to this project")

        if status in ("Tracked", "Imported", ""):
            suggestions.append("Define a clear project status (Development / Production / Maintenance)")

        context_path = os.path.join(PROJECTS_DIR, p["name"], "context.md")
        if os.path.exists(context_path):
            try:
                with open(context_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "## Next Steps" in content:
                    parts = content.split("## Next Steps")
                    if len(parts) > 1:
                        section = parts[1].split("##")[0]
                        for line in section.split("\n"):
                            line = line.strip()
                            if line.startswith("- ") or line.startswith("* "):
                                suggestions.append(line.strip("- *").strip())
            except Exception:
                pass

        return suggestions

    def import_project(self, folder_path):
        folder_path = folder_path.strip()
        if not os.path.isdir(folder_path):
            return {"success": False, "error": f"Folder not found: {folder_path}"}

        folder_name = os.path.basename(folder_path)
        safe_name = "".join(c for c in folder_name if c.isalnum() or c in ('-', '_')).lower() or "project"

        existing = self._find_project(safe_name)
        if existing:
            existing["folder_path"] = folder_path
            self._save_index()
            return {"success": True, "name": safe_name, "note": "Updated existing entry."}

        description = ""
        tech_stack = []
        context_content = ""

        context_candidates = ["context.md", "context.txt", "PROJECT_SUMMARY.md", "PROJECT_DESCRIPTION.txt", "README.md"]
        found_context = None
        for candidate in context_candidates:
            cp = os.path.join(folder_path, candidate)
            if os.path.exists(cp):
                found_context = cp
                break

        if found_context:
            try:
                with open(found_context, "r", encoding="utf-8", errors="ignore") as f:
                    context_content = f.read()
                lines = context_content.split("\n")
                in_tech_stack = False
                in_description = False
                for i, line in enumerate(lines):
                    ll = line.strip().lower()
                    if ll.startswith("## tech stack"):
                        in_tech_stack = True
                        continue
                    if ll.startswith("## ") and not ll.startswith("## tech stack"):
                        in_tech_stack = False
                    if in_tech_stack and (ll.startswith("- ") or ll.startswith("* ")):
                        tech_stack.append(line.strip("- *").strip())
                    if ll.startswith("# ") and not description:
                        description = line.strip("# ").strip()
                    if ll.startswith("## description"):
                        in_description = True
                        continue
                    if ll.startswith("## ") and not ll.startswith("## description"):
                        in_description = False
                    if in_description and ll and not ll.startswith("#"):
                        description = line.strip()
                        in_description = False
            except Exception:
                pass

        project_dir = os.path.join(PROJECTS_DIR, safe_name)
        os.makedirs(project_dir, exist_ok=True)

        if not context_content:
            context_content = f"# {folder_name}\n\n## Description\nImported from {folder_path}\n\n## Tech Stack\n- See project files\n\n## Status\nImported\n"

        context_path = os.path.join(project_dir, "context.md")
        with open(context_path, "w", encoding="utf-8") as f:
            f.write(context_content)

        entry = {
            "name": safe_name,
            "display_name": folder_name,
            "description": description or f"Project imported from {folder_path}",
            "tech_stack": tech_stack,
            "status": "Tracked",
            "folder_path": folder_path,
            "last_context": "",
            "last_context_time": "",
            "progress_log": [],
        }
        self.index["projects"].append(entry)
        self._save_index()

        return {
            "success": True,
            "name": safe_name,
            "display_name": folder_name,
            "description": entry["description"],
        }


