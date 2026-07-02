import json, os, base64, time
from pathlib import Path
from datetime import datetime

PHOTOS_DIR = Path("projects/camera_captures").resolve()
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = PHOTOS_DIR / "photos.jsonl"

_SUPABASE = None

def _db():
    global _SUPABASE
    if _SUPABASE is None:
        from supabase_client import get_supabase
        _SUPABASE = get_supabase()
    return _SUPABASE

def save_photo(base64_data, description="", facing="user"):
    ts = datetime.now().isoformat()
    slug = int(time.time())
    file_path = PHOTOS_DIR / f"photo_{slug}.jpg"

    try:
        img_bytes = base64.b64decode(base64_data)
        file_path.write_bytes(img_bytes)
    except Exception as e:
        return {"success": False, "error": f"Failed to save image: {e}"}

    record = {"ts": ts, "file_path": str(file_path), "description": description, "facing": facing}

    db = _db()
    if db:
        try:
            db.table("camera_photos").insert(record).execute()
        except Exception as e:
            with open(str(INDEX_PATH), "a") as f:
                f.write(json.dumps(record) + "\n")
    else:
        with open(str(INDEX_PATH), "a") as f:
            f.write(json.dumps(record) + "\n")

    return {"success": True, "record": record}

def query_photos(limit=10):
    results = []
    db = _db()
    if db:
        try:
            resp = db.table("camera_photos").select("*").order("ts", desc=True).limit(limit).execute()
            results = resp.data or []
        except Exception as e:
            results = []

    if not results and INDEX_PATH.exists():
        lines = INDEX_PATH.read_text().strip().split("\n")
        for line in reversed(lines[-limit:]):
            try:
                results.append(json.loads(line))
            except:
                pass

    return results
