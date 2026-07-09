"""
Persistent user memory for SODA.
- Profile: name, preferences, favorite things
- Facts: key-value facts the user tells SODA to remember
- History: last N user/model exchanges (rolling buffer)
- Recall: search facts by keyword

Storage: Supabase (if configured) or file-based fallback
"""
import json
from pathlib import Path
from datetime import datetime

MEM_DIR = Path("projects/long_term_memory").resolve()
MEM_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_PATH = MEM_DIR / "user_profile.json"
FACTS_PATH = MEM_DIR / "facts.jsonl"
HISTORY_PATH = MEM_DIR / "history.jsonl"

DEFAULT_PROFILE = {
    "name": "Sir",
    "creator": "RM Abir",
    "nationality": "Bangladeshi Bengali",
    "favorite_color": None,
    "timezone": None,
    "wake_word": "soda",
    "language": "en",
    "preferences": {},
    "created": datetime.now().isoformat(),
    "updated": datetime.now().isoformat(),
}

_SUPABASE = None

def _db():
    global _SUPABASE
    if _SUPABASE is None:
        from supabase_client import get_supabase
        _SUPABASE = get_supabase()
    return _SUPABASE


# ── Profile ──

def _load_profile() -> dict:
    db = _db()
    if db:
        try:
            r = db.table("profiles").select("*").limit(1).execute()
            if r.data and len(r.data) > 0:
                row = r.data[0]
                prefs = row.get("preferences") or {}
                return {
                    **DEFAULT_PROFILE,
                    "name": row.get("name", "Sir"),
                    "creator": row.get("creator", ""),
                    "nationality": row.get("nationality", ""),
                    "language": row.get("language", "en"),
                    "preferences": prefs if isinstance(prefs, dict) else {},
                    "created": row.get("created", "") or row.get("created_at", ""),
                    "updated": row.get("updated", "") or row.get("updated_at", ""),
                }
        except Exception as e:
            print(f"[Supabase] load_profile failed: {e}")
    if not PROFILE_PATH.exists():
        return dict(DEFAULT_PROFILE)
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return {**DEFAULT_PROFILE, **json.load(f)}
    except Exception:
        return dict(DEFAULT_PROFILE)


def _save_profile(profile: dict) -> None:
    profile["updated"] = datetime.now().isoformat()
    db = _db()
    if db:
        try:
            existing = db.table("profiles").select("id").limit(1).execute()
            now_iso = datetime.now().isoformat()
            payload = {
                "name": profile.get("name", "Sir"),
                "creator": profile.get("creator", ""),
                "nationality": profile.get("nationality", ""),
                "language": profile.get("language", "en"),
                "preferences": profile.get("preferences", {}),
                "updated_at": now_iso,
            }
            if existing.data and len(existing.data) > 0:
                row_id = existing.data[0]["id"]
                db.table("profiles").update(payload).eq("id", row_id).execute()
            else:
                payload["created_at"] = now_iso
                db.table("profiles").insert(payload).execute()
        except Exception as e:
            print(f"[Supabase] _save_profile failed: {e}")
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


def get_profile() -> dict:
    return _load_profile()


def set_profile_field(field: str, value) -> dict:
    p = _load_profile()
    if field in DEFAULT_PROFILE or field == "preferences":
        p[field] = value
        _save_profile(p)
        return {"success": True, "field": field, "value": value, "profile": p}
    return {"success": False, "error": f"Unknown field: {field!r}. Allowed: {list(DEFAULT_PROFILE.keys())}"}


def set_preference(key: str, value) -> dict:
    p = _load_profile()
    p.setdefault("preferences", {})[key] = value
    _save_profile(p)
    return {"success": True, "key": key, "value": value}


# ── Facts ──

def add_fact(key: str, value: str) -> dict:
    entry = {
        "key": key.strip().lower(),
        "value": value.strip(),
        "ts": datetime.now().isoformat(),
    }
    db = _db()
    if db:
        try:
            db.table("facts").insert({
                "key": entry["key"],
                "value": entry["value"],
                "category": "general",
            }).execute()
        except Exception as e:
            print(f"[Supabase] add_fact failed: {e}")
    FACTS_PATH.touch(exist_ok=True)
    with open(FACTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"success": True, "key": entry["key"], "value": entry["value"], "ts": entry["ts"]}


