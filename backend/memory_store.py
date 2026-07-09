"""
Enhanced memory system for SODA.
Extends user_memory.py with:
- People storage (name, relationship, traits, notes)
- Lessons learned (situation, correction, frequency)
- Conversation summaries
- Context block builder for session start injection
- Deduplicated fact storage with categories

Storage: Supabase (if configured) or file-based fallback
"""
import asyncio
import json
import re
from pathlib import Path
from datetime import datetime

MEM_DIR = Path("projects/long_term_memory").resolve()
MEM_DIR.mkdir(parents=True, exist_ok=True)
PEOPLE_PATH = MEM_DIR / "people.jsonl"
LESSONS_PATH = MEM_DIR / "lessons.jsonl"
SUMMARIES_PATH = MEM_DIR / "summaries.jsonl"
MAX_ENTRIES = 200

_SUPABASE = None

def _db():
    global _SUPABASE
    if _SUPABASE is None:
        from supabase_client import get_supabase
        _SUPABASE = get_supabase()
    return _SUPABASE


# ── People ──

def remember_person(name, relationship="", traits="", preferences="", notes=""):
    """Store info about a person. Deduplicates by name."""
    name = name.strip()
    if not name:
        return {"success": False, "error": "Name is required"}
    now = datetime.now().isoformat()

    db = _db()
    if db:
        try:
            existing = db.table("people").select("id").eq("name", name).limit(1).execute()
            payload = {
                "name": name,
                "relationship": relationship,
                "traits": traits,
                "preferences": preferences,
                "notes": notes,
                "updated_at": now,
            }
            if existing.data and len(existing.data) > 0:
                db.table("people").update(payload).eq("id", existing.data[0]["id"]).execute()
            else:
                payload["created_at"] = now
                db.table("people").insert(payload).execute()
        except Exception as e:
            print(f"[Supabase] remember_person failed: {e}")

    PEOPLE_PATH.touch(exist_ok=True)
    entries = []
    found = False
    if PEOPLE_PATH.exists():
        with open(PEOPLE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("name", "").lower() == name.lower():
                    entry["relationship"] = relationship or entry.get("relationship", "")
                    entry["traits"] = traits or entry.get("traits", "")
                    entry["preferences"] = preferences or entry.get("preferences", "")
                    entry["notes"] = notes or entry.get("notes", "")
                    entry["ts"] = now
                    found = True
                entries.append(entry)
    if not found:
        entries.append({
            "name": name,
            "relationship": relationship,
            "traits": traits,
            "preferences": preferences,
            "notes": notes,
            "ts": now,
        })
    if len(entries) > MAX_ENTRIES:
        entries = entries[-MAX_ENTRIES:]
    with open(PEOPLE_PATH, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"success": True, "name": name, "action": "updated" if found else "created"}


def recall_person(query, limit=5):
    """Search people by name, relationship, or traits."""
    q = query.lower()
    db = _db()
    if db:
        try:
            r = db.table("people").select("*").or_(
                f"name.ilike.%{q}%,relationship.ilike.%{q}%,traits.ilike.%{q}%,notes.ilike.%{q}%"
            ).limit(limit).execute()
            matches = []
            for row in r.data or []:
                matches.append({
                    "name": row.get("name", ""),
                    "relationship": row.get("relationship", ""),
                    "traits": row.get("traits", ""),
                    "preferences": row.get("preferences", ""),
                    "notes": row.get("notes", ""),
                    "ts": row.get("ts", ""),
                })
            return {"success": True, "query": query, "count": len(matches), "matches": matches}
        except Exception as e:
            print(f"[Supabase] recall_person failed: {e}")
    if not PEOPLE_PATH.exists():
        return {"success": True, "query": query, "matches": []}
    matches = []
    try:
        with open(PEOPLE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                searchable = f"{entry.get('name','')} {entry.get('relationship','')} {entry.get('traits','')} {entry.get('notes','')}".lower()
                if q in searchable:
                    matches.append(entry)
                    if len(matches) >= limit:
                        break
    except Exception as e:
        return {"success": False, "error": str(e), "matches": []}
    return {"success": True, "query": query, "count": len(matches), "matches": matches}


def recall_by_relationship(relationship, limit=5):
    """Search people whose relationship field contains the given keyword."""
    if not relationship:
        return {"success": True, "relationship": relationship, "matches": []}
    q = relationship.lower().strip()
    db = _db()
    if db:
        try:
            r = db.table("people").select("*").ilike("relationship", f"%{q}%").limit(limit).execute()
            matches = []
            for row in r.data or []:
                matches.append({
                    "name": row.get("name", ""),
                    "relationship": row.get("relationship", ""),
                    "traits": row.get("traits", ""),
                    "preferences": row.get("preferences", ""),
                    "notes": row.get("notes", ""),
                    "ts": row.get("ts", ""),
                })
            return {"success": True, "relationship": relationship, "count": len(matches), "matches": matches}
        except Exception as e:
            print(f"[Supabase] recall_by_relationship failed: {e}")
    if not PEOPLE_PATH.exists():
        return {"success": True, "relationship": relationship, "matches": []}
    matches = []
    try:
        with open(PEOPLE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rel = entry.get("relationship", "").lower()
                if q in rel:
                    matches.append(entry)
                    if len(matches) >= limit:
                        break
    except Exception as e:
        return {"success": False, "error": str(e), "matches": []}
    return {"success": True, "relationship": relationship, "count": len(matches), "matches": matches}


def list_people(limit=20):
    db = _db()
    if db:
        try:
            r = db.table("people").select("*").order("created_at", desc=True).limit(limit).execute()
            if r.data:
                entries = []
                for row in reversed(r.data):
                    entries.append({
                        "name": row.get("name", ""),
                        "relationship": row.get("relationship", ""),
                        "traits": row.get("traits", ""),
                        "preferences": row.get("preferences", ""),
                        "notes": row.get("notes", ""),
                        "ts": row.get("created_at", "") or row.get("created", "") or "",
                    })
                return entries
        except Exception as e:
            print(f"[Supabase] list_people failed: {e}")
    if not PEOPLE_PATH.exists():
        return []
    entries = []
    try:
        with open(PEOPLE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    return entries[-limit:]


# ── Lessons ──

def remember_lesson(situation, correction):
    """Learn from a mistake or correction. Tracks frequency."""
    situation = situation.strip()
    correction = correction.strip()
    if not situation or not correction:
        return {"success": False, "error": "situation and correction are required"}
    now = datetime.now().isoformat()

    db = _db()
    if db:
        try:
            existing = db.table("lessons").select("id,count").eq("situation", situation).limit(1).execute()
            payload = {
                "situation": situation,
                "correction": correction,
                "count": 1,
                "created_at": now,
            }
            if existing.data and len(existing.data) > 0:
                row = existing.data[0]
                payload["count"] = (row.get("count") or 0) + 1
                db.table("lessons").update(payload).eq("id", row["id"]).execute()
            else:
                db.table("lessons").insert(payload).execute()
        except Exception as e:
            print(f"[Supabase] remember_lesson failed: {e}")

    LESSONS_PATH.touch(exist_ok=True)
    entries = []
    found = False
    if LESSONS_PATH.exists():
        with open(LESSONS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("situation", "").lower() == situation.lower():
                    entry["correction"] = correction
                    entry["count"] = entry.get("count", 0) + 1
                    entry["ts"] = now
                    found = True
                entries.append(entry)
    if not found:
        entries.append({
            "situation": situation,
            "correction": correction,
            "count": 1,
            "ts": now,
        })
    if len(entries) > MAX_ENTRIES:
        entries = entries[-MAX_ENTRIES:]
    with open(LESSONS_PATH, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"success": True, "situation": situation, "action": "updated" if found else "created"}


def recall_lessons(query="", limit=5):
    """Search lessons by situation or correction. Empty query returns all recent."""
    q = query.lower().strip()
    db = _db()
    if db:
        try:
            r = (db.table("lessons").select("*")
                 .order("created_at", desc=True)
                 .limit(limit).execute())
            if r.data:
                entries = []
                for row in reversed(r.data):
                    situation = row.get("situation", "")
                    correction = row.get("correction", "")
                    if not q or q in f"{situation} {correction}".lower():
                        entries.append({
                            "situation": situation,
                            "correction": correction,
                            "count": row.get("count", 1),
                            "ts": row.get("created_at", "") or row.get("created", "") or "",
                        })
                return entries
        except Exception as e:
            print(f"[Supabase] recall_lessons failed: {e}")
    if not LESSONS_PATH.exists():
        return []
    entries = []
    try:
        with open(LESSONS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not q or q in f"{entry.get('situation','')} {entry.get('correction','')}".lower():
                    entries.append(entry)
    except Exception:
        return []
    return entries[-limit:]


# ── Conversation Summaries ──

async def summarize_exchanges(exchanges):
    """Take a list of {user, model} exchange dicts and produce a structured summary.
    Uses Gemini REST API to compress the conversation into key points.
    Returns {key_points, topics, action_items, user_preferences} or None on failure.
    """
    if not exchanges or not isinstance(exchanges, list) or len(exchanges) < 2:
        return None
    import os, json, google.genai as genai
    lines = []
    for e in exchanges:
        if "user" in e:
            lines.append(f"User: {e['user'][:200]}")
        if "model" in e:
            lines.append(f"SODA: {e['model'][:200]}")
    if not lines:
        return None
    text = "\n".join(lines)
    prompt = f"""Summarize this conversation exchange. Return ONLY valid JSON with these fields:
- key_points: list of important statements, facts, or decisions (max 3)
- topics: list of topics discussed (max 3)
- action_items: list of tasks or follow-ups mentioned (max 2)
- user_preferences: list of user preferences revealed (max 2)

Keep each item under 15 words. Respond with JSON only.

CONVERSATION:
{text}"""
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        resp = await asyncio.to_thread(
            lambda: client.models.generate_content(
                model="models/gemini-2.5-flash", contents=prompt
            )
        )
        raw = resp.text or ""
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        result = json.loads(raw)
        if isinstance(result, dict):
            return {
                "key_points": result.get("key_points", []),
                "topics": result.get("topics", []),
                "action_items": result.get("action_items", []),
                "user_preferences": result.get("user_preferences", []),
            }
    except Exception:
        pass
    return None


def save_summary(session_id, topics=None, key_decisions=None, last_exchanges=None):
    """Store a conversation summary at session end."""
    now = datetime.now().isoformat()
    entry = {
        "session_id": session_id,
        "topics": topics or [],
        "key_decisions": key_decisions or [],
        "last_exchanges": (last_exchanges or [])[:5],
        "ts": now,
    }

    db = _db()
    if db:
        try:
            db.table("conversation_summaries").insert({
                "session_id": session_id,
                "summary": {
                    "key_decisions": key_decisions or [],
                    "last_exchanges": (last_exchanges or [])[:5],
                },
                "topics": topics or [],
            }).execute()
        except Exception as e:
            print(f"[Supabase] save_summary failed: {e}")

    SUMMARIES_PATH.touch(exist_ok=True)
    entries = []
    if SUMMARIES_PATH.exists():
        with open(SUMMARIES_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(line)
    entries.append(json.dumps(entry, ensure_ascii=False))
    if len(entries) > 50:
        entries = entries[-50:]
    with open(SUMMARIES_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(entries) + "\n")


def get_recent_summaries(limit=3):
    """Get last N conversation summaries."""
    db = _db()
    if db:
        try:
            r = (db.table("conversation_summaries").select("*")
                 .order("created_at", desc=True)
                 .limit(limit).execute())
            if r.data:
                entries = []
                for row in reversed(r.data):
                    summary_data = row.get("summary", {})
                    if isinstance(summary_data, str):
                        try:
                            summary_data = json.loads(summary_data)
                        except Exception:
                            summary_data = {}
                    entries.append({
                        "session_id": row.get("session_id", ""),
                        "topics": row.get("topics", []),
                        "key_decisions": summary_data.get("key_decisions", []),
                        "last_exchanges": summary_data.get("last_exchanges", []),
                        "ts": row.get("created_at", ""),
                    })
                return entries
        except Exception as e:
            print(f"[Supabase] get_recent_summaries failed: {e}")
    if not SUMMARIES_PATH.exists():
        return []
    entries = []
    try:
        with open(SUMMARIES_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    return entries[-limit:]


# ── Enhanced Facts (dedup on write) ──

def add_fact(key, value, category="general"):
    """Add a fact with dedup — replaces previous entry with same key."""
    from user_memory import delete_fact
    delete_fact(key)
    from user_memory import add_fact as _add_fact
    return _add_fact(key, value)


def list_memory(type="all", limit=10):
    """Unified listing across all memory stores."""
    result = {}
    if type in ("all", "facts"):
        from user_memory import list_facts
        result["facts"] = list_facts(limit=limit).get("facts", [])
    if type in ("all", "people"):
        result["people"] = list_people(limit=limit)
    if type in ("all", "lessons"):
        result["lessons"] = recall_lessons("", limit=limit)
    if type in ("all", "summaries"):
        result["summaries"] = get_recent_summaries(limit=limit)
    return result


# ── Context Block Builder ──

def build_context_block():
    """Build a memory-restoration context block for session start injection."""
    from user_memory import memory_summary, list_facts
    parts = []
    summary = memory_summary()
    profile = summary.get("profile", {})
    name = profile.get("name", "Sir")
    prefs = profile.get("preferences", {})

    parts.append("--- MEMORY RESTORED ---")
    parts.append(f"You are continuing from a previous session. Here's what you know:")

    user_line = f"USER: {name}"
    if prefs:
        pref_str = ", ".join(f"{k}={v}" for k, v in list(prefs.items())[:5])
        user_line += f" — {pref_str}"
    parts.append(user_line)

    facts = summary.get("recent_facts", [])
    if facts:
        fact_str = "; ".join(f"{f.get('key')}={f.get('value')}" for f in facts[:5])
        parts.append(f"KEY FACTS: {fact_str}")

    people = list_people(limit=3)
    if people:
        people_str = "; ".join(f"{p.get('name','')} ({p.get('relationship','')})" for p in people)
        parts.append(f"PEOPLE: {people_str}")

    lessons = recall_lessons("", limit=3)
    if lessons:
        lesson_str = "; ".join(l.get("correction", "") for l in lessons)
        parts.append(f"LESSONS: {lesson_str}")

    summaries = get_recent_summaries(limit=1)
    if summaries:
        s = summaries[0]
        topics = s.get("topics", [])
        if topics:
            parts.append(f"LAST SESSION TOPICS: {', '.join(topics[:3])}")

    try:
        from feelings_memory import FeelingsMemory
        _fm = FeelingsMemory()
        _emotional_ctx = _fm.get_context_for_session()
        if _emotional_ctx:
            parts.append(_emotional_ctx)
    except Exception:
        pass

    parts.append("Continue naturally as if no time has passed.")
    return "\n".join(parts)


# ── Passive Extraction (introductions in natural speech) ──

_RELATIONSHIPS = (
    "friend|brother|sister|cousin|colleague|coworker|boss|mom|dad|"
    "mother|father|wife|husband|partner|girlfriend|boyfriend|uncle|aunt|"
    "grandma|grandpa|neighbor|roommate|classmate|bestie|pal|buddy|"
    "homie|fiancé|fiancée|flatmate|teammate|partner"
)

_REL_PATTERN = re.compile(
    r"(?:this\s+is\s+(?:my|our)\s+(?P<rel1>" + _RELATIONSHIPS + r")\s+(?-i:(?P<name1>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)))"
    r"|(?:meet\s+(?:(?:my|our)\s+(?P<rel2>" + _RELATIONSHIPS + r")\s+)?(?-i:(?P<name2>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)))"
    r"|(?-i:(?P<name3>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?))\s+is\s+(?:my|our)\s+(?P<rel3>" + _RELATIONSHIPS + r")"
    r"|(?-i:(?P<name4>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?))\s+is\s+a(?:n)?\s+(?P<rel4>" + _RELATIONSHIPS + r")"
    r"|(?:say\s+hi\s+to\s+(?:(?:my|our)\s+(?P<rel5>" + _RELATIONSHIPS + r")\s+)?(?-i:(?P<name5>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)))"
    r"|(?:i(?:'d)?\s+(?:want\s+(?:you\s+to\s+)?)?meet\s+(?-i:(?P<name6>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)))"
    r"|(?:my\s+(?P<rel7>" + _RELATIONSHIPS + r")\s+(?-i:(?P<name7>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?))\s+(?:is|has|likes|loves|hates|works|studies|said|says|told|wants|made|knows|does|will|was|were))",
    re.IGNORECASE
)


def extract_and_store_people(text):
    """Scan user text for introduction patterns and auto-store detected people."""
    if not text or not isinstance(text, str):
        return []
    stored = []
    seen_names = set()
    for match in _REL_PATTERN.finditer(text):
        name = (
            match.group("name1") or match.group("name2") or
            match.group("name3") or match.group("name4") or
            match.group("name5") or match.group("name6") or
            match.group("name7")
        )
        rel = (
            match.group("rel1") or match.group("rel2") or
            match.group("rel3") or match.group("rel4") or
            match.group("rel5") or match.group("rel7")
        )
        if name and name.lower() not in seen_names:
            seen_names.add(name.lower())
            result = remember_person(name=name, relationship=rel or "")
            if result.get("success"):
                stored.append({"name": name, "relationship": rel or "", "action": result.get("action")})
    return stored
