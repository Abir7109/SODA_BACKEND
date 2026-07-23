import json
import secrets
import time
from pathlib import Path
import httpx

_REGISTRY_FILE = Path(__file__).resolve().parent.parent / "projects_registry.json"

def _load():
    if not _REGISTRY_FILE.exists():
        return {"projects": []}
    try:
        return json.loads(_REGISTRY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"projects": []}

def _save(data):
    _REGISTRY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def generate_key():
    return "sk-soda-" + secrets.token_urlsafe(32)


def register(name: str, endpoint: str) -> dict:
    data = _load()
    pid = "proj_" + secrets.token_hex(8)
    api_key = generate_key()
    entry = {
        "id": pid,
        "name": name,
        "api_key": api_key,
        "endpoint": endpoint.rstrip("/"),
        "created_at": time.time(),
        "last_status": "unknown",
        "last_data": None,
        "last_error": None,
    }
    data["projects"].append(entry)
    _save(data)
    return {"id": pid, "name": name, "api_key": api_key, "endpoint": endpoint}


def list_projects() -> list:
    data = _load()
    return [
        {k: v for k, v in p.items() if k != "api_key"}
        for p in data["projects"]
    ]


def remove(project_id: str) -> dict:
    data = _load()
    before = len(data["projects"])
    data["projects"] = [p for p in data["projects"] if p["id"] != project_id]
    if len(data["projects"]) == before:
        return {"success": False, "error": "Project not found"}
    _save(data)
    return {"success": True}


async def query(project_id: str) -> dict:
    data = _load()
    entry = next((p for p in data["projects"] if p["id"] == project_id), None)
    if not entry:
        return {"success": False, "error": "Project not found"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{entry['endpoint']}/api/soda-stats",
                headers={"Authorization": f"Bearer {entry['api_key']}"},
            )
            resp.raise_for_status()
            body = resp.json()
            entry["last_status"] = "online"
            entry["last_data"] = body
            entry["last_error"] = None
            _save(data)
            return {"success": True, "project": entry["name"], "data": body}
    except httpx.TimeoutException:
        entry["last_status"] = "timeout"
        entry["last_error"] = "Request timed out after 15s"
        _save(data)
        return {"success": False, "project": entry["name"], "error": "timeout"}
    except Exception as e:
        entry["last_status"] = "error"
        entry["last_error"] = str(e)
        _save(data)
        return {"success": False, "project": entry["name"], "error": str(e)}


async def query_all() -> list:
    data = _load()
    results = []
    for p in data["projects"]:
        r = await query(p["id"])
        results.append(r)
    return results
