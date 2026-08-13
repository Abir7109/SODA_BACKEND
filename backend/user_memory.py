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


def _pg():
    from supabase_client import get_db, db_fetch, db_execute
    return get_db(), db_fetch, db_execute


# ── Profile ──

def _load_profile() -> dict:
    db, fetch, execute = _pg()
    if db:
        try:
            rows = fetch(
                "SELECT name, creator, nationality, language, preferences, created_at, updated_at "
                "FROM profiles ORDER BY id LIMIT 1"
            )
            if rows:
                row = rows[0]
                prefs = row.get("preferences") or {}
                if isinstance(prefs, str):
                    try:
                        prefs = json.loads(prefs)
                    except Exception:
                        prefs = {}
                return {
                    **DEFAULT_PROFILE,
                    "name": row.get("name", "Sir") or "Sir",
                    "creator": row.get("creator", "") or "",
                    "nationality": row.get("nationality", "") or "",
                    "language": row.get("language", "en") or "en",
                    "preferences": prefs if isinstance(prefs, dict) else {},
                    "created": str(row.get("created_at", "") or ""),
                    "updated": str(row.get("updated_at", "") or ""),
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
    db, fetch, execute = _pg()
    if db:
        try:
            now_iso = datetime.now().isoformat()
            payload = {
                "name": profile.get("name", "Sir"),
                "creator": profile.get("creator", ""),
                "nationality": profile.get("nationality", ""),
                "language": profile.get("language", "en"),
                "preferences": json.dumps(profile.get("preferences", {})),
                "updated_at": now_iso,
            }
            rows = fetch("SELECT id FROM profiles ORDER BY id LIMIT 1")
            if rows:
                execute(
                    "UPDATE profiles SET name=%s, creator=%s, nationality=%s, language=%s, "
                    "preferences=%s, updated_at=%s WHERE id=%s",
                    (payload["name"], payload["creator"], payload["nationality"],
                     payload["language"], payload["preferences"], now_iso, rows[0]["id"]),
                )
            else:
                execute(
                    "INSERT INTO profiles (name, creator, nationality, language, preferences, "
                    "created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (payload["name"], payload["creator"], payload["nationality"],
                     payload["language"], payload["preferences"], now_iso, now_iso),
                )
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
    db, fetch, execute = _pg()
    if db:
        try:
            execute(
                "INSERT INTO facts (key, value, category) VALUES (%s,%s,%s)",
                (entry["key"], entry["value"], "general"),
            )
            return {"success": True, "key": entry["key"], "value": entry["value"], "ts": entry["ts"]}
        except Exception as e:
            print(f"[Supabase] add_fact failed: {e}")
    FACTS_PATH.touch(exist_ok=True)
    with open(FACTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"success": True, "key": entry["key"], "value": entry["value"], "ts": entry["ts"]}


def search_facts(query: str, limit: int = 5) -> dict:
    q = query.lower()
    db, fetch, execute = _pg()
    if db:
        try:
            rows = fetch(
                "SELECT key, value, created_at FROM facts "
                "WHERE key ILIKE %s OR value ILIKE %s ORDER BY id DESC LIMIT %s",
                (f"%{q}%", f"%{q}%", limit),
            )
            if rows is not None:
                matches = [{
                    "key": r["key"], "value": r["value"],
                    "ts": str(r["created_at"] or ""),
                } for r in rows]
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
    db, fetch, execute = _pg()
    if db:
        try:
            rows = fetch(
                "SELECT key, value, created_at FROM facts ORDER BY id DESC LIMIT %s", (limit,)
            )
            if rows is not None:
                facts = [{
                    "key": r["key"], "value": r["value"],
                    "ts": str(r["created_at"] or ""),
                } for r in rows]
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
    db, fetch, execute = _pg()
    if db:
        try:
            execute("DELETE FROM facts WHERE key=%s", (key,))
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