def search_facts(query: str, limit: int = 5) -> dict:
    q = query.lower()
    db = _db()
    if db:
        try:
            r = db.table("facts").select("*").or_(f"key.ilike.%{q}%,value.ilike.%{q}%").limit(limit).execute()
            matches = []
            for row in r.data or []:
                matches.append({
                    "key": row.get("key", ""),
                    "value": row.get("value", ""),
                    "ts": row.get("created_at", ""),
                })
            return {"success": True, "query": query, "count": len(matches), "matches": matches}
        except Exception as e:
            print(f"[Supabase] search_facts failed: {e}")
    if not FACTS_PATH.exists():
        return {"success": True, "query": query, "matches": []}
    matches = []
    try:
        with open(FACTS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if q in entry.get("key", "").lower() or q in entry.get("value", "").lower():
                    matches.append(entry)
                    if len(matches) >= limit:
                        break
    except Exception as e:
        return {"success": False, "error": str(e), "matches": []}
    return {"success": True, "query": query, "count": len(matches), "matches": matches}


def list_facts(limit: int = 50) -> dict:
    db = _db()
    if db:
        try:
            r = db.table("facts").select("*").order("created_at", desc=True).limit(limit).execute()
            if r.data:
                facts = []
                for row in reversed(r.data):
                    facts.append({
                        "key": row.get("key", ""),
                        "value": row.get("value", ""),
                        "ts": row.get("created_at", ""),
                    })
                return {"success": True, "count": len(facts), "facts": facts}
        except Exception as e:
            print(f"[Supabase] list_facts failed: {e}")
    if not FACTS_PATH.exists():
        return {"success": True, "count": 0, "facts": []}
    facts = []
    try:
        with open(FACTS_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                facts.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except Exception as e:
        return {"success": False, "error": str(e), "facts": []}
    return {"success": True, "count": len(facts), "facts": facts}


def delete_fact(key: str) -> dict:
    key = key.strip().lower()
    db = _db()
    if db:
        try:
            r = db.table("facts").delete().eq("key", key).execute()
        except Exception as e:
            print(f"[Supabase] delete_fact failed: {e}")
    if not FACTS_PATH.exists():
        return {"success": False, "error": "No facts stored"}
    kept = []
    deleted = 0
    try:
        with open(FACTS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    kept.append(line)
                    continue
                if entry.get("key", "").lower() == key:
                    deleted += 1
                else:
                    kept.append(json.dumps(entry, ensure_ascii=False))
        with open(FACTS_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(kept) + ("\n" if kept else ""))
    except Exception as e:
        return {"success": False, "error": str(e), "deleted": 0}
    return {"success": True, "key": key, "deleted": deleted}


# ── History (file-only, lightweight) ──

def add_history(role: str, text: str) -> None:
    HISTORY_PATH.touch(exist_ok=True)
    entry = {
        "role": role,
        "text": text[:2000],
        "ts": datetime.now().isoformat(),
    }
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > 200:
            with open(HISTORY_PATH, "w", encoding="utf-8") as f:
                f.writelines(lines[-200:])
    except Exception as e:
        print(f"[Supabase] add_history truncation failed: {e}")


def search_history(query: str, limit: int = 5) -> dict:
    if not HISTORY_PATH.exists():
        return {"success": True, "query": query, "matches": []}
    q = query.lower()
    matches = []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if q in entry.get("text", "").lower():
                    matches.append(entry)
                    if len(matches) >= limit:
                        break
    except Exception as e:
        return {"success": False, "error": str(e), "matches": []}
    return {"success": True, "query": query, "count": len(matches), "matches": matches}


def memory_summary() -> dict:
    p = _load_profile()
    facts = list_facts(limit=20).get("facts", [])
    return {
        "profile": p,
        "fact_count": len(facts),
        "recent_facts": facts[-5:],
    }
